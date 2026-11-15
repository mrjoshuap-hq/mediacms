---
name: plan-history
description: Archive MediaCMS Cursor plans into .agent/plan-history with INDEX.md and manifest.json. Use when creating or updating a plan, finishing plan implementation, syncing plan history, or when the user mentions plan archive, plan history, or .agent/plan-history.
---

# Plan history archival

## When (required)

Archive after any of these for **this** MediaCMS repo:

1. A new Cursor plan is written or saved under `~/.cursor/plans/`
2. An existing plan is substantially revised (scope, todos, or overview change)
3. Plan implementation is completed or abandoned (final snapshot)
4. The user asks to sync / refresh plan history

Skip non-MediaCMS plans (other products, homelab, unrelated repos).

## Where

| Path | Role |
| ---- | ---- |
| `~/.cursor/plans/*.plan.md` | Live Cursor plans (source) |
| `.agent/plan-history/*.plan.md` | Project archive (copies) |
| `.agent/plan-history/INDEX.md` | Human catalog |
| `.agent/plan-history/manifest.json` | Machine-readable metadata |

Preserve the original filename (e.g. `rbac_permissions_audit_ef026657.plan.md`).

## How

1. Identify the plan file in `~/.cursor/plans/` (newest matching MediaCMS plan if unclear).
2. Copy into `.agent/plan-history/` (overwrite same filename with the latest snapshot).
3. Refresh the catalog:

```bash
python3 skills/plan-history/scripts/refresh_index.py
```

4. Briefly confirm archival in the reply (filename + that INDEX was refreshed). Do not commit unless the user asks.

## MediaCMS check

Treat as MediaCMS if any of:

- Filename or body mentions `mediacms` / this repo path
- Touches MediaCMS paths (`admin_customizations/`, `files/`, `frontend/`, `cms/`, `docs/en/`, …)
- Continues work already represented in `.agent/plan-history/`

If unsure, ask before copying.

## Anti-patterns

- Ending a plan-only or plan→implement session without an archive copy
- Rewriting INDEX/manifest by hand when the refresh script exists
- Archiving unrelated `~/.cursor/plans/` files into this repo
- Deleting live plans from `~/.cursor/plans/` as part of archival (copy only)
