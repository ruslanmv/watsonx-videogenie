#!/usr/bin/env python3
"""Watson X Orchestrate Service Job Runner.

This script enriches video creation requests using Watson X Orchestrate AI skills,
then publishes the enriched payload to Kafka for GPU rendering. Designed to run
as a Code Engine Job.

Author: Ruslan Magana (https://ruslanmv.com)
License: Apache 2.0
"""

import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List

import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Kafka Configuration
KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS", "").split(",")
TOPIC = os.getenv("KAFKA_TOPIC", "videoJob")

# Watson X Orchestrate Configuration
ORCH_API = os.getenv(
    "ORCH_API",
    "https://orchestrate.ai.cloud.ibm.com/api",
)
ORCH_KEY = os.environ.get("ORCH_APIKEY")
TIMEOUT = int(os.getenv("ORCH_TIMEOUT", "30"))

# Validate required environment variables
if not KAFKA_BROKERS or not KAFKA_BROKERS[0]:
    logger.error("KAFKA_BROKERS environment variable not set")
    raise EnvironmentError("KAFKA_BROKERS is required")

if not ORCH_KEY:
    logger.error("ORCH_APIKEY environment variable not set")
    raise EnvironmentError("ORCH_APIKEY is required")


def create_kafka_producer() -> KafkaProducer:
    """Create and configure Kafka producer with JSON serialization.

    Returns:
        KafkaProducer: Configured Kafka producer instance.

    Raises:
        KafkaError: If connection to Kafka brokers fails.
    """
    try:
        logger.info(f"Connecting to Kafka brokers: {KAFKA_BROKERS}")

        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",  # Wait for all replicas
            retries=3,
            max_in_flight_requests_per_connection=1,
        )

        logger.info("Successfully connected to Kafka")
        return producer

    except KafkaError as e:
        logger.error(f"Failed to connect to Kafka: {e}")
        raise


def call_skill(skill: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a Watson X Orchestrate AI skill.

    Calls a specific AI skill via the Watson X Orchestrate API to process
    the provided parameters. Skills can perform tasks like script rewriting
    and slide generation.

    Args:
        skill: Name of the AI skill to invoke (e.g., 'rewrite-script').
        params: Dictionary of parameters to pass to the skill.

    Returns:
        Dict containing the skill execution result.

    Raises:
        requests.HTTPError: If the API call fails.
        requests.Timeout: If the request exceeds the timeout.
        ValueError: If the response format is invalid.

    Example:
        >>> result = call_skill("rewrite-script", {"text": "Hello world"})
        >>> print(result)
        {'enhanced_text': '...'}
    """
    try:
        url = f"{ORCH_API}/skills/{skill}:invoke"

        logger.info(f"Calling Watson X Orchestrate skill: {skill}")
        logger.debug(f"Skill parameters: {params}")

        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {ORCH_KEY}",
                "Content-Type": "application/json",
            },
            json={"params": params},
            timeout=TIMEOUT,
        )

        response.raise_for_status()
        result = response.json()

        if "result" not in result:
            raise ValueError(f"Invalid response format from skill '{skill}'")

        logger.info(f"Successfully executed skill: {skill}")
        return result["result"]

    except requests.HTTPError as e:
        logger.error(f"HTTP error calling skill '{skill}': {e}")
        logger.error(f"Response: {e.response.text if e.response else 'N/A'}")
        raise

    except requests.Timeout:
        logger.error(f"Timeout calling skill '{skill}' after {TIMEOUT}s")
        raise

    except requests.RequestException as e:
        logger.error(f"Network error calling skill '{skill}': {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error calling skill '{skill}': {e}")
        raise


def process_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process and enrich video creation payload using Watson X Orchestrate.

    Applies AI skills to enhance the script and generate slide segmentation.

    Args:
        payload: Raw video creation request payload.

    Returns:
        Dict containing enriched payload with processed script and slides.

    Raises:
        KeyError: If required fields are missing from payload.
        Exception: If skill invocation fails.
    """
    try:
        # Validate required fields
        if "text" not in payload:
            raise KeyError("Payload must contain 'text' field")

        original_text = payload["text"]
        logger.info(f"Processing payload with {len(original_text)} characters")

        # Step 1: Rewrite script for better pacing and pronunciation
        logger.info("Step 1: Rewriting script for pacing and pronunciation")
        enhanced_script = call_skill(
            "rewrite-script",
            {"text": original_text},
        )
        payload["script"] = enhanced_script

        # Step 2: Generate slide segmentation
        logger.info("Step 2: Generating slide segmentation")
        slides = call_skill(
            "generate-slides",
            {"text": enhanced_script},
        )
        payload["slides"] = slides

        logger.info("Payload processing completed successfully")
        return payload

    except KeyError as e:
        logger.error(f"Missing required field in payload: {e}")
        raise

    except Exception as e:
        logger.error(f"Error processing payload: {e}")
        raise


def publish_to_kafka(
    producer: KafkaProducer,
    payload: Dict[str, Any],
    job_id: str,
) -> None:
    """Publish enriched job payload to Kafka topic.

    Args:
        producer: Kafka producer instance.
        payload: Enriched job payload to publish.
        job_id: Unique job identifier.

    Raises:
        KafkaError: If message publishing fails.
    """
    try:
        message = {"jobId": job_id, **payload}

        logger.info(f"Publishing job {job_id} to Kafka topic: {TOPIC}")

        future = producer.send(TOPIC, value=message)
        record_metadata = future.get(timeout=10)

        logger.info(
            f"Successfully published to Kafka - "
            f"Topic: {record_metadata.topic}, "
            f"Partition: {record_metadata.partition}, "
            f"Offset: {record_metadata.offset}"
        )

    except KafkaError as e:
        logger.error(f"Failed to publish to Kafka: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected error publishing to Kafka: {e}")
        raise


def main() -> None:
    """Main execution function.

    Orchestrates the complete workflow:
    1. Load input payload from environment
    2. Enrich payload using Watson X Orchestrate skills
    3. Publish to Kafka for GPU rendering
    4. Log execution metrics

    Raises:
        EnvironmentError: If INPUT_PAYLOAD is not set.
        Exception: For any processing errors.
    """
    start_time = time.time()

    try:
        # Load input payload
        payload_str = os.environ.get("INPUT_PAYLOAD")
        if not payload_str:
            raise EnvironmentError("INPUT_PAYLOAD environment variable not set")

        logger.info("Loading input payload")
        payload = json.loads(payload_str)

        # Generate unique job ID
        job_id = str(uuid.uuid4())
        logger.info(f"Processing job ID: {job_id}")

        # Create Kafka producer
        producer = create_kafka_producer()

        try:
            # Process payload with Watson X Orchestrate
            enriched_payload = process_payload(payload)

            # Publish to Kafka
            publish_to_kafka(producer, enriched_payload, job_id)

            # Calculate metrics
            elapsed = round(time.time() - start_time, 2)
            logger.info(f"Job {job_id} completed successfully in {elapsed}s")

            print(f"✓ Job queued: {job_id}")
            print(f"✓ Elapsed time: {elapsed}s")

        finally:
            # Ensure producer is properly closed
            producer.flush()
            producer.close()
            logger.info("Kafka producer closed")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in INPUT_PAYLOAD: {e}")
        raise SystemExit(1)

    except EnvironmentError as e:
        logger.error(f"Environment configuration error: {e}")
        raise SystemExit(1)

    except Exception as e:
        logger.error(f"Job processing failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    logger.info("=== Watson X Orchestrate Job Runner Started ===")
    main()
    logger.info("=== Watson X Orchestrate Job Runner Finished ===")
