---
name: Upgrade audit plan
overview: Add a read-only upgrade audit, profiled database exports, sidebar page placement, and a browse-only pending-approval state, with contract tests for each and Compose checks for the scratch database.
todos:
  - id: export-profiles
    content: Add engagement and noisy-status export switches, a manifest, and round-trip tests. Keep the admin download on the default profile.
    status: completed
  - id: sidebar-slugs
    content: Validate sidebar and inject slugs, group them in the context processor, render sections in the sidebar, and protect auth and API names.
    status: completed
  - id: approval-browse
    content: Let pending users sign in and read. Refuse upload, media and playlist writes, and manage pages, including for editors.
    status: completed
  - id: upgrade-audit
    content: Add upgrade_site inventory, scratch migrate, and one-shot apply. Report hash mismatches, page collisions, listable drift, reports, and approval counts.
    status: completed
  - id: postgres-gate
    content: Add a separate pg_restore integrity script that does not run Django migrate.
    status: completed
  - id: tests
    content: Cover export, slugs, approval, and audit helpers in pytest and Jest. Add Compose checks for the scratch database and the Postgres gate.
    status: completed
isProject: false
---

# Upgrade audit, exports, sidebar pages, and approval

Ship the contracts already settled. Leave anonymous public-page behavior and extra RBAC grant rewrites unspecified: the audit reports them and does not change rows for them.

```mermaid
flowchart LR
  postgresGate[Postgres gate]
  audit[upgrade_site audit]
  scratch[Scratch database]
  answers[Stored answers]
  cutover[Cutover]
  postgresGate --> audit
  audit --> scratch
  scratch --> answers
  answers --> cutover
```

The audit container uses the new image. The old install is mounted read-only at `/audit/previous` and media at `/audit/media`. Those mounts stay off `/home/mediacms.io/mediacms/` so the new code is the code that runs. The container overrides [deploy/docker/entrypoint.sh](deploy/docker/entrypoint.sh) and does not run [deploy/docker/prestart.sh](deploy/docker/prestart.sh).

## Export profiles

Default stays the quiet set in [actions/models.py](actions/models.py) `EXPORTED_MEDIA_ACTIONS` and [admin_customizations/database_backup.py](admin_customizations/database_backup.py) `EXCLUDED_MODELS`: reports and moderation or integrity actions only. Omit likes, dislikes, watches, and ratings. Omit failed encodings and all trim and transcription requests.

Add two switches, recorded in a small JSON manifest beside the fixture:

- Engagement includes `like`, `dislike`, `watch`, and `rate`.
- Noisy status includes failed encodings and trim and transcription requests in any status.

The admin download keeps the default profile. A management command accepts the switches. Restore rejects a fixture whose rows disagree with its manifest. Same profile is used for the scratch database and the smoke export.

Passphrase encryption of the dump is a follow-on. This pass writes the manifest and the profile filters so encryption can wrap the same bytes later.

## Sidebar and fragment pages

[files/models/page.py](files/models/page.py) gains `clean()` for the slug grammar. [files/context_processors.py](files/context_processors.py) stops putting every non-reserved page into one `CMS_SIDEBAR_PAGES` list. It groups rows for [templates/config/installation/contents.html](templates/config/installation/contents.html).

- Link form `sidebar-<section>--<name>` with section `browse`, `library`, `personal`, `info`, or `manage`. Public URL is `/<name>`. Order within a section is by title.
- HTML slots `sidebar-below--<name>`, `sidebar-after-theme--<name>`, and `sidebar-footer--<name>` render into `belowNavMenu`, `belowThemeSwitcher`, and the footer. `get_page` returns 404.
- Fragments `inject-head`, `inject-css`, `inject-header`, `inject-footer`, and `inject-js` render in [templates/root.html](templates/root.html), [templates/components/header.html](templates/components/header.html), and [templates/components/footer.html](templates/components/footer.html). CSS and script slugs are not passed through the HTML body.
- Bare `about`, `tos`, `contact`, and `setlanguage` stay the built-in info links. A second `sidebar-info--tos` is rejected.

