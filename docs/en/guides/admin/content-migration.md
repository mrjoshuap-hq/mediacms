# Content migration

Use this page to import media from another platform into MediaCMS. Supported sources are Kaltura, YouTube, Panopto, and a filesystem library that is mounted on the server.

!!! warning
    Content migration is not a site upgrade. Content migration imports media from **another platform**. A site upgrade moves an **existing MediaCMS install** to a new MediaCMS version. For a site upgrade, read [Site upgrade](site-upgrade.md).

Only a superuser can use content migration. The entry point is **Migrations** in the top right menu.

## Pages and URLs

| Page | URL |
|------|-----|
| List of migrations | `/migrations` |
| Choose a source | `/migrations/new` |
| New migration for one source | `/migrations/new/<source>` where `<source>` is `kaltura`, `youtube`, `panopto`, or `filesystem` |
| One migration | `/migrations/<id>` |
| Edit a migration | `/migrations/<id>/edit` |
| REST API | `/api/v1/migrations` |

The source of a saved migration cannot change. To use another source, create a new migration.

## Compare the sources

| | Kaltura | YouTube | Panopto | Filesystem library |
|--|---------|---------|---------|--------------------|
| Needs | App token (service URL, partner ID, token ID, token value) | `yt-dlp`. Cookies on servers | API client and a local service account with admin rights | A directory bound under `FILESYSTEM_IMPORT_ROOT` on the web and Celery containers |
| What you give it | Categories to migrate | Video, playlist, or channel URLs | Folders to migrate | One mount, and optionally a folder inside it |
| Owners | Accounts are created or matched | One MediaCMS user owns all media | Accounts are created or matched | One MediaCMS user owns all media. You must choose it |
| Captions | WebVTT, optional | English only, if the uploader gave one | If Panopto offers a caption file | Sidecar `.vtt` and `.srt` files beside the media file |
| Reuse of existing encodings | Yes, with **Migrate media flavors / encodings** | Yes, with **Attempt to skip transcoding** | No. One mp4 per recording. MediaCMS encodes | No. MediaCMS encodes, unless `DO_NOT_TRANSCODE_VIDEO` is on |
| RBAC groups | Yes, with `USE_RBAC` | No | Yes, with `USE_RBAC` | No |

## Run a migration

1. Open `/migrations`.
2. Select **New migration**.
3. Select the source.
4. Enter the connection values for the source.
5. Select **Test connection**. This reads counts and loads the choices. It imports nothing.
6. Select the categories, folders, or URLs to migrate.
7. Set the options.
8. Select **Save draft** or **Save and start**. Nothing is imported until you start.
9. Open `/migrations/<id>`. Watch the progress, the live log, and the ID mapping table.

Credentials are encrypted at rest. The API never returns a secret. **Test connection** makes the server contact the address in the form. For this reason only a superuser can use it.

## Before you start

1. Back up the database and the `media_files` directory.
2. Check the active encode profiles at `/admin/files/encodeprofile/`. They decide which encodings can be attached.
3. Check the settings that change the result:

| Setting | Why it matters |
|---------|----------------|
| `USE_RBAC` | Without it, private categories have no groups. Media still arrives private |
| `USE_LTI` | Needed to wire LMS courses to an LTI platform (Kaltura and Panopto) |
| `PORTAL_WORKFLOW` and `MEDIA_IS_REVIEWED` | See the listing rules in [Library and engagement](library.md) |
| `MIGRATION_PAGE_SIZE`, `MIGRATION_API_TIMEOUT`, `MIGRATION_DOWNLOAD_TIMEOUT`, `MIGRATION_MAX_RETRIES` | Tune a large run |

## Control a running migration

| Button | Result |
|--------|--------|
| **Pause** | Stops after the items in progress. Keeps the position |
| **Resume** | Continues from the saved position |
| **Abort** | Stops for good. Keeps what was imported. You can still restart it |
| **Run again** | Sweeps the source once more on a finished migration |

