# Releases

Use this section to compare **upstream MediaCMS (≤v9 / latest upstream)** with the **mrjoshuap fork 10.0.0** lines (**stable** and **beta**), then find upgrade and migration tips.

!!! danger "Beta is a moving target"
    The beta line (`mediacms-next`, `ghcr.io/mrjoshuap-hq/mediacms:beta`) publishes a GitHub pre-release on **every push**. Models, permissions, admin screens, frontend bundles, and docs can change without a long notice period. Do not use `:beta` as a production pin. Use a date-stamped image tag (`:10.0.0.YYYYMMDD[.N]`) or `:stable` when you need a fixed build.

!!! danger "Upgrade can change who can do what"
    Fork 10 realigns global roles and media ACLs with the roles and permissions guides. Existing editors, pending users, shares, and RBAC groups can lose or gain access. Read [Permission access changes](../guides/admin/permissions-changes.md) and [Upgrade tips](upgrade-tips.md) before you cut over.

!!! warning "Back up before every line change"
    Back up PostgreSQL and `media_files` before you move between upstream, fork stable, and fork beta. Confirm a restore path. See [Update](../getting-started/update.md) and [Site upgrade](../guides/admin/site-upgrade.md).

## The three lines at a glance

| Line | Typical image / branch | Cadence | Use when |
|------|------------------------|---------|----------|
| Upstream ≤v9 / latest | `mediacms/mediacms` on Docker Hub; [mediacms-io/mediacms](https://github.com/mediacms-io/mediacms) | Upstream releases | You want the community baseline |
| Fork 10.0.0 **stable** | `ghcr.io/mrjoshuap-hq/mediacms:stable` (and `:full`); stamp tags from `main` | Stamped tags only | You want fork features with a fixed digest |
| Fork 10.0.0 **beta** | `ghcr.io/mrjoshuap-hq/mediacms:beta` / `:mediacms-next` | Every push to `mediacms-next` | You test early; you accept churn |

Legend used in comparison tables:

| Mark | Meaning |
|------|---------|
| Yes | Present and intended on that line |
| No | Not present |
| Partial | Present with different behavior or a subset |
| Beta-first | Lands on beta; appears on stable only after a stamp from `main` |

## Capability snapshot

| Area | Upstream ≤v9 | Fork 10 stable | Fork 10 beta |
|------|--------------|----------------|--------------|
| Classic media CMS (upload, encode, play, share) | Yes | Yes | Yes |
| Role-aligned ACL (editors / pending / RBAC delete) | Partial | Yes | Yes |
| Admin workflow sidebar and health dashboards | No | Yes | Yes |
| Site upgrade tooling (`upgrade_site`, UpgradeDecision) | No | Yes | Yes |
| Password-protected media (session unlock API) | No | Yes | Yes |
| MkDocs docs at `/documentation/` + mike channels | No | Yes | Yes |
| GHCR `:beta` / `:stable` date-stamped images | No | Yes | Yes |
| Faster combined PR / issue test bed | No | Partial | Yes |
| Customization playground (headers, banners, ads) without code edits | No | Partial | Beta-first |

Open [Compare lines](compare.md) for the full matrix by feature, fix, model, and frontend impact.

## Pages in this section

| Page | Use it to |
|------|-----------|
| [Compare lines](compare.md) | Side-by-side view of significant capabilities, bugs, and ops differences |
| [Features](features.md) | What the fork adds or rethinks (admin, media, ops, docs) |
| [Fixes and known issues](fixes.md) | Shipped bug fixes and risks that remain on a fast line |
| [Models and migrations](migrations.md) | Database and model changes you must apply |
| [Frontend](frontend.md) | When you must rebuild React bundles and copy static files |
| [Upgrade tips](upgrade-tips.md) | `manage.py`, Make, Docker, and admin portal commands for known problems |

## Related reference

| Page | Role |
|------|------|
| [What's new](../reference/whats-new.md) | Full curated bullet list (generated from `docs/_shared/fork-whats-new.md`) plus upstream notes |
| [This version](../reference/this-version.md) | Version, channel, and artifact identity for this docs build |
| [Changelog](../reference/changelog.md) | Upstream changelog with a short fork preamble |
| [Fork beta and stable images](../getting-started/install.md#fork-beta-and-stable-images-ghcr) | Exact GHCR tags to pull |
