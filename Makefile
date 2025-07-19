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
SERVICES        := avatar-service prompt-service orchestrate-service renderer
CONTAINER_REG   ?= icr.io/videogenie
TAG             ?= $(shell git rev-parse --short HEAD)
PY           	  ?= python3.11
VENV_DIR        ?= .venv

# Colours for pretty output
GREEN  := \033[0;32m
RESET  := \033[0m

define PRINT_TARGET
	@printf "$(GREEN)%-16s$(RESET) %s\n" "$(1)" "$(2)"
endef

# ----------------------------------------------------------------------#
# Help                                                                  #
# ----------------------------------------------------------------------#
.PHONY: help
help:          ## Show this help
	@echo "WatsonX‑VideoGenie developer Makefile"
	@echo
	$(call PRINT_TARGET,setup,Create Python venv + install core tooling)
	$(call PRINT_TARGET,container-build,Build all Docker images with TAG=$(TAG))
	$(call PRINT_TARGET,container-push,Push all images to $(CONTAINER_REG))
	$(call PRINT_TARGET,build-all,Alias of container-build (deprecated)      )
	$(call PRINT_TARGET,push-all ,Alias of container-push  (deprecated)      )
	$(call PRINT_TARGET,install-istio ,Install Istio via Helm               )
	$(call PRINT_TARGET,install-argo  ,Install Argo Workflows & Events       )
	$(call PRINT_TARGET,install-keda  ,Install KEDA autoscaler               )
	$(call PRINT_TARGET,kind-up       ,Spin local Kind cluster for smoke test)
	$(call PRINT_TARGET,kind-down     ,Delete Kind cluster                   )

# ----------------------------------------------------------------------#
# Local tooling                                                         #
# ----------------------------------------------------------------------#
.PHONY: setup
setup: $(VENV_DIR)/bin/activate ## Create virtual‑env and install python deps
$(VENV_DIR)/bin/activate:
	@echo "🔧 Creating venv at $(VENV_DIR)"
	$(PY) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip wheel
	$(VENV_DIR)/bin/pip install pre-commit
	@echo "✅ venv ready. Activate with: source $(VENV_DIR)/bin/activate"

# ----------------------------------------------------------------------#
# Docker images                                                         #
# ----------------------------------------------------------------------#
.PHONY: container-build build-all
container-build build-all: ## Build all service images
	@for svc in $(SERVICES); do \
		echo "🔨 Building $$svc"; \
		docker build -t $(CONTAINER_REG)/$$svc:$(TAG) services/$$svc ; \
	done
	@echo "✅ All images built with tag $(TAG)"

.PHONY: container-push push-all
container-push push-all: ## Push all images to registry
	@for svc in $(SERVICES); do \
		echo "📤 Pushing $$svc"; \
		docker push $(CONTAINER_REG)/$$svc:$(TAG) ; \
	done
	@echo "✅ All images pushed"

# ----------------------------------------------------------------------#
# Cluster add‑ons                                                       #
# ----------------------------------------------------------------------#
.PHONY: install-istio
install-istio: ## Install Istio (simplified demo chart)
	@echo "🚀 Installing Istio via Helm"
	helm repo add istio https://istio-release.storage.googleapis.com/charts
	helm upgrade --install istio-base istio/base -n istio-system --create-namespace
	helm upgrade --install istiod istio/istiod -n istio-system
	helm upgrade --install istio-ingress istio/gateway -n istio-system
	@echo "✅ Istio installed"

.PHONY: install-argo
install-argo: ## Install Argo Workflows & Events
	@echo "🚀 Installing Argo Workflows"
	helm repo add argo https://argoproj.github.io/argo-helm
	helm upgrade --install argo argo/argo-workflows -n argo --create-namespace
	helm upgrade --install argo-events argo/argo-events -n argo-events --create-namespace
	@echo "✅ Argo installed"

.PHONY: install-keda
install-keda: ## Install KEDA autoscaler
	@echo "🚀 Installing KEDA"
	helm repo add kedacore https://kedacore.github.io/charts
	helm upgrade --install keda kedacore/keda -n keda --create-namespace
	@echo "✅ KEDA installed"

# ----------------------------------------------------------------------#
# Kind mini‑cluster (CPU‑only smoke)                                    #
# ----------------------------------------------------------------------#
.PHONY: kind-up
kind-up: ## Spin Kind cluster with Istio + Knative for local smoke tests
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
