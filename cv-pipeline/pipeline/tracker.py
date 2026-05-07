"""
Songa CV — Tracker
Multi-object tracking using ByteTrack via supervision.
Integrates Kalman ball tracking, appearance-based ReID, and team classification.
"""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .detector import Detection, DetectionResult

logger = logging.getLogger(__name__)

_TRAJECTORY_LEN = 30            # number of past positions to keep per player
_BALL_MAX_PREDICT_FRAMES = 15   # max consecutive Kalman-only frames before giving up
_TEAM_FIT_MIN_PLAYERS = 6       # minimum detections to trigger TeamClassifier.fit
_TEAM_PREDICT_INTERVAL = 30     # call TeamClassifier.predict every N frames


@dataclass
class TrackedPlayer:
    """A player with a stable track ID across frames."""
    track_id: int
    bbox: tuple[float, float, float, float]  # xyxy
    confidence: float
    trajectory: list[tuple[float, float]] = field(default_factory=list)

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)


@dataclass
class TrackedObject:
    """A tracked non-player object (ball)."""
    track_id: int
    bbox: tuple[float, float, float, float]
    confidence: float
    trajectory: list[tuple[float, float]] = field(default_factory=list)

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)


@dataclass
class TrackedFrame:
    """All tracked objects for a single frame."""
    tracked_players: list[TrackedPlayer] = field(default_factory=list)
    tracked_ball: Optional[TrackedObject] = None
    frame_id: int = 0
    # Kalman filter state for the ball: [x, y, vx, vy, ax, ay] or None
    ball_kalman_state: Optional[np.ndarray] = None
    # Team labels for each tracked player: {track_id: team_id}
    team_labels: dict[int, int] = field(default_factory=dict)


