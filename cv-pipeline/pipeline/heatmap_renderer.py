"""
Songa CV — Heatmap Renderer
Generates spatial heatmap images from player tracking and shot data.
Uses Gaussian kernel density estimation on top of a basketball court template.
"""
from __future__ import annotations

import base64
import logging
import math
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Court colours (BGR)
# ---------------------------------------------------------------------------
_BG_COLOR = (11, 13, 14)        # #0E0D0B → BGR
_LINE_COLOR = (49, 54, 58)      # #3A3631 → BGR
_BASKET_COLOR = (80, 116, 232)  # muted orange-ish


# ---------------------------------------------------------------------------
# CourtTemplate
# ---------------------------------------------------------------------------

class CourtTemplate:
    """
    Renders a top-down NBA basketball court in BGR at 1000x527 pixels.
    Origin corresponds to bottom-left corner of the court (28.65 x 15.24 m).
    """

    WIDTH_PX: int = 1000
    HEIGHT_PX: int = 527
    SCALE: float = WIDTH_PX / 28.65   # pixels per metre  ≈ 34.9 px/m

    # Court dimensions (metres)
    _W = 28.65
    _H = 15.24

    def court_to_pixel(self, court_x_m: float, court_y_m: float) -> tuple[int, int]:
        """Convert real court coordinates (metres) to image pixel coordinates."""
        px = int(round(court_x_m * self.SCALE))
        # Image y-axis is flipped relative to court y-axis
        py = int(round(self.HEIGHT_PX - court_y_m * self.SCALE))
        return (px, py)

    def draw_court(
        self,
        bg_color: tuple[int, int, int] = (14, 13, 11),
        line_color: tuple[int, int, int] = (58, 54, 49),
    ) -> np.ndarray:
        """
        Draw an NBA-standard court template and return a BGR numpy array
        of shape (527, 1000, 3).
        """
        img = np.full((self.HEIGHT_PX, self.WIDTH_PX, 3), bg_color, dtype=np.uint8)
        lw = 2  # line width

        def pt(xm: float, ym: float) -> tuple[int, int]:
            return self.court_to_pixel(xm, ym)

        # --- Outer boundary ---
        tl = pt(0.0, self._H)
        br = pt(self._W, 0.0)
        cv2.rectangle(img, tl, br, line_color, lw)

        # --- Centre line ---
        cv2.line(img, pt(self._W / 2, 0.0), pt(self._W / 2, self._H), line_color, lw)

        # --- Centre circle (r=1.8m) ---
        cx, cy = pt(self._W / 2, self._H / 2)
        r_centre = int(round(1.8 * self.SCALE))
        cv2.circle(img, (cx, cy), r_centre, line_color, lw)

        # --- Paint / key areas (left and right) ---
        # Left paint: x=0..4.57, y=3.66..11.58
        cv2.rectangle(img, pt(0.0, 11.58), pt(4.57, 3.66), line_color, lw)
        # Right paint
        cv2.rectangle(img, pt(24.08, 11.58), pt(self._W, 3.66), line_color, lw)

        # --- Free-throw lines (already part of paint rectangle but draw circles too) ---
        # Left FT circle (radius 1.8m centred on FT line at x=4.57, y=7.62)
        ftl_cx, ftl_cy = pt(4.57, 7.62)
        ft_r = int(round(1.8 * self.SCALE))
        cv2.circle(img, (ftl_cx, ftl_cy), ft_r, line_color, lw)
        # Right FT circle
        ftr_cx, ftr_cy = pt(24.08, 7.62)
        cv2.circle(img, (ftr_cx, ftr_cy), ft_r, line_color, lw)

        # --- Three-point arcs ---
        # Left 3pt arc: radius 7.24m from basket at (1.575, 7.62)
        # Corner lines at x=0..6.7, y=0..2 and y=13.24..15.24 are already implied by
        # the polygon zones; draw the curved arc portion with cv2.ellipse
        b_left = pt(1.575, 7.62)
        b_right = pt(27.075, 7.62)
        arc_r_px = int(round(6.75 * self.SCALE))  # 3pt arc radius ≈ 6.75m

        # Left 3pt arc (semi-circle opening to the right)
        cv2.ellipse(img, b_left, (arc_r_px, arc_r_px), 0, -70, 70, line_color, lw)
        # Left corner lines
        cv2.line(img, pt(0.0, 2.0), pt(6.7, 2.0), line_color, lw)
        cv2.line(img, pt(0.0, 13.24), pt(6.7, 13.24), line_color, lw)

        # Right 3pt arc
        cv2.ellipse(img, b_right, (arc_r_px, arc_r_px), 0, 110, 250, line_color, lw)
        # Right corner lines
        cv2.line(img, pt(self._W, 2.0), pt(21.95, 2.0), line_color, lw)
        cv2.line(img, pt(self._W, 13.24), pt(21.95, 13.24), line_color, lw)

        # --- Baskets (circles) ---
        basket_r = int(round(0.23 * self.SCALE))  # ~23cm rim radius
        cv2.circle(img, b_left, max(basket_r, 4), (80, 116, 200), 2)
        cv2.circle(img, b_right, max(basket_r, 4), (80, 116, 200), 2)

        # --- Backboards ---
        cv2.line(img, pt(1.2, 5.9), pt(1.2, 9.34), line_color, lw)
        cv2.line(img, pt(self._W - 1.2, 5.9), pt(self._W - 1.2, 9.34), line_color, lw)

        return img


