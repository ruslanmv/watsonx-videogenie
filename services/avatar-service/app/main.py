"""Avatar Service Main Module.

This FastAPI service provides avatar video rendering capabilities using Wav2Lip.
It manages avatar images, accepts rendering jobs, and returns processed video files.

Author: Ruslan Magana (https://ruslanmv.com)
License: Apache 2.0
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.render import download_voice, wav2lip_render

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Avatar Service",
    description="AI-powered avatar video rendering service using Wav2Lip",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuration
AVATAR_DIR = Path(os.getenv("AVATAR_DIR", "/models"))
WORK_ROOT = Path(os.getenv("WORK_ROOT", "/tmp/avatar-jobs"))
WORK_ROOT.mkdir(parents=True, exist_ok=True)


class RenderTaskRequest(BaseModel):
    """Request model for rendering tasks.

    Attributes:
        avatarId: Unique identifier for the avatar (without .png extension).
        voiceUrl: URL to the audio file for lip-sync rendering.
    """

    avatarId: str = Field(..., description="Avatar identifier (file name without extension)")
    voiceUrl: str = Field(..., description="URL to download the voice audio file")


class RenderTaskResponse(BaseModel):
    """Response model for render task submission.

    Attributes:
        jobId: Unique identifier for the rendering job.
        statusUrl: Endpoint to check job status and retrieve the video.
    """

    jobId: str = Field(..., description="Unique job identifier")
    statusUrl: str = Field(..., description="URL to check job status")


class JobStatusResponse(BaseModel):
    """Response model for job status when still processing.

    Attributes:
        state: Current state of the rendering job.
    """

    state: str = Field(..., description="Job state: 'processing', 'completed', or 'failed'")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict containing health status.
    """
    return {"status": "healthy", "service": "avatar-service"}


@app.get("/avatars", response_model=List[str])
async def list_avatars() -> JSONResponse:
    """List all available avatar images.

    Scans the avatar directory for PNG files and returns their identifiers.

    Returns:
        JSONResponse: List of avatar identifiers (filenames without extensions).

    Raises:
        HTTPException: If avatar directory doesn't exist or is inaccessible.
    """
    try:
        if not AVATAR_DIR.exists():
            logger.error(f"Avatar directory not found: {AVATAR_DIR}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Avatar directory not configured: {AVATAR_DIR}",
            )

        avatars = [p.stem for p in AVATAR_DIR.glob("*.png")]
        logger.info(f"Found {len(avatars)} avatars")
        return JSONResponse(content=avatars)

    except Exception as e:
        logger.error(f"Error listing avatars: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list avatars",
        )


@app.post("/render", response_model=RenderTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def render(task: RenderTaskRequest, bg: BackgroundTasks) -> Dict[str, str]:
    """Submit a rendering job for avatar lip-sync video generation.

    Creates a new rendering job that processes the avatar image with the provided
    audio using Wav2Lip technology. The job runs asynchronously in the background.

    Args:
        task: RenderTaskRequest containing avatarId and voiceUrl.
        bg: FastAPI BackgroundTasks for async processing.

    Returns:
        Dict containing jobId and statusUrl for tracking the job.

    Raises:
        HTTPException: If avatar doesn't exist or parameters are invalid.
    """
    try:
        # Validate avatar exists
        avatar_path = AVATAR_DIR / f"{task.avatarId}.png"
        if not avatar_path.exists():
            logger.warning(f"Avatar not found: {task.avatarId}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Avatar '{task.avatarId}' not found",
            )

        # Create job directory
        job_id = str(uuid4())
        job_dir = WORK_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        # Save job metadata
        out_mp4 = job_dir / "out.mp4"
        meta_file = job_dir / "meta.json"
        meta_file.write_text(
            json.dumps(
                {
                    "jobId": job_id,
                    "avatarId": task.avatarId,
                    "voiceUrl": task.voiceUrl,
                }
            )
        )

        # Schedule background rendering task
        bg.add_task(wav2lip_render, task.avatarId, task.voiceUrl, str(out_mp4))
        logger.info(f"Rendering job created: {job_id} for avatar: {task.avatarId}")

        return {
            "jobId": job_id,
            "statusUrl": f"/status/{job_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating render job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create rendering job",
        )


@app.get("/status/{job_id}")
async def get_job_status(job_id: str) -> FileResponse | Dict[str, str]:
    """Check rendering job status and retrieve completed video.

    If the job is complete, returns the rendered video file.
    If still processing, returns the current status.

    Args:
        job_id: Unique identifier for the rendering job.

    Returns:
        FileResponse: Rendered MP4 video if job is complete.
        Dict: Status information if job is still processing.

    Raises:
        HTTPException: If job ID is not found or invalid.
    """
    try:
        job_dir = WORK_ROOT / job_id

        if not job_dir.exists():
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job '{job_id}' not found",
            )

        mp4_file = job_dir / "out.mp4"
        error_file = job_dir / "error.txt"

        # Check for errors
        if error_file.exists():
            error_msg = error_file.read_text()
            logger.error(f"Job {job_id} failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Rendering failed: {error_msg}",
            )

        # Return video if complete
        if mp4_file.exists():
            logger.info(f"Returning completed video for job: {job_id}")
            return FileResponse(
                path=mp4_file,
                media_type="video/mp4",
                filename=f"{job_id}.mp4",
            )

        # Job still processing
        return {"state": "processing", "jobId": job_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking job status {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status",
        )


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup event handler.

    Validates required directories and logs configuration.
    """
    logger.info("Starting Avatar Service")
    logger.info(f"Avatar directory: {AVATAR_DIR}")
    logger.info(f"Work directory: {WORK_ROOT}")

    if not AVATAR_DIR.exists():
        logger.warning(f"Avatar directory does not exist: {AVATAR_DIR}")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Application shutdown event handler."""
    logger.info("Shutting down Avatar Service")
