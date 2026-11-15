---
name: Dashboard section reorder
overview: Reorder the admin dashboard, strengthen Content Moderation and User Statistics (approval workflow without new audit logs), and trim/refocus Media Overview metrics.
todos:
  - id: stats-backend
    content: Update get_moderation/user/media statistics in admin_customizations/admin.py
    status: completed
  - id: template-reorder
    content: Reorder sections and refresh moderation/user/media tiles+tables in templates/admin/index.html
    status: completed
  - id: tests
    content: Add dashboard stats/index order tests
    status: completed
isProject: false
---

# Dashboard section reorder and metrics refresh

## Section order
In [`templates/admin/index.html`](templates/admin/index.html), reorder blocks to:

1. Content Moderation
2. User Statistics
3. Media Overview
4. Engagement Metrics
5. System & Infrastructure

(Keep any trailing app-list / recent-actions content after these.)

## Content Moderation (first)
In [`admin_customizations/admin.py`](admin_customizations/admin.py) `get_moderation_statistics`, add 7-day counts:

- `clears_last_7_days` — `MediaAction` `report_cleared`
- `confirms_last_7_days` — `report_confirmed`
- `approved_last_7_days` — `media_reviewed` (media marked reviewed)

Top tiles (two rows of three, `col-lg-4 col-6`), each with drill-down:

| Tile | Drill-down |
|------|------------|
| Reported Media | `files_media_changelist?reported=yes` |
| Above Threshold | `?reported=threshold` |
| Unreviewed Media | `?is_reviewed__exact=0` |
| Report Clears (7d) | `actions_mediaaction_changelist?action__exact=report_cleared` |
| Report Confirms (7d) | `?action__exact=report_confirmed` |
| Media Approved (7d) | `?action__exact=media_reviewed` |

Remove the current “Recent Reports (7d)” tile (clears/confirms/approved supersede it as workflow outcomes). Keep the existing 2×2 recent tables (Confirmations, Clears, Reviews, Top Reviewers).

## User Statistics (Option A — no audit log)
Always surface approval metrics when `USERS_NEEDS_TO_BE_APPROVED` is true (not only when pending &gt; 0):

- **Pending Approvals** → `users_user_changelist?is_approved__exact=0`
- **Approved Users** → `?is_approved__exact=1`

Keep Total Users + New Users (7d) as the other two top tiles when approval is on (drop Active Users from the top row in that mode to stay at four tiles). When approval is off, keep today’s Total / New (7d) / Active (30d) trio.

Add a **Recent Pending Users** table (last 5 by `date_added`, unapproved), 2-column layout with Top Uploaders beside it when approval is enabled; otherwise Top Uploaders full width as today. Leave commenter/reporter/liker/disliker tables as-is in 2-col pairs.

Stats updates in `get_user_statistics`:

- `pending_approvals` / `approved_users` when flag on
- `approval_workflow_enabled` boolean for the template
- `recent_pending_users` list of `{id, username, date_added}`

## Media Overview
Defaults from “all look great”: replace weak ops tiles with encoding-focused ones, and drop duration leaderboard.

Top tiles:

1. Total Media (unchanged)
2. Successfully Encoded (unchanged)
3. **Failed encodings** (replaces Needs Review) → `?encoding_status__exact=fail`
4. **Encoding queue** pending+running (replaces Uploaded 7d) → link to encoding status filters or changelist with `encoding_status__in` if supported; otherwise pending filter plus note that running is in the Encoding Status row

Add **Featured** count as a row in the existing Media by State card (`?featured__exact=1`). Public already lives there.

Remove:

- Needs Review tile + `needs_review` usage from this section
- Entire **Top Videos by Duration** block
- `longest_videos` / `format_duration` usage in media stats (delete `format_duration` if unused elsewhere)

## Files to change
- [`templates/admin/index.html`](templates/admin/index.html) — reorder sections; update moderation/user/media markup
- [`admin_customizations/admin.py`](admin_customizations/admin.py) — stats fields above

## Tests
Add focused coverage in a new `tests/admin/test_admin_dashboard_stats.py` (or extend existing admin tests):

- Moderation stats include 7d clears/confirms/approved counts
- User stats expose pending/approved/recent_pending when `USERS_NEEDS_TO_BE_APPROVED=True`
- Media stats expose `failed` / `encoding_queue` / `featured`; no `longest_videos`
- Admin index 200 and contains section headings in the new order (Content Moderation before User Statistics before Media Overview)