Nothing is imported twice. MediaCMS stores a record for each imported object. A repeat run skips records that succeeded. It retries records that failed. It also picks up new items at the source.

Migration statuses: `pending`, `running`, `paused`, `success`, `error`, `aborted`. Record statuses: `success`, `failed`, `skipped`.

For Kaltura, **Do not run between** holds a run inside a window of hours. The time zone is the portal time zone. A page in progress is finished first.

### If a migration is stuck in running

1. Open the list. Read **Last activity**.
2. If the time is old, a worker may have stopped.
3. Select **Pause**.
4. Select **Resume**.

Replaying a page is safe. Each importer checks the mapping table before it writes.

## Kaltura

- Create an app token with `sessionType=2` (admin rights). A long `expiry` stops the token from ending a long run.
- Enter **Service URL**, **Partner ID**, **App token ID**, and **App token value**. Do not add `/api_v3` to the service URL.
- Select at least one top-level category. Each top-level category is one site. Media that is only in other top-level categories is not migrated. Media in no category is migrated and arrives private.
- Choose one user option: **Migrate all users**, **Only migrate below listed users**, or **Only migrate users that own media**.
- Check the **Global role mapping** tab before you start. **Super user and staff** creates a Django superuser. A role is applied only to accounts that the migration creates.
- Visibility comes from the categories of the entry. An entry in no category is private.

Kaltura groups can become RBAC groups with **Migrate groups**. A group gives no access until you attach it to a category.

## YouTube

- Install `yt-dlp` with `pip install -r requirements.txt`. Update it with `pip install -U yt-dlp` when extraction fails.
- Enter one URL, playlist, channel, or video ID on each line.
- Select the **Owner**. All media belongs to this one user.
- From a server, YouTube can show a bot check. Paste a cookies file into **Cookies file contents**. Export it from a separate browser profile. Do not use that profile again.
- YouTube never serves the original file. MediaCMS imports the best rendition that YouTube gives.

!!! note
    Download only video that you own or that the licence allows.

## Panopto

- Create an API client of type **User-Based Server Application**.
- Create a local Panopto service account with admin rights. SSO-only accounts do not work.
- Select the folders to migrate. **My Folder** and **Remote Recorders** do not become categories.
- Check **downloads** in the **Test connection** result first. If downloads are off, there is no file to import.
- A public folder becomes a plain category. Other folders become RBAC categories when `USE_RBAC` is on.
- Folders for LMS assignments become no category. Each submission stays with its student.

## Filesystem library

Use **Filesystem library** when the media files already sit on a disk that the server can read, for example a NAS share or an archive drive. The migration is a **library sync**. You run it again whenever the library changes.

!!! note
    The library is scanned only. It is never published by nginx. Viewers always see the opaque MediaCMS path `/media/original/<aa>/<bb>/<uid>/source.<ext>`. The mount name, folder names, and original file names never appear in a public URL.

### Mount the library

1. Bind your library as one or more child directories of `FILESYSTEM_IMPORT_ROOT` (default `/external-media_files`). Each child directory is one **mount**.
2. Add the same bind to the `web` and the `celery_worker` containers. The worker reads the files.

    ```yaml
    services:
      web:
        volumes:
          - /srv/archive-a:/external-media_files/archive-a:ro
      celery_worker:
        volumes:
          - /srv/archive-a:/external-media_files/archive-a:ro
    ```

3. Restart the containers. Open `/migrations/new/filesystem`. **Library mount** lists the directories under the import root.

A read-only bind (`:ro`) works for both storage modes. Hard links in **Copy into MediaCMS storage** mode need the library and `MEDIA_ROOT` on the same file system. Otherwise MediaCMS copies the file.

### Set up the migration

