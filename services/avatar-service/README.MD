# Avatar Service – Text‑to‑Lip‑Sync Micro‑service

This README provides an overview of the `avatar‑service`, a microservice for generating lip‑synced avatar videos using voice input. It is compatible with CUDA‑enabled laptops or OpenShift GPU environments.

---

## 1 · Directory Layout

The `avatar‑service` project is organized as follows:

```text
avatar-service/
├── app/                 # FastAPI application with rendering logic and models
├── Dockerfile           # Defines a CUDA‑enabled container image
└── knative.yaml         # Knative Service configuration for deployment
````

---

## 2 · Service Overview

The FastAPI service exposes these endpoints:

* `GET /avatars`
  Lists available avatar images.

* `POST /render`
  Starts a rendering job (avatar + voice clip).

* `GET /status/{jobId}`
  Checks job status or returns the completed MP4.

Rendering uses Wav2Lip under the hood, downloading voice clips on demand and syncing them to avatar PNGs.

---

## 3 · Docker Image

The `Dockerfile` builds a CUDA‑ready image with:

* Python 3.11 in a virtualenv
* PyTorch 2.3.0+cu124 & torchvision
* FastAPI, Uvicorn, OpenCV‑headless, Requests, Pydantic

It exposes port 8080 and launches via Uvicorn.

---

## 4 · Knative Deployment

The `knative.yaml` manifest configures:

* **Autoscaling**: minScale 0, maxScale 5, target 80 concurrency
* **Resources**: 2 CPUs, 4 GiB memory
* **Envs**: MODEL\_BUCKET (S3), AWS\_REGION
* **GPU** compatibility for OpenShift clusters

---

## 5 · Build & Push in One Go

```bash
# 1. Set your registry and tag
export REG=icr.io/videogenie
export TAG=$(git rev-parse --short HEAD)

# 2. Move into the service directory
cd services/avatar-service

# 3. Build the Docker image
docker build -t $REG/avatar-service:$TAG .

# 4. Push to your registry
docker push $REG/avatar-service:$TAG
```

> After pushing, update `knative.yaml` or your Helm values to point at `$REG/avatar-service:$TAG`.

---

## 6 · Local GPU Testing

```bash
# Run the container locally with GPU support and model mount
docker run --rm --gpus all -p 8080:8080 \
  -v $(pwd)/app/models:/models:ro \
  icr.io/videogenie/avatar-service:latest
```

In another terminal:

```bash
# Trigger a render job (replace with a real WAV URL)
curl -X POST http://localhost:8080/render \
  -H "Content-Type: application/json" \
  -d '{"avatarId":"alice","voiceUrl":"https://your-domain.com/clip.wav"}'

# You’ll receive {"jobId":"<id>","statusUrl":"/status/<id>"}
# Poll for completion and download:
curl http://localhost:8080/status/<id> --output result.mp4
```

---

## 7 · Troubleshooting

* **CUDA mismatch**
  Ensure your host NVIDIA driver ≥ 545 matches CUDA 12.4 runtime.

* **Checkpoint missing**
  Mount or copy `wav2lip_gan.pth` into `app/Wav2Lip/checkpoints/`.

* **Cold‑start latency**
  Increase Knative `minScale` or enable provisioned concurrency.

