---
name: Release v10.0.0 promotion
overview: "Promote mediacms-next to main for the first fork stable release v10.0.0.YYYYMMDD: draft cited release notes, open the promotion PR, and hand merge, tag date, and tag to Joshua."
todos:
  - id: verify-state
    content: Re-verify mediacms-next vs main, tags, CI, branch protection, merge conflicts
    status: completed
  - id: draft-notes
    content: Draft docs/en/releases/v10.0.0.md with citations; fix migrations.md gaps (users.0003, actions.0004)
    status: completed
  - id: notes-pr
    content: Open docs(releases) PR into mediacms-next with notes + this plan in .agent/plan-history
    status: completed
  - id: journal-pr
    content: Open bot-journal PR with this plan, notes copy, and citation list
    status: completed
  - id: promotion-pr
    content: Open chore(release) PR mediacms-next -> main with release-approval and triage needs-joshua labels
    status: completed
  - id: joshua-merge-notes
    content: Joshua (or Engineering Lead if clean and green) merges the notes PR into mediacms-next
    status: pending
  - id: joshua-promote
    content: Joshua reviews and merges the promotion PR with a merge commit (no squash, no rebase)
    status: pending
  - id: joshua-tag
    content: Joshua picks an unused YYYYMMDD[.N] stamp and pushes the stable tag on main
    status: pending
  - id: post-release
    content: Verify the Release run, GHCR :stable images, and docs; final plan snapshot
    status: pending
isProject: false
---

# Release v10.0.0 promotion (mediacms-next -> main)

- Owner: Release Engineering (Grok Bot) for @mrjoshuap. Times are ET.
- Snapshot: 2026-11-14, 7:30 PM ET.
- Rules: `AGENTS.md` and skills `fork-docs-release`, `maintainer`, `merge-hygiene`, `plan-history` on `mediacms-next`; `engineering/RULES.md` in bot-journal (sections 4, 5, 6, 8, 11).
- Tracking: milestone `M4 Fork 10.0.0 stable`, issues #23 (epic), #24 (stable tags on main), #26 (first stable cut checklist, `agent: plan-only`).

## Links

- Notes PR into `mediacms-next`: https://github.com/mrjoshuap/mediacms/pull/84
- Promotion PR `mediacms-next` -> `main`: https://github.com/mrjoshuap/mediacms/pull/85 (labels `release-approval`, `triage: needs-joshua`)
- Journal PR: https://github.com/mrjoshuap/bot-journal/pull/5

## Scope

- Promote all of `mediacms-next` to `main`. At the snapshot, `mediacms-next` (`7eb9447`) is 115 commits ahead of `main` (`e25fb95`) and 0 behind. A merge has no conflicts (`main` is an ancestor of `mediacms-next`).
- Add draft stable release notes at `docs/en/releases/v10.0.0.md` (MkDocs nav under Releases) and a citation list.
- Fix two gaps in `docs/en/releases/migrations.md`: `users.0003_remove_user_media_count` and `actions.0004` were missing.
- Out of scope for agents: merging to `main`, tags, GitHub Releases, upstream, branch deletion, the dev instance, PR template disclosure and attestation boxes.

## How the stable pipeline works (from release.yml)

1. A tag push matching `v*.*.*.*` starts `.github/workflows/release.yml`.
2. The `context` job continues only when the tag commit is on `main` (`MEDIACMS_STABLE_BRANCH=main`) and the tag matches `^v\d+\.\d+\.\d+\.\d{8}(\.\d+)?$`.
3. `scripts/release_version.py --channel stable` checks that the tag base equals `version/FORK_VERSION` (`10.0.0`).
4. pre-commit, Python tests, and the frontend build run again.
5. `docker-build-push.yml` pushes `ghcr.io/mrjoshuap/mediacms:{stable,10.0.0.YYYYMMDD[.N],sha-<7>,upgrade-audit}` and `ghcr.io/mrjoshuap/mediacms-full:{stable,10.0.0.YYYYMMDD[.N],sha-<7>}`. `MEDIACMS_GHCR_OWNER` is not set, so the owner is `mrjoshuap`.
6. The `publish` job creates a GitHub Release (not a pre-release). The body is `INSTALL-stable.md` plus GitHub generated notes. **The workflow does not read curated notes from a file.** To use the curated notes, edit the Release after it is created.
7. `docs.yml` deploys mike docs: a push to `main` updates the `dev` alias, a tag updates `latest`.

