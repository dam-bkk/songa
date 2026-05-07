"""
Songa CV — Shot & Action Detector
Analyses ball trajectories to detect shot attempts and key game events.
"""
from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .tracker import TrackedFrame, TrackedPlayer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Basket positions in court metres (NBA standard, both ends)
# ---------------------------------------------------------------------------
_BASKET_LEFT_M = (1.575, 7.62)
_BASKET_RIGHT_M = (27.075, 7.62)
_BASKET_RADIUS_M = 0.60   # ball must pass within this radius to count as made
_SHOT_ARC_MIN_HEIGHT_PX = 30   # minimum upward pixel travel to classify as a shot arc
_BALL_TRAJ_WINDOW = 25   # frames of ball trajectory to analyse


@dataclass
class ShotEvent:
    """A detected shot attempt."""
    frame_id: int
    shooter_id: int
    release_point_px: tuple[float, float]
    release_point_court: Optional[tuple[float, float]]
    zone: str
    arc_height: float           # estimated max height in pixels
    timestamp: float            # seconds from video start
    made: bool = False


@dataclass
class StealEvent:
    """A detected steal / forced turnover."""
    frame_id: int
    type: str = "steal"
    players_involved: list[int] = field(default_factory=list)
    court_position: Optional[tuple[float, float]] = None
    timestamp: float = 0.0


@dataclass
class ScreenEvent:
    """A detected pick / screen action."""
    frame_id: int
    type: str = "screen"
    players_involved: list[int] = field(default_factory=list)
    court_position: Optional[tuple[float, float]] = None
    timestamp: float = 0.0


@dataclass
class KeyEvent:
    """Generic key game event."""
    frame_id: int
    type: str
    players_involved: list[int]
    court_position: Optional[tuple[float, float]]
    timestamp: float


# ---------------------------------------------------------------------------
# ShotDetector
# ---------------------------------------------------------------------------

