---
name: merge-hygiene
description: Safely merge or sync branches into mediacms-next while preserving fork work and avoiding local_settings commits. Use when merging FIX branches, syncing outdated PRs, resolving conflicts into mediacms-next, or unstaging deploy/docker/local_settings.py.
---

# Merge hygiene

## Instructions

1. **Never commit** `deploy/docker/local_settings.py`. Stash or unstage it before commit/merge; restore locally afterward.
2. Prefer a three-dot audit of the incoming branch vs `mediacms-next` before merging; note hotspots (admin, logging, docs, tests, translations).
3. On conflicts, **preserve both sides** when features coexist; re-adapt rather than dropping fork or incoming work blindly.
4. After merge / preview-host changes, verify `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` (often in local settings — still don’t commit them).
5. Post-merge gate:
   - `pre-commit run --all-files`
   - `TESTING=True` pytest for affected areas
   - Docs / `fork-whats-new` if user-facing behavior changed (skill `fork-docs-release`)
6. Do not force-push shared branches unless the user explicitly requests it.

## Additional resources

- Root `AGENTS.md` (hard rules)
- Skill `fork-docs-release` for docs/release conflicts
- Skill `test-ci` for verification commands
- `deploy/docker/local_settings.py` (local only)
