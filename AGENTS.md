# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Overview

MediaCMS is an open source video and media CMS built with **Django + React**, exposing a REST API. It supports video/audio/image/PDF media, automatic transcoding (multiple resolutions/profiles, HLS), Whisper-based auto-transcription, RBAC, SAML/LTI integrations, and more. See `README.md` for the full feature list.

**Stack:** Python 3.11+ / Django 5.2 / DRF / Celery / Redis / PostgreSQL · React 19 / Webpack / Node >= 20.9.0 · Docker (supervisord in production images).

## Change Impact Policy

Prefer the **least invasive** change that solves the problem:

1. Templates, CSS, admin config, docs, and tests
2. Settings overrides in `cms/local_settings.py` or `deploy/docker/local_settings.py` (never edit `cms/settings.py` for a deployment)
3. Application logic without schema changes
4. Model / database migrations — only when explicitly required

Do not introduce schema or migration changes unless the task cannot be done otherwise.

## Repository Layout

| Path | Purpose |
| ----------------------------------- | ---------------------------------------------------------------- |
| `cms/` | Django project settings, urls, celery |
| `files/` | Main app: media models, API, Celery tasks, frontend translations |
| `frontend/` | React app (`src/entries/` → `static/js/`) |
| `admin_customizations/` | Jazzmin admin portal (dashboard, sidebar, health) |
| `templates/`, `static/` | Django templates and collected static assets |
| `tests/`, `frontend/tests/` | Pytest and Jest |
| `docs/en/` | MkDocs documentation (source of truth for deep context) |
| `deploy/docker/` | Docker entrypoints and `local_settings.py` |
| `skills/` | Agent skills (lazy-loaded workflows); see Skill Index below |

## Development Environment

Docker-first from the repo root:

```bash
make docker-build
make docker-up
```

- App: **http://localhost:80** (built bundles). Webpack HMR: **http://localhost:8088** (proxies to Django).
- Default credentials: `admin` / `admin`.
- Frontend changes on port 80 require `make frontend-build` (or `make build-frontend`).
- Docs preview: `make docs-up` → **http://localhost/documentation/** (not `/docs/`).
- Run `make help` for the full Makefile target list.

## Hard Rules

- **Tests:** Always set `TESTING=True` when running pytest (Celery otherwise hits a missing broker).
- **Lint:** `pre-commit run --all-files` is the lint source of truth (black, isort, flake8, Prettier, ESLint). Install frontend package deps before hooks if you touch those packages.
- **Commits:** Conventional Commits (`feat`, `fix`, `chore`, `docs`, `style`, `refactor`, `perf`, `test`, `depr`). Do not bump `package.json` version or hand-edit `CHANGELOG.md`.
- **Translations:** New UI strings go in `files/frontend_translations/en.py` first, then `make languages` / `process_translations`. Admin portal strings use Django gettext. See skill `i18n`.
- **Never commit** `deploy/docker/local_settings.py` (local overrides only).
- **Encoding model** is named `Encoding` (not Encode). Workers must share the same filesystem.

## Skill Index

Read the matching skill under `skills/<name>/SKILL.md` before deep work. Cursor discovers them via `.cursor/skills` → `skills/`.

| Skill | Use when |
| -------------------- | ---------------------------------------------------------------- |
| `admin-portal` | Jazzmin dashboard, sidebar, health checks, changelists, theme |
| `auth-identity` | Login, allauth, IdP/OAuth/SAML, Login Options, secrets |
| `i18n` | Translations, gettext, RTL, `process_translations` |
| `fork-docs-release` | Docs site, mike, what’s new, GHCR, beta/stable |
| `media-pipeline` | Encoding, HLS, integrity, media paths, import |
| `rbac-permissions` | Roles, RBAC, FE/BE permission alignment, `CAN_*` settings |
| `test-ci` | Pytest, Jest, CI failures, pre-commit, coverage |
| `merge-hygiene` | Merges into `mediacms-next`, `local_settings` stash |
| `issue-triage` | Issue applicability, minimal fix plans |
| `dev-stack` | Compose up/down, rebuilds, restarts, :80 vs :8088 |
| `dev-manage` | `manage.py`, fake media, DB export, shell in web |
| `dev-api` | Live `/api/v1` smoke, upload metadata, Swagger |

## Lazy-Load Docs

Do not invent architecture — read these when needed:

- Architecture: `docs/en/guides/developer/architecture.md`
- Local dev: `docs/en/guides/developer/local-dev.md`
- Tests: `docs/en/guides/developer/tests.md`
- Translations: `docs/en/guides/developer/translations.md`
- Roles / RBAC: `docs/en/roles/`, `docs/en/guides/operator/permissions.md`
- Settings catalog: `docs/en/guides/admin/settings.md`
- Releases / fork: `docs/en/releases/`
- Writing docs: `docs/en/contributing/writing.md`
