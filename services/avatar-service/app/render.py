"""Thin wrappers around Wav2Lip CLI utilities."""
import subprocess, tempfile, requests, shutil, os

WAV2LIP_CHECKPOINT = "Wav2Lip/checkpoints/wav2lip_gan.pth"
WAV2LIP_SCRIPT = "Wav2Lip/inference.py"
MODELS_DIR = "/models"

def download_voice(url: str) -> str:
    """Download voice clip to a temp WAV file and return path."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with os.fdopen(fd, "wb") as f:
            shutil.copyfileobj(r.raw, f)
    return path

def wav2lip_render(avatar_id: str, voice_url: str, out_path: str):
    face_path = f"{MODELS_DIR}/{avatar_id}.png"
    if not os.path.exists(face_path):
        raise RuntimeError(f"Avatar {avatar_id} not found")
    audio_path = download_voice(voice_url)
    cmd = [
        "python", WAV2LIP_SCRIPT,
        "--checkpoint", WAV2LIP_CHECKPOINT,
        "--face", face_path,
        "--audio", audio_path,
        "--outfile", out_path,
    ]
    subprocess.check_call(cmd)
