# Makefile ──────────────────────────────────────────────────────────────
# Production-ready developer workflow for WatsonX VideoGenie
# Author: Ruslan Magana (https://ruslanmv.com)
# License: Apache 2.0
#
# Usage:
#   make <target>
# Run `make help` to see all available targets.
# ----------------------------------------------------------------------

.SILENT:
.DEFAULT_GOAL := help

# ----------------------------------------------------------------------#
# Globals                                                               #
# ----------------------------------------------------------------------#
SERVICES        := avatar-service prompt-service orchestrate-service
CONTAINER_REG   ?= icr.io/videogenie
TAG             ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")
PY              ?= python3.11
VENV_DIR        ?= .venv
UV              ?= uvx --from uv

# Paths
PROJECT_ROOT    := $(shell pwd)
TESTS_DIR       := tests
COVERAGE_DIR    := htmlcov

# Colours for pretty output
GREEN           := \033[0;32m
YELLOW          := \033[0;33m
RED             := \033[0;31m
BLUE            := \033[0;34m
RESET           := \033[0m
BOLD            := \033[1m

define PRINT_TARGET
	@printf "  $(GREEN)%-24s$(RESET) %s\n" "$(1)" "$(2)"
endef

define PRINT_SECTION
	@printf "\n$(BOLD)$(BLUE)$(1)$(RESET)\n"
endef

# ----------------------------------------------------------------------#
# Help & Self-Documentation                                             #
# ----------------------------------------------------------------------#
.PHONY: help
help:          ## Show this comprehensive help menu
	@echo "$(BOLD)$(BLUE)════════════════════════════════════════════════════════════════$(RESET)"
	@echo "$(BOLD)  WatsonX VideoGenie - Production Developer Makefile$(RESET)"
	@echo "$(BOLD)  Author: Ruslan Magana (https://ruslanmv.com)$(RESET)"
	@echo "$(BOLD)════════════════════════════════════════════════════════════════$(RESET)"
	$(call PRINT_SECTION,📦 Package Management & Setup)
	$(call PRINT_TARGET,install,Install all dependencies using UV)
	$(call PRINT_TARGET,install-dev,Install with dev dependencies)
	$(call PRINT_TARGET,setup,Create Python venv (legacy method))
	$(call PRINT_TARGET,update,Update all dependencies to latest versions)
	$(call PRINT_TARGET,sync,Sync dependencies from lock file)
	$(call PRINT_SECTION,🔍 Code Quality & Linting)
	$(call PRINT_TARGET,lint,Run all linters (ruff + flake8))
	$(call PRINT_TARGET,format,Format code with black and isort)
	$(call PRINT_TARGET,format-check,Check code formatting without changes)
	$(call PRINT_TARGET,type-check,Run mypy type checking)
	$(call PRINT_TARGET,check,Run all quality checks (lint + format + type))
	$(call PRINT_SECTION,🧪 Testing)
	$(call PRINT_TARGET,test,Run all tests with pytest)
	$(call PRINT_TARGET,test-unit,Run unit tests only)
	$(call PRINT_TARGET,test-integration,Run integration tests only)
	$(call PRINT_TARGET,test-cov,Run tests with coverage report)
	$(call PRINT_TARGET,test-watch,Run tests in watch mode)
	$(call PRINT_SECTION,🧹 Cleanup)
	$(call PRINT_TARGET,clean,Remove build artifacts and caches)
	$(call PRINT_TARGET,clean-all,Deep clean including venv and models)
	$(call PRINT_TARGET,clean-pyc,Remove Python cache files)
	$(call PRINT_TARGET,clean-test,Remove test and coverage artifacts)
	$(call PRINT_SECTION,🤖 AI/ML Models & Dependencies)
	$(call PRINT_TARGET,fetch-wav2lip,Clone/download Wav2Lip repo & checkpoint)
	$(call PRINT_TARGET,prepare-models,Create /models directory for avatar PNGs)
	$(call PRINT_SECTION,🐳 Container Operations)
	$(call PRINT_TARGET,container-build,Build all Docker images [TAG=$(TAG)])
	$(call PRINT_TARGET,container-push,Push all images to $(CONTAINER_REG))
	$(call PRINT_TARGET,container-clean,Remove local Docker images)
	$(call PRINT_SECTION,☸️  Kubernetes & Infrastructure)
	$(call PRINT_TARGET,install-istio,Install Istio service mesh via Helm)
	$(call PRINT_TARGET,install-argo,Install Argo Workflows & Events)
	$(call PRINT_TARGET,install-keda,Install KEDA autoscaler)
	$(call PRINT_TARGET,kind-up,Create local Kind cluster for testing)
	$(call PRINT_TARGET,kind-down,Delete Kind cluster)
	$(call PRINT_SECTION,📊 CI/CD & Development)
	$(call PRINT_TARGET,pre-commit,Install pre-commit hooks)
	$(call PRINT_TARGET,ci,Run full CI pipeline locally)
	@echo "$(BOLD)$(BLUE)════════════════════════════════════════════════════════════════$(RESET)"
	@echo ""

# ----------------------------------------------------------------------#
# Package Management (UV-based)                                         #
# ----------------------------------------------------------------------#
.PHONY: install
install:       ## Install all dependencies using UV
	@echo "$(BLUE)📦 Installing dependencies with UV...$(RESET)"
	@command -v uv >/dev/null 2>&1 || { echo "$(RED)❌ UV not found. Install from: https://github.com/astral-sh/uv$(RESET)"; exit 1; }
	uv pip install -e .
	@echo "$(GREEN)✅ Dependencies installed successfully$(RESET)"

.PHONY: install-dev
install-dev:   ## Install with development dependencies
	@echo "$(BLUE)📦 Installing dev dependencies with UV...$(RESET)"
	@command -v uv >/dev/null 2>&1 || { echo "$(RED)❌ UV not found. Install from: https://github.com/astral-sh/uv$(RESET)"; exit 1; }
	uv pip install -e ".[dev,test,docs]"
	@echo "$(GREEN)✅ Dev dependencies installed successfully$(RESET)"

.PHONY: update
update:        ## Update all dependencies to latest compatible versions
	@echo "$(BLUE)🔄 Updating dependencies...$(RESET)"
	uv pip install --upgrade -e ".[all]"
	@echo "$(GREEN)✅ Dependencies updated$(RESET)"

.PHONY: sync
sync:          ## Sync dependencies from lock file (deterministic install)
	@echo "$(BLUE)🔄 Syncing dependencies...$(RESET)"
	uv pip install -e . --no-deps
	uv pip sync
	@echo "$(GREEN)✅ Dependencies synced$(RESET)"

.PHONY: setup
setup: $(VENV_DIR)/bin/activate ## Create virtual env (legacy method - prefer 'make install')
$(VENV_DIR)/bin/activate:
	@echo "$(YELLOW)🔧 Creating venv at $(VENV_DIR) (consider using 'uv venv' instead)$(RESET)"
	$(PY) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip wheel
	@echo "$(GREEN)✅ venv ready. Activate with: source $(VENV_DIR)/bin/activate$(RESET)"

# ----------------------------------------------------------------------#
# Code Quality & Linting                                                #
# ----------------------------------------------------------------------#
.PHONY: lint
lint:          ## Run all linters (ruff + flake8)
	@echo "$(BLUE)🔍 Running linters...$(RESET)"
	@command -v ruff >/dev/null 2>&1 || uv pip install ruff
	ruff check services/ renderer/ tests/ --fix
	flake8 services/ renderer/ tests/ --max-line-length=88 --extend-ignore=E203,W503
	@echo "$(GREEN)✅ Linting complete$(RESET)"

.PHONY: format
format:        ## Format code with black and isort
	@echo "$(BLUE)✨ Formatting code...$(RESET)"
	black services/ renderer/ tests/
	isort services/ renderer/ tests/
	@echo "$(GREEN)✅ Code formatted$(RESET)"

.PHONY: format-check
format-check:  ## Check code formatting without making changes
	@echo "$(BLUE)🔍 Checking code format...$(RESET)"
	black --check services/ renderer/ tests/
	isort --check-only services/ renderer/ tests/
	@echo "$(GREEN)✅ Format check passed$(RESET)"

.PHONY: type-check
type-check:    ## Run mypy type checking
	@echo "$(BLUE)🔍 Running type checks...$(RESET)"
	mypy services/ renderer/ --config-file=pyproject.toml
	@echo "$(GREEN)✅ Type checking complete$(RESET)"

.PHONY: check
check: format-check lint type-check ## Run all quality checks
	@echo "$(GREEN)✅ All quality checks passed!$(RESET)"

# ----------------------------------------------------------------------#
# Testing                                                               #
# ----------------------------------------------------------------------#
.PHONY: test
test:          ## Run all tests with pytest
	@echo "$(BLUE)🧪 Running tests...$(RESET)"
	pytest $(TESTS_DIR) -v
	@echo "$(GREEN)✅ Tests complete$(RESET)"

.PHONY: test-unit
test-unit:     ## Run unit tests only
	@echo "$(BLUE)🧪 Running unit tests...$(RESET)"
	pytest $(TESTS_DIR) -v -m unit
	@echo "$(GREEN)✅ Unit tests complete$(RESET)"

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo "$(BLUE)🧪 Running integration tests...$(RESET)"
	pytest $(TESTS_DIR) -v -m integration
	@echo "$(GREEN)✅ Integration tests complete$(RESET)"

.PHONY: test-cov
test-cov:      ## Run tests with coverage report
	@echo "$(BLUE)🧪 Running tests with coverage...$(RESET)"
	pytest $(TESTS_DIR) --cov --cov-report=term --cov-report=html
	@echo "$(GREEN)✅ Coverage report generated in $(COVERAGE_DIR)/$(RESET)"

.PHONY: test-watch
test-watch:    ## Run tests in watch mode
	@echo "$(BLUE)🧪 Running tests in watch mode...$(RESET)"
	pytest-watch $(TESTS_DIR) -v

# ----------------------------------------------------------------------#
# Cleanup                                                               #
# ----------------------------------------------------------------------#
.PHONY: clean
clean: clean-pyc clean-test ## Remove build artifacts and caches
	@echo "$(BLUE)🧹 Cleaning build artifacts...$(RESET)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

.PHONY: clean-all
clean-all: clean ## Deep clean including venv and models
	@echo "$(BLUE)🧹 Deep cleaning project...$(RESET)"
	rm -rf $(VENV_DIR)
	rm -rf services/avatar-service/app/Wav2Lip
	rm -rf models/
	rm -rf node_modules/
	@echo "$(GREEN)✅ Deep clean complete$(RESET)"

.PHONY: clean-pyc
clean-pyc:     ## Remove Python cache files
	@echo "$(BLUE)🧹 Removing Python cache files...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✅ Python cache cleaned$(RESET)"

.PHONY: clean-test
clean-test:    ## Remove test and coverage artifacts
	@echo "$(BLUE)🧹 Cleaning test artifacts...$(RESET)"
	rm -rf .pytest_cache/
	rm -rf $(COVERAGE_DIR)/
	rm -f .coverage
	rm -f coverage.xml
	@echo "$(GREEN)✅ Test artifacts cleaned$(RESET)"

# ----------------------------------------------------------------------#
# AI/ML Models & Dependencies                                           #
# ----------------------------------------------------------------------#
.PHONY: fetch-wav2lip
fetch-wav2lip: ## Clone Wav2Lip repo + download checkpoint
	@echo "$(BLUE)🔄 Cloning/updating Wav2Lip...$(RESET)"
	@mkdir -p services/avatar-service/app/Wav2Lip
	@if [ -d services/avatar-service/app/Wav2Lip/.git ]; then \
	  cd services/avatar-service/app/Wav2Lip && git pull; \
	else \
	  git clone --depth 1 https://github.com/Rudrabha/Wav2Lip.git services/avatar-service/app/Wav2Lip; \
	fi
	@mkdir -p services/avatar-service/app/Wav2Lip/checkpoints
	@echo "$(BLUE)📥 Downloading checkpoint (may take a while on first run)...$(RESET)"
	@wget -q -nc \
	  https://github.com/Rudrabha/Wav2Lip/releases/download/v0.1/wav2lip_gan.pth \
	  -O services/avatar-service/app/Wav2Lip/checkpoints/wav2lip_gan.pth || true
	@echo "$(GREEN)✅ Wav2Lip ready$(RESET)"

.PHONY: prepare-models
prepare-models: ## Create /models directory for avatar PNGs
	@echo "$(BLUE)🔧 Preparing models directory...$(RESET)"
	@mkdir -p models
	@echo "$(GREEN)✅ models/ directory ready$(RESET)"

# ----------------------------------------------------------------------#
# Container Operations                                                  #
# ----------------------------------------------------------------------#
.PHONY: container-build
container-build: ## Build all Docker images
	@echo "$(BLUE)🔨 Building Docker images with tag: $(TAG)$(RESET)"
	@for svc in $(SERVICES); do \
		echo "$(BLUE)  Building $$svc...$(RESET)"; \
		docker build -t $(CONTAINER_REG)/$$svc:$(TAG) services/$$svc ; \
	done
	@echo "$(BLUE)  Building renderer...$(RESET)"
	@docker build -t $(CONTAINER_REG)/renderer:$(TAG) renderer
	@echo "$(GREEN)✅ All images built with tag $(TAG)$(RESET)"

.PHONY: container-push
container-push: ## Push all images to registry
	@echo "$(BLUE)📤 Pushing images to $(CONTAINER_REG)...$(RESET)"
	@for svc in $(SERVICES); do \
		echo "$(BLUE)  Pushing $$svc:$(TAG)...$(RESET)"; \
		docker push $(CONTAINER_REG)/$$svc:$(TAG) ; \
	done
	@echo "$(BLUE)  Pushing renderer:$(TAG)...$(RESET)"
	@docker push $(CONTAINER_REG)/renderer:$(TAG)
	@echo "$(GREEN)✅ All images pushed$(RESET)"

.PHONY: container-clean
container-clean: ## Remove local Docker images
	@echo "$(BLUE)🧹 Removing local Docker images...$(RESET)"
	@for svc in $(SERVICES); do \
		docker rmi $(CONTAINER_REG)/$$svc:$(TAG) 2>/dev/null || true; \
	done
	@docker rmi $(CONTAINER_REG)/renderer:$(TAG) 2>/dev/null || true
	@echo "$(GREEN)✅ Docker images removed$(RESET)"

# ----------------------------------------------------------------------#
# Kubernetes & Infrastructure                                           #
# ----------------------------------------------------------------------#
.PHONY: install-istio
install-istio: ## Install Istio service mesh via Helm
	@echo "$(BLUE)🚀 Installing Istio service mesh...$(RESET)"
	helm repo add istio https://istio-release.storage.googleapis.com/charts
	helm repo update
	helm upgrade --install istio-base istio/base   -n istio-system --create-namespace
	helm upgrade --install istiod     istio/istiod -n istio-system
	helm upgrade --install istio-gw   istio/gateway -n istio-system
	@echo "$(GREEN)✅ Istio installed successfully$(RESET)"

.PHONY: install-argo
install-argo: ## Install Argo Workflows & Events via Helm
	@echo "$(BLUE)🚀 Installing Argo Workflows & Events...$(RESET)"
	helm repo add argo https://argoproj.github.io/argo-helm
	helm repo update
	helm upgrade --install argo         argo/argo-workflows -n argo --create-namespace
	helm upgrade --install argo-events  argo/argo-events     -n argo-events --create-namespace
	@echo "$(GREEN)✅ Argo installed successfully$(RESET)"

.PHONY: install-keda
install-keda: ## Install KEDA autoscaler via Helm
	@echo "$(BLUE)🚀 Installing KEDA autoscaler...$(RESET)"
	helm repo add kedacore https://kedacore.github.io/charts
	helm repo update
	helm upgrade --install keda kedacore/keda -n keda --create-namespace
	@echo "$(GREEN)✅ KEDA installed successfully$(RESET)"

# ----------------------------------------------------------------------#
# Local Kubernetes (Kind cluster for testing)                           #
# ----------------------------------------------------------------------#
.PHONY: kind-up
kind-up: ## Create local Kind cluster for testing
	@echo "$(BLUE)🚀 Creating Kind cluster 'videogenie'...$(RESET)"
	kind create cluster --name videogenie --image kindest/node:v1.30.0
	kubectl wait --for=condition=Ready node --all --timeout=120s
	@echo "$(GREEN)✅ Kind cluster ready$(RESET)"

.PHONY: kind-down
kind-down: ## Delete Kind cluster
	@echo "$(BLUE)🗑️  Deleting Kind cluster 'videogenie'...$(RESET)"
	kind delete cluster --name videogenie
	@echo "$(GREEN)✅ Kind cluster deleted$(RESET)"

# ----------------------------------------------------------------------#
# CI/CD & Development Workflow                                          #
# ----------------------------------------------------------------------#
.PHONY: pre-commit
pre-commit:    ## Install pre-commit hooks
	@echo "$(BLUE)🔧 Installing pre-commit hooks...$(RESET)"
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "$(GREEN)✅ Pre-commit hooks installed$(RESET)"

.PHONY: ci
ci: clean install-dev check test-cov ## Run full CI pipeline locally
	@echo "$(GREEN)✅ Full CI pipeline completed successfully!$(RESET)"
