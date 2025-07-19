# AI Job Composer Service

Welcome to the AI Job Composer service, a key microservice in the VideoGenie stack. This service acts as the initial entry point for a video creation request. It takes the user's choices (avatar, voice, script) from the `/assist` API endpoint and uses the power of **IBM watsonx** to refine the script for optimal pacing and clarity.

It's important to clarify the role of the AI service used here. While it is a powerful platform capable of orchestrating complex multi-agent systems, this project uses its core feature of invoking AI-powered "skills" for specific, automated tasks—in this case, enhancing and preparing text for video generation.

The core logic is encapsulated within an **IBM Cloud Code Engine Job**, a serverless, run-to-completion model. This is a highly efficient approach because the service only consumes resources during its brief execution time, making it perfect for handling bursty, unpredictable workloads without maintaining idle pods.

-----

## ✨ Core Functionality

  * **Asynchronous Processing:** Accepts requests from the front end and immediately returns a job ID, preventing the UI from blocking while waiting for processing.
  * **AI-Powered Script Enhancement:** Leverages AI "skills" to automatically rewrite the user's script, improving pacing, pronunciation, and overall flow for the text-to-speech engine.
  * **Immutable Job Creation:** After processing, it publishes a single, enriched message to the `videoJob` Kafka topic. This message contains all the information required for the downstream rendering pipeline.
  * **Serverless Efficiency:** As a Code Engine Job, it scales from zero to thousands of parallel invocations on demand and incurs costs only for the seconds of CPU time used.

-----

## 📁 Directory Structure

The service is composed of the following files:

```text
services/orchestrate-service/
├── job.py            # The Python script containing the core logic
├── Dockerfile        # A minimal Dockerfile for building the container image
└── codeengine.yaml   # The IBM Cloud Code Engine Job definition
```

-----

## 1\. The Python Job (`job.py`)

This script is the heart of the service. It performs the following steps:

1.  **Reads Input:** Ingests the initial JSON payload (containing avatar, voice, and text) from an environment variable.
2.  **Calls AI Skills:** Makes secure API calls to invoke two skills:
      * `rewrite-script`: To enhance the raw text.
      * `generate-slides`: To segment the rewritten script into logical slides.
3.  **Enqueues Job:** Connects to the Kafka cluster and publishes the final, enriched payload to the `videoJob` topic with a unique `jobId`.

## 2\. The Container (`Dockerfile`)

This file defines a lightweight, efficient container image for the job.

  * **Base Image:** Uses the `python:3.11-slim` image to keep the final container size minimal.
  * **Dependencies:** Installs only the necessary Python libraries (`kafka-python`, `requests`).
  * **Entrypoint:** Sets the container to execute the `job.py` script upon startup.

## 3\. The Job Definition (`codeengine.yaml`)

This manifest defines how the service runs on IBM Cloud Code Engine.

  * **Kind:** Defines the resource as a Code Engine `Job`.
  * **Run Policy:** Configures the job to time out after 5 minutes (`maxExecutionTime`) and to retry up to 2 times on failure.
  * **Container Spec:** Specifies the container image to run and how to configure it.
  * **Secure Configuration:** It securely injects the API Key from a Kubernetes secret (`orch-creds`) into the container as an environment variable, avoiding hardcoded credentials.
  * **Optional Scheduling:** Includes a commented-out `schedule` property, which can be enabled to run the job on a cron schedule (e.g., for testing or heartbeat purposes).

-----

## 🚀 Setup and Deployment

### **1. One-Time Secret Creation**

Before deploying the job, you must create a Kubernetes secret to hold your API key.

```bash
kubectl create secret generic orch-creds \
  --from-literal=apikey=$ORCH_KEY \
  -n videogenie
```

### **2. Build and Deploy Workflow**

Follow these steps to build the container image and deploy the job.

1.  **Set Environment Variables:**

    ```bash
    export REG=icr.io/videogenie
    export TAG=$(git rev-parse --short HEAD)
    ```

2.  **Build and Push the Container Image:**

    ```bash
    docker build -t $REG/orchestrate-service:$TAG services/orchestrate-service
    docker push $REG/orchestrate-service:$TAG
    ```

3.  **Deploy the Code Engine Job:**
    This command substitutes the `latest` image tag in the YAML with your new git commit tag and applies the configuration to Code Engine.

    ```bash
    sed -e "s|latest|$TAG|" services/orchestrate-service/codeengine.yaml | \
      ibmcloud ce job apply -f -
    ```

-----

## ⚙️ End-to-End Flow

When a user clicks "Generate" in the front-end application, the `/assist` API endpoint invokes this Code Engine Job, passing the user's selections as the `INPUT_PAYLOAD`.

The job runs, calls the AI service to enhance the script, and places the final message onto the Kafka topic. From there, KEDA detects the new message, scales up the GPU renderer pool, and Argo Workflows orchestrates the video creation.

This fully decoupled, pay-per-use architecture provides a powerful and cost-effective solution for handling video creation requests at scale.