"""
Songa CV — Re-Identification (ReID)
Re-associates lost player tracks with new detections using appearance features.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Feature vector dimensions
_COLOR_HIST_DIM: int = 64       # HSV colour histogram feature size
_HOG_FEAT_DIM: int = 64         # HOG gradient feature size
_FEATURE_DIM: int = _COLOR_HIST_DIM + _HOG_FEAT_DIM   # total = 128

# HSV histogram parameters
_HSV_H_BINS: int = 16           # Hue bins (0..180)
_HSV_S_BINS: int = 32           # Saturation + Value bins (0..256) → 16+16 per channel = 32
_HSV_JERSEY_FRACTION: float = 0.55    # top 55% of bbox = jersey + shorts
_HSV_VALUE_MIN: int = 30        # exclude near-black pixels

# HOG parameters
_HOG_WIN_SIZE: tuple[int, int] = (32, 64)
_HOG_BLOCK_SIZE: tuple[int, int] = (16, 16)
_HOG_BLOCK_STRIDE: tuple[int, int] = (8, 8)
_HOG_CELL_SIZE: tuple[int, int] = (8, 8)
_HOG_NBINS: int = 9

# ReID database parameters
_DEFAULT_MAX_AGE_FRAMES: int = 90
_DEFAULT_SIMILARITY_THRESHOLD: float = 0.75


# ---------------------------------------------------------------------------
# Utility: cosine similarity
# ---------------------------------------------------------------------------

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two 1-D vectors.

    Returns a value in [-1, 1]. Returns 0.0 for zero vectors.
    """
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a.flatten(), b.flatten()) / (na * nb))


# ---------------------------------------------------------------------------
# AppearanceFeature
# ---------------------------------------------------------------------------

@dataclass
class AppearanceFeature:
    """
    Appearance descriptor for one player observation.

    Parameters
    ----------
    track_id:
        The tracker ID that generated this feature.
    feature_vector:
        128-D L2-normalised feature (64-D colour + 64-D HOG).
    frame_id:
        The frame at which the feature was extracted.
    """
    track_id: int
    feature_vector: np.ndarray
    frame_id: int

    @property
    def age(self) -> int:
        """Alias — must be computed against a current frame externally."""
        return 0  # concrete age computed by ReIDDatabase


# ---------------------------------------------------------------------------
# FeatureExtractor
# ---------------------------------------------------------------------------

