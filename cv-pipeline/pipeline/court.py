"""
Songa CV — Court Model
Homography-based court calibration and shot zone classification.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NBA court dimensions (metres)
# Origin: bottom-left corner of the court when viewed from above.
# ---------------------------------------------------------------------------
COURT_WIDTH_M = 28.65   # sideline to sideline
COURT_HEIGHT_M = 15.24  # baseline to baseline

# 12 standard keypoints: name -> (x_m, y_m)
COURT_KEYPOINTS: dict[str, tuple[float, float]] = {
    "corner_bl":        (0.0,          0.0),
    "corner_br":        (COURT_WIDTH_M, 0.0),
    "corner_tl":        (0.0,          COURT_HEIGHT_M),
    "corner_tr":        (COURT_WIDTH_M, COURT_HEIGHT_M),
    "ft_left_bot":      (4.57,         3.66),   # left free-throw lane corner
    "ft_left_top":      (4.57,         11.58),
    "ft_right_bot":     (24.08,        3.66),
    "ft_right_top":     (24.08,        11.58),
    "center_left":      (14.325,       0.0),
    "center_right":     (14.325,       COURT_HEIGHT_M),
    "basket_left":      (1.575,        7.62),   # left basket projection on floor
    "basket_right":     (27.075,       7.62),
}


@dataclass
class CourtCalibrator:
    """
    Computes and applies homography between pixel space and court metres.

    Usage:
        H = calibrator.compute_homography(src_px, dst_m)
        court_pt = calibrator.project_to_court(px_pt, H)
    """

    def compute_homography(
        self,
        src_points: list[tuple[float, float]],
        dst_points: list[tuple[float, float]],
    ) -> Optional[np.ndarray]:
        """
        Compute homography matrix H such that dst ~ H @ src (in homogeneous coords).

        Requires at least 4 point correspondences.
        Returns None on failure.
        """
        if len(src_points) < 4 or len(dst_points) < 4:
            logger.error(
                "compute_homography needs >= 4 points (got %d)", len(src_points)
            )
            return None

        src = np.array(src_points, dtype=np.float32)
        dst = np.array(dst_points, dtype=np.float32)

        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if H is None:
            logger.error("findHomography failed — collinear or insufficient points?")
        return H

    def project_to_court(
        self,
        pixel_point: tuple[float, float],
        H: np.ndarray,
    ) -> tuple[float, float]:
        """
        Project a single pixel point to court coordinates (metres).
        """
        pt = np.array([[pixel_point]], dtype=np.float32)
        projected = cv2.perspectiveTransform(pt, H)
        x, y = float(projected[0][0][0]), float(projected[0][0][1])
        return (x, y)

    def project_batch(
        self,
        pixel_points: list[tuple[float, float]],
        H: np.ndarray,
    ) -> np.ndarray:
        """
        Project a list of pixel points to court coordinates.

        Returns an (N, 2) numpy array in metres.
        """
        if not pixel_points:
            return np.empty((0, 2), dtype=np.float32)
        pts = np.array(pixel_points, dtype=np.float32).reshape(-1, 1, 2)
        projected = cv2.perspectiveTransform(pts, H)
        return projected.reshape(-1, 2)

    def auto_calibrate(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Attempt automatic court calibration from a single frame using line detection.

        This is a best-effort approach: detects the court rectangle via edge detection
        and contour analysis, then maps it to known court dimensions.
        Returns None if calibration cannot be determined.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        edges = cv2.Canny(blurred, 30, 100)

        # Find the largest quadrilateral contour
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        contours_sorted = sorted(contours, key=cv2.contourArea, reverse=True)
        court_contour = None
        for c in contours_sorted[:10]:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                court_contour = approx
                break

        if court_contour is None:
            logger.warning("Auto-calibration: no quadrilateral court boundary found.")
            return None

        h, w = frame.shape[:2]
        pts = court_contour.reshape(4, 2).astype(np.float32)

        # Order points: top-left, top-right, bottom-right, bottom-left
        pts = self._order_points(pts)
        dst = np.array([
            [0.0, 0.0],
            [COURT_WIDTH_M, 0.0],
            [COURT_WIDTH_M, COURT_HEIGHT_M],
            [0.0, COURT_HEIGHT_M],
        ], dtype=np.float32)

        H, _ = cv2.findHomography(pts, dst)
        return H

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Order 4 points as [top-left, top-right, bottom-right, bottom-left]."""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]   # top-left
        rect[2] = pts[np.argmax(s)]   # bottom-right
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # top-right
        rect[3] = pts[np.argmax(diff)]  # bottom-left
        return rect


# ---------------------------------------------------------------------------
# Shot zone polygons (NBA standard)
# ---------------------------------------------------------------------------

try:
    from shapely.geometry import Point, Polygon  # type: ignore
    _SHAPELY_AVAILABLE = True
