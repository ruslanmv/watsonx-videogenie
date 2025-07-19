# CI/CD Pipelines for VideoGenie (Argo Workflows & Tekton)

Welcome to the CI/CD for VideoGenie. This section contains all the necessary YAML configurations to establish a robust, automated pipeline for continuous integration, continuous delivery, and asynchronous job processing using Tekton and Argo Workflows.

The pipelines are designed to work within two distinct namespaces:

  * `cicd`: For all build, push, and deployment tasks.
  * `videogenie`: For runtime resources, including the Argo event listeners and workflows.

-----

## ✨ Pipeline Overview

This setup is divided into two main components:

1.  **Argo Workflows:** Manages the asynchronous, event-driven video rendering process. It listens for jobs on a Kafka topic and triggers a GPU-powered rendering workflow for each message.
2.  **Tekton:** Handles the CI/CD process. It automatically builds and pushes container images upon a `git push` and then deploys the new version to the cluster using Helm.

-----

## 📁 Directory Structure

The `pipelines/` directory is organized as follows:

```text
pipelines/
├── argo/
│   ├── event-source.yaml    # Listens for messages on the Kafka topic
│   ├── sensor.yaml          # Connects the Kafka event to a workflow trigger
│   └── render-workflow.yaml # Defines the steps for the GPU rendering pipeline
└── tekton/
    ├── build-deploy.yaml    # The main CI/CD pipeline definition
    ├── pvc.yaml             # A persistent volume for the Tekton workspace
    ├── trigger.yaml         # Configures the webhook listener and trigger
    └── tasks/
        ├── buildah.yaml     # A task for building container images with Buildah
        └── helm-upgrade.yaml# A task for deploying releases with Helm
```

-----

## 1\. Argo Workflows: Asynchronous Rendering

The Argo components work together to create an event-driven system that processes video rendering jobs.

  * **`event-source.yaml`:** This resource configures Argo to listen to the `videoJob` topic on the Kafka instance. It's the entry point for all rendering requests.
  * **`sensor.yaml`:** This acts as the bridge between the event source and the workflow. When a message is detected on the Kafka topic, the sensor triggers the submission of a new rendering workflow.
  * **`render-workflow.yaml`:** This is the core workflow definition that outlines the multi-step process of rendering a video on a GPU-enabled node.

-----

## 2\. Tekton: Continuous Integration & Delivery

The Tekton pipeline automates the process of building and deploying the application.

  * **`pvc.yaml`:** Creates a `PersistentVolumeClaim` that serves as a shared workspace for the pipeline tasks, allowing them to share files (like the cloned source code).
  * **`tasks/`:** This directory contains the reusable, standalone tasks that make up the pipeline.
      * **`buildah.yaml`:** A task that uses Buildah to build a container image from a Dockerfile and, optionally, push it to a container registry.
      * **`helm-upgrade.yaml`:** A task that executes a `helm upgrade --install` command to deploy or update a release.
  * **`build-deploy.yaml`:** This is the main `Pipeline` resource that chains the tasks together:
    1.  **`git-clone`:** Clones the source code from the GitHub repository.
    2.  **`build-images`:** Builds the container images using the `buildah` task.
    3.  **`push-images`:** Pushes the newly built images to the container registry.
    4.  **`helm-upgrade`:** Deploys the new version using the `helm-upgrade-from-source` task.
  * **`trigger.yaml`:** This file contains the resources that expose the pipeline to the outside world.
      * **`EventListener`:** Creates a service that listens for incoming HTTP POST requests (from a GitHub webhook).
      * **`TriggerBinding`:** Extracts the git commit ID from the webhook payload.
      * **`TriggerTemplate`:** Defines a `PipelineRun` template that will be executed when the trigger is activated, passing the commit ID as a parameter.

-----

## 🚀 Deployment and Usage

Follow these steps to apply the pipeline configurations to your cluster.

1.  **Apply the Argo Workflow Resources:**
    These resources should be applied to the `videogenie` namespace.

    ```bash
    kubectl apply -f pipelines/argo/event-source.yaml
    kubectl apply -f pipelines/argo/sensor.yaml
    kubectl apply -f pipelines/argo/render-workflow.yaml
    ```

2.  **Apply the Tekton CI/CD Resources:**
    These resources should be applied to the `cicd` namespace.

    ```bash
    # Create the persistent volume claim
    kubectl apply -f pipelines/tekton/pvc.yaml

    # Create the reusable tasks
    kubectl apply -f pipelines/tekton/tasks/

    # Create the main pipeline
    kubectl apply -f pipelines/tekton/build-deploy.yaml

    # Create the webhook trigger
    kubectl apply -f pipelines/tekton/trigger.yaml
    ```

3.  **Configure the GitHub Webhook:**

      * Get the public URL of the `el-github-listener` service created by the `EventListener`.
      * In your GitHub repository settings, create a new webhook.
      * Set the **Payload URL** to the listener's public URL.
      * Set the **Content type** to `application/json`.
      * Configure the webhook to trigger on **push** events.

Once configured, any `git push` to your repository will automatically trigger the Tekton pipeline, which will build, push, and deploy the new version of your application.