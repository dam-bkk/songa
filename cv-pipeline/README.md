# Songa CV Pipeline

**Computer Vision engine for Songa — African Basketball Analytics Platform**

Concu en Cote d'Ivoire · Pour l'Afrique

---

## What it does

Songa CV analyses basketball game footage to produce structured performance data:

- **Player detection & tracking** — YOLOv8 + ByteTrack, stable IDs across the full game
- **Court calibration** — homography-based projection from pixel space to real court metres (NBA standard 28.65 m x 15.24 m)
- **Shot detection** — arc trajectory analysis to detect shot attempts and classify by zone
- **Action detection** — steals, screens, key events
- **Stats aggregation** — per-player distance, speed, paint time, shooting %; team spacing, possession proxy
- **Export** — JSON (for API/frontend), CSV (for analysis), PDF-ready dict, heatmap data

---

## System requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.11+ | 3.12 |
| RAM | 8 GB | 16 GB |
| GPU | — (CPU ok for dev) | NVIDIA CUDA 12+ (prod) |
| Storage | 2 GB (models + deps) | 10 GB (video library) |
| OS | Linux / macOS | Ubuntu 22.04 |

---

## Installation

```bash
# 1. Clone / enter the directory
cd cv-pipeline/

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) GPU support — install the CUDA-enabled torch build first:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# then re-run: pip install -r requirements.txt
```

The first run will auto-download `yolov8n.pt` (~6 MB) from Ultralytics if no custom model is found in `models/`.

---

## CLI Usage

```bash
# Basic analysis (CPU, auto-download yolov8n)
python analyze.py --video path/to/game.mp4

# With a custom model and GPU
python analyze.py --video game.mp4 --model models/songa-basketball.pt --device cuda

# Specify output directory and confidence threshold
python analyze.py --video game.mp4 --output results/game_01 --conf 0.4

# Live preview window during analysis
python analyze.py --video game.mp4 --preview

# With pre-computed court calibration
python analyze.py --video game.mp4 --calibration calibration/court_a.json

# RTSP live stream
python analyze.py --video rtsp://192.168.1.10:554/stream

# MKV file, MPS device (Apple Silicon)
python analyze.py --video game.mkv --device mps --fps 25
```

### CLI arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--video` | required | Video file path or RTSP URL |
| `--model` | `models/songa-basketball.pt` | YOLO model weights |
| `--output` | `output/` | Results directory |
| `--fps` | 30 | FPS for time calculations |
| `--device` | `cpu` | `cpu`, `cuda`, or `mps` |
| `--conf` | 0.35 | Detection confidence threshold (0–1) |
| `--preview` | off | Show live annotation window |
| `--calibration` | — | Path to calibration JSON |

---

## API Usage

```bash
# Start the FastAPI server
uvicorn api:app --host 0.0.0.0 --port 8000

# Development mode with auto-reload
uvicorn api:app --reload --port 8000
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| POST | `/analyze` | Upload video, start analysis job |
| GET | `/job/{job_id}` | Poll job status |
| GET | `/results/{job_id}` | Fetch completed JSON results |
| GET | `/demo-stats` | Return example stats (no video needed) |

### Example — upload and poll

```bash
# Upload a video and start analysis
curl -X POST http://localhost:8000/analyze \
  -F "file=@game.mp4"
# -> {"job_id": "a1b2c3d4", "status": "queued", ...}

# Poll until done
curl http://localhost:8000/job/a1b2c3d4
# -> {"status": "processing", "progress": 0.0, ...}
# -> {"status": "done", "result_path": "output/a1b2c3d4/match_stats.json", ...}

# Fetch results
curl http://localhost:8000/results/a1b2c3d4

# Frontend dev: no video needed
curl http://localhost:8000/demo-stats
```

---

## Pipeline architecture

```
Video frame
    |
    v
[1] Detector (detector.py)
    YOLOv8 — detects persons + sports ball
    Output: DetectionResult { players: [Detection], ball: Detection | None }
    |
    v
[2] Tracker (tracker.py)
    ByteTrack — assigns stable track IDs, builds 30-frame trajectories
    Output: TrackedFrame { tracked_players, tracked_ball, frame_id }
    |
    v
[3] Court Calibration (court.py)
    Homography — maps pixels to NBA court metres (28.65 x 15.24 m)
    ShotZoneClassifier — 12 NBA zones defined as Shapely polygons
    Output: H matrix, court positions, zone classifications
    |
    v
