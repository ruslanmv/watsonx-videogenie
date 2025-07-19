# Makefile ──────────────────────────────────────────────────────────────
# Top‑level developer workflow for WatsonX‑VideoGenie
#
# Usage:
#   make <target>
# Run `make help` to see all available targets.
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------#
# Globals                                                               #
# ----------------------------------------------------------------------#
SERVICES        := avatar-service prompt-service orchestrate-service   # renderer is top‑level
CONTAINER_REG   ?= icr.io/videogenie
TAG             ?= $(shell git rev-parse --short HEAD)
PY              ?= python3.11
VENV_DIR        ?= .venv

# Colours for pretty output
GREEN  := \033[0;32m
RESET  := \033[0m

define PRINT_TARGET
	@printf "$(GREEN)%-24s$(RESET) %s\n" "$(1)" "$(2)"
endef

# ----------------------------------------------------------------------#
# Help                                                                  #
# ----------------------------------------------------------------------#
.PHONY: help
help:          ## Show this help
	@echo "WatsonX‑VideoGenie developer Makefile"
	@echo
	$(call PRINT_TARGET,setup,Create Python venv + install core tooling)
	$(call PRINT_TARGET,fetch-wav2lip,Clone/download Wav2Lip repo & checkpoint)
	$(call PRINT_TARGET,prepare-models,Create /models directory for avatar PNGs)
	$(call PRINT_TARGET,container-build,Build all Docker images with TAG=$(TAG))
	$(call PRINT_TARGET,container-push,Push all images to $(CONTAINER_REG))
	$(call PRINT_TARGET,install-istio,Install Istio via Helm)
	$(call PRINT_TARGET,install-argo,Install Argo Workflows & Events)
	$(call PRINT_TARGET,install-keda,Install KEDA autoscaler)
	$(call PRINT_TARGET,kind-up,Spin local Kind cluster for smoke test)
	$(call PRINT_TARGET,kind-down,Delete Kind cluster)
	@echo

# ----------------------------------------------------------------------#
# Local tooling                                                         #
# ----------------------------------------------------------------------#
.PHONY: setup
setup: $(VENV_DIR)/bin/activate ## Create virtual‑env and install python deps
$(VENV_DIR)/bin/activate:
	@echo "🔧 Creating venv at $(VENV_DIR)"
	$(PY) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip wheel pre-commit
	@echo "✅ venv ready. Activate with: source $(VENV_DIR)/bin/activate"

# ----------------------------------------------------------------------#
# Wav2Lip & Models Prep                                                 #
# ----------------------------------------------------------------------#
.PHONY: fetch-wav2lip
fetch-wav2lip: ## Clone Wav2Lip repo + download checkpoint
	@echo "🔄 Cloning/updating Wav2Lip..."
	@mkdir -p services/avatar-service/app/Wav2Lip
	@if [ -d services/avatar-service/app/Wav2Lip/.git ]; then \
	  cd services/avatar-service/app/Wav2Lip && git pull; \
	else \
	  git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git services/avatar-service/app/Wav2Lip; \
	fi
	@mkdir -p services/avatar-service/app/Wav2Lip/checkpoints
	@echo "📥 Downloading checkpoint (only first run may take a while)..."
	@wget -q -nc \
	  https://github.com/Rudrabha/Wav2Lip/releases/download/v0.1/wav2lip_gan.pth \
	  -O services/avatar-service/app/Wav2Lip/checkpoints/wav2lip_gan.pth
	@echo "✅ Wav2Lip ready."

.PHONY: prepare-models
prepare-models: ## Create /models directory for avatar PNGs
	@echo "🔧 Preparing models directory..."
	@mkdir -p models
	@echo "✅ models/ directory ready."

# ----------------------------------------------------------------------#
# Docker images                                                         #
# ----------------------------------------------------------------------#
.PHONY: container-build
container-build: ## Build all Docker images
	@for svc in $(SERVICES); do \
		echo "🔨 Building $$svc"; \
		docker build -t $(CONTAINER_REG)/$$svc:$(TAG) services/$$svc ; \
	done
	# build renderer image (top‑level)
	echo "🔨 Building renderer"; \
	docker build -t $(CONTAINER_REG)/renderer:$(TAG) renderer
	@echo "✅ Images built with tag $(TAG)"

.PHONY: container-push
container-push: ## Push all images to registry
	@for svc in $(SERVICES); do \
		echo "📤 Pushing $$svc"; \
		docker push $(CONTAINER_REG)/$$svc:$(TAG) ; \
	done
	# push renderer
	echo "📤 Pushing renderer"; \
	docker push $(CONTAINER_REG)/renderer:$(TAG)
	@echo "✅ All images pushed"

# ----------------------------------------------------------------------#
# Cluster add‑ons                                                       #
# ----------------------------------------------------------------------#
.PHONY: install-istio
install-istio: ## Install Istio via Helm
	@echo "🚀 Installing Istio"
	helm repo add istio https://istio-release.storage.googleapis.com/charts
	helm upgrade --install istio-base istio/base   -n istio-system --create-namespace
	helm upgrade --install istiod     istio/istiod -n istio-system
	helm upgrade --install istio-gw   istio/gateway -n istio-system
	@echo "✅ Istio installed"

.PHONY: install-argo
install-argo: ## Install Argo Workflows & Events via Helm
	@echo "🚀 Installing Argo"
	helm repo add argo https://argoproj.github.io/argo-helm
	helm upgrade --install argo         argo/argo-workflows -n argo --create-namespace
	helm upgrade --install argo-events  argo/argo-events     -n argo-events --create-namespace
	@echo "✅ Argo installed"

.PHONY: install-keda
install-keda: ## Install KEDA autoscaler via Helm
	@echo "🚀 Installing KEDA"
	helm repo add kedacore https://kedacore.github.io/charts
	helm upgrade --install keda kedacore/keda -n keda --create-namespace
	@echo "✅ KEDA installed"

# ----------------------------------------------------------------------#
# Kind mini‑cluster (CPU‑only smoke)                                    #
# ----------------------------------------------------------------------#
.PHONY: kind-up
kind-up: ## Spin Kind cluster (includes Istio, Knative etc.)
	@echo "🚀 Creating Kind cluster"
	kind create cluster --name videogenie --image kindest/node:v1.30.0
	kubectl wait --for=condition=Ready node --all --timeout=120s
	@echo "✅ Kind cluster ready"

.PHONY: kind-down
kind-down: ## Delete Kind cluster
	kind delete cluster --name videogenie

# ----------------------------------------------------------------------#
# Default                                                               #
# ----------------------------------------------------------------------#
.DEFAULT_GOAL := help
