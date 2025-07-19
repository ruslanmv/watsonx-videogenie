# services/avatar-service/app/main.py

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from uuid import uuid4
from pathlib import Path
import tempfile, os, json
from app.render import wav2lip_render, download_voice

app = FastAPI(title="avatar‑svc", version="0.1.0")

AVATAR_DIR = Path("/models")
WORK_ROOT = Path("/tmp/avatar-jobs")
WORK_ROOT.mkdir(parents=True, exist_ok=True)

@app.get("/avatars")
async def list_avatars():
    avatars = [p.stem for p in AVATAR_DIR.glob("*.png")]
    return JSONResponse(avatars)

@app.post("/render")
async def render(task: dict, bg: BackgroundTasks):
    avatar_id = task.get("avatarId")
    voice_url = task.get("voiceUrl")
    if not avatar_id or not voice_url:
        raise HTTPException(400, "avatarId and voiceUrl required")
    job_id = str(uuid4())
    job_dir = WORK_ROOT / job_id
    job_dir.mkdir()
    out_mp4 = job_dir / "out.mp4"
    meta = job_dir / "meta.json"
    meta.write_text(json.dumps(task))
    bg.add_task(wav2lip_render, avatar_id, voice_url, out_mp4)
    return {"jobId": job_id, "statusUrl": f"/status/{job_id}"}

@app.get("/status/{job_id}")
async def status(job_id: str):
    job_dir = WORK_ROOT / job_id
    if not job_dir.exists():
        raise HTTPException(404, "job not found")
    mp4 = job_dir / "out.mp4"
    if mp4.exists():
        return FileResponse(mp4, media_type="video/mp4")
    return {"state": "processing"}