# ---------------------------------------------------------------------------
# HeatmapRenderer
# ---------------------------------------------------------------------------

class HeatmapRenderer:
    """
    Renders various types of heatmaps on top of the court template.
    """

    def __init__(
        self,
        resolution: tuple[int, int] = (1000, 527),
        sigma_m: float = 1.2,
    ) -> None:
        self.width, self.height = resolution
        self._court = CourtTemplate()
        # sigma in pixels
        self._sigma_px = sigma_m * CourtTemplate.SCALE

    # ------------------------------------------------------------------
    # Gaussian KDE helpers
    # ------------------------------------------------------------------

    def _gaussian_kde_numpy(
        self,
        positions_px: list[tuple[int, int]],
    ) -> np.ndarray:
        """
        Manual Gaussian KDE using numpy when scipy is unavailable.
        Returns a float32 array of shape (height, width).
        """
        density = np.zeros((self.height, self.width), dtype=np.float32)
        if not positions_px:
            return density

        sigma = max(self._sigma_px, 1.0)
        # Use a 6-sigma window to limit computation
        half_win = int(math.ceil(sigma * 3))

        yy, xx = np.mgrid[0:self.height, 0:self.width]

        for px, py in positions_px:
            # Restrict to bounding box for speed
            x0 = max(0, px - half_win)
            x1 = min(self.width, px + half_win + 1)
            y0 = max(0, py - half_win)
            y1 = min(self.height, py + half_win + 1)

            local_xx = xx[y0:y1, x0:x1]
            local_yy = yy[y0:y1, x0:x1]
            kernel = np.exp(-0.5 * ((local_xx - px) ** 2 + (local_yy - py) ** 2) / (sigma ** 2))
            density[y0:y1, x0:x1] += kernel.astype(np.float32)

        return density

    def _to_pixel(self, xm: float, ym: float) -> tuple[int, int]:
        return self._court.court_to_pixel(xm, ym)

    # ------------------------------------------------------------------
    # Player heatmap
    # ------------------------------------------------------------------

    def render_player_heatmap(
        self,
        positions_m: list[tuple[float, float]],
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Render a player position heatmap (INFERNO colormap) blended over the court.

        positions_m: list of (court_x_m, court_y_m) tuples.
        """
        court_img = self._court.draw_court()
        positions_px = [self._to_pixel(x, y) for x, y in positions_m]

        # Try scipy KDE first, fall back to numpy manual
        density: Optional[np.ndarray] = None
        if positions_px:
            try:
                from scipy.stats import gaussian_kde  # type: ignore
                pts = np.array([[p[0] for p in positions_px], [p[1] for p in positions_px]], dtype=np.float64)
                bw = self._sigma_px / (np.std(pts, axis=1).mean() + 1e-6)
                kde = gaussian_kde(pts, bw_method=bw)
                xx, yy = np.meshgrid(np.arange(self.width), np.arange(self.height))
                grid = np.vstack([xx.ravel(), yy.ravel()])
                density = kde(grid).reshape(self.height, self.width).astype(np.float32)
            except Exception:
                density = self._gaussian_kde_numpy(positions_px)
        else:
            density = np.zeros((self.height, self.width), dtype=np.float32)

        # Normalise to 0-255
        dmax = density.max()
        if dmax > 0:
            density = density / dmax
        heat_u8 = (density * 255).astype(np.uint8)

        # Apply INFERNO colormap
        heat_colored = cv2.applyColorMap(heat_u8, cv2.COLORMAP_INFERNO)

        # Alpha blend: where density is high → heatmap; elsewhere → court
        alpha = density[..., np.newaxis]  # (H, W, 1)
        blended = (
            heat_colored.astype(np.float32) * alpha
            + court_img.astype(np.float32) * (1 - alpha)
        ).astype(np.uint8)

        if output_path:
            cv2.imwrite(output_path, blended)
            logger.info("Player heatmap saved to %s", output_path)

        return blended

    # ------------------------------------------------------------------
    # Shot heatmap
    # ------------------------------------------------------------------

    def render_shot_heatmap(
        self,
        shots: list[tuple[float, float, bool]],
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Render shot locations as coloured circles on the court.

        shots: list of (court_x_m, court_y_m, is_made).
        Made shots = green (#7BE0A8 → BGR 168, 224, 123)
        Missed shots = dark red (BGR 60, 60, 180)
        Circle size is proportional to local density.
        """
        img = self._court.draw_court()

        if not shots:
            if output_path:
                cv2.imwrite(output_path, img)
            return img

        # Convert to pixel
        shot_px = [(self._to_pixel(x, y), made) for x, y, made in shots]

        # Compute local density per shot using proximity counting
        # (simple: number of shots within 50px)
        PROXIMITY_PX = 50
        densities = []
        for i, (pi, _) in enumerate(shot_px):
            count = sum(
                1 for j, (pj, _) in enumerate(shot_px)
                if i != j and math.hypot(pi[0] - pj[0], pi[1] - pj[1]) < PROXIMITY_PX
            )
            densities.append(count)

        max_density = max(densities) if densities else 0

        BASE_R = 8
        MAX_R = 22

        for (px, made), density in zip(shot_px, densities):
            radius = BASE_R + int((MAX_R - BASE_R) * (density / max(max_density, 1)))
            if made:
                color = (168, 224, 123)   # #7BE0A8 → BGR
            else:
                color = (60, 60, 160)     # dark red-ish

            cv2.circle(img, px, radius, color, -1)
            cv2.circle(img, px, radius, (200, 200, 200), 1)  # thin outline

        if output_path:
            cv2.imwrite(output_path, img)
            logger.info("Shot heatmap saved to %s", output_path)

        return img

    # ------------------------------------------------------------------
    # Zone heatmap
    # ------------------------------------------------------------------

    def render_zone_heatmap(
        self,
        zone_stats: dict,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Colorise shot zones by efficiency and overlay text stats.

        zone_stats: {zone_name: {made, attempted, pct}}
        Gradient: slate (#3A3631) at 0%, orange (#E8743C) at 40%, signal (#7BE0A8) at 60%+
        """
        img = self._court.draw_court()

        # Zone polygons in metres, mapped to pixel polygons
        ZONE_POLYGONS: dict[str, list[tuple[float, float]]] = {
            "paint_left":         [(0.0, 3.66), (4.57, 3.66), (4.57, 11.58), (0.0, 11.58)],
            "paint_right":        [(24.08, 3.66), (28.65, 3.66), (28.65, 11.58), (24.08, 11.58)],
            "mid_range_left":     [(4.57, 2.0), (13.0, 2.0), (13.0, 13.24), (4.57, 13.24)],
            "mid_range_right":    [(15.65, 2.0), (24.08, 2.0), (24.08, 13.24), (15.65, 13.24)],
            "mid_range_center":   [(13.0, 3.0), (15.65, 3.0), (15.65, 12.24), (13.0, 12.24)],
            "corner_3_left_bot":  [(0.0, 0.0), (6.7, 0.0), (6.7, 2.0), (0.0, 2.0)],
            "corner_3_left_top":  [(0.0, 13.24), (6.7, 13.24), (6.7, 15.24), (0.0, 15.24)],
            "corner_3_right_bot": [(21.95, 0.0), (28.65, 0.0), (28.65, 2.0), (21.95, 2.0)],
            "corner_3_right_top": [(21.95, 13.24), (28.65, 13.24), (28.65, 15.24), (21.95, 15.24)],
            "arc_3_left":         [(0.0, 2.0), (6.7, 2.0), (10.0, 3.5), (10.0, 11.74), (6.7, 13.24), (0.0, 13.24)],
            "arc_3_right":        [(18.65, 2.0), (28.65, 2.0), (28.65, 13.24), (21.95, 13.24), (18.65, 11.74), (18.65, 3.5)],
            "top_key_3":          [(10.0, 3.5), (18.65, 3.5), (18.65, 11.74), (10.0, 11.74)],
        }

        ZONE_CENTRES_M: dict[str, tuple[float, float]] = {
            "paint_left":         (2.3, 7.62),
            "paint_right":        (26.35, 7.62),
            "mid_range_left":     (8.8, 7.62),
            "mid_range_right":    (20.0, 7.62),
            "mid_range_center":   (14.3, 7.62),
            "corner_3_left_bot":  (3.35, 1.0),
            "corner_3_left_top":  (3.35, 14.2),
            "corner_3_right_bot": (25.3, 1.0),
            "corner_3_right_top": (25.3, 14.2),
            "arc_3_left":         (4.5, 7.62),
            "arc_3_right":        (24.1, 7.62),
            "top_key_3":          (14.3, 7.62),
        }

        def _lerp_color(t: float) -> tuple[int, int, int]:
            """
            Colour gradient:
              0.0  → slate   #3A3631 → BGR (49,54,58)
              0.4  → orange  #E8743C → BGR (60,116,232)
              0.67+ → signal #7BE0A8 → BGR (168,224,123)
            """
            t = max(0.0, min(1.0, t))
            if t <= 0.4:
                s = t / 0.4
                r = int(49 + s * (60 - 49))
                g = int(54 + s * (116 - 54))
                b = int(58 + s * (232 - 58))
            else:
                s = (t - 0.4) / 0.6
                s = min(s, 1.0)
                r = int(60 + s * (168 - 60))
                g = int(116 + s * (224 - 116))
                b = int(232 + s * (123 - 232))
            return (r, g, b)

        overlay = img.copy()

        for zone, stats in zone_stats.items():
            if zone not in ZONE_POLYGONS:
                continue

            poly_m = ZONE_POLYGONS[zone]
            poly_px = np.array([self._to_pixel(x, y) for x, y in poly_m], dtype=np.int32)

            pct = float(stats.get("pct", stats.get("made", 0) / max(stats.get("attempted", 1), 1)))
            color = _lerp_color(pct / 0.67)

            cv2.fillPoly(overlay, [poly_px], color)

        # Alpha blend zones
        cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)

        # Overlay text stats in each zone
        font = cv2.FONT_HERSHEY_SIMPLEX

        for zone, stats in zone_stats.items():
            if zone not in ZONE_CENTRES_M:
                continue
            cx, cy = self._to_pixel(*ZONE_CENTRES_M[zone])
            made = int(stats.get("made", 0))
            attempted = int(stats.get("attempted", 0))
            pct = float(stats.get("pct", made / max(attempted, 1)))

            line1 = f"{made}/{attempted}"
            line2 = f"{pct*100:.0f}%"

            scale = 0.35
            thickness = 1
            text_color = (240, 240, 240)

            # Centre each line
            (w1, h1), _ = cv2.getTextSize(line1, font, scale, thickness)
            (w2, h2), _ = cv2.getTextSize(line2, font, scale, thickness)

            cv2.putText(img, line1, (cx - w1 // 2, cy - 2), font, scale, text_color, thickness, cv2.LINE_AA)
            cv2.putText(img, line2, (cx - w2 // 2, cy + h2 + 2), font, scale, text_color, thickness, cv2.LINE_AA)

        if output_path:
            cv2.imwrite(output_path, img)
            logger.info("Zone heatmap saved to %s", output_path)

        return img


# ---------------------------------------------------------------------------
# TrajectoryRenderer
# ---------------------------------------------------------------------------

class TrajectoryRenderer:
    """Renders player movement trajectories onto a video frame."""

    # HOME = court orange #E8743C → BGR (60, 116, 232)
    # AWAY = signal #7BE0A8 → BGR (168, 224, 123)
    HOME_COLOR_BGR: tuple[int, int, int] = (60, 116, 232)
    AWAY_COLOR_BGR: tuple[int, int, int] = (168, 224, 123)
    DEFAULT_COLOR_BGR: tuple[int, int, int] = (180, 180, 180)

    def render_trajectories(
        self,
        frame: np.ndarray,
        trajectories: dict[int, list[tuple[float, float]]],
        team_labels: dict[int, int] = {},
    ) -> np.ndarray:
        """
        Draw player trajectories (in pixel space) onto a copy of frame.

        trajectories: {track_id: [(px, py), ...]} oldest → newest
        team_labels:  {track_id: team_id}  where team_id 1=HOME, 2=AWAY
        """
        out = frame.copy()
        MIN_ALPHA = 0.2
        RADIUS = 5

        for track_id, positions in trajectories.items():
            if not positions:
                continue

            team_id = team_labels.get(track_id)
            if team_id == 1:
                base_color = self.HOME_COLOR_BGR
            elif team_id == 2:
                base_color = self.AWAY_COLOR_BGR
            else:
                base_color = self.DEFAULT_COLOR_BGR

            n = len(positions)

            for i, pos in enumerate(positions):
                # alpha increases from MIN_ALPHA (oldest) to 1.0 (newest)
                alpha = MIN_ALPHA + (1.0 - MIN_ALPHA) * (i / max(n - 1, 1))

                px, py = int(pos[0]), int(pos[1])

                # Draw line segment from previous point
                if i > 0:
                    prev = positions[i - 1]
                    ppx, ppy = int(prev[0]), int(prev[1])
                    # Blend line onto out
                    line_overlay = out.copy()
                    cv2.line(line_overlay, (ppx, ppy), (px, py), base_color, 2, cv2.LINE_AA)
                    cv2.addWeighted(line_overlay, alpha, out, 1 - alpha, 0, out)

            # Current position — filled circle at full opacity
            if positions:
                last = positions[-1]
                lx, ly = int(last[0]), int(last[1])
                cv2.circle(out, (lx, ly), RADIUS, base_color, -1, cv2.LINE_AA)

        return out
