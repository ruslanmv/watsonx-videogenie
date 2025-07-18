# 🎬 WatsonX VideoGenie 

> Turn plain text into AI‑generated avatar videos using IBM Cloud managed services, watsonx foundation models and OpenShift GPU compute.  This repository contains everything required to deploy the full stack end‑to‑end.

[![Built for IBM Cloud](https://img.shields.io/badge/IBM%20Cloud‑Ready-blue)]()
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License Apache‑2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)]()
[![CI Status](https://github.com/videogenie/videogenie-ibmcloud/actions/workflows/ci.yml/badge.svg)]()

 A **proof of concept** that turns plain text into a narrated avatar video using nothing but IBM Cloud managed services, OpenShift GPU nodes and watsonx foundation models.



## What you get

A single Git repo that spins up **every layer** of the platform described in the diagram below: CIS edge, App ID auth, API Gateway, Istio mesh, Knative micro‑services, Event Streams, Argo Workflows, GPU render pods, Cloud Object Storage delivery, Log Analysis and Instana tracing.  The front‑end is a React SPA that calls these APIs to create an MP4 in about a minute.

```mermaid
flowchart TD
    subgraph Client
        U[User Browser]
    end

    subgraph Edge["IBM Cloud Internet Services CDN + WAF"]
        CISCDN[CIS Edge POP]
        SPA[React SPA static<br/>from COS]
    end
    U -- HTTPS --> CISCDN
    CISCDN -- "HTML/CSS/JS" --> SPA

    subgraph Auth
        AppID[IBM Cloud App ID]
    end
    SPA -- OAuth2 --> AppID
    AppID -- JWT --> SPA

    subgraph APIGateway["IBM API Gateway REST<br/>+ Istio Mesh"]
        JWTAuth[JWT Plug‑in]
        IstioEnvoy[Istio Ingress<br/>Envoy]
    end
    SPA -- "Bearer JWT" --> JWTAuth --> IstioEnvoy

    subgraph AI["Back‑end Services"]
        AvatarSvc[Knative Service<br/>avatar‑svc]
        VoiceSvc[Watson TTS/STT]
        PromptSvc[watsonx.ai<br/>LLM prompt]
        OrchestrateSvc[Code Engine Job<br/>assisted‑creation]
        MetricsSvc[Cloud Functions<br/>metrics]
    end
    IstioEnvoy --> AvatarSvc
    IstioEnvoy --> VoiceSvc
    IstioEnvoy --> PromptSvc
    IstioEnvoy --> OrchestrateSvc
    IstioEnvoy --> MetricsSvc

    subgraph Async
        Kafka[Event Streams<br/>Kafka]
        Argo[Argo Workflows]
        WS[Istio Ingress<br/>WebSocket /notify]
    end
    OrchestrateSvc --> Kafka
    Kafka --> Argo --> WS
    SPA -- "WS" --> WS

    subgraph GPU["OpenShift GPU Pool V100"]
        Renderer[Avatar Renderer Pod]
    end
    Argo --> Renderer

    subgraph Storage
        COS[Cloud Object Storage]
    end
    Renderer --> COS

    subgraph Delivery
        CISVid[CIS CDN<br/>/assets-public/]
        SharePlayer[Embed Player]
    end
    COS --> CISVid
    CISVid --> SPA
    CISVid --> SharePlayer

    subgraph Observability
        Logs[IBM Log Analysis]
        Instana[Instana APM]
    end
    AvatarSvc --> Logs
    VoiceSvc --> Logs
    Renderer --> Logs
    IstioEnvoy --> Instana

    classDef serverless fill:#fdf6e3,stroke:#268bd2
    class AvatarSvc,MetricsSvc serverless
    classDef watson fill:#e8f6ff,stroke:#2aa198
    class VoiceSvc,PromptSvc,OrchestrateSvc watson
    classDef gpu fill:#ffe8e8,stroke:#d33682
    class Renderer gpu
```

---

## Quick start (local dev in ten minutes)

```bash
# 1 – clone
$ git clone https://github.com/videogenie/watsonx-videogenie.git
$ cd watsonx-videogenie

# 2 – spin a Python venv and install tools
$ make setup

# 3 – copy credentials
$ cp .env.example .env   # then edit with App ID keys, watsonx key, COS bucket

# 4 – launch the server stack with Kind (only for local smoke)
$ make kind-up  # installs Istio, Knative, Argo, KEDA on a Kind cluster with CPU‑only renderer

# 5 – run the SPA
$ cd frontend && npm ci && npm start
```

For a real cloud deployment follow the full step‑by‑step below.

---

## 1 · Prerequisites

* IBM Cloud account with **resource group** `videogenie` and **VPC** enabled
* OpenShift 4.15 cluster with at least one V100 or L40S worker pool (`role=gpu=true`)
* `ibmcloud` CLI with the following plugins: `container‑registry`, `kubernetes‑service`, `cis`, `resource‑group`, `app‑id`, `fn`, `secrets‑manager`
* `oc`, `helm`, `terraform` and `make` locally

---

## 2 · Provision IBM Cloud foundation (Terraform)

```bash
cd infra/terraform
terraform init
terraform apply -auto-approve \
  -var domain="videogenie.cloud" \
  -var region="eu-de"
```

Terraform creates CIS with TLS, COS buckets, Event Streams, App ID, Log Analysis and Secrets Manager then prints all outputs you need for the next steps.

---

## 3 · Build and push images to IBM Container Registry

```bash
ibmcloud cr region-set eu-de && ibmcloud cr login
export TAG=$(git rev-parse --short HEAD)
make build-all tag=$TAG && make push-all tag=$TAG
```

---

## 4 · Deploy to OpenShift

1. Download cluster creds:

```bash
ibmcloud ks cluster config --cluster vg-cluster
```

2. Label GPU nodes and add taints:

```bash
oc label node -l kubernetes.io/hostname=<gpu-node> role=gpu=true
oc adm taint nodes -l role=gpu=true dedicated=gpu:NoSchedule
```

3. Install Infra add‑ons:

```bash
make install-istio install-argo install-keda
```

4. Install application charts:

```bash
helm upgrade --install videogenie charts/videogenie \
  --namespace videogenie --create-namespace \
  --set global.image.tag=$TAG \
  --set spa.bucket=$(terraform -chdir=../infra/terraform output -raw spa_bucket)
```

KEDA’s ScaledObject automatically grows `renderer` replicas when the `videoJob` Kafka topic lag increases.

---

## 5 · CI/CD pipeline

`/.github/workflows/ci.yml` builds, tests and pushes images, then triggers **Tekton** to roll the cluster via Argo CD.  On every successful deploy the workflow purges edge cache through CIS API so the new SPA is live globally within seconds.

---

## 6 · Smoke test

Navigate to `https://app.videogenie.cloud`, sign in, paste any script and click *Generate*.  Watch browser dev tools—WebSocket frames stream status and the final frame contains a signed COS URL.  Open it to view the freshly rendered MP4.

---

## 7 · Project tree (top level)

```text
videogenie-ibmcloud
├── frontend          – React SPA
├── services          – Knative & Code Engine sources
├── renderer          – GPU worker image and code
├── charts            – Helm chart for entire app
├── infra             – Terraform for edge/auth/infra
├── pipelines         – Argo & Tekton pipelines
├── manifests         – KEDA, Istio, WebSocket YAML
├── .github           – CI/CD workflows
└── README.md         – this file
```

---

## 8 · Cleaning up

```bash
helm uninstall videogenie -n videogenie
make kind-down    # if you used Kind
terraform -chdir=infra/terraform destroy
ibmcloud cis instance-delete <zone-id> -f
```

---

## License

Apache 2.0.  Use it, fork it, break it, fix it.  If you build something cool with it let the community know!
