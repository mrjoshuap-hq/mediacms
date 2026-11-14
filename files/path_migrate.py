"""Gated move of one media's files from the legacy layout to the sharded layout.

Legacy files (original/user/<username>/..., encoded/<profile>/<username>/..., thumbnails and
subtitles keyed by username, hls/<uid>/...) stay where they are until an operator runs this
migration. It is fail closed and never deletes the old files until the new ones are proven:

1. gate     (`can_migrate_media_paths`): every referenced path must exist and be readable,
            no encode may be running, and no destination may be in the way.
2. stage    hard link (else copy) every file to its sharded destination. Symlinks (preserve
            imports) are recreated with the same target, never copied through. Old paths are
            left untouched.
3. verify   size + blake2b checksum for files, readlink/samefile for symlinks, a matching
            counterpart for every entry of an HLS/chapters tree. Any miss scrubs only what
            was staged and leaves the database and old layout as they were.
4. cutover  update the database (queryset updates, no model signals) in one transaction and
            drop the xaccel caches.
5. re-verify through the new database paths. A miss restores the old names, scrubs only the
            new files, and does not touch the old ones.
6. remove   the legacy paths that nothing else references. Symlinks are unlinked, never
            followed, so an archive a "preserve" import points at is untouched.
7. audit    `path_migrated` MediaAction.

Running it again on a migrated media is a no-op ("skipped").
"""

import hashlib
import logging
import os
import shutil
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q

from . import helpers
from .methods import record_moderation_action
from .models import Category, Encoding, Media, Subtitle, Tag
from .models.utils import (
    encoding_media_file_path,
    media_uid_dir,
    media_uid_shard_path,
    subtitles_file_path,
)

logger = logging.getLogger(__name__)

STATUS_MIGRATED = "migrated"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"

ALREADY_SHARDED_REASON = "already on the sharded layout"

# Media FileFields whose file is moved. Their destination is whatever the field's own
# upload_to helper returns, so the layout cannot drift from what new uploads get.
MEDIA_FILE_FIELDS = ("media_file", "poster", "uploaded_poster", "thumbnail", "uploaded_thumbnail", "sprites")
LISTING_THUMBNAIL_FIELDS = ("thumbnail", "uploaded_thumbnail")

DIGEST_CHUNK_SIZE = 1024 * 1024
LOCK_TIMEOUT_SECONDS = 4 * 60 * 60
AUDIT_SUMMARY_LENGTH = 500


class PathMigrationError(Exception):
    """A gate or verification failure. The message is the operator facing reason."""


@dataclass
class Artifact:
    """One file (or one HLS/chapters tree) that moves from `old` to `new` (absolute paths)"""

    kind: str
    ref: tuple
    old: str
    new: str
    tree: bool = False
    link_target: Optional[str] = None


@dataclass
class Cutover:
    """The database names to switch: {key: (old, new)}"""

    media_fields: dict = field(default_factory=dict)
    encodings: dict = field(default_factory=dict)
    subtitles: dict = field(default_factory=dict)
    hls_file: Optional[tuple] = None
    preview: Optional[tuple] = None
    listing_urls: dict = field(default_factory=dict)

    @property
    def empty(self):
        return not (self.media_fields or self.encodings or self.subtitles or self.hls_file or self.preview)


@dataclass
class Plan:
    media: Media
    artifacts: list
    cutover: Cutover

    @property
    def already_sharded(self):
        return not self.artifacts and self.cutover.empty


@dataclass
class Staged:
    """What staging created, so a failure can remove exactly that and nothing else"""

    files: list = field(default_factory=list)
    dirs: list = field(default_factory=list)


@dataclass
class PathMigrationResult:
    status: str
    reason: str = ""
    moved: int = 0
    removed: int = 0

    @property
    def ok(self):
        return self.status in (STATUS_MIGRATED, STATUS_SKIPPED)

    def as_dict(self):
        return {"status": self.status, "reason": self.reason, "moved": self.moved, "removed": self.removed}


# --------------------------------------------------------------------------- paths


