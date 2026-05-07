"""
Songa CV — Possession Detector
Determines which team has possession based on ball proximity and velocity.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

# HOME=1, AWAY=2 by convention


class PossessionState(Enum):
    HOME = "home"
    AWAY = "away"
    CONTESTED = "contested"
    DEAD_BALL = "dead_ball"
    UNKNOWN = "unknown"


@dataclass
class PossessionEvent:
    frame_id: int
    state: PossessionState
    player_id: Optional[int]        # player holding the ball (None if dead/unknown)
    team_id: Optional[int]          # team id (None if contested/dead/unknown)
    court_position: Optional[tuple[float, float]]  # metres; None if unavailable
    duration_frames: int            # how long this possession has lasted so far


class PossessionDetector:
    """
    Frame-by-frame possession detector.

    Call update() once per frame; call get_possession_stats() / get_possession_timeline()
    at the end of the clip.
    """

    def __init__(
        self,
        proximity_threshold_px: float = 80.0,
        min_duration_frames: int = 5,
    ) -> None:
        self.proximity_threshold_px = proximity_threshold_px
        self.min_duration_frames = min_duration_frames

        # Temporal smoothing state
        self._candidate_state: PossessionState = PossessionState.UNKNOWN
        self._candidate_player_id: Optional[int] = None
        self._candidate_team_id: Optional[int] = None
        self._candidate_run: int = 0        # how many consecutive frames in candidate state

        # Confirmed (committed) state
        self._current_state: PossessionState = PossessionState.UNKNOWN
        self._current_player_id: Optional[int] = None
        self._current_team_id: Optional[int] = None
        self._current_start_frame: int = 0
        self._current_duration: int = 0
        self._frame_id: int = 0

        # Counters
        self._home_frames: int = 0
        self._away_frames: int = 0
        self._contested_frames: int = 0
        self._dead_ball_frames: int = 0
        self._possession_changes: int = 0

        # Full timeline — one entry per *possession sequence*
        self._timeline: list[PossessionEvent] = []

        # For avg duration
        self._completed_sequences: list[int] = []  # durations (frames) of finished sequences

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bbox_center(bbox: tuple) -> tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @staticmethod
    def _px_dist(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _raw_state(
        self,
        tracked_frame,
        team_labels: dict[int, int],
    ) -> tuple[PossessionState, Optional[int], Optional[int]]:
        """Compute raw (unsmoothed) possession state for this frame."""
        ball = tracked_frame.tracked_ball
        players = tracked_frame.tracked_players

        if ball is None:
            return PossessionState.DEAD_BALL, None, None

        ball_center = self._bbox_center(ball.bbox)

        if not players:
            return PossessionState.DEAD_BALL, None, None

        # Sort players by distance to ball
        dists = []
        for p in players:
            pc = self._bbox_center(p.bbox)
            d = self._px_dist(pc, ball_center)
            dists.append((d, p.track_id, team_labels.get(p.track_id)))

        dists.sort(key=lambda x: x[0])
        closest_dist, closest_id, closest_team = dists[0]

        threshold = self.proximity_threshold_px
        contested_threshold = threshold * 1.5

        if closest_dist >= contested_threshold:
            # Nobody close enough — ball in the air or loose
            return PossessionState.UNKNOWN, None, None

        # Check if any player from a *different* team is also within contested_threshold
        if closest_dist < threshold:
            # At least one player is within strict threshold
            for d, pid, tid in dists[1:]:
                if d >= contested_threshold:
                    break
                # Another player close enough to contest
                if tid is not None and tid != closest_team:
                    return PossessionState.CONTESTED, None, None

            # Sole possessor
            if closest_team == 1:
                return PossessionState.HOME, closest_id, closest_team
            elif closest_team == 2:
                return PossessionState.AWAY, closest_id, closest_team
            else:
                # Team unknown but player known
                return PossessionState.HOME, closest_id, closest_team
        else:
            # Between threshold and contested_threshold — check for contest
            for d, pid, tid in dists[1:]:
                if d >= contested_threshold:
                    break
                if tid is not None and tid != closest_team:
                    return PossessionState.CONTESTED, None, None
            # Loosely near, single team
            if closest_team == 1:
                return PossessionState.HOME, closest_id, closest_team
            elif closest_team == 2:
                return PossessionState.AWAY, closest_id, closest_team
            return PossessionState.UNKNOWN, None, None

    def _commit_state(
        self,
        new_state: PossessionState,
        player_id: Optional[int],
        team_id: Optional[int],
        frame_id: int,
    ) -> None:
        """Commit a new possession state and record a timeline change."""
        if self._current_state != PossessionState.UNKNOWN:
            # Save completed sequence duration
            self._completed_sequences.append(self._current_duration)

        if self._current_state not in (PossessionState.UNKNOWN, new_state):
            self._possession_changes += 1

        self._current_state = new_state
        self._current_player_id = player_id
        self._current_team_id = team_id
        self._current_start_frame = frame_id
        self._current_duration = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, tracked_frame, team_labels: dict[int, int]) -> PossessionEvent:
        """
        Process one frame and return a PossessionEvent.

        tracked_frame must expose:
          - tracked_players : list of objects with .track_id and .bbox
          - tracked_ball    : object with .bbox, or None
          - frame_id        : int
        """
        frame_id = getattr(tracked_frame, "frame_id", self._frame_id)
        self._frame_id = frame_id

        raw_state, raw_player, raw_team = self._raw_state(tracked_frame, team_labels)

        # Temporal smoothing
        if raw_state == self._candidate_state:
            self._candidate_run += 1
        else:
            self._candidate_state = raw_state
            self._candidate_player_id = raw_player
            self._candidate_team_id = raw_team
            self._candidate_run = 1

        # Commit when candidate has been stable for min_duration_frames
        if self._candidate_run >= self.min_duration_frames:
            if self._candidate_state != self._current_state:
                self._commit_state(
                    self._candidate_state,
                    self._candidate_player_id,
                    self._candidate_team_id,
                    frame_id,
                )
            else:
                self._current_duration += 1
                self._current_player_id = self._candidate_player_id
                self._current_team_id = self._candidate_team_id
        else:
            if self._current_state != PossessionState.UNKNOWN:
                self._current_duration += 1

        # Accumulate counters for confirmed state
        state = self._current_state
        if state == PossessionState.HOME:
            self._home_frames += 1
        elif state == PossessionState.AWAY:
            self._away_frames += 1
        elif state == PossessionState.CONTESTED:
            self._contested_frames += 1
        elif state == PossessionState.DEAD_BALL:
            self._dead_ball_frames += 1

        event = PossessionEvent(
            frame_id=frame_id,
            state=state,
            player_id=self._current_player_id,
            team_id=self._current_team_id,
            court_position=None,  # court projection handled by stats aggregator
            duration_frames=self._current_duration,
        )
        self._timeline.append(event)
        self._frame_id += 1
        return event

    def get_possession_stats(self) -> dict:
        """Return aggregate possession statistics."""
        total = self._home_frames + self._away_frames + self._contested_frames + self._dead_ball_frames
        total_active = self._home_frames + self._away_frames
        home_pct = (self._home_frames / total_active * 100.0) if total_active > 0 else 50.0
        away_pct = (self._away_frames / total_active * 100.0) if total_active > 0 else 50.0

        all_durations = list(self._completed_sequences)
        if self._current_duration > 0:
            all_durations.append(self._current_duration)

        avg_dur_frames = (
            sum(all_durations) / len(all_durations) if all_durations else 0.0
        )

        # We don't have fps here; caller can multiply by (1/fps) if needed
        # We return frames; the stats aggregator knows fps
        return {
            "home_possession_frames": self._home_frames,
            "away_possession_frames": self._away_frames,
            "contested_frames": self._contested_frames,
            "dead_ball_frames": self._dead_ball_frames,
            "home_possession_pct": round(home_pct, 2),
            "away_possession_pct": round(away_pct, 2),
            "possession_changes": self._possession_changes,
            "avg_possession_duration_s": round(avg_dur_frames, 1),  # in frames; divide by fps outside
        }

    def get_possession_timeline(self) -> list[PossessionEvent]:
        """Return a copy of the full per-frame possession event list."""
        return list(self._timeline)
