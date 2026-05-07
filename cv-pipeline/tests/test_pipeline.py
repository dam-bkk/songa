"""
Songa CV — Pipeline Unit Tests
Importable without GPU, without ultralytics, without real video.
"""
import numpy as np
import pytest


def test_shot_zone_classifier():
    from pipeline.court import ShotZoneClassifier
    clf = ShotZoneClassifier()
    assert clf.classify_shot((2.0, 7.5)) == "paint_left"
    assert clf.classify_shot((0.5, 0.8)) in (
        "corner_3_left_bot", "corner_3_left_top", "corner_3_left"
    )


def test_kalman_filter():
    try:
        from pipeline.kalman import BallKalmanFilter
        kf = BallKalmanFilter()
        kf.reset(100.0, 200.0)
        state = kf.predict()
        assert len(state) == 6
        kf.update((105.0, 195.0))
        assert kf.is_initialized
    except ImportError:
        pytest.skip("kalman module not yet available")


def test_heatmap_renderer():
    from pipeline.heatmap_renderer import HeatmapRenderer, CourtTemplate

    court = CourtTemplate()
    img = court.draw_court()
    assert img.shape == (527, 1000, 3)

    renderer = HeatmapRenderer()
    positions = [(5.0, 7.0), (14.0, 4.0), (14.0, 10.0), (8.0, 7.0)]
    heatmap = renderer.render_player_heatmap(positions)
    assert heatmap.shape[2] == 3
    assert heatmap.shape[:2] == (527, 1000)


def test_possession_detector():
    from pipeline.possession import PossessionDetector, PossessionState

    det = PossessionDetector(proximity_threshold_px=80)

    class FakeFrame:
        tracked_players = []
        tracked_ball = None
        frame_id = 0

    event = det.update(FakeFrame(), {})
    assert event.state in (PossessionState.DEAD_BALL, PossessionState.UNKNOWN)


def test_exporter_json():
    from pipeline.exporter import Exporter
    from pipeline.stats import MatchSummary, TeamStats

    summary = MatchSummary(
        duration_frames=1000,
        fps=30,
        players_tracked=10,
        total_possessions=45,
        key_events=[],
        player_stats={},
        team_stats=TeamStats(
            team_id=-1,
            possession_pct=52.0,
            avg_spacing=4.5,
            paint_touches=20,
            transition_speed=3.0,
        ),
        per_team_stats={},
        shot_chart={},
    )

    import tempfile, json, os

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "stats.json")
        Exporter().to_json(summary, out)
        with open(out) as f:
            data = json.load(f)
        assert "meta" in data
        assert "team_stats" in data