def _media_root():
    return os.path.normpath(settings.MEDIA_ROOT)


def _abs(name):
    """Absolute path of a MEDIA_ROOT relative stored name; refuses anything outside"""
    path = os.path.normpath(os.path.join(_media_root(), name))
    if not path.startswith(os.path.join(_media_root(), "")):
        raise PathMigrationError(f"path outside MEDIA_ROOT: {name}")
    return path


def _rel(path):
    return os.path.relpath(path, _media_root())


def _link_target(path):
    """Absolute target of a symlink, or None when path is not one.

    A relative target is resolved against the link's own directory so the recreated link
    (which lives in a different directory) points at the same file.
    """
    if not os.path.islink(path):
        return None
    target = os.readlink(path)
    if not os.path.isabs(target):
        target = os.path.join(os.path.dirname(path), target)
    return os.path.normpath(target)


def _check_readable(label, path, tree=False):
    if os.path.islink(path):
        if not os.path.exists(path):
            raise PathMigrationError(f"{label}: symlink target is missing ({_rel(path)})")
        if tree or not os.path.isfile(path):
            raise PathMigrationError(f"{label}: unsupported symlink ({_rel(path)})")
        if not os.access(path, os.R_OK):
            raise PathMigrationError(f"{label}: symlink target is not readable ({_rel(path)})")
        return
    if tree:
        if not os.path.isdir(path):
            raise PathMigrationError(f"{label}: directory missing on disk ({_rel(path)})")
        if not os.access(path, os.R_OK | os.X_OK):
            raise PathMigrationError(f"{label}: directory is not readable ({_rel(path)})")
        return
    if not os.path.isfile(path):
        raise PathMigrationError(f"{label}: file missing on disk ({_rel(path)})")
    if not os.access(path, os.R_OK):
        raise PathMigrationError(f"{label}: file is not readable ({_rel(path)})")


def _already_staged(artifact):
    """A destination left by an earlier interrupted run: the very same file or link"""
    if artifact.link_target:
        return _link_target(artifact.new) == artifact.link_target
    if os.path.islink(artifact.new) or not os.path.isfile(artifact.new):
        return False
    return os.path.samestat(os.stat(artifact.old), os.stat(artifact.new))


def _check_destination(artifact):
    if not os.path.lexists(artifact.new):
        return
    if artifact.tree:
        if os.path.isdir(artifact.new) and not os.path.islink(artifact.new) and not os.listdir(artifact.new):
            return
    elif _already_staged(artifact):
        return
    raise PathMigrationError(f"{artifact.kind}: destination already exists ({_rel(artifact.new)})")


# --------------------------------------------------------------------------- plan / gate