## Steps

1. Release Engineering (done): verify state, draft notes and citations, open the notes PR (into `mediacms-next`), the journal PR, and the promotion PR (labels `release-approval`, `triage: needs-joshua`).
2. Review and merge the notes PR into `mediacms-next`. This push starts a beta Release and mints a beta tag for the current UTC date. The promotion PR picks up the commit on its own.
3. Wait for CI and Release on the new `mediacms-next` head to go green. Optional: smoke `ghcr.io/mrjoshuap/mediacms:beta` first (#26 checklist).
4. Joshua merges the promotion PR with **Create a merge commit**. Do not squash or rebase: that rewrites 115 commits, breaks the beta tags' ancestry and the commit links in the notes, and makes the next promotion conflict.
5. Joshua picks the stamp. Check that no beta tag already uses it:
   ```bash
   git fetch --tags origin
   git tag --list 'v10.0.0.YYYYMMDD*'
   ```
   If the date is taken, use the next free `.N` (for example `v10.0.0.20261115.2`).
6. Joshua tags the merge commit on `main` and pushes the tag with his own credentials (a tag pushed by `GITHUB_TOKEN` does not start workflows):
   ```bash
   git fetch origin main
   git tag -a v10.0.0.YYYYMMDD -m "MediaCMS fork v10.0.0.YYYYMMDD (stable)" origin/main
   git push origin v10.0.0.YYYYMMDD
   ```
7. Check the Release run, the `:stable` images, and the docs `latest` alias.
8. Optional: add the curated notes to the Release body (keep the generated install section):
   `gh release edit v10.0.0.YYYYMMDD --notes-file <file>`. Keep the AI disclosure footer (skill `maintainer`).
9. Optional: merge `main` back into `mediacms-next` by PR so `mediacms-next` is 0 behind again (only the merge commit differs).
10. Release Engineering writes the final plan snapshot in both places.

## What Joshua must do

- Review and merge (or approve) the notes PR.
- Review the promotion PR. Tick the disclosure and attestation boxes yourself if you want them filled. Merge with a merge commit.
- Pick the tag date (`YYYYMMDD`, plus `.N` if a beta tag already uses that date) and push the stable tag on `main`.
- Decide whether to protect `main` (it has no branch protection and no required checks today).

## Risks

- **Migrations.** 10 new migrations (`actions` 0004-0007, `files` 0021-0024, `migrationservice` 0002, `users` 0003). `users.0003` drops `User.media_count`; a backward migrate does not restore it. Back up first. Escalation item under RULES section 6 (database migrations).
- **Breaking changes.** Compose default image changed to `${MEDIACMS_IMAGE:-mediacms:local}` (operators must set `MEDIACMS_IMAGE` or build). Permission ACL alignment changes who can do what. Sharded media paths need extra nginx location blocks for custom configs.
- **Beta tags not on main.** All five existing `v*.*.*.*` tags are beta pre-releases on `mediacms-next` commits (`v10.0.0.20261115.1` on `7eb9447` was added at 7:37 PM ET). After a merge commit, the `v10.0.0.*` beta tags become ancestors of `main`, but they stay pre-releases. No tag push happens on merge, so no stable run starts by accident.
- **Tag namespace collision.** Beta and stable share `v10.0.0.YYYYMMDD[.N]`. Beta pushes take the UTC date first. The stable tag must use a free name (step 5). The two `v1.2.3.*` tags are pipeline test runs from before the 10.0.0 bump.
- **CI history.** The `CI` workflow on `mediacms-next` was cancelled on `f349fa8` and `eeb71d6` (superseded pushes). It is green on `7eb9447`. Watch for a repeat (RULES section 6).
- **No branch protection on main.** Nothing blocks a direct push or a squash merge. The `Release` stable path re-runs the tests, so a red tree does not publish images.
- **Semantic-release.** After the merge, `main` uses the gated `semantic-release.yaml`. It stays off while `MEDIACMS_ENABLE_SEMANTIC_RELEASE` is unset. Do not set it.
- **Docs drift.** `docs/en/releases/index.md` writes "`:stable` (and `:full`)"; the full image is `ghcr.io/mrjoshuap/mediacms-full:stable`. Follow-up docs fix.

---
_AI disclosure: drafted by an AI agent (Grok Bot, Release Engineering) for @mrjoshuap._
