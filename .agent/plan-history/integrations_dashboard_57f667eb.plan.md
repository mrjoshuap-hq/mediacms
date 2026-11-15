---
name: Integrations dashboard
overview: Move Integrations above Site in the admin sidebar and dashboard switcher, and add an Integrations overview that reports counts for the same objects the sidebar lists, using the existing status-box and object-total patterns.
todos:
  - id: nav-order
    content: Move Integrations above Site in sidebar, Jazzmin order, switcher, and index tile; add Overview link and dashboard section
    status: completed
  - id: metrics
    content: Add integrations stats (migration status groups plus flag-gated object counts) and overview templates
    status: completed
  - id: i18n-tests
    content: Add translation strings and update sidebar and dashboard tests
    status: completed
isProject: false
---

# Integrations overview above Site

Integrations is currently the last sidebar group in [`admin_customizations/sidebar.py`](admin_customizations/sidebar.py) and is absent from the dashboard switcher in [`templates/admin/dashboard/_section_nav.html`](templates/admin/dashboard/_section_nav.html). Other workflow groups start with an Overview link into `/admin/dashboard/<section>/`.

## Navigation

- In `build_workflow_app_list`, build the Integrations group before Site. Prepend an Overview queue link (`IntegrationsOverview` → `/admin/dashboard/integrations/`), matching Moderation, Library, Processing, People, and Site.
- Update `JAZZMIN_SETTINGS["order_with_respect_to"]` in [`cms/settings.py`](cms/settings.py) to `people`, `integrations`, `site`, and add `integrations.integrationsoverview`: `fas fa-tachometer-alt`.
- Register the section in `DASHBOARD_SECTIONS` in [`admin_customizations/views.py`](admin_customizations/views.py) (`title` Integrations, icon `fas fa-plug`, template `admin/dashboard/integrations.html`).
- Insert the Integrations button in the switcher immediately before Site.
- Add a matching section tile on the admin index ([`templates/admin/index.html`](templates/admin/index.html)), placed with the other section tiles and linking to the new overview. Headline lines: migrations in error, failed migration records, plus identity/LTI counts only when those flags are on.

## Overview metrics

Add `stats["integrations"]` from `calculate_statistics` in [`admin_customizations/admin.py`](admin_customizations/admin.py) and bump `DASHBOARD_STATS_CACHE_KEY` so cached payloads pick up the new key.

Reuse the migration status groups already built in [`admin_customizations/processing_stats.py`](admin_customizations/processing_stats.py) (`migrations` and `migration_records`: pending/running/paused/success/error/aborted and success/failed/skipped). Render them with the same small-box loop as [`templates/admin/dashboard/_processing.html`](templates/admin/dashboard/_processing.html). Leave those groups on the Processing overview.

Add count cards (label, count, icon, changelist URL), shown only when the matching sidebar flag is on, following the Site object-total cards in [`templates/admin/dashboard/_site.html`](templates/admin/dashboard/_site.html):

- `USE_IDENTITY_PROVIDERS`: social apps, social accounts, login options, active login options, identity-provider user logs, logs in the last 7 days.
- `USE_SAML`: SAML configurations.
- `USE_LTI`: platforms, resource links, user mappings, role mappings, tool keys, launch logs, successful launches, failed launches, launches in the last 7 days.

New page: `templates/admin/dashboard/integrations.html` extending `section_base.html`, plus `_integrations.html`. New user-facing strings go in [`files/frontend_translations/en.py`](files/frontend_translations/en.py) first, then `process_translations` fills the other language files. Reuse strings that already exist (`Migrations`, `Pending`, `Social accounts` only if present).

## Tests

- [`tests/admin/test_admin_sidebar.py`](tests/admin/test_admin_sidebar.py): group order becomes `moderation`, `library`, `processing`, `people`, `integrations`, `site`, and integrations starts with `IntegrationsOverview`.
- [`tests/admin/test_admin_dashboard_stats.py`](tests/admin/test_admin_dashboard_stats.py): `/admin/dashboard/integrations/` returns 200, shows migration status labels, and the index and switcher include the integrations URL before Site. With identity/LTI/SAML flags on, the page includes those object labels and filtered changelist links.