def _build_plan(media):
    """Collect every on-disk reference of a media and where it must go.

    Raises PathMigrationError for the first thing that makes the media ineligible.
    """
    artifacts = []
    cutover = Cutover()
    destinations = {}

    def add_file(kind, ref, old_name, new_name):
        old = _abs(old_name)
        new = _abs(new_name)
        _check_readable(kind, old)
        if new in destinations:
            raise PathMigrationError(f"{kind}: destination collides with {destinations[new]} ({_rel(new)})")
        destinations[new] = kind
        if old == new:
            return old, new
        artifact = Artifact(kind=kind, ref=ref, old=old, new=new, link_target=_link_target(old))
        _check_destination(artifact)
        artifacts.append(artifact)
        return old, new

    if media.encoding_status == "running":
        raise PathMigrationError("encoding is running")
    if _hls_locked(media):
        raise PathMigrationError("HLS packaging is in progress")

    if not media.media_file:
        raise PathMigrationError("media_file: no original file recorded")

    for name in MEDIA_FILE_FIELDS:
        file_field = getattr(media, name)
        if not file_field:
            continue
        old_name = file_field.name
        new_name = Media._meta.get_field(name).upload_to(media, os.path.basename(old_name))
        old, new = add_file(name, ("media", name), old_name, new_name)
        if old != new:
            cutover.media_fields[name] = (old_name, new_name)
            if name in LISTING_THUMBNAIL_FIELDS:
                cutover.listing_urls[helpers.url_from_path(old)] = helpers.url_from_path(new)

    encoding_paths = {}
    for encoding in media.encodings.select_related("profile", "media").order_by("id"):
        if encoding.status in ("pending", "running"):
            raise PathMigrationError(f"encoding {encoding.id} is {encoding.status}")
        if not encoding.media_file:
            continue
        old_name = encoding.media_file.name
        if encoding.status == "fail" and not os.path.lexists(_abs(old_name)):
            continue
        basename = os.path.basename(old_name)
        chunk_prefix = f"{encoding.profile.id}.chunk."
        if encoding.chunk and basename.startswith(chunk_prefix):
            basename = basename[len(chunk_prefix) :]  # the helper adds it back: keep this idempotent
        new_name = encoding_media_file_path(encoding, basename)
        old, new = add_file("encoding", ("encoding", encoding.pk), old_name, new_name)
        encoding_paths[old] = new
        if old != new:
            cutover.encodings[encoding.pk] = (old_name, new_name)

    if media.preview_file_path:
        preview = os.path.normpath(media.preview_file_path)
        if preview not in encoding_paths:
            raise PathMigrationError("preview_file_path does not match any encoding file")
        if encoding_paths[preview] != preview:
            cutover.preview = (media.preview_file_path, encoding_paths[preview])

    for subtitle in media.subtitles.select_related("language", "media").order_by("id"):
        if not subtitle.subtitle_file:
            continue
        old_name = subtitle.subtitle_file.name
        new_name = subtitles_file_path(subtitle, os.path.basename(old_name))
        old, new = add_file("subtitle", ("subtitle", subtitle.pk), old_name, new_name)
        if old != new:
            cutover.subtitles[subtitle.pk] = (old_name, new_name)

    _plan_hls(media, artifacts, cutover, destinations)
    _plan_chapters(media, artifacts)

    return Plan(media=media, artifacts=artifacts, cutover=cutover)


def _plan_hls(media, artifacts, cutover, destinations):
    if not media.hls_file:
        return
    master = os.path.normpath(media.hls_file)
    source_dir = os.path.dirname(master)
    target_dir = os.path.normpath(media_uid_dir("hls", media.uid))
    legacy_dir = os.path.normpath(os.path.join(settings.HLS_DIR, media.uid.hex))
    if not os.path.isfile(master) or not os.access(master, os.R_OK):
        raise PathMigrationError(f"hls: master playlist missing or unreadable ({_rel(master)})")
    if source_dir == target_dir:
        return
    if source_dir != legacy_dir:
        raise PathMigrationError(f"hls: unexpected HLS directory ({source_dir})")
    _check_readable("hls", source_dir, tree=True)
    artifact = Artifact(kind="hls", ref=("hls", None), old=source_dir, new=target_dir, tree=True)
    _check_destination(artifact)
    artifacts.append(artifact)
    cutover.hls_file = (media.hls_file, os.path.join(target_dir, os.path.relpath(master, source_dir)))


def _plan_chapters(media, artifacts):
    """Chapter assets are not in the database: the folder name is derived from the media"""
    legacy = os.path.normpath(media.legacy_video_chapters_folder)
    target = os.path.normpath(media.video_chapters_folder)
    if legacy == target or os.path.islink(legacy) or not os.path.isdir(legacy):
        return
    _check_readable("chapters", legacy, tree=True)
    artifact = Artifact(kind="chapters", ref=("chapters", None), old=legacy, new=target, tree=True)
    _check_destination(artifact)
    artifacts.append(artifact)


def _hls_locked(media):
    from .tasks import _hls_lock_key

    return bool(cache.get(_hls_lock_key(media.uid.hex)))


def _fresh_media(media):
    return Media.objects.select_related("user").get(pk=media.pk)


