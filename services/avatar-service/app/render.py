"""Wav2Lip Rendering Module.

Thin wrappers around Wav2Lip CLI utilities for avatar lip-sync video generation.
Handles audio download and execution of the Wav2Lip inference pipeline.

Author: Ruslan Magana (https://ruslanmv.com)
License: Apache 2.0
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import requests

# Configure logging
logger = logging.getLogger(__name__)

# Configuration constants
WAV2LIP_CHECKPOINT = os.getenv(
    "WAV2LIP_CHECKPOINT",
    "Wav2Lip/checkpoints/wav2lip_gan.pth",
)
WAV2LIP_SCRIPT = os.getenv("WAV2LIP_SCRIPT", "Wav2Lip/inference.py")
MODELS_DIR = Path(os.getenv("MODELS_DIR", "/models"))
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "60"))


def download_voice(url: str, timeout: Optional[int] = None) -> str:
    """Download voice audio file from URL.

    Downloads an audio file from the provided URL and saves it to a temporary
    location. The file is saved with a .wav extension for Wav2Lip compatibility.

    Args:
        url: URL to download the audio file from.
        timeout: Request timeout in seconds. Defaults to DOWNLOAD_TIMEOUT.

    Returns:
        str: Absolute path to the downloaded temporary audio file.

    Raises:
        requests.HTTPError: If the download fails with an HTTP error.
        requests.Timeout: If the download exceeds the timeout.
        requests.RequestException: For other network-related errors.

    Example:
        >>> audio_path = download_voice("https://example.com/voice.wav")
        >>> print(audio_path)
        '/tmp/tmpxyz123.wav'
    """
    if timeout is None:
        timeout = DOWNLOAD_TIMEOUT

    try:
        logger.info(f"Downloading voice from: {url}")

        fd, path = tempfile.mkstemp(suffix=".wav")

        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()

            # Get file size if available
            total_size = response.headers.get("content-length")
            if total_size:
                logger.info(f"Downloading {int(total_size) / 1024 / 1024:.2f} MB")

            with os.fdopen(fd, "wb") as file:
                shutil.copyfileobj(response.raw, file)

        logger.info(f"Voice downloaded successfully to: {path}")
        return path

    except requests.HTTPError as e:
        logger.error(f"HTTP error downloading voice: {e}")
        raise RuntimeError(f"Failed to download voice from {url}: HTTP {e.response.status_code}")
    except requests.Timeout as e:
        logger.error(f"Timeout downloading voice from {url}")
        raise RuntimeError(f"Download timeout after {timeout} seconds")
    except requests.RequestException as e:
        logger.error(f"Network error downloading voice: {e}")
        raise RuntimeError(f"Network error downloading voice: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error downloading voice: {e}")
        raise RuntimeError(f"Unexpected error: {str(e)}")


def wav2lip_render(
    avatar_id: str,
    voice_url: str,
    out_path: str,
    quality: str = "high",
) -> None:
    """Execute Wav2Lip rendering to generate lip-synced avatar video.

    Runs the Wav2Lip inference pipeline to generate a video where the avatar's
    lip movements are synchronized with the provided audio. Uses the Wav2Lip GAN
    checkpoint for high-quality results.

    Args:
        avatar_id: Identifier for the avatar (without .png extension).
        voice_url: URL to download the voice audio file.
        out_path: Output path for the generated MP4 video file.
        quality: Rendering quality preset ('high', 'medium', 'fast').

    Raises:
        RuntimeError: If avatar file is not found.
        subprocess.CalledProcessError: If Wav2Lip inference fails.

    Example:
        >>> wav2lip_render(
        ...     avatar_id="john_doe",
        ...     voice_url="https://example.com/speech.wav",
        ...     out_path="/tmp/output.mp4"
        ... )
    """
    try:
        # Validate avatar exists
        face_path = MODELS_DIR / f"{avatar_id}.png"
        if not face_path.exists():
            error_msg = f"Avatar '{avatar_id}' not found at {face_path}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info(f"Starting Wav2Lip render for avatar: {avatar_id}")

        # Download audio file
        audio_path = download_voice(voice_url)

        try:
            # Construct Wav2Lip command
            cmd = [
                "python",
                WAV2LIP_SCRIPT,
                "--checkpoint_path",
                WAV2LIP_CHECKPOINT,
                "--face",
                str(face_path),
                "--audio",
                audio_path,
                "--outfile",
                str(out_path),
            ]

            # Add quality-specific parameters
            if quality == "fast":
                cmd.extend(["--resize_factor", "2"])
            elif quality == "high":
                cmd.extend(["--resize_factor", "1", "--wav2lip_batch_size", "32"])

            logger.info(f"Executing Wav2Lip: {' '.join(cmd)}")

            # Run Wav2Lip inference
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )

            logger.info(f"Wav2Lip render completed successfully: {out_path}")

            if result.stdout:
                logger.debug(f"Wav2Lip stdout: {result.stdout}")

        finally:
            # Cleanup temporary audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.debug(f"Cleaned up temporary audio file: {audio_path}")

    except subprocess.CalledProcessError as e:
        error_msg = f"Wav2Lip inference failed: {e.stderr}"
        logger.error(error_msg)

        # Write error to file for status endpoint
        error_file = Path(out_path).parent / "error.txt"
        error_file.write_text(error_msg)

        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = f"Rendering error: {str(e)}"
        logger.error(error_msg)

        # Write error to file
        error_file = Path(out_path).parent / "error.txt"
        error_file.write_text(error_msg)

        raise