class Tracker:
    """
    Wraps supervision.ByteTrack to assign stable IDs to players and the ball.

    Maintains per-ID trajectory history (last _TRAJECTORY_LEN positions).
    Falls back to a simple nearest-neighbour tracker if supervision is unavailable.

    Additional subsystems:
    - BallKalmanFilter : 6-state Kalman filter for smooth ball tracking /
      prediction during occlusion (up to _BALL_MAX_PREDICT_FRAMES frames).
    - ReIDDatabase + FeatureExtractor : re-identifies players whose tracks
      were dropped by ByteTrack and re-links them to the original track ID.
    - TeamClassifier + TeamTracker : clusters jersey colours into home / away
      and maintains a stable majority-vote team label per track ID.
    """

    def __init__(self) -> None:
        self._byte_track = self._init_bytetrack()
        # trajectory history: track_id -> deque of (cx, cy)
        self._trajectories: dict[int, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=_TRAJECTORY_LEN)
        )
        # Simple fallback state
        self._next_id = 1
        self._prev_players: list[dict] = []
        self._ball_track_id = 0
        self._frame_id = 0

        # --- Kalman ball filter ---
        from .kalman import BallKalmanFilter, BallTrajectoryBuffer
        self._ball_kf = BallKalmanFilter()
        self._ball_traj_buf = BallTrajectoryBuffer()
        self._ball_predict_streak = 0   # consecutive predict-only frames

        # --- ReID ---
        from .reid import ReIDDatabase, FeatureExtractor
        self._reid_db = ReIDDatabase()
        self._feat_extractor = FeatureExtractor()
        # track_ids active in the previous frame (for detecting dropped tracks)
        self._prev_active_ids: set[int] = set()
        # canonical ID mapping: short-lived new_id -> original old_id
        self._id_remap: dict[int, int] = {}

        # --- Team classification ---
        from .team import TeamClassifier, TeamTracker
        self._team_clf = TeamClassifier()
        self._team_tracker = TeamTracker()
        self._team_fit_done = False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_bytetrack(self):
        try:
            import supervision as sv  # type: ignore
            return sv.ByteTrack()
        except ImportError:
            logger.warning(
                "supervision not installed — using fallback tracker. "
                "Install with: pip install supervision>=0.24.0"
            )
            return None
        except Exception as exc:
            logger.warning("ByteTrack init failed (%s) — using fallback tracker.", exc)
            return None

    def _update_trajectory(
        self, track_id: int, center: tuple[float, float]
    ) -> list[tuple[float, float]]:
        self._trajectories[track_id].append(center)
        return list(self._trajectories[track_id])

    def _apply_id_remap(self, track_id: int) -> int:
        """Follow the remap chain to get the canonical (original) track ID."""
        seen: set[int] = set()
        current = track_id
        while current in self._id_remap and current not in seen:
            seen.add(current)
            current = self._id_remap[current]
        return current

    # ------------------------------------------------------------------
    # Ball Kalman integration
    # ------------------------------------------------------------------

    def _update_ball_kalman(
        self, ball: Optional[Detection]
    ) -> tuple[Optional[TrackedObject], Optional[np.ndarray]]:
        """
        Update the Kalman filter with the current ball detection (or predict
        if occluded).

        Returns
        -------
        (tracked_ball, kalman_state):
            tracked_ball — the TrackedObject to put in TrackedFrame (may be
                           a Kalman prediction if YOLO missed the ball).
            kalman_state — raw 6-D state vector [x, y, vx, vy, ax, ay].
        """
        if ball is not None:
            # Observed frame: update Kalman
            cx, cy = ball.center
            if not self._ball_kf.is_initialized:
                self._ball_kf.reset(cx, cy)
            kalman_state = self._ball_kf.update((cx, cy))
            self._ball_predict_streak = 0

            # Push to trajectory buffer (real observation)
            self._ball_traj_buf.push(cx, cy, self._frame_id, is_predicted=False)

            traj = self._update_trajectory(self._ball_track_id, (cx, cy))
            tracked = TrackedObject(
                track_id=self._ball_track_id,
                bbox=ball.bbox,
                confidence=ball.confidence,
                trajectory=traj,
            )
            return tracked, kalman_state

        # Ball not detected this frame
        if (
            self._ball_kf.is_initialized
            and self._ball_predict_streak < _BALL_MAX_PREDICT_FRAMES
        ):
            # Kalman prediction during occlusion
            px, py = self._ball_kf.predict_only()
            self._ball_predict_streak += 1

            # Push predicted position to buffer
            self._ball_traj_buf.push(px, py, self._frame_id, is_predicted=True)

            # Synthesise a minimal TrackedObject from the prediction
            half = 15.0
            synthetic_bbox = (px - half, py - half, px + half, py + half)
            traj = self._update_trajectory(self._ball_track_id, (px, py))
            tracked = TrackedObject(
                track_id=self._ball_track_id,
                bbox=synthetic_bbox,
                confidence=0.0,    # 0 confidence signals predicted (not detected)
                trajectory=traj,
            )
            # Get the latest state after prediction
            state = self._ball_kf._kf.statePre.flatten()
            return tracked, state

        # Too many consecutive missed frames — give up
        return None, None

    # ------------------------------------------------------------------
    # ReID integration
    # ------------------------------------------------------------------

    def _update_reid(
        self, players: list[TrackedPlayer], frame: np.ndarray
    ) -> list[TrackedPlayer]:
        """
        Register active tracks, detect dropped tracks, attempt re-id, and
        remap track IDs where a match is found.

        Returns players with canonical (remapped) track IDs.
        """
        current_ids: set[int] = {p.track_id for p in players}

        # Detect dropped tracks (were active last frame, now gone)
        dropped_ids = self._prev_active_ids - current_ids
        for dropped_id in dropped_ids:
            self._reid_db.mark_lost(dropped_id, self._frame_id)

        # Register / update all currently active tracks
        for p in players:
            try:
                feat = self._feat_extractor.extract(frame, p.bbox)
                self._reid_db.register(p.track_id, feat, self._frame_id)
            except Exception as exc:
                logger.debug("Feature extraction failed for track %d: %s", p.track_id, exc)

        # For genuinely new track IDs (not in prev active), try to match
        new_ids = current_ids - self._prev_active_ids
        remapped: dict[int, int] = {}
        for new_id in new_ids:
            player = next((p for p in players if p.track_id == new_id), None)
            if player is None:
                continue
            try:
                feat = self._feat_extractor.extract(frame, player.bbox)
                matched_id = self._reid_db.find_match(feat, self._frame_id)
                if matched_id is not None and matched_id != new_id:
                    self._reid_db.reactivate(old_track_id=matched_id,
                                              new_track_id=new_id)
                    self._id_remap[new_id] = matched_id
                    remapped[new_id] = matched_id
                    logger.debug(
                        "ReID: new track %d reassigned to %d", new_id, matched_id
                    )
            except Exception as exc:
                logger.debug("ReID failed for track %d: %s", new_id, exc)

        # Apply ID remapping and rebuild trajectories under canonical IDs
        remapped_players: list[TrackedPlayer] = []
        for p in players:
            canonical_id = self._apply_id_remap(p.track_id)
            if canonical_id != p.track_id:
                # Merge trajectory history into canonical ID
                if p.track_id in self._trajectories:
                    old_traj = self._trajectories[p.track_id]
                    self._trajectories[canonical_id].extend(old_traj)
                traj = self._update_trajectory(canonical_id, p.center)
                remapped_players.append(
                    TrackedPlayer(
                        track_id=canonical_id,
                        bbox=p.bbox,
                        confidence=p.confidence,
                        trajectory=traj,
                    )
                )
            else:
                remapped_players.append(p)

        self._prev_active_ids = {p.track_id for p in remapped_players}

        # Periodic database cleanup
        if self._frame_id % 150 == 0:
            self._reid_db.purge_old(self._frame_id)

        return remapped_players

    # ------------------------------------------------------------------
    # Team classification integration
    # ------------------------------------------------------------------

    def _update_teams(
        self,
        players: list[TrackedPlayer],
        detections: DetectionResult,
        frame: np.ndarray,
    ) -> dict[int, int]:
        """
        Run team classification and update TeamTracker.

        Returns
        -------
        dict[int, int]
            {track_id: team_id} for all players with a known team.
        """
        team_labels: dict[int, int] = {}

        # Build a player_detection list that maps track_id → Detection
        # We use the positions of tracked players to create synthetic Detections
        # for the classifier, keyed by track index.
        synthetic_dets: list[Detection] = []
        idx_to_tid: dict[int, int] = {}
        for i, p in enumerate(players):
            idx_to_tid[i] = p.track_id
            synthetic_dets.append(
                Detection(
                    id=i,
                    bbox=p.bbox,
                    confidence=p.confidence,
                    class_name="person",
                )
            )

        # Fit on the first frame with enough players
        if (
            not self._team_fit_done
            and len(synthetic_dets) >= _TEAM_FIT_MIN_PLAYERS
        ):
            try:
                fit_result = self._team_clf.fit(frame, synthetic_dets)
                if fit_result:
                    self._team_fit_done = True
                    logger.debug(
                        "TeamClassifier fitted on frame %d with %d players",
                        self._frame_id,
                        len(synthetic_dets),
                    )
                    for det_idx, team_id in fit_result.items():
                        tid = idx_to_tid.get(det_idx)
                        if tid is not None:
                            self._team_tracker.update(tid, team_id)
            except Exception as exc:
                logger.debug("TeamClassifier.fit failed: %s", exc)

        # Predict every _TEAM_PREDICT_INTERVAL frames (after fitting)
        elif (
            self._team_fit_done
            and self._frame_id % _TEAM_PREDICT_INTERVAL == 0
            and synthetic_dets
        ):
            try:
                pred_result = self._team_clf.predict(frame, synthetic_dets)
                for det_idx, team_id in pred_result.items():
                    tid = idx_to_tid.get(det_idx)
                    if tid is not None:
                        self._team_tracker.update(tid, team_id)
            except Exception as exc:
                logger.debug("TeamClassifier.predict failed: %s", exc)

        # Collect majority-vote team labels
        for p in players:
            label = self._team_tracker.get_team(p.track_id)
            if label is not None:
                team_labels[p.track_id] = label

        return team_labels

    # ------------------------------------------------------------------
    # ByteTrack path
    # ------------------------------------------------------------------

    def _update_bytetrack(
        self, detections: DetectionResult, frame: np.ndarray
    ) -> TrackedFrame:
        import supervision as sv  # type: ignore

        tracked_ball, kalman_state = self._update_ball_kalman(detections.ball)

        if not detections.players:
            return TrackedFrame(
                tracked_ball=tracked_ball,
                frame_id=self._frame_id,
                ball_kalman_state=kalman_state,
            )

        # Build supervision Detections object for players only
        bboxes = np.array([list(d.bbox) for d in detections.players], dtype=np.float32)
        confs = np.array([d.confidence for d in detections.players], dtype=np.float32)
        class_ids = np.zeros(len(detections.players), dtype=int)

        sv_dets = sv.Detections(
            xyxy=bboxes,
            confidence=confs,
            class_id=class_ids,
        )

        tracked = self._byte_track.update_with_detections(sv_dets)

        players: list[TrackedPlayer] = []
        for i in range(len(tracked)):
            tid = int(tracked.tracker_id[i])
            bbox = tuple(float(v) for v in tracked.xyxy[i])  # type: ignore
            conf = float(tracked.confidence[i]) if tracked.confidence is not None else 0.5
            traj = self._update_trajectory(tid, (
                (bbox[0] + bbox[2]) / 2,
                (bbox[1] + bbox[3]) / 2,
            ))
            players.append(
                TrackedPlayer(track_id=tid, bbox=bbox, confidence=conf, trajectory=traj)
            )

        # ReID pass
        players = self._update_reid(players, frame)

        # Team classification pass
        team_labels = self._update_teams(players, detections, frame)

        return TrackedFrame(
            tracked_players=players,
            tracked_ball=tracked_ball,
            frame_id=self._frame_id,
            ball_kalman_state=kalman_state,
            team_labels=team_labels,
        )

    # ------------------------------------------------------------------
    # Fallback nearest-neighbour tracker
    # ------------------------------------------------------------------

    def _update_fallback(
        self, detections: DetectionResult, frame: np.ndarray
    ) -> TrackedFrame:
        current_centers = [d.center for d in detections.players]
        prev_centers = [p["center"] for p in self._prev_players]

        assigned: dict[int, int] = {}  # current_idx -> track_id

        if prev_centers and current_centers:
            # Simple greedy nearest-neighbour assignment
            used_prev: set[int] = set()
            for ci, cc in enumerate(current_centers):
                best_dist = float("inf")
                best_pi = -1
                for pi, pc in enumerate(prev_centers):
                    if pi in used_prev:
                        continue
                    dist = np.hypot(cc[0] - pc[0], cc[1] - pc[1])
                    if dist < best_dist:
                        best_dist = dist
                        best_pi = pi
                if best_pi != -1 and best_dist < 150:
                    assigned[ci] = self._prev_players[best_pi]["id"]
                    used_prev.add(best_pi)

        players: list[TrackedPlayer] = []
        new_prev: list[dict] = []
        for ci, det in enumerate(detections.players):
            tid = assigned.get(ci, self._next_id)
            if ci not in assigned:
                self._next_id += 1
            traj = self._update_trajectory(tid, det.center)
            players.append(
                TrackedPlayer(
                    track_id=tid,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    trajectory=traj,
                )
            )
            new_prev.append({"id": tid, "center": det.center})

        self._prev_players = new_prev

        # ReID + team classification (also run in fallback mode)
        players = self._update_reid(players, frame)
        team_labels = self._update_teams(players, detections, frame)

        tracked_ball, kalman_state = self._update_ball_kalman(detections.ball)

        return TrackedFrame(
            tracked_players=players,
            tracked_ball=tracked_ball,
            frame_id=self._frame_id,
            ball_kalman_state=kalman_state,
            team_labels=team_labels,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, detections: DetectionResult, frame: np.ndarray) -> TrackedFrame:
        """
        Update tracker with new detections.

        Returns a TrackedFrame with stable track IDs, per-player trajectories,
        Kalman ball state, and team labels.
        """
        self._frame_id += 1
        if self._byte_track is not None:
            return self._update_bytetrack(detections, frame)
        return self._update_fallback(detections, frame)

    def get_trajectories(self) -> dict[int, list[tuple[float, float]]]:
        """Return the full trajectory history keyed by track ID."""
        return {tid: list(traj) for tid, traj in self._trajectories.items()}