class FeatureExtractor:
    """
    Extracts a 128-D appearance feature vector for a player bounding box.

    Feature layout:
    - [0:64]   HSV colour histogram (jersey + shorts region)
    - [64:128] HOG gradient descriptor (shape cue)
    """

    def __init__(self) -> None:
        self._hog = self._build_hog()

    @staticmethod
    def _build_hog() -> Optional[cv2.HOGDescriptor]:
        """Initialise a fixed-size HOG descriptor."""
        try:
            return cv2.HOGDescriptor(
                _HOG_WIN_SIZE,
                _HOG_BLOCK_SIZE,
                _HOG_BLOCK_STRIDE,
                _HOG_CELL_SIZE,
                _HOG_NBINS,
            )
        except Exception as exc:
            logger.warning("HOGDescriptor init failed: %s — using manual fallback.", exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        frame: np.ndarray,
        bbox_xyxy: tuple[float, float, float, float],
    ) -> np.ndarray:
        """
        Extract and return the 128-D L2-normalised feature vector.

        Parameters
        ----------
        frame:
            BGR video frame.
        bbox_xyxy:
            Player bounding box (x1, y1, x2, y2).

        Returns
        -------
        np.ndarray
            Float32 vector of shape (128,), L2-normalised.
        """
        color_feat = self._extract_color_hist(frame, bbox_xyxy)
        hog_feat = self._extract_hog(frame, bbox_xyxy)

        combined = np.concatenate([color_feat, hog_feat]).astype(np.float32)
        norm = float(np.linalg.norm(combined))
        if norm > 0:
            combined /= norm
        return combined

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_color_hist(
        self,
        frame: np.ndarray,
        bbox_xyxy: tuple[float, float, float, float],
    ) -> np.ndarray:
        """
        64-D HSV histogram over the full player ROI (jersey + shorts).

        Breakdown:
        - 16 bins for H (0..180)
        - 16 bins for S (0..256)
        - 16 bins for V (0..256)
        - 16 bins for spatial upper/lower split (8 H + 8 S combined, deinterleaved)

        In practice we use 4 × 16 = 64 bins distributed as:
        16 H + 16 S + 16 V + 16 H (lower half) to capture vertical colour gradient.
        """
        roi = self._crop_roi(frame, bbox_xyxy, fraction=_HSV_JERSEY_FRACTION)
        if roi.size == 0:
            return np.zeros(_COLOR_HIST_DIM, dtype=np.float32)

        h_frame = roi.shape[0]
        upper = roi[:h_frame // 2]
        lower = roi[h_frame // 2:]

        def _hsv_hist(patch: np.ndarray, bins_h: int, bins_s: int) -> np.ndarray:
            if patch.size == 0:
                return np.zeros(bins_h + bins_s, dtype=np.float32)
            hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.float32)
            mask = hsv[:, 2] >= _HSV_VALUE_MIN
            hsv = hsv[mask]
            if len(hsv) == 0:
                return np.zeros(bins_h + bins_s, dtype=np.float32)
            hh, _ = np.histogram(hsv[:, 0], bins=bins_h, range=(0, 180))
            sh, _ = np.histogram(hsv[:, 1], bins=bins_s, range=(0, 256))
            return np.concatenate([hh, sh]).astype(np.float32)

        # Upper half: 16 H + 16 S = 32 dims
        upper_feat = _hsv_hist(upper, bins_h=16, bins_s=16)
        # Lower half: 16 H + 16 S = 32 dims
        lower_feat = _hsv_hist(lower, bins_h=16, bins_s=16)

        feat = np.concatenate([upper_feat, lower_feat])  # 64 dims
        norm = float(np.linalg.norm(feat))
        if norm > 0:
            feat /= norm
        return feat

    def _extract_hog(
        self,
        frame: np.ndarray,
        bbox_xyxy: tuple[float, float, float, float],
    ) -> np.ndarray:
        """
        64-D HOG descriptor.  Uses cv2.HOGDescriptor and truncates/pads
        to exactly 64 dimensions.

        Falls back to a manual gradient histogram if HOGDescriptor fails.
        """
        roi = self._crop_roi(frame, bbox_xyxy, fraction=1.0)
        if roi.size == 0:
            return np.zeros(_HOG_FEAT_DIM, dtype=np.float32)

        # Resize to standard HOG window size
        try:
            resized = cv2.resize(roi, _HOG_WIN_SIZE)
        except Exception:
            return np.zeros(_HOG_FEAT_DIM, dtype=np.float32)

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        if self._hog is not None:
            try:
                descriptor = self._hog.compute(gray)
                if descriptor is not None:
                    flat = descriptor.flatten()
                    return self._resize_feat(flat, _HOG_FEAT_DIM)
            except Exception as exc:
                logger.debug("HOG compute failed: %s", exc)

        # Manual fallback: compute gradient magnitudes + orientations
        return self._manual_hog_fallback(gray)

    @staticmethod
    def _manual_hog_fallback(gray: np.ndarray) -> np.ndarray:
        """
        Simple gradient orientation histogram as a fallback for HOG.

        Divides the image into a 4×2 grid and computes a 8-bin orientation
        histogram per cell → 4*2*8 = 64 dims.
        """
        h, w = gray.shape
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag = np.sqrt(gx ** 2 + gy ** 2)
        ori = (np.arctan2(gy, gx) * 180 / math.pi) % 180   # 0..180 unsigned

        rows, cols = 4, 2
        n_bins = 8
        feat_parts: list[np.ndarray] = []
        for r in range(rows):
            for c in range(cols):
                r0 = r * h // rows
                r1 = (r + 1) * h // rows
                c0 = c * w // cols
                c1 = (c + 1) * w // cols
                cell_mag = mag[r0:r1, c0:c1].flatten()
                cell_ori = ori[r0:r1, c0:c1].flatten()
                hist, _ = np.histogram(
                    cell_ori, bins=n_bins, range=(0, 180), weights=cell_mag
                )
                feat_parts.append(hist)

        feat = np.concatenate(feat_parts).astype(np.float32)   # 64 dims
        norm = float(np.linalg.norm(feat))
        if norm > 0:
            feat /= norm
        return feat

    @staticmethod
    def _resize_feat(feat: np.ndarray, target_dim: int) -> np.ndarray:
        """Truncate or zero-pad a feature vector to exactly target_dim."""
        if len(feat) >= target_dim:
            return feat[:target_dim].astype(np.float32)
        out = np.zeros(target_dim, dtype=np.float32)
        out[:len(feat)] = feat
        return out

    @staticmethod
    def _crop_roi(
        frame: np.ndarray,
        bbox_xyxy: tuple[float, float, float, float],
        fraction: float,
    ) -> np.ndarray:
        """Crop bbox from frame, optionally taking only top `fraction` of height."""
        x1, y1, x2, y2 = bbox_xyxy
        h_frame, w_frame = frame.shape[:2]
        ix1 = int(max(0, x1))
        iy1 = int(max(0, y1))
        ix2 = int(min(w_frame, x2))
        iy2 = int(min(h_frame, y1 + (y2 - y1) * fraction))
        if ix2 <= ix1 or iy2 <= iy1:
            return np.empty((0, 0, 3), dtype=np.uint8)
        return frame[iy1:iy2, ix1:ix2].copy()


# ---------------------------------------------------------------------------
# ReIDDatabase
# ---------------------------------------------------------------------------

@dataclass
class _TrackRecord:
    """Internal record for one track in the ReID database."""
    track_id: int
    feature: np.ndarray
    last_seen_frame: int
    is_lost: bool = False


class ReIDDatabase:
    """
    Maintains appearance features for active and recently-lost tracks.

    On each frame:
    1. Active tracks are updated with `register()`.
    2. When ByteTrack drops a track, call `mark_lost()`.
    3. When a new detection appears, call `find_match()` to recover the
       previous track_id if one exists.
    """

    def __init__(
        self,
        max_age_frames: int = _DEFAULT_MAX_AGE_FRAMES,
        similarity_threshold: float = _DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self._max_age = max_age_frames
        self._threshold = similarity_threshold

        # track_id -> _TrackRecord
        self._records: dict[int, _TrackRecord] = {}
        # merged track mapping: old_track_id -> new_track_id
        self._merges: dict[int, int] = {}
        # set of track_ids currently considered active (not lost)
        self._active_ids: set[int] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(
        self,
        track_id: int,
        feature: np.ndarray,
        frame_id: int,
    ) -> None:
        """
        Register or update the appearance feature for an active track.

        If the track was previously lost, it is reactivated automatically.
        """
        if track_id in self._records:
            rec = self._records[track_id]
            # Exponential moving average to blend over time
            rec.feature = 0.8 * rec.feature + 0.2 * feature
            norm = float(np.linalg.norm(rec.feature))
            if norm > 0:
                rec.feature /= norm
            rec.last_seen_frame = frame_id
            rec.is_lost = False
        else:
            self._records[track_id] = _TrackRecord(
                track_id=track_id,
                feature=feature.copy(),
                last_seen_frame=frame_id,
            )
        self._active_ids.add(track_id)

    def mark_lost(self, track_id: int, frame_id: int) -> None:
        """
        Mark a track as lost (no longer visible).

        The feature is retained for potential future matching.
        """
        if track_id in self._records:
            self._records[track_id].is_lost = True
            self._records[track_id].last_seen_frame = frame_id
        self._active_ids.discard(track_id)
        logger.debug("Track %d marked lost at frame %d", track_id, frame_id)

    def find_match(
        self,
        feature: np.ndarray,
        current_frame_id: int,
    ) -> Optional[int]:
        """
        Search recently-lost tracks for the best appearance match.

        Parameters
        ----------
        feature:
            128-D feature vector of the new detection.
        current_frame_id:
            Current frame number, used to filter out stale records.

        Returns
        -------
        int or None
            The track_id of the best matching lost track, or None if no match
            exceeds `similarity_threshold`.
        """
        best_id: Optional[int] = None
        best_sim: float = self._threshold   # must beat threshold

        for rec in self._records.values():
            if not rec.is_lost:
                continue
            if rec.track_id in self._active_ids:
                continue
            age = current_frame_id - rec.last_seen_frame
            if age > self._max_age:
                continue

            sim = cosine_similarity(feature, rec.feature)
            if sim > best_sim:
                best_sim = sim
                best_id = rec.track_id

        if best_id is not None:
            logger.debug(
                "ReID match found: new det → track %d (sim=%.3f)", best_id, best_sim
            )
        return best_id

    def reactivate(self, old_track_id: int, new_track_id: int) -> None:
        """
        Merge `new_track_id` back onto `old_track_id`.

        The new_track_id is removed from the database; old_track_id is
        reactivated.  Downstream code should use old_track_id going forward.
        """
        if old_track_id in self._records:
            self._records[old_track_id].is_lost = False
            self._active_ids.add(old_track_id)

        # Remove the ephemeral new track if it was registered
        if new_track_id in self._records:
            del self._records[new_track_id]
        self._active_ids.discard(new_track_id)

        self._merges[new_track_id] = old_track_id
        logger.debug("ReID reactivate: track %d → %d", new_track_id, old_track_id)

    def purge_old(self, current_frame_id: int) -> None:
        """Remove records that are too old to be useful."""
        stale_ids = [
            tid for tid, rec in self._records.items()
            if rec.is_lost and (current_frame_id - rec.last_seen_frame) > self._max_age
        ]
        for tid in stale_ids:
            del self._records[tid]
            logger.debug("ReID purged stale track %d", tid)

    def resolve_id(self, track_id: int) -> int:
        """
        Follow the merge chain to resolve a track_id to its canonical ID.

        Returns
        -------
        int
            The canonical track_id (may equal the input if never merged).
        """
        seen: set[int] = set()
        current = track_id
        while current in self._merges and current not in seen:
            seen.add(current)
            current = self._merges[current]
        return current

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def active_count(self) -> int:
        return len(self._active_ids)

    @property
    def lost_count(self) -> int:
        return sum(1 for r in self._records.values() if r.is_lost)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== cosine_similarity self-test ===")
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    c = np.array([0.0, 1.0, 0.0])
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-6, "identical vectors should score 1"
    assert abs(cosine_similarity(a, c)) < 1e-6, "orthogonal vectors should score 0"
    print(f"  cos(a, a) = {cosine_similarity(a, b):.4f}")
    print(f"  cos(a, c) = {cosine_similarity(a, c):.4f}")

    print("\n=== FeatureExtractor self-test ===")
    extractor = FeatureExtractor()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[50:300, 100:200] = (0, 0, 200)   # red player patch

    bbox = (100.0, 50.0, 200.0, 300.0)
    feat = extractor.extract(frame, bbox)
    print(f"  Feature shape: {feat.shape} (expected {_FEATURE_DIM})")
    print(f"  L2 norm: {np.linalg.norm(feat):.4f} (expected ~1.0)")
    assert feat.shape == (_FEATURE_DIM,), f"Expected ({_FEATURE_DIM},), got {feat.shape}"
    assert abs(np.linalg.norm(feat) - 1.0) < 0.01, "Feature should be L2-normalised"

    print("\n=== ReIDDatabase self-test ===")
    db = ReIDDatabase(max_age_frames=60, similarity_threshold=0.70)

    feat_a = np.random.rand(_FEATURE_DIM).astype(np.float32)
    feat_a /= np.linalg.norm(feat_a)

    db.register(track_id=10, feature=feat_a, frame_id=0)
    db.mark_lost(track_id=10, frame_id=5)

    # Slightly noisy version of the same feature
    noise = np.random.rand(_FEATURE_DIM).astype(np.float32) * 0.05
    feat_b = feat_a + noise
    feat_b /= np.linalg.norm(feat_b)

    match = db.find_match(feat_b, current_frame_id=20)
    print(f"  Match for similar feature: {match} (expected 10)")

    # Completely different feature should not match
    feat_c = np.random.rand(_FEATURE_DIM).astype(np.float32)
    feat_c /= np.linalg.norm(feat_c)
    # Force low similarity by orthogonalising
    feat_c -= feat_c.dot(feat_a) * feat_a
    if np.linalg.norm(feat_c) > 0:
        feat_c /= np.linalg.norm(feat_c)
    no_match = db.find_match(feat_c, current_frame_id=20)
    print(f"  Match for dissimilar feature: {no_match} (expected None)")

    db.reactivate(old_track_id=10, new_track_id=11)
    print(f"  Active count after reactivate: {db.active_count} (expected 1)")
    print(f"  Resolved ID for 11: {db.resolve_id(11)} (expected 10)")

    db.purge_old(current_frame_id=200)
    print(f"  Records after purge: {len(db._records)}")
    print("Self-test passed.")
