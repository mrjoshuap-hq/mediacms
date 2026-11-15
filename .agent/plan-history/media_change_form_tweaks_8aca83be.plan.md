---
name: Media change form tweaks
overview: "Tighten the media change form: theme-capable tabs, image previews with click-or-drop replace at the top of Content, edit/inspect icons on object links, and a slimmer Reports tab."
todos:
  - id: tabs
    content: Theme-capable tab borders, hover, and selected state in main.css
    status: completed
  - id: images
    content: Move poster/thumbnail to the top of Content with preview and click-or-drop replace
    status: completed
  - id: links
    content: Edit or inspect icon on user, channel, and playlist object links
    status: completed
  - id: reports
    content: Reports table is action icon plus when; readonly aligned reported_times; drop duplicate related reports; playlist ul
    status: completed
  - id: tests
    content: Update media admin tests and run them
    status: completed
isProject: false
---

# Media change form tweaks

## Tabs
In [`static/jazzmin/css/main.css`](static/jazzmin/css/main.css), inactive change-form tabs currently have no border until hover, and only the active tab is outlined (`~2930`). Give every tab a visible border and surface background using `--mc-canvas`, `--mc-surface`, `--mc-on-surface`, and `--gray`. Hover strengthens that border and background. The selected tab keeps the canvas fill, drops the bottom border so it joins the panel, and uses a `--primary` accent. The Related tab keeps its info color, with the same border weight in both themes.

## Content images
In [`files/admin.py`](files/admin.py) `MediaAdmin.get_fieldsets`, move image fields to the top of Content, before title: resolved poster, resolved thumbnail, `uploaded_poster`, `uploaded_thumbnail`, `thumbnail_time`, then the existing text fields.

- Readonly previews use `poster_url` / `thumbnail_url` (uploaded image, otherwise the generated one) and render an `<img>` only when a URL exists.
- Replace Django’s “Currently: filename” file widget with a drop-zone widget for `uploaded_poster` and `uploaded_thumbnail`: current image, “Click or drop to replace”, and the real file input. The widget template goes in [`admin_customizations/templates/admin/widgets/`](admin_customizations/templates/admin/widgets/) so the form renderer picks it up. A small handler in [`static/jazzmin/js/change_form.js`](static/jazzmin/js/change_form.js) assigns dropped files to that input. Drop-zone colors use the same theme tokens.
- Generated `poster`, `thumbnail`, and `sprites` stay on the Media file tab as pipeline fields.

## Object links
Relationship links on this form that point at one object get one icon, not a second copy of the Related-tab “View N …” links.

- Add a helper next to `admin_change_link` in [`files/admin_helpers.py`](files/admin_helpers.py): pencil and “Edit” when the target admin allows change; search and “Inspect” when the user can only view. Both open that object’s admin page.
- Use it for `link_user`, `link_channel`, and each playlist item.
- Add `"Edit"` and `"Inspect"` to [`files/frontend_translations/en.py`](files/frontend_translations/en.py) and run `process_translations`.

## Reports and Related
In `report_actions_table`, keep only Action and When. Action is a theme icon with `title` / `aria-label` (flag, check, trash, and the existing status modifiers), linking to that MediaAction. Drop the user, extra info, IP, view button, and the “Open all MediaActions” header.

- Put `reported_times` in `readonly_fields`. Align that row in CSS so the label, number, and help text share one baseline (`4` then the help text), instead of the help block sitting in a detached column.
- Remove `related_reports` from the Related fieldset. That “View 4 report/moderation action(s) (reported_times=4)” line repeats the Reports tab.
- Render `related_playlists` as a `<ul>` of title links, with “+N more” after the list when the cap of 20 is exceeded.

## Tests
Update [`tests/admin/test_admin_files.py`](tests/admin/test_admin_files.py): Content field order, reports table columns and icon tooltips, `reported_times` readonly, `related_reports` absent from Related, playlist markup as a list. Run those media admin tests with `TESTING=True`.
