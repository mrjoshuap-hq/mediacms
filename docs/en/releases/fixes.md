# Fixes and known issues

Bug fixes shipped on the fork **10.0.0** lines, and risks that remain because the beta line moves fast. The full fix list is on [What's new](../reference/whats-new.md).

!!! danger "A fix on beta is not a guarantee on your pin"
    Confirm the image digest or stamp tag includes the fix. `:beta` moves on every push. Yesterday's good build can differ from today's tag of the same name.

## Shipped fixes (fork vs typical ≤v9 pain)

| Fix | Upstream ≤v9 | Fork 10 | Notes |
|-----|--------------|---------|-------|
| Role / ACL / frontend `can.*` alignment | Partial | Yes | Can feel like a regression if you relied on old editor or pending write paths |
| Mike docs via GitHub Pages Actions path | No / broken path | Yes | Docs deploy reliability |
| German translation corrections (#1622) | Partial | Yes | i18n |
| Default template context keys (avoid AttributeError floods) | Partial | Yes | Log noise reduction |
| Skip model log handlers on fixture/raw loads | Partial | Yes | Admin DB restore not interrupted |
| Sidebar Home icon with trailing slash on `/` | Partial | Yes | UI |
| Desktop chapters overlay opens on click (#1453) | Partial | Yes | Player |
| SMTP failures surfaced on contact forms | Partial | Yes | Operators see mail errors |
| Review multipart `result="false"` + listable sync (#1275/#1280) | Partial | Yes | Review workflow |

## Access changes that look like bugs

These are intentional. Operators often report them as regressions after upgrade.

| Symptom after upgrade | Likely cause | What to do |
|-----------------------|--------------|------------|
| Editor cannot open Manage users | Managers-only Manage users | Promote the account or accept the new role split; see [Permission access changes](../guides/admin/permissions-changes.md) |
| Pending user cannot comment or like | Pending write lockdown | Approve the user, or keep browse-only pending |
| Co-editor cannot change media `state` via API | State change restricted to owner-level / portal editor | Use publish flows or owner access |
| Upload / comment buttons missing | UI flags now match server policy | Check `CAN_ADD_MEDIA`, `CAN_COMMENT`, pending, advancedUser |
| Like / dislike / report refused by API | Settings now enforced server-side | Check `CAN_LIKE_MEDIA`, `CAN_DISLIKE_MEDIA`, `CAN_REPORT_MEDIA` |

## Known risks on a fast line

| Risk | Upstream ≤v9 | Fork 10 stable | Fork 10 beta | Mitigation |
|------|--------------|----------------|--------------|------------|
| Daily API / admin UI churn | Low | Low–medium | **High** | Pin stamp tags; read [What's new](../reference/whats-new.md) each upgrade |
| Incomplete customization playground APIs | N/A | Partial | **High** | Do not build production on unfinished surfaces |
| Permission surprises after ACL alignment | Medium if customized | Medium | Medium | Dry-run on a copy; review Manage users and pending accounts |
| Missing frontend rebuild after image update | Low | Medium | Medium | Follow [Frontend](frontend.md) and [Upgrade tips](upgrade-tips.md) |
| Migration / path field changes (password, sharded paths) | N/A | Medium | Medium | Run migrations; inventory with `upgrade_site` |
| Old media stays on legacy paths until **Migrate paths** | N/A | Medium | Medium | Both layouts are served. Run **Migrate paths** from the **Manage pages** when you are ready. A failed item keeps its old layout |
| Filesystem library in **Keep files on external mount** mode | N/A | Medium | Medium | Keep the mount at the same location. A move or unmount breaks playback of the original. Use **Copy into MediaCMS storage** if the library may move |
| Docker build on **arm64** (Apple Silicon): amd64 FFmpeg / Bento4 | Medium | Medium | Medium | See [amd64 media tools in the image](#amd64-media-tools-in-the-image) |

## amd64 media tools in the image

The Dockerfile does not download a fresh FFmpeg each build. It **copies** `ffmpeg`, `ffprobe`, and `qt-faststart` from a pinned upstream image (`mediacms/mediacms:7.2.0@sha256:…`). That donor is a frozen **linux/amd64** source of binaries, not the app version you run. Bento4 is still the upstream **x86_64** SDK zip.

On an **arm64** host (Apple Silicon), `make docker-build` may show BuildKit:

```text
WARN: InvalidBaseImagePlatform: Base image mediacms/mediacms:7.2.0@sha256:…
```

| What you see | What it means |
|--------------|---------------|
| The warning | Your build platform is arm64; the FFmpeg donor (and Bento4 zip) are amd64 |
| Build still finishes | Docker often emulates amd64 steps; the image can still tag successfully |
| Slow or flaky encode / HLS | amd64 binaries under QEMU/Rosetta, or a Bento4 binary that cannot run natively |

Mitigations:

- Prefer **linux/amd64** builders or encoding workers for production-like encode/HLS testing.
- Point `FFMPEG_COMMAND`, `FFPROBE_COMMAND`, and `MP4HLS_COMMAND` at native binaries when you have them. See [Processing](../guides/admin/processing.md).
- HLS tests that need a working `mp4hls` **skip** when the binary is unusable (for example broken Rosetta under Docker Desktop). See [Tests](../guides/developer/tests.md).

This is independent of Compose image names (`mediacms:local`, GHCR tags). Changing `MEDIACMS_IMAGE` does not change how FFmpeg is copied into a local Dockerfile build.

## How to report and help

1. Note the exact image tag or commit from [This version](../reference/this-version.md).
2. Say whether you run **stable** or **beta**.
3. Prefer a reproducible path (role + URL + expected vs actual).
4. Expect the beta branch to change quickly after a fix lands.

## Related pages

- [Compare lines](compare.md)
- [Upgrade tips](upgrade-tips.md)
- [Permission access changes](../guides/admin/permissions-changes.md)
- [Local development](../guides/developer/local-dev.md)
- [Install with Docker](../getting-started/install.md#local-images-vs-registry-images)
