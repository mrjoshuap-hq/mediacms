# Compare lines

Compare **upstream MediaCMS (≤v9 / latest upstream)** with fork **10.0.0 stable** and **10.0.0 beta**. Use this page for a quick decision. Use [Features](features.md), [Fixes](fixes.md), [Models and migrations](migrations.md), and [Frontend](frontend.md) for detail. Use [Upgrade tips](upgrade-tips.md) when you cut over.

!!! danger "Do not treat Yes as \"safe to enable without a plan\""
    A Yes in the fork columns can still require migrations, a frontend build, new settings, or an ACL review. Check the **Impact** column and [Upgrade tips](upgrade-tips.md).

## How to read the columns

| Column | Means |
|--------|-------|
| Upstream ≤v9 | Community MediaCMS through the 9.x line (this fork tracks upstream `main` near 9.4.0) |
| Fork 10 stable | Features that ship in stamped GHCR `:stable` / `:10.0.0.YYYYMMDD[.N]` builds from `main` |
| Fork 10 beta | Features on `mediacms-next` / `:beta` (can be ahead of stable) |

When stable and beta both say Yes, beta may still be newer within the same feature. Prefer pinned tags.

## Admin and operations

| Capability | Upstream ≤v9 | Fork 10 stable | Fork 10 beta | Impact |
|------------|--------------|----------------|--------------|--------|
| Jazzmin admin with basic model admin | Yes | Yes | Yes | Baseline |
| Workflow sidebar (Moderation, Library, Processing, People, Integrations, Site) | No | Yes | Yes | New admin IA; train staff |
| Dashboard overviews + **Refresh stats** | No | Yes | Yes | Cached stats; optional DB models |
| Site Health, Configuration, System, Database pages | No | Yes | Yes | Superuser ops surface |
| Database backup download / restore upload | No | Yes | Yes | Dangerous restore path; back up first |
| Redacted support bundle (Get Support) | No | Yes | Yes | Share logs without secrets |
| `upgrade_site` inventory / scratch / apply | No | Yes | Yes | Migrations for `UpgradeDecision`; see [Site upgrade](../guides/admin/site-upgrade.md) |
| Integrity checks (media / metadata) in Site Health and Library | No | Yes | Yes | New audit signals |
| Structured logging, failed-login IP, `TRUSTED_PROXIES` | Partial | Yes | Yes | Settings + restart |

## Permissions and roles

| Capability | Upstream ≤v9 | Fork 10 stable | Fork 10 beta | Impact |
|------------|--------------|----------------|--------------|--------|
| Global roles (anonymous → superuser) | Yes | Yes | Yes | Baseline |
| ACL aligned with roles / permissions guides | Partial | Yes | Yes | **Breaking** for some editors and pending users; see [Permission access changes](../guides/admin/permissions-changes.md) |
| Manage users limited to managers / superusers | Partial | Yes | Yes | Editors lose Manage users |
| Pending users blocked from more write APIs | Partial | Yes | Yes | Comments / likes / reports blocked while pending |
| Co-owner / RBAC manager delete | Partial | Yes | Yes | Broader delete than some ≤v9 installs |
| Frontend `can.*` flags match server | Partial | Yes | Yes | Needs frontend rebuild |

## Media, player, and encoding

| Capability | Upstream ≤v9 | Fork 10 stable | Fork 10 beta | Impact |
|------------|--------------|----------------|--------------|--------|
| Multi-resolution encode + HLS | Yes | Yes | Yes | Baseline |
| Incremental HLS packaging + Redis lock | Partial | Yes | Yes | Worker / Redis behavior |
| Encoding chunk cleanup beat task | No | Yes | Yes | Celery beat setting |
| Password-protected media + session unlock API | No | Yes | Yes | Migration `files.0023_alter_media_password`; frontend |
| Lazy playlist membership for Save popup | No | Yes | Yes | New API route |
| Soft-nav next/prev keeps fullscreen / autoplay | No | Yes | Yes | Player UX |
| Upload metadata on create (title, description, …) | Partial | Yes | Yes | FineUploader + API |
| CJK-aware media search | No | Yes | Yes | Search behavior change |
| Sharded media paths (`<kind>/<aa>/<bb>/<uid>/…`) for new files | No | Yes | Yes | Migration `files.0024_sharded_media_paths`. nginx blocks for `thumbnails`, `categories`, `subtitles` on a custom config. Old files keep legacy paths |
| **Migrate paths** (single and bulk) on Manage media | No | Yes | Yes | Managers and superusers. Needs frontend rebuild. See [Manage media](../guides/operator/manage-media.md#move-media-to-the-sharded-path-layout) |
| **Filesystem library** source in content migration, with re-runnable sync and prune rule | No | Yes | Yes | Migration `migrationservice.0002_provider_filesystem`. Optional bind mount under `FILESYSTEM_IMPORT_ROOT`. See [Content migration](../guides/admin/content-migration.md#filesystem-library) |

## Documentation, CI, and release

| Capability | Upstream ≤v9 | Fork 10 stable | Fork 10 beta | Impact |
|------------|--------------|----------------|--------------|--------|
| MkDocs Material docs (roles, guides, scenarios) | No | Yes | Yes | Served at `/documentation/` |
| mike versioned docs (`dev` / `beta` / `latest`) | No | Yes | Yes | GitHub Pages Actions deploy |
| GHCR fork images `:beta` / `:stable` / stamp tags | No | Yes | Yes | See [Install](../getting-started/install.md#fork-beta-and-stable-images-ghcr) |
| Curated fork What's new + Upgrade impact table | No | Yes | Yes | [What's new](../reference/whats-new.md) |
| Every-push beta pre-release | No | No | Yes | High churn |

## Customization direction

| Capability | Upstream ≤v9 | Fork 10 stable | Fork 10 beta | Impact |
|------------|--------------|----------------|--------------|--------|
| Custom pages / appearance (existing tools) | Yes | Yes | Yes | See [Custom pages](../guides/admin/pages-appearance.md) |
| Playground for headers, banners, ad tracking, page mods without code edits | No | Partial | Beta-first | Expect more change on beta; do not depend on unfinished APIs |

## Next step

1. Open the detail page for your concern: [Features](features.md), [Fixes](fixes.md), [Models and migrations](migrations.md), or [Frontend](frontend.md).
2. Before you upgrade, open [Upgrade tips](upgrade-tips.md).
