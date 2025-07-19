# 🛠️  Local Development Guide — WatsonX VideoGenie

Follow these steps to spin up the whole stack **locally** on macOS / Linux.
Nothing here requires an IBM Cloud account; everything runs in Docker + Kind.

---

## 0 · Prerequisites

| Tool | Version (or newer) | Notes |
|------|--------------------|-------|
| Docker | 24.x | Enable Kubernetes ≠ needed. |
| **Kind** | v0.23 | `brew install kind` or GitHub release. |
| **Make** | GNU Make 4.x | BSD make works too. |
| Node | 18 LTS | Front‑end dev server. |
| Python | 3.11 | For helper scripts / virtual‑env. |
| Git | 2.40 | Shallow clone OK. |

> _Windows 10+_ → use WSL2 with Ubuntu 22.04 and the same tool versions.

---

## 1 · Clone the repo

```bash
git clone https://github.com/videogenie/watsonx-videogenie.git
cd watsonx-videogenie
````

---

## 2 · Create a Python toolchain *(optional)*

The repo’s Python utilities (e.g. `scripts/post_to_kafka.py`) live in a
virtual‑env so they never pollute your system site‑packages.

```bash
make setup                    # creates .venv and installs pre‑commit
# source .venv/bin/activate   # run if you want Python scripts
```

---

## 3 · Download Wav2Lip + prep avatar models

The avatar service needs the **Wav2Lip** inference script and GAN checkpoint.
Run this once:

```bash
make fetch-wav2lip            # clones repo & downloads wav2lip_gan.pth
make prepare-models           # creates ./models for your PNGs
cp assets/demo-alice.png models/alice.png   # an example avatar
```

---

## 4 · Build all Docker images

```bash
make container-build TAG=$(git rev-parse --short HEAD)
```

Images:

```
icr.io/videogenie/avatar-service:<TAG>
icr.io/videogenie/prompt-service:<TAG>
icr.io/videogenie/orchestrate-service:<TAG>
icr.io/videogenie/renderer:<TAG>
```

*No registry login needed* — they stay in your local daemon.

---

## 5 · Create a Kind cluster

```bash
make kind-up        # kind create cluster --name videogenie ...
```

Kind spins a single‑node Kubernetes 1.30 cluster.
Kubernetes context automatically switches to `kind-videogenie`.

---

## 6 · Install platform add‑ons

```bash
make install-istio install-argo install-keda
```

* **Istio** – ingress gateway + sidecars
* **Argo Workflows / Events** – async pipeline
* **KEDA** – autoscaling by Kafka lag (purely demo on Kind)

---

## 7 · Deploy VideoGenie via Helm

```bash
helm upgrade --install videogenie charts/videogenie \
  --namespace videogenie --create-namespace \
  --set global.image.tag=$(git rev-parse --short HEAD)
```

Knative, Kafka and GPU scheduling are stubbed in this local profile:

* Knative still deploys; autoscaling works but uses CPU.
* Renderer pods land on the same Kind node (no real GPUs).

---

## 8 · Run the front‑end dev server

```bash
cd frontend
npm ci
npm start     # ↗ http://localhost:5173
```

The SPA proxies **/api** to the Kind ingress via Vite’s dev proxy,
so you can click **Generate** and watch WebSocket progress.

---

## 9 · Verify everything

```bash
# Avatar list
curl -s http://localhost:8000/avatars | jq

# Prompt service
curl -s http://localhost:8081/prompt \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello VideoGenie."}' | jq
```

*Endpoints are declared in the Helm values file — adjust ports there if you
changed anything.*

---

## 10 · Tear down

```bash
# Stop the SPA and release port 5173
CTRL‑C in the terminal running `npm start`

# Delete Kind resources
make kind-down
```

---

### Troubleshooting

| Symptom                                            | Likely fix                                                                          |
| -------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `buildx` fails on Apple Silicon                    | Use Docker Desktop ≥ 4.20 or enable experimental buildx.                            |
| `Could not connect to Docker daemon`               | Make sure Docker is running and your user is in the `docker` group on Linux.        |
| `vite Could not resolve entry module "index.html"` | Ensure `frontend/public/index.html` exists and you ran `npm ci` inside `frontend/`. |
| Wav2Lip checkpoint not found                       | `make fetch-wav2lip` creates `Wav2Lip/checkpoints/wav2lip_gan.pth`.                 |

---

That’s it!
You have a fully functioning **VideoGenie** instance on your laptop — edit code, hit *save* and iterate. When you’re ready for real GPUs and edge delivery, jump to the “Provision cloud foundation” section in `README.md`.