def can_migrate_media_paths(media):
    """Whether this media's files may be moved to the sharded layout now.

    Returns (eligible: bool, reason: str). reason is empty when eligible. A media that is
    already fully sharded is not eligible, with ALREADY_SHARDED_REASON.
    """
    try:
        plan = _build_plan(_fresh_media(media))
    except PathMigrationError as exc:
        return False, str(exc)
    except Media.DoesNotExist:
        return False, "media no longer exists"
    if plan.already_sharded:
        return False, ALREADY_SHARDED_REASON
    return True, ""


# --------------------------------------------------------------------------- stage


def _makedirs(path, staged):
    missing = []
    current = path
    while current and not os.path.isdir(current):
        missing.append(current)
        current = os.path.dirname(current)
    for directory in reversed(missing):
        try:
            os.mkdir(directory)
        except FileExistsError:
            continue
        staged.dirs.append(directory)


def _copy_file(artifact, staged):
    """Copy into a path that must not exist yet (exclusive create: never clobbers)"""
    try:
        destination = open(artifact.new, "xb")
    except FileExistsError:
        raise PathMigrationError(f"{artifact.kind}: destination appeared while staging ({_rel(artifact.new)})")
    with destination:
        staged.files.append(artifact.new)  # recorded once it exists, so a partial copy is scrubbed
        with open(artifact.old, "rb") as source:
            shutil.copyfileobj(source, destination, DIGEST_CHUNK_SIZE)
    shutil.copystat(artifact.old, artifact.new)


def _stage_file(artifact, staged):
    _makedirs(os.path.dirname(artifact.new), staged)
    if os.path.lexists(artifact.new):
        if _already_staged(artifact):
            return
        raise PathMigrationError(f"{artifact.kind}: destination already exists ({_rel(artifact.new)})")
    if artifact.link_target:
        try:
            os.symlink(artifact.link_target, artifact.new)
        except FileExistsError:
            raise PathMigrationError(f"{artifact.kind}: destination appeared while staging ({_rel(artifact.new)})")
        staged.files.append(artifact.new)
        return
    try:
        os.link(artifact.old, artifact.new)
    except FileExistsError:
        raise PathMigrationError(f"{artifact.kind}: destination appeared while staging ({_rel(artifact.new)})")
    except OSError:
        # cross-device, a filesystem without hard links, link count limit: copy instead
        _copy_file(artifact, staged)
    else:
        staged.files.append(artifact.new)


def _stage_tree(artifact, staged):
    _makedirs(artifact.new, staged)
    for root, dirs, files in os.walk(artifact.old, followlinks=False):
        relative = os.path.relpath(root, artifact.old)
        target_root = artifact.new if relative == "." else os.path.join(artifact.new, relative)
        for name in dirs:
            source = os.path.join(root, name)
            if os.path.islink(source):
                _stage_file(Artifact(artifact.kind, artifact.ref, source, os.path.join(target_root, name), link_target=_link_target(source)), staged)
            else:
                _makedirs(os.path.join(target_root, name), staged)
        for name in files:
            source = os.path.join(root, name)
            _stage_file(Artifact(artifact.kind, artifact.ref, source, os.path.join(target_root, name), link_target=_link_target(source)), staged)


def _stage(plan, staged):
    for artifact in plan.artifacts:
        if artifact.tree:
            _stage_tree(artifact, staged)
        else:
            _stage_file(artifact, staged)


def _scrub(staged):
    """Remove only what staging created. Old paths are never reachable from here."""
    for path in reversed(staged.files):
        if os.path.lexists(path):
            helpers.rm_file(path)
    for directory in reversed(staged.dirs):
        try:
            os.rmdir(directory)
        except OSError:
            pass


# --------------------------------------------------------------------------- verify


def _digest(path):
    checksum = hashlib.blake2b()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(DIGEST_CHUNK_SIZE), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def _verify_file(old, new, link_target):
    """The problem with a staged file/symlink, or None when it is a faithful copy"""
    if link_target:
        if not os.path.islink(new):
            return f"not a symlink ({_rel(new)})"
        if _link_target(new) != link_target:
            return f"symlink target differs ({_rel(new)})"
        if os.path.exists(old) and not os.path.samefile(old, new):
            return f"symlink does not resolve to the same file ({_rel(new)})"
        return None
    if os.path.islink(new) or not os.path.isfile(new):
        return f"missing or wrong type ({_rel(new)})"
    if os.path.getsize(old) != os.path.getsize(new):
        return f"size mismatch ({_rel(new)})"
    if os.path.samestat(os.stat(old), os.stat(new)):
        return None  # a hard link: the very same bytes
    if _digest(old) != _digest(new):
        return f"checksum mismatch ({_rel(new)})"
    return None