[4] Shot & Action Detection (shot.py)
    ShotDetector — arc trajectory analysis (rise + fall = shot)
    ActionDetector — steal detection (multi-player ball proximity + speed)
    Output: ShotEvent[], StealEvent[]
    |
    v
[5] Stats Aggregation (stats.py)
    StatsAggregator — accumulates per-frame data:
      distance, speed, paint time, shot zones, team spacing
    Output: MatchSummary { PlayerStats[], TeamStats, shot_chart }
    |
    v
[6] Export (exporter.py)
    to_json() -> match_stats.json
    to_csv()  -> player_stats.csv
    to_pdf_data() -> dict for PDF templates
    generate_heatmap_data() -> weighted court points for frontend viz
```

---

## Supported video formats

| Format | Notes |
|--------|-------|
| MP4 (H.264) | Recommended — 1080p @ 30fps ideal |
| MKV | Fully supported |
| AVI | Supported |
| RTSP stream | Live analysis (no frame count progress) |

Minimum recommended resolution: **720p**. Analysis quality degrades significantly below 480p.

---

## Output JSON structure

```jsonc
{
  "meta": {
    "duration_frames": 72000,
    "duration_s": 2400.0,
    "fps": 30,
    "players_tracked": 5,
    "total_possessions": 52
  },
  "team_stats": {
    "possession_pct": 52.4,
    "avg_spacing_m": 4.8,
    "paint_touches": 38,
    "transition_speed_ms": 3.2
  },
  "player_stats": {
    "1": {
      "player_id": 1,
      "total_distance_m": 4820.0,
      "avg_speed_ms": 2.01,
      "max_speed_ms": 7.4,
      "time_in_paint_s": 142.0,
      "shots_attempted": 14,
      "shots_made": 8,
      "shot_pct": 0.571,
      "shot_zones": { "paint_left": { "made": 4, "attempted": 5, "pct": 0.8 } }
    }
    // ... one entry per tracked player
  },
  "shot_chart": {
    "paint_left":    { "made": 18, "attempted": 28, "pct": 0.643 },
    "top_key_3":     { "made": 6,  "attempted": 15, "pct": 0.4 },
    "corner_3_left_bot": { "made": 3, "attempted": 7, "pct": 0.429 }
    // ...
  },
  "key_events": [
    { "time_s": 134, "type": "steal", "players_involved": [1, 4] }
  ]
}
```

---

## Court calibration file format

```json
{
  "homography_matrix": [
    [0.012, 0.0, -4.5],
    [0.0, 0.011, -2.1],
    [0.0, 0.0, 1.0]
  ],
  "source_points": [[120, 80], [1160, 82], [1200, 670], [80, 672]],
  "court_points": [[0, 0], [28.65, 0], [28.65, 15.24], [0, 15.24]],
  "calibration_date": "2026-11-14"
}
```

Generate this file by providing at least 4 pixel-to-court correspondences using known court markings (corners, free-throw line intersections, etc.).

---

## Hardware recommendations

| Use case | Setup |
|----------|-------|
| Development / testing | MacBook / any CPU machine, yolov8n.pt |
| Match-day production | NVIDIA RTX 3060+ (8 GB VRAM), `--device cuda` |
| Cloud batch processing | AWS g4dn.xlarge or Azure NC4as_T4_v3 |
| Edge / courtside laptop | Apple M2/M3 with `--device mps` |

Processing speed (approximate):
- CPU (i7): ~4–6 fps
- Apple M2 (MPS): ~15–20 fps  
- RTX 3060 (CUDA): ~45–60 fps
- RTX 4090 (CUDA): ~120+ fps

For real-time analysis at 30fps, a CUDA-capable GPU is required.

---

## Project structure

```
cv-pipeline/
├── analyze.py          # CLI entry point
├── api.py              # FastAPI HTTP server
├── pipeline/
│   ├── __init__.py
│   ├── detector.py     # YOLOv8 detection
│   ├── tracker.py      # ByteTrack multi-object tracking
│   ├── court.py        # Homography + shot zone classifier
│   ├── shot.py         # Shot & action detection
│   ├── stats.py        # Stats aggregation
│   └── exporter.py     # JSON / CSV / PDF export
├── models/             # YOLO weights (gitignored)
├── sample_output/
│   └── example_stats.json
├── requirements.txt
└── README.md
```

---

Built for African basketball. Songa — voir le jeu autrement.
