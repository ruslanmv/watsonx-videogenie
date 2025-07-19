# Services Overview

This section the core micro‑services that power VideoGenie. Click on any service below to view its individual README and deployment instructions.

| Service                                    | Description                                                    |
|--------------------------------------------|----------------------------------------------------------------|
| [avatar-service](./avatar-service/README.MD) | Generates lip‑synced MP4s by combining avatar images and TTS.  |
| [prompt-service](./prompt-service/README.md/) | Cleans and splits user scripts into timed segments via watsonx.|
| [orchestrate-service](./orchestrate-service/README.md) | Enriches scripts with Orchestrate skills and enqueues render jobs. |
| [metrics-action](./metrics-action/README.md) | Records front‑end metrics and forwards them to Instana & logs. |

```bash
# Example: deploy the avatar-service
cd services/avatar-service
docker build -t icr.io/videogenie/avatar-service:latest .
docker push icr.io/videogenie/avatar-service:latest
kubectl apply -f knative.yaml
