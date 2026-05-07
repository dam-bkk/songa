"""
Songa CV — Kalman Filter for Ball Tracking
6-state Kalman filter (position, velocity, acceleration) wrapping OpenCV's
KalmanFilter implementation, plus a rolling trajectory buffer with arc analysis.
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# State dimension: [x, y, vx, vy, ax, ay]
_STATE_DIM = 6
# Measurement dimension: [x, y]
_MEAS_DIM = 2

# Default filter parameters
_DEFAULT_DT: float = 1.0 / 30.0         # seconds per frame @ 30fps
_DEFAULT_PROCESS_NOISE: float = 1e-3
_DEFAULT_MEASUREMENT_NOISE: float = 5.0
_DEFAULT_ERROR_COVARIANCE: float = 1.0

# Trajectory buffer constants
_DEFAULT_BUFFER_MAXLEN: int = 90         # 3 seconds @ 30fps
_SAVGOL_WINDOW: int = 11                 # Savitzky-Golay window (must be odd)
_SAVGOL_POLYORDER: int = 3
_MOVING_AVG_WINDOW: int = 5             # fallback smoothing window

# Arc detection constants
_ARC_PEAK_MIN_HEIGHT_PX: float = 20.0   # minimum arc height to report a peak


# ---------------------------------------------------------------------------
# BallKalmanFilter
# ---------------------------------------------------------------------------

class BallKalmanFilter:
    """
    6-dimensional Kalman filter for ball position tracking.

    State vector: [x, y, vx, vy, ax, ay]
    Measurement:  [x, y]

    Uses a constant-acceleration (Newtonian kinematics) motion model.
    """

    def __init__(
        self,
        dt: float = _DEFAULT_DT,
        process_noise: float = _DEFAULT_PROCESS_NOISE,
        measurement_noise: float = _DEFAULT_MEASUREMENT_NOISE,
    ) -> None:
        self._dt = dt
        self._process_noise = process_noise
        self._measurement_noise = measurement_noise
        self._kf = cv2.KalmanFilter(_STATE_DIM, _MEAS_DIM, 0, cv2.CV_64F)
        self._initialized = False
        self._build_matrices()

    # ------------------------------------------------------------------
    # Matrix construction
    # ------------------------------------------------------------------

    def _build_matrices(self) -> None:
        dt = self._dt
        dt2 = 0.5 * dt * dt

        # Transition matrix F (constant-acceleration kinematics)
        # [x  ]   [1  0  dt  0  dt2  0  ] [x  ]
        # [y  ] = [0  1   0 dt   0  dt2 ] [y  ]
        # [vx ]   [0  0   1  0   dt   0 ] [vx ]
        # [vy ]   [0  0   0  1    0  dt ] [vy ]
        # [ax ]   [0  0   0  0    1   0 ] [ax ]
        # [ay ]   [0  0   0  0    0   1 ] [ay ]
        F = np.array([
            [1, 0, dt, 0,  dt2, 0  ],
            [0, 1,  0, dt, 0,   dt2],
            [0, 0,  1, 0,  dt,  0  ],
            [0, 0,  0, 1,  0,   dt ],
            [0, 0,  0, 0,  1,   0  ],
            [0, 0,  0, 0,  0,   1  ],
        ], dtype=np.float64)

        # Measurement matrix H: we only observe x and y
        H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
        ], dtype=np.float64)

        self._kf.transitionMatrix = F
        self._kf.measurementMatrix = H

        # Process noise covariance Q
        self._kf.processNoiseCov = np.eye(_STATE_DIM, dtype=np.float64) * self._process_noise

        # Measurement noise covariance R
        self._kf.measurementNoiseCov = (
            np.eye(_MEAS_DIM, dtype=np.float64) * self._measurement_noise
        )

        # Initial posterior error covariance P
        self._kf.errorCovPost = (
            np.eye(_STATE_DIM, dtype=np.float64) * _DEFAULT_ERROR_COVARIANCE
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self, x: float, y: float) -> None:
        """Reinitialize the filter at a known position with zero velocity/acceleration."""
        state = np.zeros((_STATE_DIM, 1), dtype=np.float64)
        state[0, 0] = x
        state[1, 0] = y
        self._kf.statePost = state
        self._kf.errorCovPost = (
            np.eye(_STATE_DIM, dtype=np.float64) * _DEFAULT_ERROR_COVARIANCE
        )
        self._initialized = True
        logger.debug("BallKalmanFilter reset to (%.1f, %.1f)", x, y)

    def predict(self) -> np.ndarray:
        """
        Advance the filter by one time step.

        Returns the predicted state vector [x, y, vx, vy, ax, ay].
        """
        if not self._initialized:
            return np.zeros(_STATE_DIM, dtype=np.float64)
        predicted = self._kf.predict()
        return predicted.flatten()

    def update(self, measurement: tuple[float, float]) -> np.ndarray:
        """
        Correct the filter with a new observation and return the corrected state.

        Parameters
        ----------
        measurement:
            (x, y) position observed by the detector (pixels).

        Returns
        -------
        np.ndarray
            Corrected state [x, y, vx, vy, ax, ay].
        """
        meas_vec = np.array([[measurement[0]], [measurement[1]]], dtype=np.float64)

        if not self._initialized:
            self.reset(measurement[0], measurement[1])
            return self._kf.statePost.flatten()

        # Predict first, then correct
        self._kf.predict()
        corrected = self._kf.correct(meas_vec)
        return corrected.flatten()

    def predict_only(self) -> tuple[float, float]:
        """
        Predict position without any measurement (for occluded frames).

        Returns
        -------
        (x, y) predicted ball center in pixels.
        """
        state = self.predict()
        return (float(state[0]), float(state[1]))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_initialized(self) -> bool:
        """True once at least one measurement has been fed."""
        return self._initialized

    @property
    def velocity(self) -> tuple[float, float]:
        """Current estimated velocity (vx, vy) in pixels/frame."""
        if not self._initialized:
            return (0.0, 0.0)
        state = self._kf.statePost.flatten()
        return (float(state[2]), float(state[3]))

    @property
    def speed(self) -> float:
        """Scalar speed magnitude in pixels/frame."""
        vx, vy = self.velocity
        return float(np.hypot(vx, vy))


# ---------------------------------------------------------------------------
# BallTrajectoryBuffer
# ---------------------------------------------------------------------------

@dataclass
class _TrajectoryPoint:
    """A single entry in the trajectory buffer."""
    x: float
    y: float
    frame_id: int
    is_predicted: bool = False


class BallTrajectoryBuffer:
    """
    Rolling buffer of smoothed ball positions.

    Provides arc detection, peak finding, and ascending/descending
    direction classification.
    """

    def __init__(self, maxlen: int = _DEFAULT_BUFFER_MAXLEN) -> None:
        self._maxlen = maxlen
        self._buffer: deque[_TrajectoryPoint] = deque(maxlen=maxlen)

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------

    def push(
        self,
        x: float,
        y: float,
        frame_id: int,
        is_predicted: bool = False,
    ) -> None:
        """Append a new position to the buffer."""
        self._buffer.append(_TrajectoryPoint(x=x, y=y, frame_id=frame_id,
                                              is_predicted=is_predicted))

    # ------------------------------------------------------------------
    # Smoothing
    # ------------------------------------------------------------------

    def get_smooth_arc(self) -> list[tuple[float, float]]:
        """
        Return smoothed (x, y) positions.

        Uses Savitzky-Golay filter if scipy is available, otherwise a
        simple centred moving average.
        """
        pts = list(self._buffer)
        if len(pts) < 3:
            return [(p.x, p.y) for p in pts]

        xs = np.array([p.x for p in pts], dtype=np.float64)
        ys = np.array([p.y for p in pts], dtype=np.float64)

        try:
            from scipy.signal import savgol_filter  # type: ignore
            window = min(_SAVGOL_WINDOW, len(pts))
            if window % 2 == 0:
                window -= 1
            polyorder = min(_SAVGOL_POLYORDER, window - 1)
            xs_smooth = savgol_filter(xs, window, polyorder)
            ys_smooth = savgol_filter(ys, window, polyorder)
        except ImportError:
            # Fallback: centred moving average
            xs_smooth = self._moving_average(xs, _MOVING_AVG_WINDOW)
            ys_smooth = self._moving_average(ys, _MOVING_AVG_WINDOW)

        return list(zip(xs_smooth.tolist(), ys_smooth.tolist()))

    @staticmethod
    def _moving_average(arr: np.ndarray, window: int) -> np.ndarray:
        """Simple symmetric moving average with edge padding."""
        half = window // 2
        padded = np.pad(arr, (half, half), mode="edge")
        kernel = np.ones(window, dtype=np.float64) / window
        return np.convolve(padded, kernel, mode="valid")

    # ------------------------------------------------------------------
    # Arc analysis
    # ------------------------------------------------------------------

    def detect_arc_peak(self) -> Optional[tuple[int, float, float]]:
        """
        Find the highest point in the buffered trajectory (minimum Y, since
        Y increases downward in image coordinates).

        Returns
        -------
        (frame_id, x, y) at the arc peak, or None if the buffer is too short
        or the arc height is below the minimum threshold.
        """
        pts = list(self._buffer)
        if len(pts) < 5:
            return None

        ys = [p.y for p in pts]
        peak_idx = int(np.argmin(ys))

        # Require the peak to be interior (not at an edge)
        if peak_idx == 0 or peak_idx == len(pts) - 1:
            return None

        arc_h = self.arc_height_px()
        if arc_h < _ARC_PEAK_MIN_HEIGHT_PX:
            return None

        peak = pts[peak_idx]
        return (peak.frame_id, peak.x, peak.y)

    def is_ascending(self) -> bool:
        """
        True if the ball is currently moving upward (Y decreasing over the
        last few frames — i.e. vy < 0 in image coordinates).
        """
        pts = list(self._buffer)
        if len(pts) < 4:
            return False
        recent_ys = [p.y for p in pts[-4:]]
        dy = recent_ys[-1] - recent_ys[0]
        return dy < 0.0

    def is_descending(self) -> bool:
        """
        True if the ball is currently moving downward (Y increasing over the
        last few frames).
        """
        pts = list(self._buffer)
        if len(pts) < 4:
            return False
        recent_ys = [p.y for p in pts[-4:]]
        dy = recent_ys[-1] - recent_ys[0]
        return dy > 0.0

    def arc_height_px(self) -> float:
        """
        Compute the maximum vertical extent of the arc from the release point
        (first point in the buffer) to the peak.

        Returns height in pixels, or 0.0 if no clear peak exists.
        """
        pts = list(self._buffer)
        if len(pts) < 3:
            return 0.0

        ys = [p.y for p in pts]
        peak_y = min(ys)
        start_y = ys[0]
        height = start_y - peak_y   # positive because image Y increases downward
        return max(0.0, float(height))

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import math

    print("=== BallKalmanFilter self-test ===")
    kf = BallKalmanFilter(dt=1 / 30, process_noise=1e-3, measurement_noise=5.0)
    assert not kf.is_initialized

    # Feed a few measurements along a diagonal trajectory
    trajectory_measurements = [(100 + i * 5, 200 + i * 3) for i in range(20)]
    states = []
    for meas in trajectory_measurements:
        state = kf.update(meas)
        states.append(state)

    print(f"  Last corrected state: {states[-1].round(2)}")
    print(f"  Velocity: {kf.velocity}")
    print(f"  Speed: {kf.speed:.2f} px/frame")

    # Test predict_only (occlusion)
    for _ in range(5):
        px, py = kf.predict_only()
    print(f"  After 5 predict-only steps: ({px:.1f}, {py:.1f})")

    print("\n=== BallTrajectoryBuffer self-test ===")
    buf = BallTrajectoryBuffer(maxlen=60)

    # Simulate a parabolic arc
    for i in range(40):
        t = i / 39.0
        x = 100 + t * 400
        y = 300 - 120 * math.sin(math.pi * t)   # arc in image coords
        buf.push(x, y, frame_id=i)

    smooth = buf.get_smooth_arc()
    print(f"  Smoothed arc points: {len(smooth)}")

    peak = buf.detect_arc_peak()
    if peak:
        fid, px, py = peak
        print(f"  Arc peak: frame={fid}, x={px:.1f}, y={py:.1f}")
    else:
        print("  No arc peak detected (below threshold)")

    print(f"  Arc height: {buf.arc_height_px():.1f} px")
    print(f"  Ascending: {buf.is_ascending()}")
    print(f"  Descending: {buf.is_descending()}")
    print("Self-test passed.")
