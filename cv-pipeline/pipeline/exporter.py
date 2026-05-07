"""
Songa CV — Exporter
Serialises MatchSummary to JSON, CSV and PDF-ready structures.
"""
from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .stats import MatchSummary

logger = logging.getLogger(__name__)


class Exporter:
    """
    Export MatchSummary to various output formats.

    Formats supported:
    - JSON  : full structured output for the frontend / API
    - CSV   : one row per player, suitable for spreadsheet analysis
    - PDF-ready dict : pre-formatted sections for PDF generation
    """

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def to_json(self, summary: MatchSummary, output_path: str | Path) -> Path:
        """
        Write the full match summary to a JSON file.

        Returns the resolved output path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = summary.to_dict()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=_json_fallback)

        logger.info("JSON exported to %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # CSV
    # ------------------------------------------------------------------

    def to_csv(self, summary: MatchSummary, output_path: str | Path) -> Path:
        """
        Write per-player statistics to a CSV file.

        Each row represents one tracked player.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "player_id",
            "total_distance_m",
            "avg_speed_ms",
            "max_speed_ms",
            "time_in_paint_s",
            "shots_attempted",
            "shots_made",
            "shot_pct",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for pid, stats in summary.player_stats.items():
                row = stats.to_dict()
                row.pop("shot_zones", None)
                writer.writerow(row)

        logger.info("CSV exported to %s", output_path)
        return output_path

    # ------------------------------------------------------------------
    # PDF-ready dict
    # ------------------------------------------------------------------

    def to_pdf_data(self, summary: MatchSummary) -> dict[str, Any]:
        """
        Return a structured dict suitable for PDF generation libraries
        (e.g. reportlab, weasyprint or a Jinja2 template).

        Sections:
          - header     : match metadata
          - team       : team-level statistics
          - players    : sorted list of player stat rows
          - shot_chart : zone breakdown table
          - timeline   : key events ordered by time
        """
        meta = summary.to_dict()["meta"]

        players_sorted = sorted(
            summary.player_stats.values(),
            key=lambda p: p.shots_attempted,
            reverse=True,
        )

        timeline = sorted(
            summary.key_events,
            key=lambda e: e.get("timestamp", e.get("frame_id", 0)),
        )

        return {
            "header": {
                "duration_s": meta["duration_s"],
                "fps": meta["fps"],
                "players_tracked": meta["players_tracked"],
            },
            "team": summary.team_stats.to_dict(),
            "players": [p.to_dict() for p in players_sorted],
            "shot_chart": summary.shot_chart,
            "timeline": timeline,
        }

    # ------------------------------------------------------------------
    # Heatmap helper
    # ------------------------------------------------------------------

    def generate_heatmap_data(
        self, shot_chart: dict[str, dict[str, float]]
    ) -> list[dict[str, Any]]:
        """
        Convert a shot_chart dict into a list of weighted court points
        suitable for a frontend heatmap visualisation.

        Each point has x_m, y_m (court centre of the zone) and density
        (normalised 0.0–1.0 based on attempts).

        Returns a list of dicts: [{x_m, y_m, attempts, made, pct, density}]
        """
        # Approximate zone centres (x_m, y_m)
        ZONE_CENTRES: dict[str, tuple[float, float]] = {
            "paint_left":         (2.3, 7.62),
            "paint_right":        (26.35, 7.62),
            "mid_range_left":     (8.8, 7.62),
            "mid_range_right":    (20.0, 7.62),
            "mid_range_center":   (14.3, 7.62),
            "corner_3_left_bot":  (3.35, 1.0),
            "corner_3_left_top":  (3.35, 14.2),
            "corner_3_right_bot": (25.3, 1.0),
            "corner_3_right_top": (25.3, 14.2),
            "arc_3_left":         (5.0, 7.62),
            "arc_3_right":        (23.6, 7.62),
            "top_key_3":          (14.3, 3.0),
            "unknown":            (14.3, 7.62),
        }

        max_attempts = max(
            (int(v.get("attempted", 0)) for v in shot_chart.values()),
            default=1,
        ) or 1

        points = []
        for zone, stats in shot_chart.items():
            centre = ZONE_CENTRES.get(zone, (14.3, 7.62))
            attempted = int(stats.get("attempted", 0))
            made = int(stats.get("made", 0))
            pct = stats.get("pct", 0.0)
            density = attempted / max_attempts

            points.append({
                "zone": zone,
                "x_m": centre[0],
                "y_m": centre[1],
                "attempts": attempted,
                "made": made,
                "pct": round(pct, 3),
                "density": round(density, 3),
            })

        return sorted(points, key=lambda p: p["density"], reverse=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_fallback(obj: Any) -> Any:
    """JSON serialisation fallback for non-standard types."""
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    if hasattr(obj, "tolist"):  # numpy arrays
        return obj.tolist()
    return str(obj)
