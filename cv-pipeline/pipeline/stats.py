"""
Songa CV — Stats Aggregator
Accumulates per-frame tracking data into player, team and match summaries.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .tracker import TrackedFrame
from .shot import ShotEvent, StealEvent, ScreenEvent, KeyEvent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PlayerStats:
    """Statistics for a single tracked player."""
    player_id: int
    total_distance: float = 0.0       # metres
    avg_speed: float = 0.0             # m/s
    max_speed: float = 0.0             # m/s
    time_in_paint: float = 0.0         # seconds
    shots_attempted: int = 0
    shots_made: int = 0
    shot_pct: float = 0.0
    shot_zones: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "total_distance_m": round(self.total_distance, 2),
            "avg_speed_ms": round(self.avg_speed, 3),
            "max_speed_ms": round(self.max_speed, 3),
            "time_in_paint_s": round(self.time_in_paint, 1),
            "shots_attempted": self.shots_attempted,
            "shots_made": self.shots_made,
            "shot_pct": round(self.shot_pct, 3),
            "shot_zones": self.shot_zones,
        }


@dataclass
class TeamStats:
    """Aggregate statistics for a single team."""
    team_id: int
    player_ids: list[int] = field(default_factory=list)
    total_shots: int = 0
    shots_made: int = 0
    possession_pct: float = 0.0        # fraction of frames nearest the ball
    avg_spacing: float = 0.0           # average inter-player spacing in metres
    paint_touches: int = 0
    transition_speed: float = 0.0      # average speed during transition plays (m/s)

    @property
    def shot_pct(self) -> float:
        if self.total_shots == 0:
            return 0.0
        return round(self.shots_made / self.total_shots, 3)

    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "player_ids": list(self.player_ids),
            "total_shots": self.total_shots,
            "shots_made": self.shots_made,
            "shot_pct": self.shot_pct,
            "possession_pct": round(self.possession_pct, 3),
            "avg_spacing_m": round(self.avg_spacing, 2),
            "paint_touches": self.paint_touches,
            "transition_speed_ms": round(self.transition_speed, 3),
        }


@dataclass
class MatchSummary:
    """Full match analysis output."""
    duration_frames: int
    fps: float
    players_tracked: int
    total_possessions: int
    key_events: list[dict]
    player_stats: dict[int, PlayerStats]
    team_stats: TeamStats                       # legacy single-team field
    per_team_stats: dict[int, TeamStats]        # {team_id: TeamStats}
    shot_chart: dict[str, dict[str, float]]

    def to_dict(self) -> dict:
        return {
            "meta": {
                "duration_frames": self.duration_frames,
                "duration_s": round(self.duration_frames / self.fps, 1) if self.fps else 0,
                "fps": self.fps,
                "players_tracked": self.players_tracked,
                "total_possessions": self.total_possessions,
            },
            "team_stats": self.team_stats.to_dict(),
            "per_team_stats": {
                str(k): v.to_dict() for k, v in self.per_team_stats.items()
            },
            "player_stats": {str(k): v.to_dict() for k, v in self.player_stats.items()},
            "shot_chart": self.shot_chart,
            "key_events": self.key_events,
        }


# ---------------------------------------------------------------------------
# Paint zones in court metres (shared with court.py but kept local to avoid
# circular imports)
# ---------------------------------------------------------------------------
_PAINT_X_MIN_L: float = 0.0
_PAINT_X_MAX_L: float = 4.57
_PAINT_X_MIN_R: float = 24.08
_PAINT_X_MAX_R: float = 28.65
_PAINT_Y_MIN: float = 3.66
_PAINT_Y_MAX: float = 11.58

# Maximum distance (metres) from the ball to be considered "possessing"
_POSSESSION_RADIUS_M: float = 1.5
# Pixel-space possession radius when no homography is available
_POSSESSION_RADIUS_PX: float = 80.0


def _in_paint(x: float, y: float) -> bool:
    in_left = _PAINT_X_MIN_L <= x <= _PAINT_X_MAX_L and _PAINT_Y_MIN <= y <= _PAINT_Y_MAX
    in_right = _PAINT_X_MIN_R <= x <= _PAINT_X_MAX_R and _PAINT_Y_MIN <= y <= _PAINT_Y_MAX
    return in_left or in_right


# ---------------------------------------------------------------------------
# StatsAggregator
# ---------------------------------------------------------------------------

class StatsAggregator:
    """
    Accumulates per-frame data into running statistics.

    Call update() once per frame, then get_match_summary() at the end.
    """

    def __init__(self, fps: float = 30.0) -> None:
        self.fps = fps
        self._frame_count = 0
        self._all_player_ids: set[int] = set()

        # Per-player accumulators (keyed by track_id)
        self._distances: dict[int, float] = {}          # metres
        self._prev_court_pos: dict[int, tuple[float, float]] = {}
        self._speed_samples: dict[int, list[float]] = {}
        self._paint_frames: dict[int, int] = {}         # frame count in paint
        self._shots_attempted: dict[int, int] = {}
        self._shots_made: dict[int, int] = {}
        self._shot_zone_hits: dict[int, dict[str, dict[str, int]]] = {}

        # Player → team mapping (latest known assignment)
        self._player_team: dict[int, int] = {}

        # Team-level accumulators (keyed by team_id)
        self._team_shots_attempted: dict[int, int] = {}
        self._team_shots_made: dict[int, int] = {}
        # Frames where a team is closest to the ball (possession proxy)
        self._team_possession_frames: dict[int, int] = {}
        self._total_possession_frames: int = 0

        # Legacy single-team accumulators (kept for backwards compatibility)
        self._spacing_samples: list[float] = []
        self._paint_touch_count = 0
        self._transition_speeds: list[float] = []

        # Shot chart
        self._zone_stats: dict[str, dict[str, int]] = {}

        # Key events list (serialisable dicts)
        self._key_events: list[dict] = []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_player(self, tid: int) -> None:
        """Initialise per-player accumulators on first sight."""
        if tid not in self._distances:
            self._distances[tid] = 0.0
            self._speed_samples[tid] = []
            self._paint_frames[tid] = 0
            self._shots_attempted[tid] = 0
            self._shots_made[tid] = 0
            self._shot_zone_hits[tid] = {}

    def _ensure_team(self, team_id: int) -> None:
        """Initialise per-team accumulators on first sight."""
        if team_id not in self._team_shots_attempted:
            self._team_shots_attempted[team_id] = 0
            self._team_shots_made[team_id] = 0
            self._team_possession_frames[team_id] = 0

    def _closest_team_to_ball(
        self,
        court_positions: dict[int, tuple[float, float]],
        ball_court_pos: Optional[tuple[float, float]],
    ) -> Optional[int]:
        """
        Return the team_id of the player closest to the ball (court coords).
        Returns None if ball position or player positions are unavailable.
        """
        if ball_court_pos is None or not court_positions:
            return None

        bx, by = ball_court_pos
        best_dist = float("inf")
        best_tid: Optional[int] = None

        for tid, (px, py) in court_positions.items():
            d = math.hypot(px - bx, py - by)
            if d < best_dist:
                best_dist = d
                best_tid = tid

        if best_tid is None or best_dist > _POSSESSION_RADIUS_M:
            return None

        return self._player_team.get(best_tid)

    def _closest_team_to_ball_px(
        self,
        players,
        ball_center: Optional[tuple[float, float]],
    ) -> Optional[int]:
        """
        Pixel-space fallback for possession when no homography is available.
        """
        if ball_center is None or not players:
            return None

        bx, by = ball_center
        best_dist = float("inf")
        best_tid: Optional[int] = None

        for p in players:
            cx, cy = p.center
            d = math.hypot(cx - bx, cy - by)
            if d < best_dist:
                best_dist = d
                best_tid = p.track_id

        if best_tid is None or best_dist > _POSSESSION_RADIUS_PX:
            return None

        return self._player_team.get(best_tid)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        tracked_frame: TrackedFrame,
        shot_events: list[ShotEvent],
        key_events: list,
        H: Optional[np.ndarray] = None,
        zone_classifier=None,
    ) -> None:
        """
        Process one frame of tracking data.

        H: homography matrix (pixel -> court metres). If None, only pixel-level
           stats are accumulated (no real distance, no zone info).
        """
        self._frame_count += 1
        players = tracked_frame.tracked_players
        ball = tracked_frame.tracked_ball

        # Update player→team mapping from TrackedFrame labels
        for tid, team_id in tracked_frame.team_labels.items():
            self._player_team[tid] = team_id
            self._ensure_team(team_id)

        # Track known player IDs
        for p in players:
            self._all_player_ids.add(p.track_id)
            self._ensure_player(p.track_id)

        # Project player positions to court if possible
        court_positions: dict[int, tuple[float, float]] = {}
        ball_court_pos: Optional[tuple[float, float]] = None

        if H is not None:
            from .court import CourtCalibrator
            calibrator = CourtCalibrator()

            if players:
                pxs = [p.center for p in players]
                try:
                    courts = calibrator.project_batch(pxs, H)
                    for i, p in enumerate(players):
                        court_positions[p.track_id] = (
                            float(courts[i, 0]), float(courts[i, 1])
                        )
                except Exception as exc:
                    logger.debug("Batch projection failed: %s", exc)

            if ball is not None:
                try:
                    pt = calibrator.project_to_court(ball.center, H)
                    ball_court_pos = (float(pt[0]), float(pt[1]))
                except Exception as exc:
                    logger.debug("Ball projection failed: %s", exc)

        # Per-player distance and speed
        for p in players:
            tid = p.track_id
            if tid in court_positions:
                cx, cy = court_positions[tid]
                if tid in self._prev_court_pos:
                    px, py = self._prev_court_pos[tid]
                    dist = math.hypot(cx - px, cy - py)
                    self._distances[tid] += dist
                    speed_ms = dist * self.fps
                    self._speed_samples[tid].append(speed_ms)
                self._prev_court_pos[tid] = (cx, cy)

                # Paint time
                if _in_paint(cx, cy):
                    self._paint_frames[tid] += 1

        # Team spacing (using court positions; all tracked players together)
        if len(court_positions) >= 2:
            positions = list(court_positions.values())
            spacings = []
            for i in range(len(positions)):
                for j in range(i + 1, len(positions)):
                    d = math.hypot(
                        positions[i][0] - positions[j][0],
                        positions[i][1] - positions[j][1],
                    )
                    spacings.append(d)
            if spacings:
                self._spacing_samples.append(sum(spacings) / len(spacings))

        # Paint touches (new entries into paint)
        for p in players:
            tid = p.track_id
            if tid in court_positions:
                cx, cy = court_positions[tid]
                was_in = (
                    self._paint_frames.get(tid, 0) > 1
                    and _in_paint(cx, cy)
                    and not _in_paint(*self._prev_court_pos.get(tid, (cx, cy)))
                )
                if was_in:
                    self._paint_touch_count += 1
                    team_id = self._player_team.get(tid)
                    if team_id is not None:
                        self._ensure_team(team_id)

        # Possession frame attribution
        if H is not None and ball_court_pos is not None:
            closest_team = self._closest_team_to_ball(court_positions, ball_court_pos)
        elif ball is not None:
            closest_team = self._closest_team_to_ball_px(players, ball.center)
        else:
            closest_team = None

        if closest_team is not None:
            self._total_possession_frames += 1
            self._team_possession_frames[closest_team] = (
                self._team_possession_frames.get(closest_team, 0) + 1
            )

        # Shot events — attributed to player and team
        for evt in shot_events:
            tid = evt.shooter_id
            if tid < 0:
                continue
            self._ensure_player(tid)
            self._shots_attempted[tid] += 1
            if evt.made:
                self._shots_made[tid] += 1

            # Team-level shot tallying
            team_id = self._player_team.get(tid)
            if team_id is not None:
                self._ensure_team(team_id)
                self._team_shots_attempted[team_id] += 1
                if evt.made:
                    self._team_shots_made[team_id] += 1

            # Zone chart
            zone = evt.zone or "unknown"
            if zone not in self._zone_stats:
                self._zone_stats[zone] = {"made": 0, "attempted": 0}
            self._zone_stats[zone]["attempted"] += 1
            if evt.made:
                self._zone_stats[zone]["made"] += 1

            # Per-player zone breakdown
            if zone not in self._shot_zone_hits[tid]:
                self._shot_zone_hits[tid][zone] = {"made": 0, "attempted": 0}
            self._shot_zone_hits[tid][zone]["attempted"] += 1
            if evt.made:
                self._shot_zone_hits[tid][zone]["made"] += 1

        # Key events
        for evt in key_events:
            if hasattr(evt, "__dict__"):
                d = {k: v for k, v in evt.__dict__.items() if not k.startswith("_")}
            else:
                d = {"raw": str(evt)}
            self._key_events.append(d)

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    def get_player_stats(self, player_id: int) -> PlayerStats:
        """Return PlayerStats for a single player."""
        speeds = self._speed_samples.get(player_id, [])
        avg_speed = (sum(speeds) / len(speeds)) if speeds else 0.0
        max_speed = max(speeds, default=0.0)
        total_dist = self._distances.get(player_id, 0.0)
        paint_s = self._paint_frames.get(player_id, 0) / self.fps
        attempted = self._shots_attempted.get(player_id, 0)
        made = self._shots_made.get(player_id, 0)
        pct = made / attempted if attempted > 0 else 0.0

        zone_raw = self._shot_zone_hits.get(player_id, {})
        zone_out: dict[str, dict[str, float]] = {}
        for z, s in zone_raw.items():
            zpct = s["made"] / s["attempted"] if s["attempted"] > 0 else 0.0
            zone_out[z] = {
                "made": float(s["made"]),
                "attempted": float(s["attempted"]),
                "pct": round(zpct, 3),
            }

        return PlayerStats(
            player_id=player_id,
            total_distance=round(total_dist, 2),
            avg_speed=round(avg_speed, 3),
            max_speed=round(max_speed, 3),
            time_in_paint=round(paint_s, 1),
            shots_attempted=attempted,
            shots_made=made,
            shot_pct=round(pct, 3),
            shot_zones=zone_out,
        )

    def get_team_stats(self) -> TeamStats:
        """
        Return aggregate TeamStats for the combined tracked entity.

        This is the backwards-compatible single-team view (team_id=-1).
        Use get_per_team_stats() for per-team breakdown.
        """
        avg_spacing = (
            sum(self._spacing_samples) / len(self._spacing_samples)
            if self._spacing_samples else 0.0
        )
        avg_transition = (
            sum(self._transition_speeds) / len(self._transition_speeds)
            if self._transition_speeds else 0.0
        )

        total_shots = sum(self._team_shots_attempted.values())
        total_made = sum(self._team_shots_made.values())
        all_players = list(self._all_player_ids)

        # Possession percentage: weighted by all teams
        possession_pct = 50.0
        if self._total_possession_frames > 0 and self._team_possession_frames:
            # Pick the numerically smallest team_id as "the team" for this view
            key_team = min(self._team_possession_frames)
            frames = self._team_possession_frames[key_team]
            possession_pct = round(frames / self._total_possession_frames * 100, 1)

        return TeamStats(
            team_id=-1,
            player_ids=all_players,
            total_shots=total_shots,
            shots_made=total_made,
            possession_pct=possession_pct,
            avg_spacing=round(avg_spacing, 2),
            paint_touches=self._paint_touch_count,
            transition_speed=round(avg_transition, 3),
        )

    def get_per_team_stats(self) -> dict[int, TeamStats]:
        """
        Return {team_id: TeamStats} for each detected team.
        """
        result: dict[int, TeamStats] = {}

        # Collect player lists per team
        team_players: dict[int, list[int]] = {}
        for tid, team_id in self._player_team.items():
            team_players.setdefault(team_id, []).append(tid)

        known_teams = set(self._team_shots_attempted) | set(team_players)

        for team_id in known_teams:
            player_ids = team_players.get(team_id, [])
            attempted = self._team_shots_attempted.get(team_id, 0)
            made = self._team_shots_made.get(team_id, 0)

            possession_pct = 0.0
            if self._total_possession_frames > 0:
                frames = self._team_possession_frames.get(team_id, 0)
                possession_pct = round(frames / self._total_possession_frames * 100, 1)

            result[team_id] = TeamStats(
                team_id=team_id,
                player_ids=list(player_ids),
                total_shots=attempted,
                shots_made=made,
                possession_pct=possession_pct,
            )

        return result

    def get_team_possession(self, team_id: int) -> float:
        """
        Return the possession percentage for a specific team.

        Based on the fraction of frames where the closest player to the ball
        belonged to this team.

        Returns
        -------
        float
            Value in [0.0, 100.0]. Returns 0.0 if no possession data available.
        """
        if self._total_possession_frames == 0:
            return 0.0
        frames = self._team_possession_frames.get(team_id, 0)
        return round(frames / self._total_possession_frames * 100, 1)

    def get_match_summary(self) -> MatchSummary:
        """Build and return the full MatchSummary."""
        player_stats = {
            pid: self.get_player_stats(pid) for pid in self._all_player_ids
        }
        team_stats = self.get_team_stats()
        per_team_stats = self.get_per_team_stats()

        # Shot chart with percentages
        shot_chart: dict[str, dict[str, float]] = {}
        for zone, s in self._zone_stats.items():
            pct = s["made"] / s["attempted"] if s["attempted"] > 0 else 0.0
            shot_chart[zone] = {
                "made": float(s["made"]),
                "attempted": float(s["attempted"]),
                "pct": round(pct, 3),
            }

        total_shots = sum(s["attempted"] for s in self._zone_stats.values())

        return MatchSummary(
            duration_frames=self._frame_count,
            fps=self.fps,
            players_tracked=len(self._all_player_ids),
            total_possessions=total_shots,  # proxy metric
            key_events=list(self._key_events),
            player_stats=player_stats,
            team_stats=team_stats,
            per_team_stats=per_team_stats,
            shot_chart=shot_chart,
        )
