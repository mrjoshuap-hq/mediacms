---
name: Proxy SSL media health
overview: Extend Site Health with reverse-proxy/SSL/CORS/cookie settings checks and live MEDIA_ROOT/HLS/TEMP read-write permission probes, wired into the existing dashboard health table.
todos:
  - id: deployment-module
    content: Create admin_customizations/deployment_health.py with proxy/SSL/CORS/cookie and media FS probe iterators
    status: completed
  - id: wire-health
    content: Wire iterators into get_site_health_checks; extend get_site_configuration_status
    status: completed
  - id: i18n
    content: Add en.py labels and run process_translations
    status: completed
  - id: tests
    content: Add override_settings + tempdir tests for deployment and media storage health checks
    status: completed
isProject: false
---

# Reverse proxy, SSL, CORS, and media storage health checks

## Approach

Add a dedicated module [`admin_customizations/deployment_health.py`](admin_customizations/deployment_health.py) that yields health payloads (same shape as integrity/metadata iterators). Wire it into [`get_site_health_checks`](admin_customizations/admin.py) before the severity sort. Keep probes cheap (settings reads + tiny write/delete); no media-tree scans.

Severity policy:
- **Production** = not `DEBUG` and not `LOCAL_INSTALL`
- Proxy/SSL/cookie/CORS mismatches → **warn** in production, **info** locally
- Media path missing / not readable / not writable → **fail** for `MEDIA_ROOT` and `TEMP_DIRECTORY`; **warn** for secondary dirs (`HLS_DIR`, upload/encoded/chunks)

## 1. Deployment / reverse-proxy / SSL / CORS checks

`iter_deployment_health_checks()` in the new module:

| id | What | Pass criteria |
|---|---|---|
| `proxy_forwarded_host` | `USE_X_FORWARDED_HOST` | True when `FRONTEND_HOST` is https (expected behind reverse proxy per docs/docker `local_settings`) |
| `proxy_ssl_header` | `SECURE_PROXY_SSL_HEADER` | Equals `('HTTP_X_FORWARDED_PROTO', 'https')` when FRONTEND_HOST is https |
| `csrf_trusted_origins` | `CSRF_TRUSTED_ORIGINS` | When FRONTEND_HOST is https, list includes that origin (scheme+host[+port]); empty list → warn in production |
| `secure_cookies` | `CSRF_COOKIE_SECURE` + `SESSION_COOKIE_SECURE` | Both True when FRONTEND_HOST is https; warn if either False in production |
| `secure_ssl_redirect` | `SECURE_SSL_REDIRECT` | True when FRONTEND_HOST is https in production; info if unset locally |
| `cors_allow_all` | CORS settings | If `corsheaders` is in `INSTALLED_APPS` and (`CORS_ORIGIN_ALLOW_ALL` or `CORS_ALLOW_ALL_ORIGINS`) is True while production → **warn**; ok/info when DEBUG/dev; ok when corsheaders not installed (normal for MediaCMS prod) |

Reuse existing `_frontend_host_parts()` logic (move a small shared helper into the new module or import from `admin.py` via a tiny shared util to avoid circular imports — prefer putting `_frontend_host_parts` + these iterators in `deployment_health.py` and having `admin.py` import from there).

Existing `frontend_https` / `allowed_hosts` / `debug` checks stay as-is.

## 2. Media location access checks

`iter_media_storage_health_checks()` in the same module:

Paths to validate (absolute):

- `MEDIA_ROOT`
- `HLS_DIR`
- `TEMP_DIRECTORY`
- Under `MEDIA_ROOT`: `MEDIA_UPLOAD_DIR` (`original/`), `MEDIA_ENCODING_DIR` (`encoded/`), `UPLOAD_DIR` (`uploads/`), `CHUNKS_DIR` (`chunks/`)

Per path:

1. Exists and is a directory (missing → fail/warn by severity above; do **not** auto-create)
2. Readable (`os.access(..., R_OK)`)
3. Writable via probe: create `.mediacms_health_probe_<pid>`, write a few bytes, unlink — catch `OSError`/`PermissionError`

Emit one check per top-level concern (not one row per subdir):

| id | Label | Aggregates |
|---|---|---|
| `media_root_access` | MEDIA_ROOT readable/writable | exist + R/W probe |
| `hls_dir_access` | HLS_DIR readable/writable | exist + R/W |
| `temp_dir_access` | TEMP_DIRECTORY readable/writable | exist + R/W |
| `media_subdirs_access` | Media subdirs accessible | original/encoded/uploads/chunks — detail lists any failing names |

Detail strings include the absolute path and the specific failure (`missing`, `not readable`, `not writable: PermissionError...`).

## 3. Wire-up and configuration table

In [`get_site_health_checks`](admin_customizations/admin.py):

```python
from admin_customizations.deployment_health import (
    iter_deployment_health_checks,
    iter_media_storage_health_checks,
)
for payload in iter_deployment_health_checks():
    checks.append(_health_check(**payload))
for payload in iter_media_storage_health_checks():
    checks.append(_health_check(**payload))
```

Extend [`get_site_configuration_status`](admin_customizations/admin.py) with informational rows (no new settings required):

- `USE_X_FORWARDED_HOST`, `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`
- `CSRF_COOKIE_SECURE`, `SESSION_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS`
- `MEDIA_ROOT`, `HLS_DIR`, `TEMP_DIRECTORY`
- CORS flags only when `corsheaders` is installed

No template changes — [`_site.html`](templates/admin/dashboard/_site.html) already renders any health row and translates `check.label` via `custom_translate`.

## 4. Translations

Add new check labels to [`files/frontend_translations/en.py`](files/frontend_translations/en.py), then `python manage.py process_translations`.

Labels (examples): `Reverse proxy USE_X_FORWARDED_HOST`, `SECURE_PROXY_SSL_HEADER configured`, `CSRF_TRUSTED_ORIGINS includes FRONTEND_HOST`, `Secure cookies enabled`, `SECURE_SSL_REDIRECT enabled`, `CORS allow-all disabled in production`, `MEDIA_ROOT readable/writable`, `HLS_DIR readable/writable`, `TEMP_DIRECTORY readable/writable`, `Media subdirs accessible`.

## 5. Tests

In [`tests/admin/test_admin_dashboard_stats.py`](tests/admin/test_admin_dashboard_stats.py) (and/or a focused `tests/admin/test_deployment_health.py`):

- Production-like `@override_settings(DEBUG=False, LOCAL_INSTALL=False, FRONTEND_HOST="https://example.com")`:
  - missing `USE_X_FORWARDED_HOST` / bad `SECURE_PROXY_SSL_HEADER` → warn
  - insecure cookies / empty `CSRF_TRUSTED_ORIGINS` → warn
  - `CORS_ORIGIN_ALLOW_ALL=True` with corsheaders present → warn
- Local/debug → those same gaps are info (or ok), not warn
- Media storage: point `MEDIA_ROOT`/`HLS_DIR`/`TEMP_DIRECTORY` at temp dirs; assert ok; chmod or missing path asserts fail/warn
- Assert new check ids appear in `get_site_health_checks()`
- Assert new configuration labels appear in `get_site_configuration_status()`

## Out of scope

- Changing default `settings.py` / docker `local_settings` values
- Actually verifying TLS certificates or reaching an upstream reverse proxy
- Auto-creating missing media directories from the health check
- Full recursive permission audit of existing media files