def _tree_entries(root):
    entries = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        relative = os.path.relpath(current, root)
        for name in dirs:
            path = os.path.join(current, name)
            key = os.path.normpath(os.path.join(relative, name))
            entries[key] = ("link", path) if os.path.islink(path) else ("dir", path)
        for name in files:
            path = os.path.join(current, name)
            key = os.path.normpath(os.path.join(relative, name))
            entries[key] = ("link", path) if os.path.islink(path) else ("file", path)
    return entries


def _verify_tree(old, new):
    if not os.path.isdir(new) or os.path.islink(new):
        return [f"missing or wrong type ({_rel(new)})"]
    old_entries = _tree_entries(old)
    new_entries = _tree_entries(new)
    problems = []
    for key in sorted(set(old_entries) - set(new_entries)):
        problems.append(f"missing {key} under {_rel(new)}")
    for key in sorted(set(new_entries) - set(old_entries)):
        problems.append(f"unexpected {key} under {_rel(new)}")
    for key in sorted(set(old_entries) & set(new_entries)):
        old_kind, old_path = old_entries[key]
        new_kind, new_path = new_entries[key]
        if old_kind != new_kind:
            problems.append(f"type differs for {key} under {_rel(new)}")
        elif old_kind in ("file", "link"):
            problem = _verify_file(old_path, new_path, _link_target(old_path))
            if problem:
                problems.append(problem)
    return problems


def _verify_artifact(artifact):
    if artifact.tree:
        return _verify_tree(artifact.old, artifact.new)
    problem = _verify_file(artifact.old, artifact.new, artifact.link_target)
    return [problem] if problem else []


def _verify_all(plan):
    problems = []
    for artifact in plan.artifacts:
        problems.extend(f"{artifact.kind}: {problem}" for problem in _verify_artifact(artifact))
    return problems


# --------------------------------------------------------------------------- database


def _swap(pairs, index):
    return {key: values[index] for key, values in pairs.items()}


def _apply_names(plan, index, expect_index=None):
    """Write the names at `index` (1 = new, 0 = old) of every cutover pair.

    With expect_index, first check the rows still hold the other side, so a media that
    changed while the files were being staged is never overwritten blindly.
    """
    cutover = plan.cutover
    media = plan.media
    with transaction.atomic():
        row = Media.objects.select_for_update().get(pk=media.pk)
        if expect_index is not None:
            if row.encoding_status == "running" or Encoding.objects.filter(media=row, status__in=("pending", "running")).exists():
                raise PathMigrationError("an encode started while paths were being migrated")
            for name, values in cutover.media_fields.items():
                if getattr(row, name).name != values[expect_index]:
                    raise PathMigrationError(f"{name} changed while paths were being migrated")
            if cutover.hls_file and row.hls_file != cutover.hls_file[expect_index]:
                raise PathMigrationError("hls_file changed while paths were being migrated")
            if cutover.preview and row.preview_file_path != cutover.preview[expect_index]:
                raise PathMigrationError("preview_file_path changed while paths were being migrated")
            for model, pairs, attr in ((Encoding, cutover.encodings, "media_file"), (Subtitle, cutover.subtitles, "subtitle_file")):
                current = {item.pk: getattr(item, attr).name for item in model.objects.select_for_update().filter(pk__in=list(pairs))}
                for pk, values in pairs.items():
                    if current.get(pk) != values[expect_index]:
                        raise PathMigrationError(f"{model.__name__.lower()} {pk} changed while paths were being migrated")

        updates = _swap(cutover.media_fields, index)
        if cutover.hls_file:
            updates["hls_file"] = cutover.hls_file[index]
        if cutover.preview:
            updates["preview_file_path"] = cutover.preview[index]
        if updates:
            Media.objects.filter(pk=media.pk).update(**updates)
        for pk, name in _swap(cutover.encodings, index).items():
            Encoding.objects.filter(pk=pk).update(media_file=name)
        for pk, name in _swap(cutover.subtitles, index).items():
            Subtitle.objects.filter(pk=pk).update(subtitle_file=name)
        # category / tag tiles cache the media thumbnail URL until the next beat refresh
        for old_url, new_url in cutover.listing_urls.items():
            source, target = (old_url, new_url) if index == 1 else (new_url, old_url)
            for model in (Category, Tag):
                model.objects.filter(listings_thumbnail=source).update(listings_thumbnail=target)


