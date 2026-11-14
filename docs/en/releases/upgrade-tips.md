# Upgrade tips

Practical commands and admin portal paths for known or likely problems when you move between **upstream ≤v9**, fork **10.0.0 stable**, and fork **10.0.0 beta**.

!!! danger "Pick the line on purpose"
    - Production that must stay still: pin `v10.0.0.YYYYMMDD` or use `:stable`. Never float on `:beta`.
    - Early testing: `:beta` is fine on a disposable portal. Expect daily churn.
    - Leaving upstream ≤v9: treat the cutover as a **site upgrade**, not a casual image bump.

!!! warning "Back up first"
    Back up PostgreSQL and `media_files`. Verify restore. Keep `SECRET_KEY` stable across the cutover.

## Tip map

| Problem or goal | Go to |
|-----------------|-------|
| Choose image tags | [Choose an image](#choose-an-image) |
| Apply DB changes safely | [Apply migrations](#apply-migrations) |
| Fix missing buttons / old player | [Rebuild frontend](#rebuild-frontend) |
| Editors / pending users behave differently | [Review access changes](#review-access-changes) |
| Confirm the portal after upgrade | [Verify in the admin portal](#verify-in-the-admin-portal) |
| Large existing install | [Use upgrade_site](#use-upgrade_site) |
| Logging / proxy / mail after cutover | [Settings restarts](#settings-restarts) |
| Encoding leftovers | [Encoding cleanup](#encoding-cleanup) |
| Old media on legacy paths | [Move media to sharded paths](#move-media-to-sharded-paths) |
| Sync a mounted library | [Mount a filesystem library](#mount-a-filesystem-library) |
| `InvalidBaseImagePlatform` / arm64 encode flakes | [Apple Silicon Docker build](#apple-silicon-docker-build) |

## Choose an image

| Goal | Image |
|------|-------|
| Fork beta (churn OK) | `ghcr.io/mrjoshuap/mediacms:beta` (and `-full:beta` for Whisper) |
| Fork stable floating | `ghcr.io/mrjoshuap/mediacms:stable` |
| Fixed fork build | `ghcr.io/mrjoshuap/mediacms:v10.0.0.YYYYMMDD` |
| Upgrade drill aliases | `:upgrade-audit` / `:upgrade-audit-beta` |
| Upstream baseline | `mediacms/mediacms` on Docker Hub |

Full table: [Fork beta and stable images](../getting-started/install.md#fork-beta-and-stable-images-ghcr).

Example Compose override for a **pinned** beta stamp:

```yaml
services:
  web:
    image: ghcr.io/mrjoshuap/mediacms:v10.0.0.20261114
  celery_worker:
    image: ghcr.io/mrjoshuap/mediacms:v10.0.0.20261114
  celery_beat:
    image: ghcr.io/mrjoshuap/mediacms:v10.0.0.20261114
```

## Apply migrations

### Normal Compose update

1. `docker compose down`
2. Pull the target tag.
3. `docker compose up`
4. Read the `migrations` container logs until migrate finishes without error.

### One-off migrate (new image, existing DB)

```bash
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py showmigrations files actions
```

### Dev stack

```bash
docker compose -f docker-compose-dev.yaml exec -T web python manage.py migrate
docker compose -f docker-compose-dev.yaml exec -T web python manage.py showmigrations files actions
```

See [Models and migrations](migrations.md) for the fork migration list.

## Rebuild frontend

When [Frontend](frontend.md) or the What's new **Upgrade impact** table says Yes:

```bash
make build-frontend
```

Or:

```bash
docker compose -f docker-compose-dev.yaml exec -T frontend npm run dist
cp -r frontend/dist/static/* static/
docker compose -f docker-compose-dev.yaml restart web
```

If React strings changed:

```bash
python manage.py process_translations
```

Then rebuild frontend and restart web.

## Review access changes

1. Open [Permission access changes](../guides/admin/permissions-changes.md).
2. List editors who used Manage users. Move Manage users work to managers.
3. List pending users. Expect browse-only until approval.
4. Test one co-owner and one RBAC category manager for delete rules.
5. Rebuild frontend so UI flags match the server.

Manage pages (operators):

- `/manage/media`
- `/manage/users` (managers / superusers on fork 10)
- `/manage/comments`

## Verify in the admin portal

Sign in as a superuser. Check:

| Path / page | Why |
|-------------|-----|
| Admin home / workflow sidebar | Confirm Moderation, Library, Processing, People, Integrations, Site groups load |
| Site Health | Integrity and health signals after migrate |
| Database (admin) | Only if you use backup/restore tools; prefer external backups first |
| Get Support | Produce a redacted bundle if you need help |
| Configuration / System | Confirm settings visibility after `local_settings.py` changes |

Guides: [Site health and database](../guides/admin/site.md), [Admin portal map](../guides/admin/portal-map.md).

## Use upgrade_site

For an existing portal with real data:

```bash
python manage.py upgrade_site inventory --previous /audit/previous
```

If `fast_forward` is false or `problems` is not empty, **stop**.

Then use scratch on a copy, gate scripts, and only later:

```bash
python manage.py upgrade_site apply
```

Full flow: [Site upgrade](../guides/admin/site-upgrade.md). Scenario script: [Superuser upgrade inventory](../scenarios/superuser-upgrade-inventory.md).

Useful companions:

```bash
python manage.py export_database
# deploy/docker/postgres_gate.sh
# deploy/docker/upgrade_site_smoke.sh
```

## Settings restarts

After you change logging, trusted proxies, or mail-related settings in `local_settings.py`:

```bash
docker compose restart web celery_worker celery_beat
```

Dev stack:

```bash
docker compose -f docker-compose-dev.yaml restart web celery_worker celery_beat
```

Settings of interest on the fork line:

| Setting | Tip |
|---------|-----|
| `TRUSTED_PROXIES` | Empty list disables proxy-aware client IP |
| `LOGLEVEL` / `ENABLE_SQL_DEBUG_LOGGING` | Structured logs; SQL debug is noisy |
| `EMAIL_TIMEOUT` | Contact and auth mail |
| `ALLOW_POPULATE_FAKE_MEDIA` | Guard for `populate_fake_media` (dev only) |
| `ACCOUNT_LOGIN_BY_CODE_ENABLED` | Login-by-code |

Catalog: [Settings](../guides/admin/settings.md).

## Move media to sharded paths

New uploads use sharded paths. Existing media stays on the old paths and keeps working. Nothing moves on update.

1. Open **Manage media**. Sign in as a manager or a superuser.
2. Select **Migrate paths** in one row, or select several rows, select **Bulk actions**, select **Migrate paths (sharded layout)**, and select **Apply**.
3. Select **PROCEED**.

Run large batches outside peak hours. Each item is copied and verified first. The old files are deleted only after every check passes. See [Manage media](../guides/operator/manage-media.md#move-media-to-the-sharded-path-layout).

If you use your own nginx configuration, copy the `thumbnails`, `categories`, and `subtitles` blocks from `deploy/docker/nginx_http_only.conf`. See [Install](../getting-started/install.md#use-your-own-nginx-configuration-optional).

## Mount a filesystem library

1. Bind the library under `FILESYSTEM_IMPORT_ROOT` (default `/external-media_files`) on the `web` and `celery_worker` containers.
2. Restart the containers.

    ```bash
    docker compose restart web celery_worker celery_beat
    ```

3. Sign in as a superuser and open `/migrations/new/filesystem`. This is **content migration**, not a site upgrade.

See [Install](../getting-started/install.md#mount-a-media-library-for-filesystem-sync-optional) and [Content migration](../guides/admin/content-migration.md#filesystem-library).

## Encoding cleanup

If orphan encode chunks accumulate after HLS / chunk work:

1. Confirm Celery beat is running.
2. Check `ENCODING_CHUNKS_RETENTION_HOURS` in settings.
3. Restart workers after encode-task related upgrades:

    ```bash
    docker compose restart celery_worker celery_beat
    ```

See [Processing](../guides/admin/processing.md).

## Apple Silicon Docker build

If `make docker-build` prints `InvalidBaseImagePlatform` for `mediacms/mediacms:7.2.0`, the build is still often usable. The Dockerfile copies **amd64** FFmpeg from that pinned donor image and still installs the **x86_64** Bento4 zip. Encode and HLS can be slow or fail under emulation.

Full detail: [amd64 media tools in the image](fixes.md#amd64-media-tools-in-the-image). Prefer amd64 workers for reliable encoding tests, or point the FFmpeg / `mp4hls` settings at native binaries.

## Shell access

```bash
make admin-shell
```

Or:

```bash
docker compose -f docker-compose-dev.yaml exec web /bin/bash
```

## Docs after a docs-only change

```bash
make docs-build
# or
make docs-up
```

Open `http://localhost/documentation/` when the web container serves `site/`.

## Checklist (copy)

1. Back up DB + `media_files`.
2. Choose **stable stamp** or accept **beta** churn.
3. Inventory / migrate (`migrations` container or `manage.py migrate`).
4. Apply any **Upgrade impact** rows (frontend, languages, restarts).
5. Review ACL / Manage users / pending.
6. Smoke-test upload, play, comment, manage, and one admin Site Health view.
7. Record the image tag you run.

## Related pages

- [Releases](index.md)
- [Compare lines](compare.md)
- [Update](../getting-started/update.md)
- [Site upgrade](../guides/admin/site-upgrade.md)
- [What's new](../reference/whats-new.md)
