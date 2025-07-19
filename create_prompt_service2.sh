#!/bin/bash

# This script generates the directory structure and source files
# for the 'prompt-service', which orchestrates calls to watsonx.ai.

echo "🚀 Creating prompt-service directory and source files..."

# --- Create Directory Structure ---
# The service will be created inside a 'services' directory.
mkdir -p services/prompt-service/app

# --- Create services/prompt-service/app/main.py ---
cat << 'EOF' > services/prompt-service/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from utils import split_sentences
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai import IAMTokenManager

APIKEY      = os.environ["WATSONX_APIKEY"]
PROJECT_ID  = os.environ["PROJECT_ID"]
MODEL_ID    = os.getenv("MODEL_ID", "granite-13b-chat-v2")
SERVICE_URL = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

tm    = IAMTokenManager(api_key=APIKEY, url=f"{SERVICE_URL}/oidc/token")
model = Model(model_id=MODEL_ID, project_id=PROJECT_ID,
              credentials={"token_manager": tm})

class PromptBody(BaseModel):
    text: str

app = FastAPI(title="prompt-svc", version="0.1.0")

@app.post("/prompt")
async def prompt(body: PromptBody):
    if len(body.text.strip()) < 5:
        raise HTTPException(400, "text is too short")

    sentences = split_sentences(body.text)

    system_prompt  = (
        "You are a presentation script assistant. "
        "Return JSON array [{text,seconds}] predicting speaking time per sentence. "
        "Do NOT include any other keys."
    )
    user_content = "\n".join(sentences)

    response = model.generate_text(
        prompt=system_prompt,
        input=user_content,
        max_new_tokens=256,
        temperature=0.2,
    )
    return {"segments": response}
EOF

# --- Create services/prompt-service/app/utils.py ---
cat << 'EOF' > services/prompt-service/app/utils.py
import re
def split_sentences(text: str):
    """Split on punctuation followed by whitespace. Replace if you prefer spaCy."""
    return [s for s in re.split(r"(?<=[.!?]) +", text.strip()) if s]
EOF

# --- Create services/prompt-service/Dockerfile ---
cat << 'EOF' > services/prompt-service/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY app/ app/

# tiniest build — gcc only for regex back-end, then removed
RUN apt-get update && apt-get install -y gcc \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
      fastapi uvicorn pydantic \
      "ibm-watsonx-ai>=0.4.0"

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080"]
EOF

# --- Create services/prompt-service/knative.yaml ---
cat << 'EOF' > services/prompt-service/knative.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: prompt-service
  namespace: videogenie
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "10"
        autoscaling.knative.dev/target: "100"
    spec:
      containers:
        - image: icr.io/videogenie/prompt-service:latest
          env:
            - name: WATSONX_APIKEY
              valueFrom:
                secretKeyRef: { name: watsonx-secret, key: apikey }
            - name: PROJECT_ID
              value: "<project-id>"
EOF

echo "✅ 'prompt-service' directory and its source files have been created successfully."