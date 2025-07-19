
# GPU Renderer Service for OpenShift

This document describes the GPU renderer, a cloud-native service designed to perform intensive video rendering tasks on an OpenShift or Kubernetes cluster equipped with NVIDIA GPUs. It's a core component of the VideoGenie stack, responsible for processing rendering jobs.

-----

## File Overview

The service is composed of three key files, each serving a distinct purpose in the build and deployment pipeline.

```text
renderer/
├── render.py         # The core Python rendering application.
├── Dockerfile        # Instructions to build a GPU-enabled container image.
└── deployment.yaml   # Kubernetes manifest for deploying to OpenShift.
```

### `render.py`

This is the main application script written in Python. It's designed to be stateless and configurable via environment variables, a common pattern in cloud-native applications.

  * **Logic:** It simulates a complete rendering job pipeline:
      * Downloads assets from IBM Cloud Object Storage (COS).
      * Executes a placeholder GPU-intensive rendering task.
      * Uploads the resulting video file back to COS.
  * **Configuration:** All settings (like COS bucket names, endpoints, and credentials) are read from environment variables. In a live OpenShift environment, these variables are populated by Kubernetes Secrets and ConfigMaps.
  * **Dependencies:** It uses the `boto3` library to communicate with the S3-compatible API of IBM Cloud Object Storage.

### `Dockerfile`

This file defines the steps to package the `render.py` script into a container image.

  * **Base Image:** It uses `nvidia/cuda` as its base image. This is critical as it includes the necessary NVIDIA libraries and drivers for the container to interface with the GPU hardware on the host worker node.
  * **Setup:** It installs Python, copies the `render.py` script, and installs the `boto3` dependency.
  * **Entrypoint:** It sets the container's entrypoint to execute the `render.py` script, making the image runnable as a self-contained microservice.

### `deployment.yaml`

This is a standard Kubernetes Deployment manifest tailored for running the renderer on a GPU-enabled OpenShift cluster.

  * **GPU Resource Request:** The manifest explicitly requests one GPU from the cluster's resources (`nvidia.com/gpu: "1"`). This is made possible by the NVIDIA GPU Operator, which must be installed on the cluster.
  * **Node Targeting:** It uses a `nodeSelector` and `tolerations` to ensure that the renderer pods are scheduled only on worker nodes that are equipped with GPUs and are designated for such workloads.
  * **Configuration Injection:** It demonstrates how to securely inject configuration into the running container. It maps values from Kubernetes `Secrets` (for `COS_ACCESS_KEY`, `COS_SECRET_KEY`) and `ConfigMaps` (for `JOB_PAYLOAD`) to environment variables inside the pod.
  * **Scalability:** The deployment is initialized with `replicas: 0`. This is intentional, as it's designed to be managed by an external autoscaler like KEDA, which can scale the number of renderer pods up from zero based on job queue length and scale them back down to zero when idle, optimizing resource consumption.

-----

## Deployment Workflow

### Prerequisites

  * An OpenShift or Kubernetes cluster with GPU-enabled worker nodes.
  * The NVIDIA GPU Operator installed on the cluster.
  * `docker` or a similar container build tool installed locally.
  * `oc` or `kubectl` command-line tool configured to connect to your cluster.
  * A container registry (e.g., IBM Cloud Container Registry) to store the built image.

### Steps

1.  **Build and Push the Container Image:**
    Navigate to the `renderer` directory and run the following commands, replacing the image path with your own container registry URL.
    ```bash
    # Build the Docker image
    docker build -t icr.io/videogenie/renderer:latest .

    # Push the image to your container registry
    docker push icr.io/videogenie/renderer:latest
    ```
2.  **Prepare Kubernetes Resources:**
    Before applying the deployment, ensure the corresponding `Secret` and `ConfigMap` exist in the `videogenie` namespace on your cluster.
      * A secret named `cos-credentials` containing the keys `access_key_id` and `secret_access_key`.
      * A `ConfigMap` named `job-payload-cm` containing the key `payload.json`.
3.  **Deploy to OpenShift:**
    Apply the manifest to deploy the renderer service.
    ```bash
    kubectl apply -f renderer/deployment.yaml
    ```
    Once applied, KEDA (or another scaler) can begin managing the deployment, spinning up pods on GPU nodes as new rendering jobs arrive.