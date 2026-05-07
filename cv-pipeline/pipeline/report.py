"""
Songa CV — Report Generator
Generates structured match reports in multiple formats.
"""
from __future__ import annotations

import base64
import json
import logging
import math
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .heatmap_renderer import HeatmapRenderer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MatchReport dataclass
# ---------------------------------------------------------------------------

@dataclass
class MatchReport:
    meta: dict                      # game, date, duration, venue
    summary_stats: dict             # 4-5 key KPIs
    player_stats: list[dict]        # per player, sorted by points/shots
    shot_chart: dict                # zone breakdown
    key_events: list[dict]          # key events with timestamps
    heatmap_paths: dict[str, str]   # {heatmap_type: file_path}
    possession_stats: dict
    generated_at: str               # ISO 8601


# ---------------------------------------------------------------------------
# ReportGenerator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """
    Builds MatchReport objects from MatchSummary and renders them to various formats.
    """

    def __init__(self, output_dir: str) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # generate()
    # ------------------------------------------------------------------

    def generate(
        self,
        summary,
        heatmap_renderer: Optional["HeatmapRenderer"] = None,
    ) -> MatchReport:
        """
        Build a MatchReport from a MatchSummary.
        If heatmap_renderer is provided, generate and save the 3 heatmaps.
        """
        data = summary.to_dict()

        meta = dict(data.get("meta", {}))
        meta.setdefault("game", "Basketball Match")
        meta.setdefault("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        meta.setdefault("venue", "—")

        team_stats = data.get("team_stats", {})
        player_stats_raw = data.get("player_stats", {})
        shot_chart = data.get("shot_chart", {})
        key_events = data.get("key_events", [])

        # Sort players by shots_attempted descending
        players_list = list(player_stats_raw.values())
        players_list.sort(key=lambda p: p.get("shots_attempted", 0), reverse=True)

        # 4-5 summary KPIs
        total_made = sum(int(z.get("made", 0)) for z in shot_chart.values())
        total_attempted = sum(int(z.get("attempted", 0)) for z in shot_chart.values())
        fg_pct = total_made / total_attempted if total_attempted > 0 else 0.0

        summary_stats = {
            "total_shots_made": total_made,
            "total_shots_attempted": total_attempted,
            "fg_pct": round(fg_pct, 3),
            "possession_pct_home": team_stats.get("possession_pct", 50.0),
            "avg_spacing_m": team_stats.get("avg_spacing_m", 0.0),
            "paint_touches": team_stats.get("paint_touches", 0),
        }

        # Heatmaps
        heatmap_paths: dict[str, str] = {}
        if heatmap_renderer is not None:
            try:
                # Player heatmap — collect all court positions from exporter zone centres
                from .exporter import Exporter
                exporter = Exporter()
                heatmap_points = exporter.generate_heatmap_data(shot_chart)
                positions_m = [(pt["x_m"], pt["y_m"]) for pt in heatmap_points for _ in range(max(1, int(pt["attempts"])))]

                player_path = str(self.output_dir / "player_heatmap.png")
                heatmap_renderer.render_player_heatmap(positions_m, output_path=player_path)
                heatmap_paths["player"] = player_path

                # Shot heatmap
                shots_list: list[tuple[float, float, bool]] = []
                for pt in heatmap_points:
                    xm, ym = pt["x_m"], pt["y_m"]
                    made = int(pt.get("made", 0))
                    missed = int(pt.get("attempts", 0)) - made
                    shots_list.extend([(xm, ym, True)] * made)
                    shots_list.extend([(xm, ym, False)] * missed)

                shot_path = str(self.output_dir / "shot_heatmap.png")
                heatmap_renderer.render_shot_heatmap(shots_list, output_path=shot_path)
                heatmap_paths["shot"] = shot_path

                # Zone heatmap
                zone_path = str(self.output_dir / "zone_heatmap.png")
                heatmap_renderer.render_zone_heatmap(shot_chart, output_path=zone_path)
                heatmap_paths["zone"] = zone_path

            except Exception as exc:
                logger.warning("Heatmap generation failed: %s", exc)

        return MatchReport(
            meta=meta,
            summary_stats=summary_stats,
            player_stats=players_list,
            shot_chart=shot_chart,
            key_events=key_events,
            heatmap_paths=heatmap_paths,
            possession_stats=team_stats,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # to_json()
    # ------------------------------------------------------------------

    def to_json(self, report: MatchReport) -> str:
        """Serialise MatchReport to a JSON string (handles dataclass fields)."""
        def _default(obj: Any) -> Any:
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            if hasattr(obj, "tolist"):
                return obj.tolist()
            return str(obj)

        return json.dumps(asdict(report), indent=2, default=_default, ensure_ascii=False)

    # ------------------------------------------------------------------
    # to_html()
    # ------------------------------------------------------------------

    def to_html(self, report: MatchReport) -> str:
        """
        Generate a standalone HTML match report with embedded CSS.
        Includes base64-embedded heatmap images when available.
        """

        def _img_tag(path: str, alt: str) -> str:
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                return f'<img src="data:image/png;base64,{b64}" alt="{alt}" style="max-width:100%;border-radius:6px;">'
            except Exception:
                return f'<p style="color:#9A9389;font-style:italic;">Image not available: {alt}</p>'

        # Build player rows
        player_rows = ""
        for p in report.player_stats:
            pid = p.get("player_id", "?")
            dist = p.get("total_distance_m", 0)
            spd = p.get("avg_speed_ms", 0)
            paint = p.get("time_in_paint_s", 0)
            att = p.get("shots_attempted", 0)
            made = p.get("shots_made", 0)
            pct = p.get("shot_pct", 0)
            player_rows += f"""
            <tr>
              <td>#{pid}</td>
              <td>{dist:.0f} m</td>
              <td>{spd:.2f} m/s</td>
              <td>{paint:.0f} s</td>
              <td>{made}/{att}</td>
              <td>{pct*100:.1f}%</td>
            </tr>"""

        # Build shot chart rows
        zone_rows = ""
        for zone, stats in report.shot_chart.items():
            m = int(stats.get("made", 0))
            a = int(stats.get("attempted", 0))
            pct = float(stats.get("pct", 0))
            zone_rows += f"""
            <tr>
              <td>{zone.replace("_", " ").title()}</td>
              <td>{m}/{a}</td>
              <td>{pct*100:.1f}%</td>
            </tr>"""

        # Key events
        events_html = ""
        for ev in report.key_events:
            t = ev.get("time_s", ev.get("frame_id", "?"))
            etype = ev.get("type", "event")
            player = ev.get("player", "")
            events_html += f"""
            <tr>
              <td>{t}s</td>
              <td style="text-transform:capitalize;">{etype.replace("_"," ")}</td>
              <td>{player}</td>
            </tr>"""

        # Heatmap section
        heatmap_html = ""
        for htype, path in report.heatmap_paths.items():
            label = htype.replace("_", " ").title() + " Heatmap"
            heatmap_html += f"""
            <div style="margin-bottom:24px;">
              <h3 style="color:#E8743C;font-size:14px;margin-bottom:8px;">{label}</h3>
              {_img_tag(path, label)}
            </div>"""

        # KPI boxes
        kpis = report.summary_stats
        kpi_html = f"""
        <div class="kpi-grid">
          <div class="kpi"><div class="kpi-val">{kpis.get("total_shots_made",0)}/{kpis.get("total_shots_attempted",0)}</div><div class="kpi-label">Field Goals</div></div>
          <div class="kpi"><div class="kpi-val">{kpis.get("fg_pct",0)*100:.1f}%</div><div class="kpi-label">FG%</div></div>
          <div class="kpi"><div class="kpi-val">{kpis.get("possession_pct_home",50):.1f}%</div><div class="kpi-label">Possession (Home)</div></div>
          <div class="kpi"><div class="kpi-val">{kpis.get("avg_spacing_m",0):.1f} m</div><div class="kpi-label">Avg Spacing</div></div>
        </div>"""

        meta = report.meta
        game_title = meta.get("game", "Match Report")
        game_date = meta.get("date", "")
        venue = meta.get("venue", "")
        duration_s = meta.get("duration_s", meta.get("duration_frames", 0))
        if isinstance(duration_s, (int, float)):
            mins = int(duration_s) // 60
            secs = int(duration_s) % 60
            duration_str = f"{mins}:{secs:02d}"
        else:
            duration_str = str(duration_s)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Songa — {game_title}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0E0D0B;
      color: #F2EDE3;
      font-family: 'JetBrains Mono', 'Courier New', monospace;
      font-size: 13px;
      line-height: 1.6;
      padding: 32px;
    }}
    h1 {{ font-size: 22px; color: #E8743C; margin-bottom: 4px; }}
    h2 {{ font-size: 15px; color: #9A9389; margin: 32px 0 12px; text-transform: uppercase; letter-spacing: 0.1em; border-bottom: 1px solid #3A3631; padding-bottom: 6px; }}
    h3 {{ font-size: 13px; color: #E8743C; }}
    .meta {{ color: #9A9389; font-size: 12px; margin-bottom: 8px; }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px;
      margin: 16px 0;
    }}
    .kpi {{
      background: #1A1815;
      border: 1px solid #3A3631;
      border-radius: 8px;
      padding: 16px;
      text-align: center;
    }}
    .kpi-val {{ font-size: 26px; font-weight: 600; color: #7BE0A8; }}
    .kpi-label {{ font-size: 11px; color: #9A9389; margin-top: 4px; text-transform: uppercase; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
    }}
    th {{
      background: #1A1815;
      color: #9A9389;
      text-align: left;
      padding: 8px 12px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    td {{
      padding: 8px 12px;
      border-bottom: 1px solid #1A1815;
      color: #F2EDE3;
    }}
    tr:hover td {{ background: #1A1815; }}
    .heatmaps {{ margin-top: 16px; }}
    @media print {{
      body {{ background: white; color: black; padding: 16px; }}
      .kpi {{ border: 1px solid #ccc; background: #f9f9f9; }}
      .kpi-val {{ color: #2d7a4f; }}
      h1 {{ color: #c74b14; }}
      h2 {{ color: #555; border-color: #ccc; }}
      td, th {{ border-color: #ddd; }}
    }}
  </style>
</head>
<body>
  <h1>{game_title}</h1>
  <p class="meta">{game_date} &nbsp;|&nbsp; {venue} &nbsp;|&nbsp; Duration: {duration_str} &nbsp;|&nbsp; Generated: {report.generated_at}</p>

  <h2>Key Performance Indicators</h2>
  {kpi_html}

  <h2>Player Statistics</h2>
  <table>
    <thead>
      <tr>
        <th>Player</th><th>Distance</th><th>Avg Speed</th><th>Paint Time</th><th>FG</th><th>FG%</th>
      </tr>
    </thead>
    <tbody>
      {player_rows}
    </tbody>
  </table>

  <h2>Shot Chart</h2>
  <table>
    <thead>
      <tr><th>Zone</th><th>Made/Att</th><th>%</th></tr>
    </thead>
    <tbody>
      {zone_rows}
    </tbody>
  </table>

  {"<h2>Heatmaps</h2><div class='heatmaps'>" + heatmap_html + "</div>" if heatmap_html else ""}

  <h2>Key Events</h2>
  <table>
    <thead>
      <tr><th>Time</th><th>Event</th><th>Player</th></tr>
    </thead>
    <tbody>
      {events_html}
    </tbody>
  </table>

</body>
</html>"""
        return html

    # ------------------------------------------------------------------
    # to_pdf_via_html()
    # ------------------------------------------------------------------

    def to_pdf_via_html(self, report: MatchReport, output_path: str) -> bool:
        """
        Attempt to generate a PDF from the HTML report via weasyprint.
        Returns True on success, False if weasyprint is not installed or fails.
        """
        try:
            from weasyprint import HTML  # type: ignore
        except ImportError:
            logger.warning(
                "weasyprint not installed — PDF generation skipped. "
                "Install with: pip install weasyprint"
            )
            return False

        try:
            html_str = self.to_html(report)
            HTML(string=html_str, base_url=str(self.output_dir)).write_pdf(output_path)
            logger.info("PDF report written to %s", output_path)
            return True
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc)
            return False
