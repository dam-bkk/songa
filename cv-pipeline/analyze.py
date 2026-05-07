#!/usr/bin/env python3
"""
Songa CV Pipeline — Game Analysis CLI
Usage: python analyze.py --video PATH [--model PATH] [--output DIR] [--fps 30] [--device cpu]
"""
import argparse
import sys
import cv2
import json
from pathlib import Path
from pipeline.detector import Detector
from pipeline.tracker import Tracker
from pipeline.court import CourtCalibrator, ShotZoneClassifier
from pipeline.shot import ShotDetector, ActionDetector
from pipeline.stats import StatsAggregator
from pipeline.exporter import Exporter
from pipeline.possession import PossessionDetector
from pipeline.heatmap_renderer import HeatmapRenderer
from pipeline.report import ReportGenerator

def main():
    parser = argparse.ArgumentParser(description="Songa — Basketball CV Analysis")
    parser.add_argument("--video", required=True, help="Path to video file (MP4, MKV) or RTSP stream URL")
    parser.add_argument("--model", default="models/songa-basketball.pt", help="Path to YOLO model weights")
    parser.add_argument("--output", default="output", help="Output directory for results")
    parser.add_argument("--fps", type=int, default=30, help="Video FPS (used for time calculations)")
    parser.add_argument("--device", default="cpu", choices=["cpu","cuda","mps"], help="Inference device")
    parser.add_argument("--conf", type=float, default=0.35, help="Detection confidence threshold")
    parser.add_argument("--preview", action="store_true", help="Show live preview window")
    parser.add_argument("--calibration", help="Path to court calibration JSON file")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not str(video_path).startswith("rtsp://") and not video_path.exists():
        print(f"[ERROR] Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  SONGA — Computer Vision Basketball Analysis")
    print("  Concu en Cote d'Ivoire · Pour l'Afrique")
    print("=" * 60)
    print(f"  Video    : {args.video}")
    print(f"  Model    : {args.model}")
    print(f"  Device   : {args.device}")
    print(f"  Output   : {output_dir}/")
    print("=" * 60)

    # Initialize pipeline components
    print("\n[1/5] Loading detector...")
    detector = Detector(model_path=args.model, conf_threshold=args.conf, device=args.device)

    print("[2/5] Initializing tracker...")
    tracker = Tracker()

    print("[3/5] Setting up court model...")
    calibrator = CourtCalibrator()
    zone_classifier = ShotZoneClassifier()

    # Load or auto-compute homography
    H = None
    if args.calibration and Path(args.calibration).exists():
        with open(args.calibration) as f:
            cal = json.load(f)
        import numpy as np
        H = np.array(cal["homography_matrix"])
        print(f"       Court calibration loaded from {args.calibration}")
    else:
        print("       No calibration file — will attempt auto-calibration from first frame")

    print("[4/5] Initializing stats aggregator...")
    shot_detector = ShotDetector()
    action_detector = ActionDetector()
    aggregator = StatsAggregator(fps=args.fps)
    possession_detector = PossessionDetector()

    # Open video
    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {args.video}", file=sys.stderr)
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS) or args.fps

    print(f"[5/5] Starting analysis ({total_frames} frames @ {actual_fps:.1f}fps)...")
    print()

    frame_id = 0
    report_interval = max(1, int(actual_fps * 5))  # Report every 5 seconds

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Detect
            detections = detector.detect(frame)

            # Track
            tracked_frame = tracker.update(detections, frame)
            tracked_frame.frame_id = frame_id

            # Auto-calibrate on first frame if no calibration provided
            if H is None and frame_id == 0:
                H = calibrator.auto_calibrate(frame)
                if H is not None:
                    print("       Auto-calibration successful")
                else:
                    print("       Auto-calibration failed — using identity (court coords unavailable)")

            # Shot detection
            shot_events = shot_detector.update(tracked_frame, H)

            # Action detection
            key_events = action_detector.detect_steal(tracked_frame)

            # Accumulate stats
            aggregator.update(tracked_frame, shot_events, key_events, H, zone_classifier)

            # Possession detection
            possession_event = possession_detector.update(
                tracked_frame,
                tracked_frame.team_labels if hasattr(tracked_frame, "team_labels") else {},
            )

            # Progress report
            if frame_id % report_interval == 0 and total_frames > 0:
                pct = (frame_id / total_frames) * 100
                elapsed_s = frame_id / actual_fps
                print(f"  Frame {frame_id:6d}/{total_frames} ({pct:5.1f}%) — {elapsed_s:.0f}s analysed — {len(tracked_frame.tracked_players)} players tracked")

            # Preview
            if args.preview:
                preview = detector.draw_detections(frame.copy(), detections)
                cv2.imshow("Songa — Analysis", preview)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("\n[INFO] Analysis interrupted by user")
                    break

            frame_id += 1

    finally:
        cap.release()
        if args.preview:
            cv2.destroyAllWindows()

    print(f"\n  Analysis complete — {frame_id} frames processed")

    # Build summary and export
    summary = aggregator.get_match_summary()

    # Inject possession data
    possession_stats = possession_detector.get_possession_stats()
    summary.team_stats.possession_pct = possession_stats.get("home_possession_pct", 50.0)

    exporter = Exporter()

    json_path = output_dir / "match_stats.json"
    csv_path = output_dir / "player_stats.csv"

    exporter.to_json(summary, json_path)
    exporter.to_csv(summary, csv_path)

    print(f"\n  Results exported:")
    print(f"    JSON : {json_path}")
    print(f"    CSV  : {csv_path}")

    # Heatmaps and HTML/PDF report
    print("\n  Generating heatmaps...")
    renderer = HeatmapRenderer()
    report_gen = ReportGenerator(str(output_dir))
    report = report_gen.generate(summary, heatmap_renderer=renderer)

    html_path = output_dir / "match_report.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(report_gen.to_html(report))
    print(f"    HTML report : {html_path}")

    pdf_ok = report_gen.to_pdf_via_html(report, str(output_dir / "match_report.pdf"))
    if pdf_ok:
        print(f"    PDF report  : {output_dir}/match_report.pdf")

    print(f"\n  Players tracked : {summary.players_tracked}")
    print(f"  Key events      : {len(summary.key_events)}")
    print(f"\n  Done. Songa analysis complete.")

if __name__ == "__main__":
    main()
