"""
Songa CV API — FastAPI server
Serves analysis results and exposes video upload endpoint.

Run: uvicorn api:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import uuid, json, shutil, subprocess, sys
from typing import Optional

app = FastAPI(title="Songa CV API", version="1.0.0", description="Computer Vision pipeline for African Basketball")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://songa.ai"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# In-memory job store (use Redis/DB in production)
jobs: dict[str, dict] = {}

class AnalysisJob(BaseModel):
    job_id: str
    status: str  # queued | processing | done | error
    video_name: str
    progress: float = 0.0
    result_path: Optional[str] = None
    error: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok", "service": "songa-cv-api", "version": "1.0.0"}

@app.post("/analyze", response_model=AnalysisJob)
async def submit_analysis(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a video file and start analysis in background."""
    job_id = str(uuid.uuid4())[:8]
    video_path = UPLOAD_DIR / f"{job_id}_{file.filename}"

    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    jobs[job_id] = {"status": "queued", "video": str(video_path), "progress": 0.0}
    background_tasks.add_task(run_analysis, job_id, video_path)

    return AnalysisJob(job_id=job_id, status="queued", video_name=file.filename or "unknown")

@app.get("/job/{job_id}", response_model=AnalysisJob)
def get_job(job_id: str):
    """Poll analysis job status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    j = jobs[job_id]
    return AnalysisJob(
        job_id=job_id, status=j["status"],
        video_name=Path(j["video"]).name,
        progress=j.get("progress", 0.0),
        result_path=j.get("result_path"),
        error=j.get("error"),
    )

@app.get("/results/{job_id}")
def get_results(job_id: str):
    """Fetch full JSON results for a completed job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    j = jobs[job_id]
    if j["status"] != "done":
        raise HTTPException(status_code=400, detail=f"Job not complete: {j['status']}")
    result_path = Path(j["result_path"])
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    with open(result_path) as f:
        return json.load(f)

@app.get("/demo-stats")
def demo_stats():
    """Return example stats (no video needed) — for frontend development."""
    example_path = Path("sample_output/example_stats.json")
    if example_path.exists():
        with open(example_path) as f:
            return json.load(f)
    return {"error": "example_stats.json not found in sample_output/"}

@app.get("/results/{job_id}/heatmap/{heatmap_type}")
def get_heatmap(job_id: str, heatmap_type: str):
    """Serve a generated heatmap image. heatmap_type: player | shot | zone"""
    allowed = {"player", "shot", "zone"}
    if heatmap_type not in allowed:
        raise HTTPException(status_code=400, detail=f"heatmap_type must be one of {allowed}")
    img_path = OUTPUT_DIR / job_id / f"{heatmap_type}_heatmap.png"
    if not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Heatmap '{heatmap_type}' not found for job {job_id}")
    return FileResponse(str(img_path), media_type="image/png")


@app.get("/results/{job_id}/report")
def get_report(job_id: str):
    """Serve the HTML match report."""
    report_path = OUTPUT_DIR / job_id / "match_report.html"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"HTML report not found for job {job_id}")
    return FileResponse(str(report_path), media_type="text/html")


@app.get("/results/{job_id}/report.pdf")
def get_pdf_report(job_id: str):
    """Serve the PDF match report if generated."""
    pdf_path = OUTPUT_DIR / job_id / "match_report.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF report not found for job {job_id}. Ensure weasyprint is installed.")
    return FileResponse(str(pdf_path), media_type="application/pdf")


def run_analysis(job_id: str, video_path: Path):
    """Background task: run analyze.py subprocess."""
    jobs[job_id]["status"] = "processing"
    output_dir = OUTPUT_DIR / job_id
    output_dir.mkdir(exist_ok=True)
    try:
        result = subprocess.run(
            [sys.executable, "analyze.py", "--video", str(video_path), "--output", str(output_dir)],
            capture_output=True, text=True, timeout=3600
        )
        if result.returncode == 0:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["result_path"] = str(output_dir / "match_stats.json")
            jobs[job_id]["progress"] = 1.0
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = result.stderr[-500:] if result.stderr else "Unknown error"
    except subprocess.TimeoutExpired:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = "Analysis timeout (>1h)"
    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
