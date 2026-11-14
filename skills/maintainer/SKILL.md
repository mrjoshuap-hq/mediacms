---
name: maintainer
description: Fork-only maintainer rules for branch targets, upstream pull requests, authorship, demos, labels, and AI disclosure. Use when opening or writing a GitHub issue, comment, pull request, review, release note, or upstream draft, or when a fork process rule and AGENTS.md could disagree.
---

# Maintainer

Fork-only supplement for Joshua's rules on `mrjoshuap/mediacms`. It may add or narrow rules. It must not contradict upstream rules for anything sent upstream, `AGENTS.md`, or a domain skill. On a conflict, stop, leave the authoritative file unchanged, and open an issue. The full precedence list is in `AGENTS.md` under "Supplements and precedence".

`skills/github-orchestration` (issue #8) does not exist yet. When it lands, it must reference the AI disclosure rule below. Do not create that skill from this one.

## Fork and upstream branches

Fork flow (D1): topic branch, then a pull request into `mediacms-next`, then a pull request from `mediacms-next` into `main`. Open fork work against `mediacms-next`. `main` is the default branch and the promotion line. It is not the first base, and it is not an upstream mirror.

Upstream work uses a different base:

- Branch from upstream `mediacms-io/mediacms` `main`, not from fork `main`.
- Keep the change set as small as the task allows.
- Open the pull request on `mediacms-io/mediacms`.
- Track it on the fork with an `upstream: pr-open` issue.

When upstream `main` moves, one `upstream: sync` issue covers that event: merge upstream `main` into `mediacms-next` through a pull request, then rebase or merge open upstream PR branches. Fork `main` picks the result up on the next promotion. Merges into `mediacms-next` follow skill `merge-hygiene`.

Title fork pull requests with a Conventional Commit type (`AGENTS.md`). Include `Closes #N` when the PR closes an issue. Run `pre-commit` and `TESTING=True` pytest for product changes. Do not commit `deploy/docker/local_settings.py`. Do not force-push a shared branch unless Joshua explicitly requests it.

## Upstream pull requests

The upstream template sections live in `.github/pull_request_template.md` (mediacms-io/mediacms#1640). Roadmap issue #1 keeps that file free of fork-only wording, so the footer stays in this skill. Do not edit the template to embed it. On this branch the file is one trailing blank line short of upstream `main`; leave that for a sync, and do not treat a blank-line fix as permission to add fork text.

When an agent fills a pull request description:

- Leave every checkbox under **AI assistance disclosure** and **Attestation** unticked. Joshua fills those. Agents never tick them.
- You may fill the `Tool(s) and what they did` line with what the tools actually did.
- End the description with the AI disclosure footer below.
- The same rule applies to an upstream PR: Joshua still ticks disclosure and attestation. An agent does not post the PR, or a comment, on `mediacms-io/mediacms`.

Issue templates under `.github/ISSUE_TEMPLATE/` have a separate human **AI disclosure** checkbox (the reporter confirms the facts). Leave that checkbox unticked as well.

## AI disclosure

Every agent-produced GitHub artifact ends with the footer. That includes issues, issue comments, pull request comments, pull request descriptions, code reviews, release notes, and upstream comment drafts.

Default footer (last line of the artifact):

`_AI disclosure: drafted by an AI agent (<agent name>) for @mrjoshuap._`

An upstream draft that Joshua has actually reviewed uses this footer instead:

`_AI disclosure: drafted by an AI agent (<agent name>) for @mrjoshuap. Reviewed by @mrjoshuap._`

Do not add "Reviewed by" unless Joshua reviewed that draft. Replace `<agent name>` with the agent's name, for example `Grok Bot`.

Agent-authored commits add an `Assisted-by:` trailer as the last line of the commit message, for example `Assisted-by: Cursor agent (Grok Bot Docs/DevRel)`. The trailer names the agent that wrote the change.

Release notes an agent writes (a release issue, a release-note comment, or a hand-written GitHub Release body) get the footer. Do not put the footer in `docs/_shared/fork-whats-new.md`, generated what's-new pages, `CHANGELOG.md`, or the `INSTALL-*.md` asset `release.yml` publishes. Those are reader-facing docs. `AGENTS.md` already forbids hand-editing `CHANGELOG.md`.

## Commits, signing, and authorship

- Follow Conventional Commits from `AGENTS.md`. Do not bump `package.json` or hand-edit `CHANGELOG.md`.
- Agent-authored commits use the agent's own git identity. Do not set the author or committer to Josh Preston or `mrjoshuap@users.noreply.github.com`.
- Do not claim a commit is signed. Do not forge a signature and do not use Joshua's key. If signing is required and the agent cannot sign, stop and ask Joshua.
- Do not rewrite published history so that an agent commit looks like Joshua's. Decision D4 keeps Joshua's `AGENTS.md` history intact; the same restraint applies to the rest of the branch.
- Do not present an address, including the noreply GitHub address, as a mailbox someone can reach.

## Ask Joshua

Stop and ask Joshua before doing any of the following. On an issue, add `triage: needs-joshua`.

- Implementing an issue that is not labeled `agent: ok`.
- Adding `agent: ok` outside decision D7. D7 allows that label only for `type: docs`, `area: demos`, and `area: test-ci`. If Joshua has already applied `agent: ok`, that issue may be implemented.
- Ticking an AI disclosure or Attestation checkbox.
- Opening a pull request or posting a comment on `mediacms-io/mediacms`. Draft the text on the fork and let Joshua post it.
- Force-pushing a shared branch, deleting a branch, or merging a pull request.
- Changing `USERS_NEEDS_TO_BE_APPROVED` or any other setting on a shared instance (D8).
- Splitting an upstream pull request, or retiring the default `bug`, `enhancement`, or `documentation` labels.
- A data-changing demo recording.
- A conflict between this skill and `AGENTS.md` or a domain skill.
- Any commit authored as Joshua, or any use of his signing key.

`agent: plan-only` means plan only. Skill `issue-triage` still applies: do not commit or open a pull request unless the task asks for that.

## Demo recordings

- Read-only by default. Do not change data, settings, or users on a shared instance unless Joshua has approved that recording.
- Record the full commit SHA the recording was made against, and put that SHA in the upload description.
- Do not claim that email was sent or received, and do not put an email address in the narration, description, or upload.
- v1 recordings stay deleted (D6). New recordings wait until the scripts live in doc scenarios. Mark a missing recording with a named placeholder rather than filming early.
- `area: demos` has no `skills/demos`. Demo rules live in this skill.

## Labels

Issue #3 will add `.github/labels.yml` as the source of truth. Until that file is on the branch, use the labels already on the repo. Do not invent a label that is not listed here. Do not delete or rename `bug`, `enhancement`, or `documentation`; Joshua retires those later.

**Type** (Conventional Commits): `type: bug` (`fix`), `type: feature` (`feat`), `type: docs` (`docs`), `type: chore` (`chore`), `type: refactor` (`refactor`), `type: test` (`test`), `type: ci` (`ci`), `type: perf` (`perf`). `AGENTS.md` also allows commit types `style` and `depr`. There is no matching `type:` label for those. Do not invent one.

**Area** (load the matching skill): `area: admin-portal`, `area: auth-identity`, `area: i18n`, `area: media-pipeline`, `area: rbac-permissions`, `area: test-ci`, `area: dev-stack`, `area: dev-api`, `area: dev-manage`, `area: fork-docs-release`, `area: frontend`, `area: demos`.

`area: frontend` says it maps to `skills/frontend`. That skill is not in the tree. Use `.cursor/rules/frontend.mdc` and skill `i18n` for new strings. Do not create `skills/frontend` from this skill.

**Flow:** `triage: needs-triage`, `triage: needs-repro`, `triage: needs-joshua`, `triage: ready`, `blocked`.

**Upstream:** `upstream: pr-open`, `upstream: candidate`, `upstream: sync`, `fork-only`.

**Agent:** `agent: ok` (unattended implementation is allowed), `agent: plan-only`.

**Keep:** `duplicate`, `wontfix`, `invalid`, `question`, `good first issue`, `help wanted`.

Triage flow:

1. A new issue gets `triage: needs-triage` and Project Status `Inbox`.
2. Skill `issue-triage` confirms it still applies on the target branch, then adds `type:` and `area:` labels, plus Priority, Size, Workstream, and a short plan.
3. A decision goes to `triage: needs-joshua`. Otherwise `triage: ready`, and `agent: ok` only when D7 or Joshua's existing label allows it.
4. Use a GitHub **Blocked by** link when the blocker is another issue. Use the `blocked` label only when the blocker is outside GitHub.

## Project

Issue #5 creates the user-level Project **MediaCMS fork roadmap**. Use these values when the field exists. If a field is missing, do not invent a substitute.

- **Status:** Inbox, Triage, Ready, In progress, In review, Upstream review, Blocked, Done.
- **Workstream:** WS0, WS1, WS2, WS3, WS4, WS5, WS6.
- **Priority:** P0, P1, P2, P3.
- **Size:** XS, S, M, L, XL.
- **Target:** beta, stable, upstream.
- **Upstream PR:** text.
- **Start** and **Target** dates.

Parent and child work uses sub-issues. Cross-stream order uses **Blocked by** / **Blocking**. Built-in workflows auto-add fork issues and pull requests, set Status to Done on close, and set In review when a pull request links. Do not duplicate those workflows by hand.

Moving Status, writing the weekly digest, and the day-to-day issue mechanics belong to `skills/github-orchestration` (issue #8), which must reference the disclosure rule when it is added.

Milestones in use: `M0 Orchestration bootstrap`, `M1 Agent guidance aligned`, `M2 PR 1457 merge-ready`, `M3 Admin demo series v2`, `M4 Fork 10.0.0 stable`, `Backlog: upstream queue` (no due date).

## Additional resources

- `AGENTS.md` (precedence, hard rules, change impact)
- `.github/pull_request_template.md` (upstream disclosure and attestation; Joshua ticks the boxes)
- `.github/ISSUE_TEMPLATE/` (human disclosure checkbox; agents leave it unticked and add the footer)
- Skill `issue-triage`, skill `merge-hygiene`, skill `fork-docs-release`
- Issues #1 (precedence, D1–D8), #3 (labels), #5 (Project), #7 (this skill), #8 (github-orchestration, not created here)
