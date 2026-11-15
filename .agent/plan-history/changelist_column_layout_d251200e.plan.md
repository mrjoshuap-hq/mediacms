---
name: Changelist column layout
overview: "Tighten every admin changelist: sortable columns show an up/down hint until they are the active sort, icon columns stay centered, and rows that have a public page get an eye link. Then fix the specific title, tag, comment, trim, and caption layouts."
todos:
  - id: sort-and-icons
    content: Add inactive-column fa-sort hints and center icon, boolean, and eye columns in the shared changelist template and CSS
    status: completed
  - id: open-on-site
    content: Add an open-on-site helper and column for models with a public page, or the related media page
    status: completed
  - id: column-widths
    content: Make title or comment text the flexible column on media, channels, playlists, and comments; pack the other columns tight
    status: completed
  - id: tag-pairs
    content: Render the tag changelist as two title/user records per row
    status: completed
  - id: request-icons
    content: Use centered status icons for trim request and caption request columns
    status: completed
  - id: column-chooser
    content: Collapse column choosers by default and open them when any optional column is checked
    status: completed
  - id: tests-browser
    content: Update admin tests and check the affected changelists in the browser
    status: completed
isProject: false
---

# Changelist column layout

Shared changelist chrome lives in [templates/admin/change_list_results.html](templates/admin/change_list_results.html) and [static/jazzmin/css/main.css](static/jazzmin/css/main.css). Column content is built in [files/admin.py](files/admin.py), [users/admin.py](users/admin.py), and [actions/admin.py](actions/admin.py), with HTML helpers in [files/admin_helpers.py](files/admin_helpers.py).

## All changelists

**Sort hint.** In [templates/admin/change_list_results.html](templates/admin/change_list_results.html), sortable headers that are not the active sort get a `fa-sort` up/down icon beside the title (inside the sort link). The active column keeps the existing direction icon and clear control, and does not show `fa-sort`. Unsorted columns stay one-click sorts via the existing `single_sort_url` filter.

**Icon columns centered.** Extend the changelist CSS so cells that contain `.changelist-status-icon` or `.open-on-site`, plus their `th.column-*` headers, are centered, narrow, and nowrap. Header labels in those columns use `justify-content: center` (the current flex header ignores `text-align`). Same treatment for boolean icon cells (`is_active`, `is_rbac_category`, `is_lms_course`, and the media checkbox columns).

**Open on site.** Add `admin_open_on_site_link()` in [files/admin_helpers.py](files/admin_helpers.py) using the dashboard eye (`fas fa-eye`, class `open-on-site`, new tab, existing “Open on site” string). An `OpenOnSiteMixin` appends a non-sortable `open_on_site` column. Admins that already override `get_list_display` append it on the way out.

Link target, most specific page available:

- Media, category, tag, page, playlist, channel, user: `get_absolute_url()` (watch page, `?c=`, `?t=`, page, playlist, channel, profile).
- Encoding, subtitle, trim request, caption request, media permission, media action: the related media watch page. Subtitle’s own URL is the subtitle editor, so it is not used here.
- Comment: no separate column. The eye goes in the text cell (below). Comments only resolve to the media page; there is no per-comment address on the site.
- Encode profiles, languages, licenses, and auth/RBAC/LTI/migration admins have no public page, so they get no column.

## Channels and playlists

Column order is already add date, title, user. In [static/jazzmin/css/main.css](static/jazzmin/css/main.css), keep `table-layout: fixed`. Title stays the flexible column. User grows from the current 7rem cap to about 12rem with ellipsis, so a username still fits. Token, media count, and the eye stay `width: 1%` and nowrap.

## Tags

Default columns are title and user, so one full-width table looks empty. A tag-only branch in the results template pairs each page of rows into one visual row: checkbox, title, user, optional media count, eye, then the same cells for the next tag. The second header copy does not repeat the select-all checkbox id. An odd last tag leaves the right half empty. Bulk-action checkboxes stay in the same table and form. CSS splits the two title columns across the width and keeps user, count, and eye shrink-wrapped.

## Media

Title stays directly after add date and is the only flexible column. Every other visible column (type, state, encoding, listable, optional user/duration/flags/counts, eye) is `width: 1%`, nowrap, and packed to the right. Icon and checkbox cells stay centered.

## Comments

Text is the flexible column; date, media, and user shrink to content so the text column is clearly longer. `display_text` becomes a flex row: clipped comment text, then an eye to `Comment.get_absolute_url()` (the media page) when the comment has media.

## Trim requests and caption requests

Replace plain choice text with `admin_status_icon`, centered like the media status columns.

Trim status: initial `fa-hourglass-start`, running `fa-spinner`, success `fa-check-circle`, fail `fa-times-circle`.

Trim action: replace `fa-exchange-alt`, save as new `fa-copy`, create segments `fa-cut`.

Trim style: no encoding `fa-bolt`, precise `fa-crosshairs`.

Caption status reuses the encoding status icons. Translate-to-English becomes an icon: `fa-language` when on, muted `fa-minus` when off. Hover text stays the translated choice label.

## Column choosers

Every optional-column chooser (media, categories, tags, playlists, channels, users, encodings, media actions) stays collapsed. The “Columns” summary is always visible. The checkbox body opens when the user expands it, and it is open on load when any optional column is checked (including a column a filter forced on). Use one shared `<details>` include so the eight changelist templates stay in sync. The chooser form stays outside `#changelist-form`.

## Tests and check

Update exact `get_list_display` assertions in [tests/admin/test_admin_files.py](tests/admin/test_admin_files.py) for the new column. The existing sort test counts `fa-sort-alpha-`, so the hint must use `fa-sort` and that count stays valid. Add coverage for paired tag rows, an eye href on media (and one related-media row), the comment-text eye, and trim/caption icon classes.

No new translatable strings: the eye reuses “Open on site”, and icon labels reuse choice displays.

After implementation, open the media, tag, channel, playlist, comment, trim, and caption changelists in the admin and confirm column widths, the sort hint, centering, and the eye links.
