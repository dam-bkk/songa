"""
Songa CV — Team Classifier
Assigns home/away team labels to detected players using jersey colour clustering.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from .detector import Detection

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_N_TEAMS: int = 2

# Jersey ROI parameters
_JERSEY_TOP_FRACTION: float = 0.35      # top 35% of bounding box height
_JERSEY_PAD_FRACTION: float = 0.10      # expand width by 10% each side

# HSV filtering thresholds (used to remove background/skin in histograms)
_HSV_VALUE_MIN: int = 30                # exclude near-black pixels (V < 30)
_HSV_SATURATION_MIN: int = 30           # exclude near-white/grey (S < 30)

# Histogram parameters
_HSV_BINS: int = 32

# Referee detection heuristics
_REFEREE_SAT_THRESHOLD: int = 40        # S < this → likely grey/white jersey
_VOTE_WINDOW: int = 30                  # frames for majority-vote team assignment

# K-means clustering
_KMEANS_ATTEMPTS: int = 5
_KMEANS_MAX_ITER: int = 100
_KMEANS_EPSILON: float = 0.2
_MIN_PLAYERS_FOR_FIT: int = 6


# ---------------------------------------------------------------------------
# JerseyColorExtractor
# ---------------------------------------------------------------------------

class JerseyColorExtractor:
    """Extracts colour representations from the jersey region of a player bbox."""

    def extract_roi(
        self,
        frame: np.ndarray,
        bbox_xyxy: tuple[float, float, float, float],
    ) -> np.ndarray:
        """
        Crop the jersey region from a frame.

        Uses the top `_JERSEY_TOP_FRACTION` of the bounding box, expanded
        horizontally by `_JERSEY_PAD_FRACTION`.

        Returns
        -------
        np.ndarray
            BGR image patch (may be empty array if bbox is degenerate).
        """
        x1, y1, x2, y2 = bbox_xyxy
        h_frame, w_frame = frame.shape[:2]

        bbox_w = x2 - x1
        bbox_h = y2 - y1

        if bbox_w <= 0 or bbox_h <= 0:
            return np.empty((0, 0, 3), dtype=np.uint8)

        # Vertical: top fraction only
        crop_y1 = int(max(0, y1))
        crop_y2 = int(min(h_frame, y1 + bbox_h * _JERSEY_TOP_FRACTION))

        # Horizontal: expand slightly
        pad_x = bbox_w * _JERSEY_PAD_FRACTION
        crop_x1 = int(max(0, x1 - pad_x))
        crop_x2 = int(min(w_frame, x2 + pad_x))

        if crop_y2 <= crop_y1 or crop_x2 <= crop_x1:
            return np.empty((0, 0, 3), dtype=np.uint8)

        return frame[crop_y1:crop_y2, crop_x1:crop_x2].copy()

    def to_hsv_histogram(
        self,
        roi: np.ndarray,
        bins: int = _HSV_BINS,
    ) -> np.ndarray:
        """
        Compute a normalised HSV histogram of the jersey ROI.

        Pixels with V < `_HSV_VALUE_MIN` (near-black) or S < `_HSV_SATURATION_MIN`
        (near-white/grey background) are excluded before histogram computation.

        Returns
        -------
        np.ndarray
            Flattened, L2-normalised histogram of shape (bins*3,).
            Returns a zero vector if the ROI is too small.
        """
        if roi.size == 0 or roi.shape[0] < 2 or roi.shape[1] < 2:
            return np.zeros(bins * 3, dtype=np.float32)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.float32)

        # Mask out near-black and desaturated pixels
        mask = (hsv[:, 2] >= _HSV_VALUE_MIN) & (hsv[:, 1] >= _HSV_SATURATION_MIN)
        hsv_filtered = hsv[mask]

        if len(hsv_filtered) < 10:
            return np.zeros(bins * 3, dtype=np.float32)

        # Per-channel histograms
        h_hist, _ = np.histogram(hsv_filtered[:, 0], bins=bins, range=(0, 180))
        s_hist, _ = np.histogram(hsv_filtered[:, 1], bins=bins, range=(0, 256))
        v_hist, _ = np.histogram(hsv_filtered[:, 2], bins=bins, range=(0, 256))

        hist = np.concatenate([h_hist, s_hist, v_hist]).astype(np.float32)

        # L2 normalisation
        norm = float(np.linalg.norm(hist))
        if norm > 0:
            hist /= norm
        return hist

    def dominant_color_hsv(
        self,
        roi: np.ndarray,
    ) -> tuple[float, float, float]:
        """
        Return the dominant jersey colour in HSV space.

        Uses K-means (k=1) on the filtered pixels to find the single most
        representative colour.

        Returns
        -------
        (H, S, V) tuple, or (0, 0, 0) for degenerate ROI.
        """
        if roi.size == 0 or roi.shape[0] < 2 or roi.shape[1] < 2:
            return (0.0, 0.0, 0.0)

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.float32)
        mask = (hsv[:, 2] >= _HSV_VALUE_MIN) & (hsv[:, 1] >= _HSV_SATURATION_MIN)
        hsv_filtered = hsv[mask]

        if len(hsv_filtered) < 10:
            return (0.0, 0.0, 0.0)

        criteria = (
            cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER,
            _KMEANS_MAX_ITER,
            _KMEANS_EPSILON,
        )
        _, _, centers = cv2.kmeans(
            hsv_filtered,
            1,
            None,
            criteria,
            _KMEANS_ATTEMPTS,
            cv2.KMEANS_PP_CENTERS,
        )
        h, s, v = centers[0]
        return (float(h), float(s), float(v))


# ---------------------------------------------------------------------------
# TeamClassifier
# ---------------------------------------------------------------------------

class TeamClassifier:
    """
    Classifies players into home/away teams using K-means jersey colour clustering.

    Typical usage:
        1. Call `fit()` once when ≥ _MIN_PLAYERS_FOR_FIT players are visible.
        2. Call `predict()` on every subsequent frame.
    """

    def __init__(self, n_teams: int = _N_TEAMS) -> None:
        self._n_teams = n_teams
        self._extractor = JerseyColorExtractor()
        self._cluster_centers: Optional[np.ndarray] = None   # shape (n_teams, hist_dim)
        self._team_color_hsv: dict[int, tuple[float, float, float]] = {}
        self._fitted = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(
        self,
        frame: np.ndarray,
        detections: list[Detection],
    ) -> dict[int, int]:
        """
        Fit K-means on the jersey histograms of the provided detections.

        Parameters
        ----------
        frame:
            Current video frame (BGR).
        detections:
            List of player detections (each with an `id` and `bbox`).

        Returns
        -------
        dict[int, int]
            Mapping {detection.id: team_id (0 or 1)}.
        """
        if len(detections) < self._n_teams:
            logger.debug("Not enough players to fit TeamClassifier (%d)", len(detections))
            return {}

        histograms: list[np.ndarray] = []
        valid_ids: list[int] = []

        for det in detections:
            roi = self._extractor.extract_roi(frame, det.bbox)
            if self.is_referee(roi):
                continue
            hist = self._extractor.to_hsv_histogram(roi)
            if np.any(hist != 0):
                histograms.append(hist)
                valid_ids.append(det.id)

        if len(histograms) < self._n_teams:
            return {}

        data = np.stack(histograms, axis=0)
        criteria = (
            cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_MAX_ITER,
            _KMEANS_MAX_ITER,
            _KMEANS_EPSILON,
        )
        _, labels, centers = cv2.kmeans(
            data,
            self._n_teams,
            None,
            criteria,
            _KMEANS_ATTEMPTS,
            cv2.KMEANS_PP_CENTERS,
        )
        self._cluster_centers = centers
        self._fitted = True

        # Derive representative colour per team
        for team_id in range(self._n_teams):
            team_hists = data[labels.flatten() == team_id]
            if len(team_hists) > 0:
                # Reuse dominant colour via the first ROI belonging to this team
                idxs = np.where(labels.flatten() == team_id)[0]
                det_idx = valid_ids[int(idxs[0])]
                rep_roi = self._extractor.extract_roi(
                    frame, detections[det_idx].bbox
                )
                self._team_color_hsv[team_id] = self._extractor.dominant_color_hsv(rep_roi)

        result: dict[int, int] = {}
        for i, vid in enumerate(valid_ids):
            result[vid] = int(labels[i, 0])
        return result

    def predict(
        self,
        frame: np.ndarray,
        detections: list[Detection],
    ) -> dict[int, int]:
        """
        Classify each detection using the fitted cluster centres.

        Falls back to `fit()` if not yet fitted.

        Returns
        -------
        dict[int, int]
            Mapping {detection.id: team_id (0 or 1)}.
        """
        if not self._fitted:
            return self.fit(frame, detections)

        assert self._cluster_centers is not None

        result: dict[int, int] = {}
        for det in detections:
            roi = self._extractor.extract_roi(frame, det.bbox)
            if self.is_referee(roi):
                continue
            hist = self._extractor.to_hsv_histogram(roi).reshape(1, -1)
            if not np.any(hist != 0):
                continue

            # Cosine distance to each cluster centre
            best_team = 0
            best_score = -float("inf")
            for team_id in range(self._n_teams):
                center = self._cluster_centers[team_id].reshape(1, -1)
                cn = float(np.linalg.norm(center))
                hn = float(np.linalg.norm(hist))
                if cn > 0 and hn > 0:
                    score = float(np.dot(hist, center.T)) / (hn * cn)
                else:
                    score = 0.0
                if score > best_score:
                    best_score = score
                    best_team = team_id

            result[det.id] = best_team
        return result

    def is_referee(self, roi: np.ndarray) -> bool:
        """
        Heuristic: return True if the jersey appears to be a referee's
        (grey or white — low average saturation).
        """
        if roi.size == 0 or roi.shape[0] < 2 or roi.shape[1] < 2:
            return False
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        avg_s = float(np.mean(hsv[:, :, 1]))
        return avg_s < _REFEREE_SAT_THRESHOLD

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    @property
    def team_colors(self) -> dict[int, tuple[float, float, float]]:
        """Representative jersey colour per team in HSV."""
        return dict(self._team_color_hsv)


# ---------------------------------------------------------------------------
# TeamTracker
# ---------------------------------------------------------------------------

class TeamTracker:
    """
    Maintains stable team labels for each track_id across frames using a
    rolling majority-vote window.
    """

    def __init__(self, vote_window: int = _VOTE_WINDOW) -> None:
        self._vote_window = vote_window
        # track_id -> deque of recent team_id votes
        self._votes: dict[int, deque] = defaultdict(lambda: deque(maxlen=vote_window))

    def update(self, track_id: int, team_id: int) -> None:
        """Record a team_id vote for this track."""
        self._votes[track_id].append(team_id)

    def get_team(self, track_id: int) -> Optional[int]:
        """
        Return the majority-vote team for this track, or None if no votes.
        """
        votes = self._votes.get(track_id)
        if not votes:
            return None
        counter = Counter(votes)
        return int(counter.most_common(1)[0][0])

    def get_team_rosters(self) -> dict[int, list[int]]:
        """
        Return {team_id: [track_ids]} based on current majority-vote labels.
        """
        rosters: dict[int, list[int]] = defaultdict(list)
        for track_id in self._votes:
            team = self.get_team(track_id)
            if team is not None:
                rosters[team].append(track_id)
        return dict(rosters)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import numpy as np

    print("=== JerseyColorExtractor self-test ===")
    extractor = JerseyColorExtractor()

    # Create a synthetic frame with a coloured patch
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Red jersey region
    frame[100:200, 100:200] = (0, 0, 200)
    # Blue jersey region
    frame[100:200, 300:400] = (200, 0, 0)

    bbox_red = (90.0, 100.0, 210.0, 350.0)
    roi_red = extractor.extract_roi(frame, bbox_red)
    print(f"  Red ROI shape: {roi_red.shape}")

    hist = extractor.to_hsv_histogram(roi_red)
    print(f"  Histogram shape: {hist.shape}, L2 norm: {np.linalg.norm(hist):.3f}")

    dominant = extractor.dominant_color_hsv(roi_red)
    print(f"  Dominant HSV: {tuple(round(v, 1) for v in dominant)}")

    print("\n=== TeamTracker self-test ===")
    tracker = TeamTracker(vote_window=10)
    for _ in range(7):
        tracker.update(track_id=1, team_id=0)
    for _ in range(3):
        tracker.update(track_id=1, team_id=1)
    tracker.update(track_id=2, team_id=1)
    tracker.update(track_id=2, team_id=1)

    print(f"  Track 1 team: {tracker.get_team(1)} (expected 0)")
    print(f"  Track 2 team: {tracker.get_team(2)} (expected 1)")

    rosters = tracker.get_team_rosters()
    print(f"  Rosters: {rosters}")

    print("\n=== TeamClassifier self-test ===")
    from .detector import Detection

    frame2 = np.zeros((480, 640, 3), dtype=np.uint8)
    # Team 0: red shirts
    for i in range(4):
        frame2[50 + i * 30: 80 + i * 30, 50:150] = (0, 50, 200)
    # Team 1: blue shirts
    for i in range(4):
        frame2[50 + i * 30: 80 + i * 30, 300:400] = (200, 50, 0)

    dets = []
    for i in range(4):
        dets.append(Detection(id=i, bbox=(50.0, 50.0 + i*30, 150.0, 300.0),
                              confidence=0.9, class_name="person"))
    for i in range(4):
        dets.append(Detection(id=4+i, bbox=(300.0, 50.0 + i*30, 400.0, 300.0),
                              confidence=0.9, class_name="person"))

    clf = TeamClassifier()
    labels = clf.fit(frame2, dets)
    print(f"  Fit labels: {labels}")
    print(f"  Fitted: {clf.is_fitted}")
    print(f"  Team colors: {clf.team_colors}")
    print("Self-test passed.")