except ImportError:
    _SHAPELY_AVAILABLE = False
    logger.warning("shapely not installed — ShotZoneClassifier will use fallback geometry.")


def _poly(coords: list[tuple[float, float]]):
    """Create a Shapely Polygon or None if shapely unavailable."""
    if _SHAPELY_AVAILABLE:
        from shapely.geometry import Polygon as P
        return P(coords)
    return coords  # store raw coords as fallback


# Zone definitions in court metres (origin: bottom-left corner)
_ZONES: dict[str, object] = {
    "paint_left": _poly([
        (0.0, 3.66), (4.57, 3.66), (4.57, 11.58), (0.0, 11.58)
    ]),
    "paint_right": _poly([
        (24.08, 3.66), (COURT_WIDTH_M, 3.66),
        (COURT_WIDTH_M, 11.58), (24.08, 11.58)
    ]),
    "mid_range_left": _poly([
        (4.57, 2.0), (13.0, 2.0), (13.0, 13.24), (4.57, 13.24)
    ]),
    "mid_range_right": _poly([
        (15.65, 2.0), (24.08, 2.0), (24.08, 13.24), (15.65, 13.24)
    ]),
    "mid_range_center": _poly([
        (13.0, 3.0), (15.65, 3.0), (15.65, 12.24), (13.0, 12.24)
    ]),
    "corner_3_left_bot": _poly([
        (0.0, 0.0), (6.7, 0.0), (6.7, 2.0), (0.0, 2.0)
    ]),
    "corner_3_left_top": _poly([
        (0.0, 13.24), (6.7, 13.24), (6.7, COURT_HEIGHT_M), (0.0, COURT_HEIGHT_M)
    ]),
    "corner_3_right_bot": _poly([
        (21.95, 0.0), (COURT_WIDTH_M, 0.0),
        (COURT_WIDTH_M, 2.0), (21.95, 2.0)
    ]),
    "corner_3_right_top": _poly([
        (21.95, 13.24), (COURT_WIDTH_M, 13.24),
        (COURT_WIDTH_M, COURT_HEIGHT_M), (21.95, COURT_HEIGHT_M)
    ]),
    "arc_3_left": _poly([
        (0.0, 2.0), (6.7, 2.0), (10.0, 3.5), (10.0, 11.74),
        (6.7, 13.24), (0.0, 13.24)
    ]),
    "arc_3_right": _poly([
        (18.65, 2.0), (COURT_WIDTH_M, 2.0),
        (COURT_WIDTH_M, 13.24), (21.95, 13.24),
        (18.65, 11.74), (18.65, 3.5)
    ]),
    "top_key_3": _poly([
        (10.0, 3.5), (18.65, 3.5), (18.65, 11.74), (10.0, 11.74)
    ]),
}


def _point_in_poly_fallback(
    x: float, y: float, coords: list[tuple[float, float]]
) -> bool:
    """Ray-casting point-in-polygon for fallback when shapely is absent."""
    n = len(coords)
    inside = False
    px, py = x, y
    j = n - 1
    for i in range(n):
        xi, yi = coords[i]
        xj, yj = coords[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


@dataclass
class Shot:
    """A single shot attempt with court location."""
    frame_id: int
    shooter_id: int
    court_point: tuple[float, float]
    zone: str = "unknown"
    made: bool = False


class ShotZoneClassifier:
    """
    Classifies court positions into NBA-standard shot zones.
    """

    def classify_shot(self, court_point: tuple[float, float]) -> str:
        """
        Return the zone name for a given court position (metres).
        Returns 'unknown' if the point falls in no defined zone.
        """
        x, y = court_point
        for zone_name, poly in _ZONES.items():
            if _SHAPELY_AVAILABLE:
                from shapely.geometry import Point as P
                if poly.contains(P(x, y)):  # type: ignore
                    return zone_name
            else:
                if _point_in_poly_fallback(x, y, poly):  # type: ignore
                    return zone_name
        return "unknown"

    def get_zone_stats(
        self, shots: list[Shot]
    ) -> dict[str, dict[str, float]]:
        """
        Aggregate shot results by zone.

        Returns: {zone: {made, attempted, pct}}
        """
        stats: dict[str, dict[str, int]] = {}
        for shot in shots:
            z = shot.zone or "unknown"
            if z not in stats:
                stats[z] = {"made": 0, "attempted": 0}
            stats[z]["attempted"] += 1
            if shot.made:
                stats[z]["made"] += 1

        result: dict[str, dict[str, float]] = {}
        for z, s in stats.items():
            pct = s["made"] / s["attempted"] if s["attempted"] > 0 else 0.0
            result[z] = {
                "made": float(s["made"]),
                "attempted": float(s["attempted"]),
                "pct": round(pct, 3),
            }
        return result