def _cutover(plan):
    _apply_names(plan, index=1, expect_index=0)


def _restore(plan):
    _apply_names(plan, index=0)


def _invalidate_caches(plan):
    keys = [f"xaccel:state:{plan.media.uid.hex}"]
    for artifact in plan.artifacts:
        if not artifact.tree:
            keys.append(f"xaccel:path:{_rel(artifact.old)}")
            keys.append(f"xaccel:path:{_rel(artifact.new)}")
    cache.delete_many(keys)


def _db_path(fresh, artifact):
    group, key = artifact.ref
    if group == "media":
        return _abs(getattr(fresh, key).name)
    if group == "encoding":
        return _abs(Encoding.objects.get(pk=key).media_file.name)
    if group == "subtitle":
        return _abs(Subtitle.objects.get(pk=key).subtitle_file.name)
    if group == "hls":
        return os.path.dirname(os.path.normpath(fresh.hls_file))
    return os.path.normpath(fresh.video_chapters_folder)


def _reverify(plan):
    """Check every artifact again through the names the database now holds"""
    from .views.media_auth import _resolve_uid

    fresh = _fresh_media(plan.media)
    problems = []
    for artifact in plan.artifacts:
        in_db = _db_path(fresh, artifact)
        if in_db != artifact.new:
            problems.append(f"{artifact.kind}: database holds {_rel(in_db)}, expected {_rel(artifact.new)}")
            continue
        problems.extend(f"{artifact.kind}: {problem}" for problem in _verify_artifact(artifact))
        probe = f"{_rel(artifact.new)}/_" if artifact.tree else _rel(artifact.new)
        if _resolve_uid(probe) != fresh.uid.hex:
            problems.append(f"{artifact.kind}: media_auth cannot resolve {probe}")
    if plan.cutover.preview:
        preview = os.path.normpath(fresh.preview_file_path)
        if preview != plan.cutover.preview[1] or not os.path.isfile(preview):
            problems.append("preview: preview_file_path does not point at the migrated file")
    return problems


# --------------------------------------------------------------------------- remove old


def _file_referenced_elsewhere(path, media):
    name = _rel(path)
    media_q = Q(preview_file_path=path)
    for field_name in MEDIA_FILE_FIELDS:
        media_q |= Q(**{field_name: name})
    if Media.objects.exclude(pk=media.pk).filter(media_q).exists():
        return True
    if Encoding.objects.exclude(media=media).filter(media_file=name).exists():
        return True
    if Subtitle.objects.exclude(media=media).filter(subtitle_file=name).exists():
        return True
    return Category.objects.filter(thumbnail=name).exists()


def _tree_referenced_elsewhere(path, media):
    return Media.objects.exclude(pk=media.pk).filter(hls_file__startswith=os.path.join(path, "")).exists()


def _remove_legacy(plan):
    """Delete the old paths nothing references any more; returns how many were removed"""
    keep = {artifact.new for artifact in plan.artifacts}
    removed = 0
    for artifact in plan.artifacts:
        if artifact.old in keep or artifact.old == artifact.new:
            continue
        if artifact.tree:
            if _tree_referenced_elsewhere(artifact.old, plan.media):
                continue
            removed += bool(helpers.rm_dir(artifact.old))
        else:
            if _file_referenced_elsewhere(artifact.old, plan.media):
                continue
            removed += bool(helpers.rm_file(artifact.old))
    return removed


