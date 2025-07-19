#!/usr/bin/env python3
"""Enrich a create-video request with watsonx Orchestrate
   then enqueue it on Kafka for the GPU renderer."""

import json, os, uuid, time
from kafka import KafkaProducer
import requests

KAFKA_BROKERS = os.environ["KAFKA_BROKERS"].split(",")
TOPIC = os.getenv("KAFKA_TOPIC", "videoJob")

ORCH_API   = os.getenv("ORCH_API", "https://orchestrate.ai.cloud.ibm.com/api")
ORCH_KEY   = os.environ["ORCH_APIKEY"]
TIMEOUT    = int(os.getenv("ORCH_TIMEOUT", "30"))

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKERS,
    value_serializer=lambda v: json.dumps(v).encode(),
)

def call_skill(skill: str, params: dict):
    r = requests.post(
        f"{ORCH_API}/skills/{skill}:invoke",
        headers={"Authorization": f"Bearer {ORCH_KEY}"},
        json={"params": params},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["result"]

def main():
    payload = json.loads(os.environ["INPUT_PAYLOAD"])

    # 1 · Rewrite the script for pacing and pronunciation
    payload["script"] = call_skill("rewrite-script", {"text": payload["text"]})

    # 2 · (Optionally) split into slides
    payload["slides"] = call_skill("generate-slides", {"text": payload["script"]})

    # 3 · Send to Kafka
    job_id = str(uuid.uuid4())
    producer.send(TOPIC, {"jobId": job_id, **payload})
    producer.flush()
    print("queued", job_id)

if __name__ == "__main__":
    t0 = time.time()
    main()
    print("elapsed", round(time.time() - t0, 2), "s")
