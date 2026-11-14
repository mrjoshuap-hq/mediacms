# Frontend

When fork **10.0.0** changes React or static assets, the image or tree can ship Python that does not match `static/js`. That mismatch shows up as missing buttons, wrong permission flags, or old player behavior.

!!! warning "Port 80 shows built bundles; port 8088 shows the webpack dev server"
    In local Docker development, frontend hot reload is on **8088**. The app on **80** only picks up frontend changes after `make build-frontend` (or an equivalent `npm run dist` + copy into `static/`).

## When a rebuild is required

| Change area | Upstream ≤v9 | Fork 10 | Rebuild? | Also |
|-------------|--------------|---------|----------|------|
| Permission ACL / `can.*` flags | Partial | Yes | **Yes** | Restart web |
| Password-protected media UI | No | Yes | **Yes** | Migration; optional language rebuild |
| Player soft-nav / chapters fixes | Partial | Yes | **Yes** | Restart web |
| Playlist Save popup (lazy membership) | No | Yes | **Yes** | New API must match JS |
| Content migration **Filesystem library** form | No | Yes | **Yes** | New strings: `process_translations` |
| **Migrate paths** on **Manage media** (single and bulk) | No | Yes | **Yes** | Needs the `migrate_paths` API. Shows only to managers and superusers |
| Translation-only React strings | Partial | Yes | **Yes** when React strings change | `process_translations` |
| Admin-only Python / Jazzmin | N/A | Yes | Usually **No** | Collect static if you do not use the image pipeline |
| Settings-only (`TRUSTED_PROXIES`, logging) | Partial | Yes | **No** | Restart web / Celery |

See the **Upgrade impact** table on [What's new](../reference/whats-new.md).

## Commands

### Local development compose

```bash
make build-frontend
```

That runs `npm run dist` in the frontend container, copies `frontend/dist/static/*` into `static/`, and restarts `web`.

Equivalent:

```bash
docker compose -f docker-compose-dev.yaml exec -T frontend npm run dist
cp -r frontend/dist/static/* static/
docker compose -f docker-compose-dev.yaml restart web
```

### Language strings (when UI copy changes)

1. Add English strings to `files/frontend_translations/en.py` first.
2. Run:

    ```bash
    python manage.py process_translations
    ```

3. Translate other languages under `files/frontend_translations/`.
4. Rebuild the frontend if React surfaces the string.
5. Restart web after you copy static files.

### Production image

Official fork images normally ship built static files. If you mount your own tree over the app directory, you must rebuild and copy yourself. Prefer the image static pipeline; do not mount an old tree onto the application directory during upgrade.

## How to tell you skipped a rebuild

| Symptom | Likely mismatch |
|---------|-----------------|
| Upload / comment / like buttons disagree with the API | Old `can.*` flags in JS |
| Password unlock UI missing or broken | Old media viewer bundle |
| Save-to-playlist popup slow or wrong | Old playlist membership client |
| No **Filesystem library** card at `/migrations/new` | Old migrations bundle |
| No **Migrate paths** in **Manage media** for a manager | Old manage-media bundle |
| Docs say a player fix is in; UI still broken | Port 80 still serving old `static/js` |

## Related pages

- [Upgrade tips](upgrade-tips.md)
- [Models and migrations](migrations.md)
- [Translations](../guides/developer/translations.md)
- [Local development](../guides/developer/local-dev.md)
