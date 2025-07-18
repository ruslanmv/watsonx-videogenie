# VideoGenie on IBM Cloud

This repository contains everything you need to stand up a fully‑featured text‑to‑avatar video generation platform built on IBM Cloud technology.  It ships a React single‑page application, a set of containerised back‑end services, IaC definitions for edge, auth, storage and messaging, and all Kubernetes/Knative manifests that land the stack on Red Hat OpenShift with GPU acceleration.

## Prerequisites

Install the CLIs and plugins first.

```bash
brew install ibmcloud/tap/ibm-cloud-cli
ibmcloud plugin install container-registry kubernetes-service cis cloud-object-storage app-id resource-group fn
brew install openshift-cli
brew install helm
brew install yq jq git
```

Log in and create or select a resource group.

```bash
ibmcloud login --sso
ibmcloud target -r eu-de -g videogenie
```

Clone the repo and enter the directory.

```bash
git clone https://github.com/ruslanmv/videogenie-ibmcloud.git
cd videogenie-ibmcloud
```

## Bootstrapping the foundation layer with Terraform

Change into the infra folder and apply.

```bash
cd infra/terraform
terraform init
terraform apply -auto-approve \
  -var domain=videogenie.cloud \
  -var region=eu-de
```

The configuration provisions a CIS zone and wildcard certificate, a Cloud Object Storage instance, a static bucket for the SPA, an App ID instance, an Event Streams lite plan, a Log Analysis instance and a Secrets Manager.  Terraform outputs the COS bucket CRN, App ID credentials and the CIS edge CNAME for later.

## Building and pushing container images

Authenticate to IBM Cloud Container Registry once.

```bash
ibmcloud cr region-set eu-de
ibmcloud cr login
```

Build the back‑end images and push them with the commit SHA tag.

```bash
export TAG=$(git rev-parse --short HEAD)
make build-all tag=$TAG
make push-all tag=$TAG
```

## Preparing the front‑end

Install dependencies and create an optimised production bundle.

```bash
cd frontend
npm ci
REACT_APP_APPID_CLIENTID=<client-id-from-tf> \
REACT_APP_APPID_DISCOVERY=<discovery-url-from-tf> \
REACT_APP_APIGW=https://api.prd.videogenie.cloud \
npm run build
```

Sync the `build` directory to the static bucket.

```bash
COS_BUCKET=$(terraform -chdir=../infra/terraform output -raw spa_bucket)
ibmcloud cos upload --bucket $COS_BUCKET --key "" --file build --recursive
```

Purge the edge cache for the root path so the new bundle is served immediately.

```bash
CIS_ID=$(terraform -chdir=../infra/terraform output -raw cis_zone_id)
curl -X POST https://api.cis.cloud.ibm.com/v1/${CIS_ID}/purge-cache -H "Authorization: $(ibmcloud iam oauth-tokens | grep IAM | awk '{print $4}')" -d '{"purge_everything":true}'
```

## Bootstrapping the OpenShift layer

Log in to the cluster and add the GPU pool.

```bash
ibmcloud ks cluster config --cluster vg-cluster
oc login -u apikey -p $(ibmcloud iam api-key)
oc label node -l ":worker" role=gpu=true
oc adm taint nodes -l role=gpu=true dedicated=gpu:NoSchedule
```

Install Istio, Argo CD, KEDA and Argo Workflows.

```bash
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm upgrade --install istio-base istio/base -n istio-system --create-namespace
helm upgrade --install istiod istio/istiod -n istio-system --set profile=default
helm repo add argo https://argoproj.github.io/argo-helm
helm upgrade --install argo-workflows argo/argo-workflows -n argo --create-namespace
helm upgrade --install keda kedacore/keda -n keda --create-namespace
```

## Deploying application charts

Argo CD pulls the `charts/` directory and syncs automatically.  If you need a manual push you can do:

```bash
helm dependency update charts/videogenie
helm upgrade --install videogenie charts/videogenie -n videogenie \
  --set image.tag=$TAG \
  --set spa.bucket=$COS_BUCKET
```

## Local smoke test

Open the React SPA URL printed by Terraform.  Sign in with App ID, paste `Hello world` as the script, click **Generate** and tail workflow logs.

```bash
oc logs -n argo -l workflows.argoproj.io/workflow-name -f
```

When the render pod finishes check the COS bucket for a new MP4, and load the file through the signed URL in your browser to verify playback.

## Directory structure

```text
watsonx-videogenie/
├── .github/
│   └── workflows/ci.yml
├── frontend/
│   ├── src/
│   ├── public/
│   └── build/
├── services/
│   ├── avatar-service/
│   │   ├── Dockerfile
│   │   └── knative.yaml
│   ├── prompt-service/
│   │   ├── Dockerfile
│   │   └── knative.yaml
│   ├── orchestrate-service/
│   │   ├── Dockerfile
│   │   └── codeengine.yaml
│   └── metrics-action/
│       └── index.ts
├── renderer/
│   ├── Dockerfile
│   └── render.py
├── charts/
│   └── videogenie/
│       ├── Chart.yaml
│       ├── templates/
│       └── values.yaml
├── pipelines/
│   ├── argo/
│   └── tekton/
├── manifests/
│   ├── keda-scaledobject.yaml
│   └── websocket.yaml
├── infra/
│   └── terraform/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── README.md
```

## Cleaning up

Destroy all resources in reverse order: helm uninstall videogenie, delete the GPU node pool, run `terraform destroy` in the infra folder and finally delete the CIS zone if you no longer need the domain.

## License

Apache 2.0.
