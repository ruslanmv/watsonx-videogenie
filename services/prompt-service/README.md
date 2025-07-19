# Prompt Service — Watson X LLM Orchestration

The prompt‑service is the **first AI hop** in the VideoGenie back‑end.
It transforms unstructured user text into a sentence‑timed script that:
1. is easy for the TTS engine to pronounce,
2. respects slide and breath breaks,
3. estimates spoken length so the lip‑sync renderer can pace itself.

Under the hood we call a **Granite chat model** (or any other
watsonx.ai foundation model you configure) and return a small JSON
payload.  
Because the work is CPU‑only and bursts with user demand, we deploy it
as a **Knative Service** that scales from 0 → 10 pods automatically.

---

## Why not do this in the browser?

• Large LLM checkpoints live only in watsonx.ai.  
• You want consistent slide cuts no matter the user device.  
• Centralised error handling and logging.  
The browser simply sends raw text and gets back a clean, timed script.

---

## Repository layout

```

services/prompt-service
├── app/
│   ├── main.py   → FastAPI entry‑point
│   └── utils.py  → naive sentence‑split; replace with spaCy if you like
├── Dockerfile    → python:3.11‑slim, 60 MB compressed
└── knative.yaml  → autoscale 0↔10, 100 reqs per pod

````

---

## REST contract

`POST /prompt`  
Request body must contain a single key `text`.

```bash
curl -XPOST https://prompt.videogenie.cloud/prompt \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello world. This is VideoGenie."}'
````

Success → `200 OK`

```jsonc
{
  "segments": [
    { "text": "Hello world.",              "seconds": 1.5 },
    { "text": "This is VideoGenie.",       "seconds": 1.9 }
  ]
}
```

Failures:

\* `400 Bad Request` – text shorter than five characters.
\* `500 Internal` – watsonx.ai error (returned as plain JSON).

---

## Environment variables (all required)

\* `WATSONX_APIKEY` – service credentials.
\* `PROJECT_ID`     – your watsonx.ai project (UUID).
\* `MODEL_ID`       – default `granite-13b-chat-v2` but any chat model works.
\* `WATSONX_URL`    – region base (`https://eu-de.ml.cloud.ibm.com`, etc.).

Set them via a Kubernetes Secret; see `knative.yaml`.

---

## Build, push, deploy

```bash
REG=icr.io/videogenie
TAG=$(git rev-parse --short HEAD)

docker build -t $REG/prompt-service:$TAG services/prompt-service
docker push  $REG/prompt-service:$TAG

# one‑time secret
kubectl create secret generic watsonx-secret \
  -n videogenie --from-literal=apikey=$WATSONX_APIKEY

# deploy / roll image
sed "s/latest/$TAG/" services/prompt-service/knative.yaml | \
  kubectl apply -f -
```

Pods start in < 1 s (no CUDA). Cold start is dominated by model token
manager (\~300 ms).

---

## Local smoke test

You can run the service without Kubernetes:

```bash
docker run --rm -p 8080:8080 \
  -e WATSONX_APIKEY=$WATSONX_APIKEY \
  -e PROJECT_ID=$PROJECT_ID \
  icr.io/videogenie/prompt-service:$TAG &

curl localhost:8080/prompt \
  -H "Content-Type: application/json" \
  -d '{"text":"Quick test. Two sentences."}' | jq .
```

---

## Failure modes & troubleshooting

\***401 Unauthorized** – API key wrong or IAM block.
• Verify it in the watsonx Console → Service credentials.

\***504 Gateway timeout** – model took > 30 s.
• Increase `max_new_tokens` or lower `temperature`.
• Retry once; Granite usually responds on second attempt.

\*Knative stays at 0 replicas while requests 502.
• Check Quotas: Knative needs at least one free CPU on the cluster.
• Tail logs `kubectl logs -l app=prompt-service -n videogenie -f`.

---

## Scaling tips

\* `autoscaling.knative.dev/target: 100` means 100 concurrent HTTP
requests per pod. Adjust downwards if CPU usage > 80 %.
\* If you expect thousands of parallel users, increase
`maxScale` above 10 and watch IAM token‑manager rate limits
(500 req/min by default).

---

## Next ideas

\* Swap naïve splitter with spaCy for smarter sentence boundaries.
\* Cache previously processed scripts with Redis (`text` → `segments`
hash) to remove model load for duplicates.
\* Return slide index hints so the SPA can pre‑visualise breaks.

Happy prompting — drop this folder into the repo, wire the service URL
into the back‑end, and your users will get perfectly timed speech
segments every time!
