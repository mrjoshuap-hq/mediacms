# Features

Significant capabilities on the fork **10.0.0** lines relative to **upstream ≤v9**. The full bullet list lives on [What's new](../reference/whats-new.md). This page groups what operators and early adopters usually care about.

!!! warning "Beta can be ahead of stable"
    Features often land on `mediacms-next` / `:beta` first. A stamped `:stable` build may lag. Confirm the image tag and [This version](../reference/this-version.md) for the build you run.

## Admin portal rethink

| Feature | Upstream ≤v9 | Fork 10 | Why it matters |
|---------|--------------|---------|----------------|
| Workflow sidebar groups | No | Yes | Staff navigate by Moderation, Library, Processing, People, Integrations, Site |
| Overview dashboards + **Refresh stats** | No | Yes | Cached portal statistics without ad-hoc SQL |
| Site Health / Configuration / System / Database | No | Yes | One place for health, settings visibility, and DB tools |
| Backup download and restore upload | No | Yes | Superuser recovery path (still back up outside the app) |
| Get Support redacted bundle | No | Yes | Safer support hand-offs |
| Library and Engagement overviews | No | Yes | Content and interaction signals |
| Grouped Actions and richer changelists | No | Yes | Faster bulk and object work |
| Navbar language chooser | No | Yes | Admin UI language switch |

See [Admin portal map](../guides/admin/portal-map.md) and the admin guides under [Guides → Admin](../guides/admin/index.md).

## Roles and access consistency

| Feature | Upstream ≤v9 | Fork 10 | Why it matters |
|---------|--------------|---------|----------------|
| ACL aligned with roles / permissions docs | Partial | Yes | Product behavior matches published role pages |
| Manage users for managers only | Partial | Yes | Editors keep media/comment manage paths |
| Pending write lockdown | Partial | Yes | Pending accounts browse; they do not write |
| Co-owner / RBAC manager delete | Partial | Yes | Delete matches share and category manager rules |
| Frontend permission flags match API | Partial | Yes | Buttons hide when the server would refuse |

This is a capability **and** a breaking change. Read [Permission access changes](../guides/admin/permissions-changes.md).

## Media and playback

| Feature | Upstream ≤v9 | Fork 10 | Why it matters |
|---------|--------------|---------|----------------|
| Password-protected media + unlock API | No | Yes | Session unlock: `POST /api/v1/media/{token}/unlock` |
| Lazy playlist membership API | No | Yes | Faster Save popup |
| Soft-nav next/prev in player | No | Yes | Fullscreen and autoplay continue across items |
| Upload title/description on create | Partial | Yes | Less post-upload edit |
| CJK-aware search | No | Yes | Better East Asian query matching |
| Incremental HLS packaging | Partial | Yes | Redis lock; optional full rebuild |
| Encoding chunk cleanup | No | Yes | Orphan chunk retention setting |

## Media paths and filesystem library

| Feature | Upstream ≤v9 | Fork 10 | Why it matters |
|---------|--------------|---------|----------------|
| Sharded paths for new files (`original/<aa>/<bb>/<uid>/source.<ext>`) | No | Yes | No username or client file name in a public URL. Small directories at large scale |
| Legacy paths still served | N/A | Yes | Nothing moves on update |
| **Migrate paths** on **Manage media** (single and bulk) | No | Yes | Managers move old media to the new layout. Old files are deleted only after every check passes |
| **Filesystem library** source in content migration | No | Yes | Import media that already sits on a mounted disk |
| Re-runnable library sync (**Run again**) | No | Yes | Skips imported files. Prunes media only when the file is gone and the media has no playable encoding |
| `ingest` and `preserve` storage modes | No | Yes | Copy into MediaCMS storage, or keep the bytes on the external mount |
| Audit actions `fs_imported`, `fs_original_gone`, `fs_pruned`, `path_migrated` | No | Yes | Moderation audit trail for sync and path moves |

See [Manage media](../guides/operator/manage-media.md#move-media-to-the-sharded-path-layout) and [Content migration](../guides/admin/content-migration.md#filesystem-library).

## Site upgrade and integrity

| Feature | Upstream ≤v9 | Fork 10 | Why it matters |
|---------|--------------|---------|----------------|
| `upgrade_site` inventory / scratch / apply | No | Yes | Safer move between versions |
| `UpgradeDecision` model | No | Yes | Records apply answers |
| Media / metadata integrity checks | No | Yes | Site Health and Library signals |
| MediaAction indexing / moderation audit | Partial | Yes | Stronger moderation audit trail |

## Documentation and delivery

| Feature | Upstream ≤v9 | Fork 10 | Why it matters |
|---------|--------------|---------|----------------|
| MkDocs Material docs (roles, guides, scenarios) | No | Yes | Same-origin `/documentation/` |
| Auto-generated reference pages | No | Yes | This version, What's new, API stubs |
| mike channels (`dev` / `beta` / `latest`) | No | Yes | Versioned docs on GitHub Pages |
| GHCR `:beta` / `:stable` / stamp tags | No | Yes | Pinable fork images |
| Combined PR / issue test bed | No | Yes (esp. beta) | Early adopters steer the line |

## Customization playground (direction)

| Feature | Upstream ≤v9 | Fork 10 stable | Fork 10 beta |
|---------|--------------|----------------|--------------|
| Trial headers, banners, ad tracking, page mods without code edits | No | Partial | Beta-first |

Treat unfinished playground surfaces as experimental. Prefer settings and documented admin tools until a feature appears on [What's new](../reference/whats-new.md) without a beta-only caveat.

## Related pages

- [Compare lines](compare.md)
- [Upgrade tips](upgrade-tips.md)
- [What's new](../reference/whats-new.md)