# --------------------------------------------------------------------------- orchestration


def _summary(plan, removed):
    kinds = Counter(artifact.kind for artifact in plan.artifacts)
    counts = ", ".join(f"{kind}={count}" for kind, count in sorted(kinds.items()))
    text = f"moved {len(plan.artifacts)} path(s) to {media_uid_shard_path(plan.media.uid)} ({counts}); removed {removed} legacy path(s)"
    original = next((artifact for artifact in plan.artifacts if artifact.ref == ("media", "media_file")), None)
    if original:
        text = f"{text}; original {_rel(original.old)} -> {_rel(original.new)}"
    return text[:AUDIT_SUMMARY_LENGTH]


def _lock_key(media):
    return f"path_migrate_lock_{media.uid.hex}"


def _warn(user, media, reason):
    summary = f"path migrate failed, legacy files kept: {reason}"[:AUDIT_SUMMARY_LENGTH]
    record_moderation_action(user, media, "integrity_warning", extra_info=summary)


def migrate_media_paths(media, user=None):
    """Move one media's files to the sharded layout, deleting the old ones only after
    the new ones are fully verified (see the module docstring).

    Returns a PathMigrationResult: migrated, skipped (already sharded) or failed. A failed
    result always leaves the legacy files and the database names usable.
    """
    try:
        media = _fresh_media(media)
    except Media.DoesNotExist:
        return PathMigrationResult(STATUS_FAILED, "media no longer exists")

    if not cache.add(_lock_key(media), "1", timeout=LOCK_TIMEOUT_SECONDS):
        return PathMigrationResult(STATUS_FAILED, "a path migration is already running for this media")
    try:
        return _migrate(media, user)
    finally:
        cache.delete(_lock_key(media))


def _migrate(media, user):
    try:
        plan = _build_plan(media)
    except PathMigrationError as exc:
        return PathMigrationResult(STATUS_FAILED, str(exc))
    if plan.already_sharded:
        return PathMigrationResult(STATUS_SKIPPED, ALREADY_SHARDED_REASON)

    staged = Staged()
    try:
        _stage(plan, staged)
        problems = _verify_all(plan)
        if problems:
            raise PathMigrationError("verification failed: " + "; ".join(problems[:5]))
        _cutover(plan)
    except Exception as exc:  # fail closed whatever went wrong: the legacy layout is intact
        logger.exception("Path migration failed before cutover - friendly_token=%s", media.friendly_token)
        _scrub(staged)
        reason = str(exc) or exc.__class__.__name__
        _warn(user, media, reason)
        return PathMigrationResult(STATUS_FAILED, reason)

    _invalidate_caches(plan)
    try:
        problems = _reverify(plan)
    except Exception as exc:
        logger.exception("Path migration re-verify errored - friendly_token=%s", media.friendly_token)
        problems = [str(exc) or exc.__class__.__name__]

    if problems:
        reason = "re-verification failed: " + "; ".join(problems[:5])
        try:
            _restore(plan)
        except Exception:
            # the names could not be put back: leave every file in place for the operator
            logger.exception("Path migration rollback failed - friendly_token=%s", media.friendly_token)
            _invalidate_caches(plan)
            _warn(user, media, f"{reason}; database rollback also failed, manual repair needed")
            return PathMigrationResult(STATUS_FAILED, f"{reason}; database rollback also failed")
        _invalidate_caches(plan)
        _scrub(staged)
        _warn(user, media, reason)
        return PathMigrationResult(STATUS_FAILED, reason)

    removed = _remove_legacy(plan)
    record_moderation_action(user, media, "path_migrated", extra_info=_summary(plan, removed))
    logger.info("Media paths migrated - friendly_token=%s, moved=%s, removed=%s", media.friendly_token, len(plan.artifacts), removed)
    return PathMigrationResult(STATUS_MIGRATED, moved=len(plan.artifacts), removed=removed)
