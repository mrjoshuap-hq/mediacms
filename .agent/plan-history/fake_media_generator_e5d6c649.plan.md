---
name: Fake media generator
overview: Extend only `populate_fake_media.py` so demo data includes captions/chapters from the existing sample VTT assets, realistic MediaPermission share patterns across users, and two CMS Pages — without touching other application code.
todos:
  - id: captions-chapters
    content: Add Language seed + Subtitle attach from sample VTTs + VideoChapterData from sample-chapters.vtt for eligible videos
    status: completed
  - id: permissions
    content: Add MediaPermission share patterns with overlapping collaborator pools
    status: completed
  - id: pages
    content: get_or_create about + faq Page records with HTML descriptions
    status: completed
  - id: wire-summary
    content: Call new steps from handle() and extend display_summary counts
    status: completed
isProject: false
---

# Enhance fake media generator

## Scope

Change only [`files/management/commands/populate_fake_media.py`](files/management/commands/populate_fake_media.py). No model, API, frontend, or fixture binary changes.

Wire new steps into `handle()` after media/comments creation and before `post_process` / `display_summary`, and extend the summary counts.

## 1. Captions + chapters on video media

**Source assets** (already in repo):

- [`frontend-tools/video-js/public/sample-subtitles.vtt`](frontend-tools/video-js/public/sample-subtitles.vtt) (English)
- [`frontend-tools/video-js/public/sample-subtitles-greek.vtt`](frontend-tools/video-js/public/sample-subtitles-greek.vtt) (Greek)
- [`frontend-tools/video-js/public/sample-chapters.vtt`](frontend-tools/video-js/public/sample-chapters.vtt) (chapter cues; production stores JSON, not VTT)

**Captions**

- Ensure `Language` rows via `get_or_create`: `en`/`English`, `el`/`Greek`.
- From created media with `media_type == 'video'` and `encoding_status == 'success'`, attach captions to ~25–35% of them:
  - Always attach English from `sample-subtitles.vtt`.
  - On ~half of those, also attach Greek from `sample-subtitles-greek.vtt`.
- Create `Subtitle` like the tests do: open the VTT path, `subtitle_file.save(..., File(...), save=False)`, set `media`/`user`/`language`, then `save()`.

**Chapters**

- MediaCMS serves chapters via `VideoChapterData.data` as a list of `{startTime, endTime, chapterTitle}` (see [`files/models/video_data.py`](files/models/video_data.py) / `handle_video_chapters`).
- Parse `sample-chapters.vtt` once into that JSON shape (string timestamps as in the VTT, e.g. `"00:00:05.000"`), then `VideoChapterData.objects.create(media=..., data=...)` for ~40% of the captioned videos (overlap is useful for the dashboard).
- After attaching chapters, bump those videos’ `duration` to at least `45` so chapter end times stay within the fake duration.

There is no hard fixture↔oceans pairing in the repo; treating successful videos as the eligible set is the practical “as appropriate” rule.

## 2. Robust media permissions

Add `create_media_permissions(created_media, users)` that builds **named, overlapping share patterns** with shared collaborator pools so the same users appear together often:

Reuse a small “collaborator pool” of 4–6 non-owner users per media owner when possible.

| Pattern | Share of eligible media | What gets created |
|---|---|---|
| Shared private (viewers) | ~20% of private | Owner-self `owner` row (shared marker) + 2–4 `viewer` grants |
| Editor collaboration | ~15% of private/unlisted | Owner-self `owner` + 1 `editor` + 1–2 `viewer` |
| Co-owner | ~8% of any state | Owner-self `owner` + 1 other user as `owner` |
| Public collab | ~10% of public | Owner-self `owner` + 1–2 `editor` |
| Owner-self only | ~5% of any | Only owner-self `owner` (shared UI without collaborators) |

Rules:

- Skip granting to the media owner as a non-self grantee.
- Respect `unique_together = (user, media)`.
- Prefer `source=MediaPermission.SOURCE_EXPLICIT`.
- Bias toward private media so viewer permissions are meaningful in the dashboard.

## 3. Create a couple of Pages

Add `create_pages()` using `Page.objects.get_or_create` for:

- `slug="about"`, title like “About”, short HTML `description`
- `slug="faq"`, title like “FAQ”, short HTML `description`

These match existing view/test conventions (`/about` special-case and [`tests/pages/test_pages_site.py`](tests/pages/test_pages_site.py)). Idempotent so re-runs / `--clear` (which only deletes `Media`) do not duplicate.

## 4. Wiring / summary

In `handle()`:

1. After comments: `create_subtitles_and_chapters(created_media)`
2. Then: `create_media_permissions(created_media, users)`
3. Then: `create_pages()`
4. Extend `display_summary` with subtitle count, chapter count, permission count, and page count

Imports to add from `files.models`: `Language`, `Subtitle`, `VideoChapterData`, `MediaPermission`, `Page`.

Resolve VTT paths via `settings.BASE_DIR / 'frontend-tools/video-js/public/...'`; if a file is missing, log a warning and skip that asset rather than failing the whole populate.

## Out of scope

- No changes to player, serializers, forms, migrations, or sample VTT contents
- No RBAC category shares, Whisper `TranscriptionRequest`, or new CLI flags unless needed later
- `--clear` remains media-only (permissions cascade; pages stay via `get_or_create`)
