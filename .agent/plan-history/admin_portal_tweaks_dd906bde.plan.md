---
name: Admin portal tweaks
overview: "Polish the admin moderation dashboard and related list UX: replace Top reviewers with Recent reports, deep-link Open buttons to the media Reports tab, normalize Actions/Go layout, add EncodeProfile inline toggles, and align remaining ModelAdmins that have custom actions with the grouped Actions dropdown standard."
todos:
  - id: moderation-recent-reports
    content: Replace Top reviewers with Recent reports (stats + index.html + translations + docs/tests)
    status: completed
  - id: reports-tab-links
    content: "Deep-link report/moderation Open + MediaAction media links to #reports-tab"
    status: completed
  - id: actions-go-css
    content: Override Jazzmin actions.html + CSS for consistent Actions/Go spacing
    status: completed
  - id: encodeprofile-list-editable
    content: Add EncodeProfileAdmin list_editable=('active',) + test
    status: completed
  - id: grouped-actions-gaps
    content: Wire GroupedActionForm on MediaActionAdmin + LTIToolKeysAdmin; Meta verbose names on MediaAction
    status: completed
isProject: false
---

# Admin portal enhancement tweaks

## 1. Moderation: remove Top reviewers, add Recent reports

In [`templates/admin/index.html`](templates/admin/index.html), replace the **Top reviewers** card (lines ~220–248) with a **Recent reports** card that mirrors the confirmed/cleared/reviews tables (Media / Reporter / When / Open).

In [`admin_customizations/admin.py`](admin_customizations/admin.py) `get_moderation_statistics()`:

- Remove `top_reviewers` query
- Add `recent_reports` = latest 5 `MediaAction` rows with `action='report'`, same `recent_moderation_values` shape as the other recent lists

Translations (mandatory workflow):

- Add `"Recent reports"` to [`files/frontend_translations/en.py`](files/frontend_translations/en.py)
- Run `python manage.py process_translations`

Update the dashboard map in [`docs/admins_docs.md`](docs/admins_docs.md) §7: drop Top Reviewers; document Recent reports → media change `#reports-tab`.

Update [`tests/admin/test_admin_dashboard_stats.py`](tests/admin/test_admin_dashboard_stats.py) / index assertions for the new card and absence of Top reviewers.

## 2. Open links → `#reports-tab`

Jazzmin slugifies the Media fieldset name `"Reports"` to `#reports-tab` (already defined in [`files/admin.py`](files/admin.py) `get_fieldsets`).

Append `#reports-tab` on media Open links that are report/moderation related:

- Dashboard: recent confirmed, cleared, reviews, and the new recent reports Open buttons in [`templates/admin/index.html`](templates/admin/index.html)
- [`actions/admin.py`](actions/admin.py) `MediaActionAdmin.link_media`: when `obj.action` is in `MEDIA_REPORT_TAB_ACTIONS`, link to the media change URL + `#reports-tab` (extend [`files/admin_helpers.py`](files/admin_helpers.py) `admin_change_link` / `admin_change_url` with an optional `fragment` arg)

Leave non-report Open links (recent uploads, engagement, etc.) as plain media change URLs.

## 3. Consistent Actions + Go layout on changelists

Root cause: Jazzmin’s packaged `actions.html` puts **inline** `margin-left/right` on Go, which fights the flex `gap` in [`static/jazzmin/css/main.css`](static/jazzmin/css/main.css) and collapses awkwardly when the select wraps.

Fix:

- Add local override [`templates/admin/actions.html`](templates/admin/actions.html) (copy Jazzmin markup, drop inline margins, add classes e.g. `changelist-actions-select` / `changelist-actions-go`)
- Tighten `#changelist .actions` CSS to match object-tools Actions: flex + `gap: 0.5rem`, select `flex: 1 1 auto; min-width: 16rem; max-width: 100%`, Go `flex: 0 0 auto` so Go stays beside or cleanly below with consistent spacing regardless of option label width

## 4. Encode profiles list toggles + Save

In [`files/admin.py`](files/admin.py) `EncodeProfileAdmin`, add:

```python
list_editable = ("active",)
```

(`active` already in `list_display`; Django will show the changelist Save button, same pattern as Media / LoginOption.)

Add a small assertion in existing admin tests if there is an EncodeProfile admin test hook; otherwise a one-liner in smoke/files admin tests.

## 5. Grouped Actions pattern gaps

Gold standard (already compliant): **MediaAdmin**, **EncodingAdmin**, **UserAdmin** — `GroupedActionForm` + `action_groups` + `get_action_choices` → placeholder **"Actions"** with hyphen separators.

### Audit finding

Only two ModelAdmins define custom bulk actions but still use Django’s default ActionForm:

| Admin | Custom action(s) | File |
|-------|------------------|------|
| **MediaActionAdmin** | `clear_reports_for_related_media` | [`actions/admin.py`](actions/admin.py) |
| **LTIToolKeysAdmin** | `regenerate_keys` | [`lti/admin.py`](lti/admin.py) |

All other ModelAdmins either already use the pattern or have no custom actions (delete-only). None of those zero-action admins are missing a reusable bulk helper already implemented elsewhere — existing helpers are domain-bound (media moderation/encoding, user approval, LTI keys) and already wired where they belong.

### Changes

**MediaActionAdmin** ([`actions/admin.py`](actions/admin.py)):

- `action_form = GroupedActionForm`
- `action_groups = [["clear_reports_for_related_media"], ["delete_selected"]]`
- `get_action_choices` via `build_grouped_action_choices`
- Set `MediaAction.Meta.verbose_name` / `verbose_name_plural` to `"Media action"` / `"Media actions"` in [`actions/models.py`](actions/models.py)
- Override `delete_selected` description to `"Delete selected media actions"` for title-case consistency (same approach as Media’s `"Delete selected media"`)

**LTIToolKeysAdmin** ([`lti/admin.py`](lti/admin.py)):

- Same wiring: `GroupedActionForm` + `action_groups = [["regenerate_keys"]]` (delete is disabled via `has_delete_permission`, so no delete group)
- Prefer `@admin.action(description=...)` style for `regenerate_keys` to match Media/Encoding (optional cleanup while touching the file)

## Out of scope

- No inventing new bulk actions on Comment/Category/Playlist/etc. — no shared helpers fit those models today
- No change to moderation small-box footer links (those correctly go to filtered changelists)
- No frontend rebuild (admin templates/CSS/translations only; Django template strings need `process_translations`, not `make build-frontend`)