`library` and `personal` are emitted only for an authenticated user. `manage` only for an editor. [frontend/src/static/js/components/page-layout/sidebar/SidebarNavigationMenu.jsx](frontend/src/static/js/components/page-layout/sidebar/SidebarNavigationMenu.jsx) reads those section lists. Today only `mainMenuExtra` is used, and `CustomMenuSection` is hardcoded.

Protected names, including the part after `--`, are rejected in `clean()` and again in `get_page`: `accounts`, `login`, `logout`, `signup`, `password`, `saml`, `approval_required`, `api`, `api-auth`, `swagger`, `docs`, `admin`, `lti`, `tinymce`, `fu`, `manage`, `user`, `channel`. This matters because the catch-all in [files/urls.py](files/urls.py) is registered before `accounts/` in [cms/urls.py](cms/urls.py).

## Pending approval

Today [cms/auth_backends.py](cms/auth_backends.py) refuses login, and [cms/middleware.py](cms/middleware.py) `ApprovalMiddleware` redirects every page except approval-required and logout, and returns 403 for all of `/api/`.

When `USERS_NEEDS_TO_BE_APPROVED` is on, a user with `is_approved` false or null can sign in and read public pages and read APIs. Upload, media edit and delete, playlist create, edit, and delete, and `/manage/media`, `/manage/users`, and `/manage/comments` stay refused. One helper used by [files/methods.py](files/methods.py) `user_allowed_to_upload`, the media and playlist write views, and the manage views. Editors are not exempt. Superusers stay exempt. With the setting off, `is_approved` is ignored.

The audit counts non-superusers with `is_approved` false or null when the mounted settings turn approval on. The stored answer is either mark that existing set approved once, or leave them pending. Migrate does not flip the column.

## Audit command

New `files/management/commands/upgrade_site.py` with three steps:

- Inventory uses raw SQL on the source database: `django_migrations`, `information_schema`, page slugs, approval counts, listable mismatches, report queues, category and tag `media_count`. Compare migration file hashes in the image with names stored in the source. Diff `/audit/previous` templates and migration files. No model querysets against the unmigrated source.
- Scratch restores a dump into a new database and runs `migrate` there. The source `django_migrations` table is unchanged.
- Apply writes accepted answers once. A second run does not repeat a data fix. Empty checks are omitted. Fast-forward means every applied migration name exists in the image with the same file hash and the target only adds later migrations. A hash mismatch is reported as do-not-fake.

Postgres major-version restore stays a separate script under `deploy/docker/`: `pg_dump`, `pg_restore`, then compare row counts, primary keys for media, users, and pages, and sequences. Django migrate is not part of that script.

Checks that only report, and do not offer a row rewrite: RBAC grants, template diffs, missing media paths, and the unspecified anonymous-page work.

## Tests

Pytest, next to the suites that already cover this behavior:

- Extend [tests/admin/test_database_stats.py](tests/admin/test_database_stats.py) for both switches, the manifest, and a round-trip whose counts match. A like in a default-profile fixture fails validation.
- Extend [tests/pages/test_pages_site.py](tests/pages/test_pages_site.py) for section placement, anonymous versus signed-in versus editor visibility, HTML-slot 404s, built-in pages not duplicated, and rejected protected slugs. A row forced in past `clean()` still 404s.
- Rewrite the pending-user expectations in [tests/users/test_users_approval.py](tests/users/test_users_approval.py): login and `GET /featured` and `GET /api/v1/media` succeed; upload, playlist write, and `/manage/media` do not; an unapproved editor is refused; a superuser is not; null `is_approved` is pending; the setting off allows upload.
- New unit tests for the audit helpers: fast-forward versus hash mismatch, empty checks omitted, protected page slugs reported and not copied, approval answer applied once, category count rebuild idempotent.
- Jest on the sidebar config: browse in the first block, info in the custom block, manage only with editor rights, library only when signed in, HTML slots not rendered as links.

Compose, not default pytest: the audit container leaves source `django_migrations` and `.secret_key` unchanged; scratch migrate, default export, import into an empty database, counts match; the Postgres gate does not add migration rows. Smoke against the scratch database: anonymous home, about, and latest; editor manage page; pending user can read and cannot upload; `/accounts/login/` is still the login form.