| Field | Required | Effect |
|-------|----------|--------|
| **Library mount** | Yes | One directory under the import root. You cannot type a path |
| **Folder inside the mount** | No | Limits the sync to one folder. A path with `..` is refused |
| **Owner** | Yes | The existing MediaCMS user who owns every imported item. The field starts empty. MediaCMS does not choose an owner for you, and **Save draft** and **Save and start migration** stay off until you pick one |
| **Storage mode** | Yes | **Copy into MediaCMS storage** (`ingest`, default) or **Keep files on external mount** (`preserve`) |
| **Create categories from folders** | No | Each folder that holds media becomes a category |
| **Import captions** | No | Sidecar `.vtt` and `.srt` files become subtitles. `name.vtt` is English. `name.fr.vtt` is French |
| **Ignore patterns** | No | Globs, one for each line, matched against file names and mount-relative paths. Hidden files and system folders are always skipped |
| **Maximum items per run** | No | Stops after this many items. Use it for a trial run |

If the server refuses a value, the message shows under **Connection** or **Import options**. The server checks that the mount is under the import root, that the owner exists, and that the storage mode is valid.

Storage modes:

| Mode | The original file | When to use it |
|------|-------------------|----------------|
| **Copy into MediaCMS storage** | Hard-linked into `MEDIA_ROOT`, or copied when a link is not possible | You may move or unmount the library later |
| **Keep files on external mount** | MediaCMS stores a symbolic link to the file. The bytes stay on the mount | The library is large and must stay where it is |

!!! warning
    In **Keep files on external mount** mode the mount must stay at the same location for as long as the media exists. A move or an unmount breaks playback of the original. Deleting the media removes only the link. It never deletes the file on the mount.

In both modes MediaCMS writes encodings, HLS, thumbnails, and subtitles under `MEDIA_ROOT`. Video is encoded as usual. Only `DO_NOT_TRANSCODE_VIDEO` turns encoding off.

### Run the sync again

Select **Run again** on `/migrations/<id>` or in the list. Each run does the following:

1. Scans the mount, or the folder you chose.
2. Imports files that are new.
3. Skips files that are already imported. MediaCMS does not create a second media item. A file that is imported again after you delete its media in MediaCMS becomes a new media item.
4. Checks every earlier import whose file is no longer on the mount, and applies the prune rule.

The prune rule:

| The file is gone and the media | Result |
|--------------------------------|--------|
| Has no playable encoding | The media is deleted. A later run imports the file again if it comes back |
| Has at least one playable encoding | The media is kept and stays playable. It is counted as **Original gone** |

A media item is never deleted only because the file is gone, when it has encodings. If the mount is unreadable, or holds no media although earlier imports came from it, MediaCMS stops the prune step and does nothing. This protects you from an unmounted drive.

`/migrations/<id>` shows **Items migrated**, **Skipped**, **Errors**, **Pruned**, and **Original gone**. The list at `/migrations` adds `pruned` and `original gone` to the progress line.

The audit log of each media item records `fs_imported`, `fs_original_gone`, and `fs_pruned` actions. Content changes at the same path are not detected. MediaCMS does not encode the file again.

## After the run

1. Open `/migrations/<id>`. Check the counts for each object type.
2. Open **Integrations** > **Migration records**. Filter by status `failed`.
3. Search users for `email-conflict.invalid`. See [People](people.md).
4. Run **Run again** to retry failed items.
5. Open **Site** > **Health**. Check the migration checks.

## MediaCMS Architecture

A migration is a Celery job. It reads from the source, writes records, and creates media, users, and categories.

```mermaid
flowchart LR
    superuser["Superuser at /migrations"] --> service["Migration service"]
    service --> provider{"Provider"}
    provider --> kaltura["Kaltura API"]
    provider --> youtube["yt-dlp for YouTube"]
    provider --> panopto["Panopto REST and SOAP"]
    provider --> filesystem["Filesystem library under FILESYSTEM_IMPORT_ROOT"]
    service --> celery["Celery worker"]
    celery --> records[("Migration records")]
    celery --> media[("Media and files")]
    celery --> users[("Users and RBAC groups")]
    celery --> categories[("Categories and playlists")]
    media --> encoding["Encoding or reuse of source encodings"]
    adminPortal["Admin portal Integrations"] --> records
```
