# 🛠️ Building VideoGenie: The Complete Guide from Local Dev to Global SaaS

## Introduction

This tutorial provides a comprehensive guide to building, deploying, and operating the VideoGenie platform. It walks through every decision, command, and line of code required, starting from a local development environment on your laptop and scaling up to a production-grade, global text-to-avatar video SaaS on IBM Cloud.

By the end, you'll have a working system featuring:

  * A **React front-end** served from IBM Cloud Object Storage and accelerated by the Cloud Internet Services (CIS) global edge network.
  * Secure **JWT-based authentication** via IBM Cloud App ID.
  * An **Istio-secured service mesh** running on Red Hat OpenShift, fronted by API Gateway.
  * **Watson-powered AI** for speech synthesis and language understanding.
  * An asynchronous **Kafka and Argo Workflows pipeline** orchestrating GPU-based video rendering.
  * Full **observability** with Log Analysis and Instana for tracing and monitoring.

We'll cover two paths: a rapid local setup using Docker and Kind for development and a full production deployment on IBM Cloud. The narrative assumes you start with nothing but an IBM Cloud account, the necessary CLIs, and a GitHub repository for your code.

-----

## Part A: Local Development Stack (≤ 10 Minutes)

This section gets the entire platform running on your laptop using **Docker and Kind**. It's perfect for UI development, rapid API iterations, or creating demo videos offline.

### Prerequisites