class ShotDetector:
    """
    Detects shot attempts by analysing ball trajectory:
    - Upward movement followed by downward movement = arc = shot
    - Ball passing near a basket position = made basket
    """

    def __init__(self, fps: float = 30.0) -> None:
        self.fps = fps
        # recent ball positions in pixel space: deque of (frame_id, cx, cy)
        self._ball_traj: deque[tuple[int, float, float]] = deque(maxlen=_BALL_TRAJ_WINDOW)
        # recent ball positions in court metres: deque of (frame_id, x_m, y_m) or None
        self._ball_court_traj: deque[tuple[int, float, float]] = deque(maxlen=_BALL_TRAJ_WINDOW)
        self._shots: list[ShotEvent] = []
        # cooldown to avoid duplicate shot events (frames)
        self._cooldown = 0
        self._cooldown_frames = int(fps * 1.5)  # 1.5 second cooldown

    def update(
        self,
        tracked_frame: TrackedFrame,
        H: Optional[np.ndarray],
    ) -> list[ShotEvent]:
        """
        Analyse the current frame for shot events.

        Returns any new ShotEvent instances detected.
        """
        events: list[ShotEvent] = []

        if self._cooldown > 0:
            self._cooldown -= 1

        ball = tracked_frame.tracked_ball
        if ball is None:
            return events

        cx, cy = ball.center
        frame_id = tracked_frame.frame_id
        self._ball_traj.append((frame_id, cx, cy))

        # Project to court if homography available
        if H is not None:
            try:
                from .court import CourtCalibrator
                calibrator = CourtCalibrator()
                court_pt = calibrator.project_to_court((cx, cy), H)
                self._ball_court_traj.append((frame_id, court_pt[0], court_pt[1]))
            except Exception:
                self._ball_court_traj.append((frame_id, -1.0, -1.0))
        else:
            self._ball_court_traj.append((frame_id, -1.0, -1.0))

        if len(self._ball_traj) < 10 or self._cooldown > 0:
            return events

        # Detect arc: look for upward followed by downward motion
        traj = list(self._ball_traj)
        ys = [pt[2] for pt in traj]  # pixel y (increases downward in image)

        arc_event = self._detect_arc(ys)
        if arc_event:
            arc_height, release_idx = arc_event
            release_frame_id = traj[release_idx][0]
            release_px = (traj[release_idx][1], traj[release_idx][2])

            # Nearest player at release frame
            shooter_id = self._find_nearest_player(
                release_px, tracked_frame.tracked_players
            )

            # Court position at release
            court_pt = None
            if len(self._ball_court_traj) > release_idx:
                ct = list(self._ball_court_traj)[release_idx]
                if ct[1] >= 0:
                    court_pt = (ct[1], ct[2])

            zone = "unknown"
            if court_pt is not None:
                try:
                    from .court import ShotZoneClassifier
                    zone = ShotZoneClassifier().classify_shot(court_pt)
                except Exception:
                    pass

            made = False
            if H is not None:
                made = self._detect_made_shot(
                    [(ct[1], ct[2]) for ct in self._ball_court_traj if ct[1] >= 0],
                    _BASKET_LEFT_M,
                ) or self._detect_made_shot(
                    [(ct[1], ct[2]) for ct in self._ball_court_traj if ct[1] >= 0],
                    _BASKET_RIGHT_M,
                )

            timestamp = release_frame_id / self.fps
            evt = ShotEvent(
                frame_id=release_frame_id,
                shooter_id=shooter_id,
                release_point_px=release_px,
                release_point_court=court_pt,
                zone=zone,
                arc_height=arc_height,
                timestamp=timestamp,
                made=made,
            )
            events.append(evt)
            self._shots.append(evt)
            self._cooldown = self._cooldown_frames
            logger.debug(
                "Shot detected at frame %d — zone=%s made=%s arc_h=%.1f",
                release_frame_id, zone, made, arc_height,
            )

        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_arc(
        self, ys: list[float]
    ) -> Optional[tuple[float, int]]:
        """
        Look for an inverted-V shape in Y pixel values (up in image = lower Y).

        Returns (arc_height_px, release_frame_index) if found, else None.
        """
        n = len(ys)
        min_y = min(ys)
        min_idx = ys.index(min_y)

        # Must have enough points before and after the peak
        if min_idx < 3 or min_idx > n - 4:
            return None

        # Descending trend before peak (ball rising = Y decreasing)
        pre = ys[:min_idx]
        post = ys[min_idx:]

        pre_drop = pre[0] - pre[-1]   # how much Y dropped going into peak
        post_rise = post[-1] - post[0]  # how much Y rose after peak

        if pre_drop < _SHOT_ARC_MIN_HEIGHT_PX:
            return None
        if post_rise < _SHOT_ARC_MIN_HEIGHT_PX * 0.5:
            return None

        arc_height = (pre_drop + post_rise) / 2.0
        # Release point: earliest frame in the pre-peak segment
        return (arc_height, max(0, min_idx - len(pre) // 2))

    def _find_nearest_player(
        self,
        position: tuple[float, float],
        players: list[TrackedPlayer],
    ) -> int:
        """Return track_id of the player nearest to position. Returns -1 if none."""
        if not players:
            return -1
        best_id = -1
        best_dist = float("inf")
        for p in players:
            d = math.hypot(p.center[0] - position[0], p.center[1] - position[1])
            if d < best_dist:
                best_dist = d
                best_id = p.track_id
        return best_id

    def detect_made_shot(
        self,
        ball_trajectory: list[tuple[float, float]],
        basket_position: tuple[float, float],
    ) -> bool:
        """
        Public method: returns True if any point in ball_trajectory passes
        within _BASKET_RADIUS_M of basket_position.
        """
        return self._detect_made_shot(ball_trajectory, basket_position)

    def _detect_made_shot(
        self,
        ball_trajectory: list[tuple[float, float]],
        basket_position: tuple[float, float],
    ) -> bool:
        bx, by = basket_position
        for x, y in ball_trajectory:
            if math.hypot(x - bx, y - by) <= _BASKET_RADIUS_M:
                return True
        return False

    @property
    def shots(self) -> list[ShotEvent]:
        return list(self._shots)


# ---------------------------------------------------------------------------
# ActionDetector
# ---------------------------------------------------------------------------

_STEAL_MAX_DIST_PX = 80     # max distance between players for a steal
_STEAL_MIN_SPEED_PX = 15    # minimum ball speed change to flag steal
_SCREEN_MAX_DIST_PX = 100   # max distance for a screen interaction
_SCREEN_MIN_STATIONARY_FRAMES = 8  # frames a player must be near-stationary


class ActionDetector:
    """
    Detects basketball actions: steals and screens.
    """

    def __init__(self, fps: float = 30.0) -> None:
        self.fps = fps
        # track_id -> deque of recent centers
        self._player_history: dict[int, deque[tuple[float, float]]] = {}
        self._cooldowns: dict[str, int] = {}

    def _update_history(self, tracked_frame: TrackedFrame) -> None:
        for p in tracked_frame.tracked_players:
            if p.track_id not in self._player_history:
                self._player_history[p.track_id] = deque(maxlen=20)
            self._player_history[p.track_id].append(p.center)

    def _player_speed(self, track_id: int) -> float:
        """Average pixel displacement per frame over recent history."""
        hist = self._player_history.get(track_id)
        if hist is None or len(hist) < 2:
            return 0.0
        dists = [
            math.hypot(hist[i][0] - hist[i - 1][0], hist[i][1] - hist[i - 1][1])
            for i in range(1, len(hist))
        ]
        return sum(dists) / len(dists)

    def _is_cooldown(self, key: str) -> bool:
        remaining = self._cooldowns.get(key, 0)
        if remaining > 0:
            self._cooldowns[key] -= 1
            return True
        return False

    def detect_steal(self, tracked_frame: TrackedFrame) -> list[StealEvent]:
        """
        Detect steal events: ball possession changes due to rapid interception.

        Heuristic: if the ball is very close to a player who is moving quickly,
        and another player is also nearby, flag as a potential steal.
        """
        self._update_history(tracked_frame)
        events: list[StealEvent] = []

        ball = tracked_frame.tracked_ball
        if ball is None or len(tracked_frame.tracked_players) < 2:
            return events

        if self._is_cooldown("steal"):
            return events

        # Find players close to the ball
        close_players = [
            p for p in tracked_frame.tracked_players
            if math.hypot(
                p.center[0] - ball.center[0],
                p.center[1] - ball.center[1],
            ) < _STEAL_MAX_DIST_PX
        ]

        if len(close_players) >= 2:
            speeds = [(p.track_id, self._player_speed(p.track_id)) for p in close_players]
            speeds.sort(key=lambda x: x[1], reverse=True)
            fastest_id, fastest_speed = speeds[0]

            if fastest_speed > _STEAL_MIN_SPEED_PX:
                involved = [s[0] for s in speeds[:2]]
                evt = StealEvent(
                    frame_id=tracked_frame.frame_id,
                    players_involved=involved,
                    timestamp=tracked_frame.frame_id / self.fps,
                )
                events.append(evt)
                self._cooldowns["steal"] = int(self.fps * 2)
                logger.debug("Steal detected at frame %d", tracked_frame.frame_id)

        return events

    def detect_screen(
        self, players: list[TrackedPlayer]
    ) -> list[ScreenEvent]:
        """
        Detect screen/pick actions: a near-stationary player positioned
        close to another player.
        """
        events: list[ScreenEvent] = []
        if len(players) < 2:
            return events

        for i, p1 in enumerate(players):
            for j, p2 in enumerate(players):
                if j <= i:
                    continue
                dist = math.hypot(
                    p1.center[0] - p2.center[0],
                    p1.center[1] - p2.center[1],
                )
                if dist > _SCREEN_MAX_DIST_PX:
                    continue

                p1_speed = self._player_speed(p1.track_id)
                p2_speed = self._player_speed(p2.track_id)

                # One player mostly stationary, other moving
                screener_id = None
                mover_id = None
                if p1_speed < 2.0 and p2_speed > 5.0:
                    screener_id, mover_id = p1.track_id, p2.track_id
                elif p2_speed < 2.0 and p1_speed > 5.0:
                    screener_id, mover_id = p2.track_id, p1.track_id

                if screener_id is not None:
                    key = f"screen_{min(p1.track_id,p2.track_id)}_{max(p1.track_id,p2.track_id)}"
                    if not self._is_cooldown(key):
                        screener = p1 if screener_id == p1.track_id else p2
                        evt = ScreenEvent(
                            frame_id=0,  # caller can set frame_id
                            players_involved=[screener_id, mover_id],
                            court_position=screener.center,
                        )
                        events.append(evt)
                        self._cooldowns[key] = int(self.fps * 3)

        return events
