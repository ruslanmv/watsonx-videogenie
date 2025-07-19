# Avatar Service Development Guide

## 1 · Clone & Prepare

```bash
git clone https://github.com/ruslanmv/watsonx-videogenie.git
cd watsonx-videogenie/services/avatar-service
```

Ensure you have:

* Python 3.11 installed
* `ffmpeg`, Git, and Jupyter installed on your machine
* NVIDIA GPU driver ≥ 545 (for CUDA)
* Wav2Lip repository and checkpoint under `app/Wav2Lip`

```bash
# Fetch Wav2Lip code & checkpoint
make fetch-wav2lip

# Prepare models directory for avatar PNGs
make prepare-models
```

Populate `models/` with your `<avatarId>.png` files (e.g. `alice.png`).

## 2 · Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn requests pydantic torch torchvision opencv-python-headless jupyterlab
```

## 3 · Interactive Notebook Testing

Launch Jupyter Lab to run the provided notebook:

```bash
jupyter lab
```

Open `test/test_avatar.ipynb`, which demonstrates:

1. Downloading a sample WAV clip
2. Invoking `render.wav2lip_render("alice", voice_url, "out.mp4")`
3. Validating the output video file

This lets you quickly iterate on the core rendering logic.

## 4 · Run the FastAPI Service Locally

With your venv active:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## 5 · Smoke Test Endpoints

```bash
# List avatars
curl http://localhost:8080/avatars

# Start a render job
curl -X POST http://localhost:8080/render \
  -H "Content-Type: application/json" \
  -d '{"avatarId":"alice","voiceUrl":"https://example.com/clip.wav"}'

# Response: {"jobId":"1234abcd","statusUrl":"/status/1234abcd"}

# Poll for completion and download
curl http://localhost:8080/status/1234abcd --output result.mp4
```

## 6 · Code Iteration & Debugging

* Edit `app/main.py` or `app/render.py`
* Restart Uvicorn for changes
* Leverage the notebook to test helper functions before full API integration

## 7 · Containerization & Deployment

Once validated:

1. **Build** locally:

   ```bash
   docker build -t icr.io/videogenie/avatar-service:local .
   ```
2. **Run with GPU**:

   ```bash
   docker run --rm --gpus all -p 8080:8080 \
     -v $(pwd)/models:/models:ro \
     icr.io/videogenie/avatar-service:local
   ```
3. **Push** and deploy via your chosen Knative manifest or Helm chart.