Before you begin, ensure you have the following tools installed:

  * Docker 24+
  * [Kind v0.23](https://kind.sigs.k8s.io/) (Kubernetes in Docker)
  * GNU Make 4.x
  * Node.js 18 LTS
  * Python 3.11
  * Git 2.40+

### Step 1: Clone the Repository and Set Up Tooling

First, clone the project repository and run the setup script. This will create a Python virtual environment (`.venv`) and install pre-commit hooks for code quality.

```bash
git clone https://github.com/ruslanmv/watsonx-videogenie.git
cd watsonx-videogenie

# This installs Python dependencies and sets up git hooks
make setup
```

### Step 2: Prepare Model Artifacts

The video rendering process requires pre-trained machine learning models. These commands will download the necessary Wav2Lip model and prepare the directory for your custom avatar images.

```bash
# Clones the Wav2Lip repo and downloads wav2lip_gan.pth
make fetch-wav2lip

# Creates the 'models/' directory; copy your avatar PNGs here
make prepare-models
```

### Step 3: Build the Docker Images

Next, build all the microservice container images. We'll tag them with the short Git commit hash for versioning.

```bash
make container-build TAG=$(git rev-parse --short HEAD)
```

### Step 4: Launch the Local Kubernetes Cluster

This command uses Kind to spin up a single-node Kubernetes v1.30 cluster inside Docker. Then, we install the core add-ons: Istio for the service mesh, Argo for workflows, and KEDA for autoscaling.

```bash
# Creates the Kind cluster (takes a minute or two)
make kind-up

# Installs Istio, Argo Workflows, and KEDA into the cluster
make install-istio install-argo install-keda
```

### Step 5: Deploy the VideoGenie Helm Chart

With the cluster and its dependencies ready, deploy the entire application stack using the provided Helm chart. This command installs all our microservices and configurations into the `videogenie` namespace.

```bash
helm upgrade --install videogenie charts/videogenie \
  --namespace videogenie --create-namespace \
  --set global.image.tag=$(git rev-parse --short HEAD)
```

### Step 6: Run the Frontend SPA

Finally, start the React-based single-page application (SPA).

```bash
cd frontend
npm ci
npm start
```

🎉 You're live\! Open your browser to **http://localhost:5173**. You can now hit "Generate" and watch the WebSocket updates show the video rendering progress in real time.

### Step 7: Clean Up

When you're finished with the local environment, you can tear everything down with a single command.

```bash
make kind-down
```

-----

## Part B: Production Deployment on IBM Cloud

This section details the steps to deploy a robust, scalable, and secure version of VideoGenie on IBM Cloud. The following commands were verified on *19 July 2025*.

### Step 1: Establishing the Edge and Static Hosting Layer

We begin at the edge. The user's first point of contact is our React application, hosted on Cloud Object Storage (COS) and delivered globally via Cloud Internet Services (CIS).

You begin by creating a CIS instance for your domain. After delegating your registrar’s name servers to the ones supplied by CIS, you request a wildcard TLS certificate.

  * **In the CIS UI:** Navigate to **TLS/SSL \> Edge Certificates**.
  * **Action:** Click **Order Certificate**, choose **Let’s Encrypt** as the issuer, and add `*.videogenie.cloud` and `videogenie.cloud` to the domains.
  * **Result:** CIS handles the DNS challenge automatically, and the certificate will become active within minutes.

Next, create a COS bucket to host the static frontend assets.

```bash
# Create a Cloud Internet Services instance
ibmcloud cis instance-create vg-cis standard eu-de

# Create a Cloud Object Storage bucket for the React SPA
ibmcloud cos bucket-create --bucket spa-assets --class standard --region eu-de
```

In the COS UI for the `spa-assets` bucket, enable **Static website hosting** and set the index document to `index.html`. A production build of the React app can now be uploaded here.

To serve these assets through your custom domain, you'll configure CIS with an **Origin Pool** pointing to the public COS static website endpoint. A **Load Balancer** will route traffic to this pool, and a **Page Rule** will enforce HTTPS and set browser caching policies.

### Step 2: Setting Up Authentication with App ID

User identity is managed by IBM Cloud App ID, which provides a fully managed OIDC-compliant identity provider.

First, create an instance of the service.

```bash
ibmcloud resource service-instance-create vg-appid appid lite eu-de
```

In the App ID dashboard:

1.  Navigate to **Manage Authentication \> Cloud Directory** and enable it as the identity source.
2.  Go to **Applications** and click **Add application**.
3.  Choose **Web App** as the type.
4.  Copy the `clientId` and `oauthServerUrl` (from the "discovery endpoint" link). Your React application will need these to initiate the OAuth 2.0 Authorization Code Flow with PKCE.
5.  In the application settings, add your frontend URL (`https://app.videogenie.cloud`) to the list of **Allowed Web Origins** and `https://app.videogenie.cloud/callback` to the list of **Allowed Redirect URIs**.

At this point, logging in will return a JWT `access_token` that the SPA can use to make authenticated API calls.

### Step 3: Infrastructure as Code with Terraform

Manually creating cloud resources works, but for a repeatable and version-controlled setup, we use Terraform. The repository includes a Terraform script to provision the foundational services.

```bash
# Navigate to the Terraform directory
cd infra/terraform

# Initialize Terraform and download providers
terraform init

# Apply the configuration to create the resources on IBM Cloud
terraform apply -auto-approve \
  -var domain="videogenie.cloud" \
  -var region="eu-de"
```

This script automatically creates:

  * The CIS zone and necessary DNS records.
  * COS buckets: `spa-assets` and `videos-prod`.
  * An Event Streams (Kafka) instance with a `videoJob` topic.
  * Instances for Log Analysis, Secrets Manager, and App ID.

Save the Terraform outputs, as they will be needed to configure the Helm chart later.

### Step 4: Provisioning OpenShift and the GPU Fleet

The core of our application runs on Red Hat OpenShift on IBM Cloud. We need a general-purpose worker pool for our stateless services and a specialized GPU pool for video rendering.

```bash
# Create the OpenShift cluster with a standard worker pool
ibmcloud oc cluster create classic --name vg-cluster --zone eu-de-1 \
  --worker-pool cpu --flavor bx2.16x64 --workers 3

# Add a GPU worker pool for rendering workloads
ibmcloud oc worker-pool create gpu --cluster vg-cluster \
  --flavor g2.8x64 --workers 2 --labels role=gpu=true
```

We must label and taint the GPU nodes to ensure that only rendering pods are scheduled on this expensive hardware.

```bash
# Label the GPU nodes (if not already done by the pool)
oc label nodes -l ibm-cloud.kubernetes.io/flavor=g2.8x64 role=gpu=true

# Taint the nodes to repel non-GPU workloads
oc adm taint nodes -l role=gpu=true dedicated=gpu:NoSchedule
```

### Step 5: Installing the Service Mesh and Add-ons

We use Istio to secure pod-to-pod communication with mutual TLS (mTLS). It's installed via the OpenShift OperatorHub. After installing the operator, create a `ServiceMeshControlPlane` custom resource in the `istio-system` namespace that enables **strict mTLS**.

The quickest way to install Istio and the other key components (Argo Workflows and KEDA) is with the `make` targets:

```bash
make install-istio install-argo install-keda
```

### Step 6: Creating the API Gateways

While Istio provides a mesh ingress, we'll use **IBM Cloud API Gateway** for its public-facing features like JWT validation, rate limiting, and seamless integration with other IBM Cloud services.

  * Create an **HTTP API** instance to front the REST endpoints (`/api/*`). For each API operation, attach the **JWT plug-in** and configure it with the JWK URL from your App ID discovery document.
  * Create a separate **WS API** instance for the WebSocket notification service at `/ws/notify`.
  * Map the API Gateway hostnames in CIS by creating DNS records that route `/api/*` and `/ws/*` to the respective gateways.

### Step 7: Building and Pushing Container Images

With the cloud infrastructure ready, we build our application's container images and push them to the IBM Cloud Container Registry (ICR).

```bash
# Log in to the IBM Cloud Container Registry for the target region
ibmcloud cr region-set eu-de && ibmcloud cr login

# Define a tag for the images (e.g., the git commit hash)
export TAG=$(git rev-parse --short HEAD)

# Build all container images with the specified tag
make container-build TAG=$TAG

# Push the newly built images to ICR
make container-push TAG=$TAG
```

### Step 8: Deploying Microservices with Helm

All backend services are deployed onto the OpenShift cluster using a single Helm chart. The stateless services (like `avatar-service` and `prompt-service`) are deployed as Knative Services, allowing them to scale to zero when idle.

We use the `helm upgrade --install` command to deploy or update the `videogenie` release, passing in the values from our Terraform outputs to connect the application to the backend services.

```bash
helm upgrade --install videogenie charts/videogenie \
  --namespace videogenie --create-namespace \
  --set global.image.tag=$TAG \
  --set spa.bucket=$(terraform -chdir=infra/terraform output -raw spa_bucket) \
  --set appid.clientId=$(terraform -chdir=infra/terraform output -raw appid_client_id) \
  --set kafka.brokers=$(terraform -chdir=infra/terraform output -raw kafka_brokers)
```

### Step 9: The Asynchronous GPU Pipeline

When a user submits a video request, the `orchestrate-service` sends a message to the `videoJob` topic in **Event Streams (Kafka)**.

An **Argo Events** `KafkaEventSource` listens to this topic. When a new message arrives, a Sensor triggers an **Argo Workflow**. This workflow spawns a renderer pod that is scheduled specifically onto a GPU node, thanks to its toleration for the `dedicated=gpu:NoSchedule` taint.

The render pod:

1.  Pulls avatar model weights from COS.
2.  Synthesizes audio with Watson Text to Speech.
3.  Runs the Wav2Lip model for lip-syncing.
4.  Encodes the final video using FFmpeg with NVENC (NVIDIA hardware encoding).
5.  Uploads the finished MP4 to the `videos-prod` COS bucket.
6.  Publishes a status update to another Kafka topic, which is fanned out to the user's browser via the WebSocket gateway for a real-time progress update.

### Step 10: Configuring GPU Autoscaling

To manage costs effectively, we use a two-tiered autoscaling strategy:

1.  **KEDA (Kubernetes Event-driven Autoscaling):** A `ScaledObject` monitors the Kafka topic lag. As the number of unprocessed jobs in the `videoJob` topic grows, KEDA scales up the number of `render-pod` replicas.
2.  **Cluster Autoscaler:** When KEDA creates new pods that cannot be scheduled due to a lack of GPU resources, the OpenShift Cluster Autoscaler automatically provisions new GPU worker nodes from the cloud provider, up to a defined maximum.

When the queue is empty, KEDA scales the renderer pods back down to zero, and the Cluster Autoscaler terminates the idle GPU nodes.

### Step 11: Observability Setup

Comprehensive observability is crucial for a production system.

  * **Logging:** The **Log Analysis** agent is deployed to the cluster. It automatically tails container logs and forwards them to a centralized LogDNA endpoint for searching and analysis.
  * **Monitoring & Tracing:** The **Instana** agent, installed via its Operator, automatically instruments the application. It traces requests through the Istio service mesh, providing a dependency map, latency heatmaps, and performance metrics without any code changes.

Deploy the agents with these commands:

```bash
# Deploy the Log Analysis agent
oc apply -f manifests/logdna-agent.yaml

# Deploy the Instana agent
oc apply -f manifests/instana-agent.yaml
```

### Step 12: Continuous Delivery Pipeline

Automation is key to reliable delivery. The repository is configured with a CI/CD pipeline:

1.  **GitHub Actions:** On every push to the `main` branch, a workflow (`.github/workflows/ci.yml`) triggers to build and push the new container images to ICR.
2.  **Tekton/Argo CD:** A GitOps tool like Argo CD, pointed at the application's Helm chart repository, detects the new image tag. It automatically syncs the cluster state, rolling out the new version of the application with zero downtime.
3.  **Cache Purge:** A post-deployment job uses the IBM Cloud CLI to purge the CIS CDN cache, ensuring users receive the latest version of the frontend immediately.

<!-- end list -->

```bash
# Command to purge the entire CIS cache
ibmcloud cis cache-purge $(ibmcloud cis zones -i vg-cis --output json | jq -r '.[0].id') --all
```

### Step 13: Smoke Test and Cleanup

After deployment, perform a final smoke test:

1.  Open `https://app.videogenie.cloud`.
2.  Log in via the App ID-hosted login page.
3.  Paste a script, select an avatar, and click **Generate**.
4.  Verify that the WebSocket connection shows progress and that the final MP4 URL points to the CIS video delivery domain (`https://assets-public.videogenie.cloud/*`).

To decommission the entire production environment, you can uninstall the Helm release and run `terraform destroy`.

```bash
# Uninstall the application from OpenShift
helm uninstall videogenie -n videogenie

# Destroy all cloud resources managed by Terraform
terraform -chdir=infra/terraform destroy -auto-approve

# Delete the CIS instance manually
ibmcloud resource service-instance-delete vg-appid -f
ibmcloud cis instance-delete vg-cis -f
```

-----

## Architecture and Security Reference

The final architecture is a cloud-native, event-driven system designed for security and scale.

### Architecture Diagram

```mermaid
flowchart TD
  subgraph Client
    U[User Browser]
  end

  subgraph Edge [IBM Cloud Internet Services]
    CDN[CIS POP / WAF] --> SPA[React SPA from COS]
  end

  subgraph Auth
    AppID[IBM Cloud App ID]
  end

  subgraph Gateway [API Gateway + Istio]
    JWT[JWT Filter] --> Mesh[Istio Ingress]
  end

  subgraph Services [OpenShift Cluster]
    Avatar[avatar-svc]
    Voice[voice-svc]
    Prompt[prompt-svc]
    Orch[orchestrate-svc]
    Metrics[metrics-action]
  end

  subgraph Async Pipeline
    ES[Event Streams (Kafka)] --> WF[Argo Workflows]
    WS[WebSocket Service]
  end

  subgraph GPU Fleet [Auto-Scaling]
    Rend[GPU Renderer Pod]
  end

  subgraph Storage
    COS[(Cloud Object Storage)]
  end

  subgraph Delivery
    VID[CIS Video Cache] --> Player[Embeddable Player]
  end

  subgraph Observability
    Logs[IBM Log Analysis]
    Inst[Instana APM]
  end

  U -- HTTPS --> CDN
  CDN --> SPA

  SPA -- OAuth Flow --> AppID
  AppID -- JWT Token --> SPA

  SPA -- /api/* (JWT) --> JWT
  JWT --> Mesh

  SPA -- /ws/* --> WS

  Mesh --> Avatar
  Mesh --> Voice
  Mesh --> Prompt
  Mesh --> Orch
  Mesh --> Metrics

  Orch -- Video Job --> ES
  ES -- Event --> WF
  WF -- Spawns Pod --> Rend
  Rend -- Renders Video --> COS
  Rend -- Status Update --> ES
  ES -- Status --> WS
  WS -- Progress --> U

  COS -- Private URL --> VID
  VID -- Cached Video --> Player

  Services -- Logs --> Logs
  Rend -- Logs & Metrics --> Logs
  Mesh -- Traces --> Inst
```

### Security and Compliance Wrap-up

  * **Network:** All public endpoints are protected by the CIS WAF and API Gateway rate limiting. All internal traffic within the OpenShift cluster is encrypted via Istio's strict mTLS.
  * **Authentication:** Short-lived JWTs from App ID (expiring in one hour) are used for all API calls.
  * **Secrets:** All credentials (API keys, database passwords) are stored in IBM Cloud Secrets Manager and securely mounted into pods using the CSI driver. Nothing sensitive is ever stored in a Git repository or container image.
  * **Data Residency:** All resources are pinned to a single region (e.g., Frankfurt `eu-de`) to meet data residency requirements. Audit events are streamed to IBM Cloud Activity Tracker.

-----

## Conclusion

You now have a complete blueprint for a production-grade, text-to-avatar video factory running entirely on IBM Cloud, built with open standards. From the edge POP that serves the initial HTML to the V100/G2 GPU cores that crunch visemes into pixels, every component is scripted, reproducible, and observable. This architecture is not only powerful but also flexible; the same blueprint can be adapted for on-premises OpenShift or other cloud providers. Because it is built on CNCF projects and managed IBM services, it is well-positioned to evolve as rapidly as the generative AI ecosystem itself.

*Enjoy building\! PRs and issues are welcome in the project repository. For support, join the community on the IBM Cloud Slack.*