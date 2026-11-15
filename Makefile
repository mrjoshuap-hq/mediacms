.PHONY: \
	help \
	admin-shell \
	build build-frontend build-docs build-languages build-docker \
	docker docker-build docker-build-full docker-up docker-down \
	frontend frontend-build frontend-lint frontend-test frontend-test-coverage \
	lint lint-frontend \
	test test-backend test-coverage test-frontend test-frontend-coverage \
	docs docs-up docs-down docs-build docs-logs \
	languages languages-build

.DEFAULT_GOAL := help

# Local image tags (Compose defaults). Override for GHCR, e.g.:
#   MEDIACMS_IMAGE=ghcr.io/mrjoshuap/mediacms:beta make docker-up
MEDIACMS_IMAGE ?= mediacms:local
MEDIACMS_FULL_IMAGE ?= mediacms:full
MEDIACMS_DEV_IMAGE ?= mediacms-dev:latest

COMPOSE := docker compose -f docker-compose.yaml
COMPOSE_FULL := docker compose -f docker-compose.yaml -f docker-compose.full.yaml
COMPOSE_DEV := docker compose -f docker-compose-dev.yaml

export MEDIACMS_IMAGE MEDIACMS_FULL_IMAGE MEDIACMS_DEV_IMAGE

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Pattern: <thing> runs common <thing>-* actions; <thing>-<action> does one action."
	@echo "Older names (build-frontend, lint-frontend, …) remain as aliases."
	@echo ""
	@echo "Aggregates"
	@echo "  build                 frontend + docs + languages"
	@echo "  docker                docker-build"
	@echo "  frontend              build + lint + test"
	@echo "  lint                  pre-commit run --all-files"
	@echo "  test                  lint + backend + frontend"
	@echo "  docs                  docs-build"
	@echo "  languages             languages-build"
	@echo ""
	@echo "Docker"
	@echo "  docker-build          build local images ($(MEDIACMS_DEV_IMAGE), $(MEDIACMS_IMAGE))"
	@echo "  docker-build-full     also build $(MEDIACMS_FULL_IMAGE) (Whisper)"
	@echo "  docker-up             start dev stack"
	@echo "  docker-down           stop dev stack"
	@echo "  Image overrides: MEDIACMS_IMAGE, MEDIACMS_FULL_IMAGE, MEDIACMS_DEV_IMAGE"
	@echo ""
	@echo "Frontend"
	@echo "  frontend-build        bundles → static/ + restart web  (alias: build-frontend)"
	@echo "  frontend-lint         ESLint hooks only                (alias: lint-frontend)"
	@echo "  frontend-test         Jest (CI)                        (alias: test-frontend)"
	@echo "  frontend-test-coverage"
	@echo ""
	@echo "Test / lint"
	@echo "  test-backend          pytest -n auto"
	@echo "  test-coverage         pytest with coverage"
	@echo "  test-frontend-coverage"
	@echo ""
	@echo "Docs / languages"
	@echo "  docs-up / docs-down / docs-logs / docs-build"
	@echo "  languages-build       process_translations  (alias: build-languages)"
	@echo ""
	@echo "Other"
	@echo "  admin-shell           bash in the web container"

admin-shell:
	@container_id=$$($(COMPOSE_DEV) ps -q web); \
	if [ -z "$$container_id" ]; then \
		echo "Web container not found. Is docker-compose-dev.yaml up?"; \
		exit 1; \
	else \
		docker exec -it $$container_id /bin/bash; \
	fi

# --- build ---
build: build-frontend build-docs build-languages

build-frontend: frontend-build
build-docs: docs-build
build-languages: languages-build
build-docker: docker-build

# --- docker ---
docker: docker-build

docker-build:
	$(COMPOSE_DEV) build
	$(COMPOSE) build

docker-build-full: docker-build
	$(COMPOSE_FULL) build celery_worker

docker-up:
	$(COMPOSE_DEV) up

docker-down:
	$(COMPOSE_DEV) down

# --- frontend ---
frontend: frontend-build frontend-lint frontend-test

frontend-build:
	$(COMPOSE_DEV) exec frontend npm run dist
	cp -r frontend/dist/static/* static/
	$(COMPOSE_DEV) restart web

frontend-lint:
	pre-commit run eslint-frontend --all-files
	pre-commit run eslint-video-js --all-files
	pre-commit run eslint-video-editor --all-files
	pre-commit run eslint-chapters-editor --all-files

frontend-test:
	$(COMPOSE_DEV) exec -T frontend npm run test -- --ci

frontend-test-coverage:
	$(COMPOSE_DEV) exec -T frontend npm run test-coverage -- --ci --coverageReporters=text-summary --coverageReporters=html

# --- lint ---
lint:
	pre-commit run --all-files

lint-frontend: frontend-lint

# --- test ---
test: lint test-backend test-frontend

test-backend:
	$(COMPOSE_DEV) exec --env TESTING=True -T web pytest -n auto

test-coverage:
	$(COMPOSE_DEV) exec --env TESTING=True -T web pytest -n auto --cov --cov-report=term --cov-report=html

test-frontend: frontend-test

test-frontend-coverage: frontend-test-coverage

# --- docs (MkDocs → site/, served at http://localhost/documentation/) ---
docs: docs-build

docs-up:
	$(COMPOSE_DEV) --profile docs up -d docs
	@echo "Documentation watcher started. Open http://localhost/documentation/"

docs-down:
	$(COMPOSE_DEV) --profile docs stop docs

docs-build:
	$(COMPOSE_DEV) --profile docs run --rm --no-deps docs bash -lc 'pip install -q -r requirements-docs.txt && python scripts/docs_dev_watch.py --once'
	@echo "Built site/. Open http://localhost/documentation/ (web container must be running)."

docs-logs:
	$(COMPOSE_DEV) --profile docs logs -f docs

# --- languages (frontend_translations) ---
languages: languages-build

languages-build:
	$(COMPOSE_DEV) exec -T web python manage.py process_translations
