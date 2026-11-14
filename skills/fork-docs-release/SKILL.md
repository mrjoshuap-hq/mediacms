---
name: fork-docs-release
description: Maintain MediaCMS fork documentation, mike/GitHub Pages channels, what’s-new notes, and GHCR beta/stable releases. Use when editing docs, fork-whats-new, docs.yml, release.yml, mike aliases, or mediacms-next vs main release docs.
---

# Fork docs and release

## Instructions

1. **Fork what’s new:** edit only `docs/_shared/fork-whats-new.md` (Conventional Commits sections). `scripts/prepare_docs_build.py` injects it into `docs/en/reference/whats-new.md` for channels `beta` / `local` / `dev` / `stable` / `latest`.
2. **Do not** hand-edit the generated reference what’s-new page or upstream `CHANGELOG.md` for fork notes.
3. **Local docs:** `make docs-up` → http://localhost/documentation/ (not `/docs/`, which is ReDoc + a protected slug).
4. **Writing:** follow `docs/en/contributing/writing.md` and glossary; add pages via `docs/en/guides/developer/add-docs-page.md`.
5. **Branches:** `MEDIACMS_STABLE_BRANCH` (default `main`) and `MEDIACMS_BETA_BRANCH` (default `mediacms-next`). Workflows list both under `on.push` because triggers cannot read vars.
6. **Mike aliases:** stable → `dev`, beta → `beta`, tags → `latest`. Pages source must be **GitHub Actions** (`docs.yml` → mike → `actions/deploy-pages`).
7. **GHCR:** `release.yml` publishes date-stamped tags from `version/FORK_VERSION`. Pushes to `mediacms-next` → pre-release + `:beta` / full `:beta`. Matching stamp tags from `main` → `:stable`. Prefer this over enabling semantic-release unless asked.

## Additional resources

- `docs/en/releases/` (index, compare, features, fixes, migrations, upgrade)
- `docs/en/contributing/writing.md`
- `docs/_shared/fork-whats-new.md`
- `scripts/prepare_docs_build.py`
- `.github/workflows/docs.yml`, `.github/workflows/release.yml`
