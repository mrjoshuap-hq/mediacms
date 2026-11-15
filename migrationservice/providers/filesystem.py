"""Filesystem library sync: media that already sits on a mounted directory tree.

An operator binds their library under settings.FILESYSTEM_IMPORT_ROOT (one child directory
per "mount"); a migration names one mount and, optionally, a folder inside it. Nothing
outside that tree is ever read: there is no free absolute path in the connection, every
path is checked with realpath against the mount before it is opened, and a symlink that
leads out of the mount is refused rather than followed.

source_system is filesystem:<mount> and a source_id is the file's path relative to the
mount, so it survives a change of subpath and a remount at another location. Nothing here
publishes the tree: the importer places each original under MEDIA_ROOT (hardlink or copy for
"ingest", a symlink for "preserve") and that opaque, sharded path is all anyone is ever shown.
"""

import fnmatch
import logging
import os
import re
import shutil
from itertools import islice

from django.conf import settings

from .base import BaseProvider

logger = logging.getLogger(__name__)

STORAGE_MODES = ("ingest", "preserve")

# by file extension, so a listing never opens a file. media_init still looks at the bytes.
MEDIA_EXTENSIONS = {
    "video": {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".mpg", ".mpeg", ".wmv", ".flv", ".ogv", ".3gp", ".ts", ".mts", ".m2ts"},
    "audio": {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".oga", ".opus", ".wma"},
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"},
    "pdf": {".pdf"},
}

CAPTION_EXTENSIONS = (".vtt", ".srt")
DEFAULT_CAPTION_LANGUAGE = "en"
LANGUAGE_CODE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?$")

# names that are never library content, whatever the operator's own patterns say
ALWAYS_IGNORED = (".*", "@eaDir", "#recycle", "Thumbs.db", "desktop.ini", "*.part", "*.tmp", "*.crdownload", "~*")

MAX_DEPTH = 64


class FilesystemError(ValueError):
    """A path or mount that is not allowed, or cannot be read.

    field names the form section the message belongs to, for the serializer.
    """

    def __init__(self, message, field="connection"):
        super().__init__(message)
        self.field = field


def is_within(path, base):
    """Whether an already resolved path is base or sits beneath it"""
    return path == base or path.startswith(base.rstrip(os.sep) + os.sep)


def import_root():
    """Real path of FILESYSTEM_IMPORT_ROOT"""
    root = getattr(settings, "FILESYSTEM_IMPORT_ROOT", "")
    if not root:
        raise FilesystemError("FILESYSTEM_IMPORT_ROOT is not configured")
    return os.path.realpath(root)


def clean_mount_name(name):
    """One path component naming a child of the import root. Never a path."""
    name = str(name or "").strip()
    if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name or os.sep in name:
        raise FilesystemError("The mount must be the name of one directory under the import root, not a path.")
    return name


def clean_relpath(value):
    """A relative path as 'a/b/c' with no '..' and no leading slash, or '' for none"""
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    if "\x00" in text or text.startswith("/"):
        raise FilesystemError("Paths must be relative to the mount.")
    parts = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise FilesystemError("Paths may not leave the mount ('..').")
        parts.append(part)
    return "/".join(parts)


def resolve_mount(name):
    """Real path of a mount, which must be a real directory inside the import root"""
    name = clean_mount_name(name)
    root = import_root()
    candidate = os.path.realpath(os.path.join(root, name))
    if not is_within(candidate, root):
        raise FilesystemError("The mount resolves outside the import root.")
    if os.path.dirname(candidate) != root:
        # a mount is a direct child of the root: a symlink may not borrow another location
        raise FilesystemError("The mount must be a direct child directory of the import root.")
    if not os.path.isdir(candidate):
        raise FilesystemError(f"Mount '{name}' is not a directory under the import root.")
    if not os.access(candidate, os.R_OK | os.X_OK):
        raise FilesystemError(f"Mount '{name}' is not readable.")
    return candidate


def list_mounts():
    """The mounts an operator can choose from: child directories of the import root"""
    try:
        root = import_root()
        entries = sorted(os.scandir(root), key=lambda entry: entry.name)
    except (FilesystemError, OSError):
        return []

    mounts = []
    for entry in entries:
        if entry.name.startswith("."):
            continue
        try:
            real = os.path.realpath(entry.path)
            if not entry.is_dir() or os.path.dirname(real) != root:
                continue
            readable = os.access(real, os.R_OK | os.X_OK)
        except OSError:
            continue
        mounts.append({"name": entry.name, "readable": readable})
    return mounts


def media_kind(filename):
    """video / audio / image / pdf by extension, or None for anything else"""
    extension = os.path.splitext(filename)[1].lower()
    for kind, extensions in MEDIA_EXTENSIONS.items():
        if extension in extensions:
            return kind
    return None


def place_original(source, destination, mode):
    """Put an original at its MediaCMS path. Returns "hardlink", "copy" or "symlink".

    ingest links when it can (no second copy of the bytes on the same filesystem) and
    copies otherwise: across devices, or from a read-only mount. preserve leaves the bytes
    where they are and links to them, so deleting the Media removes the link, not the file.
    """
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if os.path.lexists(destination):
        raise FileExistsError(destination)

    if mode == "preserve":
        os.symlink(source, destination)
        return "symlink"

    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        pass

    try:
        shutil.copy2(source, destination)
    except BaseException:
        try:
            os.unlink(destination)
        except OSError:
            pass
        raise
    return "copy"


def parse_patterns(raw):
    """Ignore patterns, one per line or comma separated"""
    return [chunk.strip() for chunk in re.split(r"[\n,]+", str(raw or "")) if chunk.strip()]


class FilesystemProvider(BaseProvider):
    name = "filesystem"
    label = "Filesystem library"
    implemented = True

    required_connection_keys = ("mount",)
    allowed_connection_keys = ("mount", "subpath")

    # No default owner: a library has no account catalogue, so someone has to be named,
    # and quietly picking whoever is signed in would hand a whole library to the wrong person.
    default_options = {
        "fallback_username": "",
        "storage_mode": "ingest",
        "categories_from_folders": True,
        "import_captions": True,
        "ignore_patterns": "",
        "max_items": None,
    }

    @classmethod
    def source_system(cls, connection):
        return f"filesystem:{str((connection or {}).get('mount') or '').strip()}"

    @classmethod
    def validate_settings(cls, connection, options):
        """Refuse a migration that could not run safely. Returns (connection, options).

        Raises ValueError with the message to show. Run by the serializer on save.
        """
        from users.models import User

        unknown = sorted(set(connection) - set(cls.allowed_connection_keys))
        if unknown:
            raise FilesystemError(f"Unknown connection fields: {', '.join(unknown)}")

        connection = dict(connection)
        connection["mount"] = clean_mount_name(connection.get("mount"))
        connection["subpath"] = clean_relpath(connection.get("subpath"))
        mount_real = resolve_mount(connection["mount"])
        if connection["subpath"]:
            target = os.path.realpath(os.path.join(mount_real, connection["subpath"]))
            if not is_within(target, mount_real) or not os.path.isdir(target):
                raise FilesystemError("The folder is not a directory inside the mount.")

        options = dict(options)
        mode = options.get("storage_mode") or "ingest"
        if mode not in STORAGE_MODES:
            raise FilesystemError(f"storage_mode must be one of: {', '.join(STORAGE_MODES)}", field="options")
        options["storage_mode"] = mode

        owner = str(options.get("fallback_username") or "").strip()
        if not owner:
            raise FilesystemError("Choose the MediaCMS user who will own the imported media.", field="options")
        if not User.objects.filter(username=owner).exists():
            raise FilesystemError(f"There is no MediaCMS user named '{owner}'.", field="options")
        options["fallback_username"] = owner

        max_items = options.get("max_items")
        if max_items in (None, ""):
            options["max_items"] = None
        else:
            try:
                options["max_items"] = int(max_items)
            except (TypeError, ValueError):
                raise FilesystemError("max_items must be a whole number.", field="options")
            if options["max_items"] < 1:
                raise FilesystemError("max_items must be at least 1.", field="options")

        options["ignore_patterns"] = "\n".join(parse_patterns(options.get("ignore_patterns")))
        return connection, options

    # ---- locations

    @property
    def subpath(self):
        return clean_relpath(self.connection.get("subpath"))

    def mount_path(self):
        return resolve_mount(self.connection.get("mount"))

    def _start_parts(self):
        return tuple(self.subpath.split("/")) if self.subpath else ()

    def base_path(self):
        """Real path of the folder a run starts from: the mount, or a folder inside it"""
        mount = self.mount_path()
        base = os.path.realpath(os.path.join(mount, *self._start_parts()))
        if not is_within(base, mount):
            raise FilesystemError("The folder resolves outside the mount.")
        if not os.path.isdir(base):
            raise FilesystemError("The folder is not a directory inside the mount.")
        return base

    def within_selection(self, full_name):
        subpath = self.subpath
        if not subpath:
            return True
        return full_name == subpath or full_name.startswith(subpath + "/")

    # ---- what is ignored and what counts as media

    def _patterns(self):
        return list(ALWAYS_IGNORED) + parse_patterns(self.options.get("ignore_patterns"))

    def _ignored(self, name, parts):
        relpath = "/".join(parts)
        return any(fnmatch.fnmatchcase(name, pattern) or fnmatch.fnmatchcase(relpath, pattern) for pattern in self._patterns())

    @staticmethod
    def _allowed_kinds():
        return set(getattr(settings, "ALLOWED_MEDIA_UPLOAD_TYPES", ["video", "audio", "image", "pdf"]))

    def _importable(self, name):
        kind = media_kind(name)
        return kind is not None and kind in self._allowed_kinds()

    # ---- walking

    def _entries(self, mount, parts):
        """Sorted directory entries, or None for a folder that cannot be read.

        The top of a run is checked first (base_path), so an unreadable folder here is a
        subfolder: skipped with a warning rather than ending the sweep.
        """
        try:
            with os.scandir(os.path.join(mount, *parts)) as handle:
                return sorted(handle, key=lambda entry: entry.name)
        except OSError as exc:
            logger.warning("filesystem sync: cannot read %s: %s", "/".join(parts) or "<mount>", exc)
            return None

    def _is_file(self, mount, entry):
        """A regular file whose real path is still inside the mount"""
        try:
            if entry.is_symlink():
                real = os.path.realpath(entry.path)
                if not is_within(real, mount):
                    logger.warning("filesystem sync: skipping %s, its symlink leaves the mount", entry.path)
                    return False
                return os.path.isfile(real)
            return entry.is_file(follow_symlinks=False)
        except OSError:
            return False

    def _walk(self, mount, parts, after, want, depth=0):
        """Yield mount relative paths in component order, resuming after a path.

        want is "files" or "folders" (folders that directly hold media). Entries are
        sorted by name at every level, so the order is the same one tuple comparison
        gives; that is what lets a cursor be one path: a folder that sorts wholly before
        it is never opened, and nothing is held in memory but the folders on the way down.
        """
        if depth > MAX_DEPTH:
            return
        entries = self._entries(mount, parts)
        if entries is None:
            return

        files, folders = [], []
        for entry in entries:
            child = parts + (entry.name,)
            if self._ignored(entry.name, child):
                continue
            if entry.is_symlink():
                # a symlinked folder is never followed: no loops, no way out
                if self._is_file(mount, entry):
                    files.append(entry)
                continue
            if entry.is_dir(follow_symlinks=False):
                folders.append(entry)
            elif self._is_file(mount, entry):
                files.append(entry)

        if want == "folders":
            holds_media = any(self._importable(entry.name) for entry in files)
            if holds_media and parts and (after is None or parts > after):
                yield "/".join(parts)
            for entry in folders:
                child = parts + (entry.name,)
                if after is None or child >= after[: len(child)]:
                    yield from self._walk(mount, child, after, want, depth + 1)
            return

        folder_names = {entry.name for entry in folders}
        for entry in sorted(files + folders, key=lambda entry: entry.name):
            child = parts + (entry.name,)
            if entry.name in folder_names:
                if after is None or child >= after[: len(child)]:
                    yield from self._walk(mount, child, after, want, depth + 1)
            elif self._importable(entry.name) and (after is None or child > after):
                yield "/".join(child)

    def _scan(self, want, after_id):
        self.base_path()  # refuses an unreadable or escaping start before any walking
        mount = self.mount_path()
        after = tuple(after_id.split("/")) if after_id else None
        return self._walk(mount, self._start_parts(), after, want)

    def iter_media(self, after=None):
        return self._scan("files", after)

    def iter_folders(self, after=None):
        return self._scan("folders", after)

    def has_media(self):
        """Whether at least one importable file is under the selection. Stops at the first."""
        return next(iter(self.iter_media()), None) is not None

    # ---- BaseProvider

    def list_mounts(self):
        return list_mounts()

    def check_connection(self):
        try:
            self.base_path()
        except FilesystemError as exc:
            return {"ok": False, "error": str(exc), "stats": {}}

        entries = sum(1 for _ in self.iter_media())
        folders = sum(1 for _ in self.iter_folders()) if self.options.get("categories_from_folders", True) else 0
        return {
            "ok": True,
            "error": "",
            "stats": {"entries": entries, "folders": folders, "users": 1},
        }

    def list_page(self, phase, cursor, page_size):
        cursor = dict(cursor or {})
        if phase == "categories":
            if not self.options.get("categories_from_folders", True):
                return [], {}
            source = self.iter_folders(cursor.get("after"))
        elif phase == "media":
            source = self.iter_media(cursor.get("after"))
        else:
            raise ValueError(f"Unknown migration phase: {phase}")

        page = list(islice(source, page_size))
        return page, {"after": page[-1]} if page else {}

    def _real_source(self, source_id):
        """Real path of a file by source id, refusing anything that is not inside the mount"""
        relpath = clean_relpath(source_id)
        if not relpath:
            raise FilesystemError("Empty source path.")
        mount = self.mount_path()
        real = os.path.realpath(os.path.join(mount, relpath))
        if not is_within(real, mount):
            raise FilesystemError(f"{relpath}: resolves outside the mount.")
        return relpath, mount, real

    def source_exists(self, source_id):
        """Whether a file by this id is still readable on the mount.

        Existence only: a file an ignore pattern has since started to hide is still there,
        and must not be pruned for it.
        """
        try:
            _relpath, _mount, real = self._real_source(source_id)
        except FilesystemError:
            return False
        return os.path.isfile(real) and os.access(real, os.R_OK)

    def fetch_media(self, source_id):
        relpath, mount, real = self._real_source(source_id)
        if not os.path.isfile(real):
            raise FilesystemError(f"{relpath}: not a file on the mount any more.")

        filename = os.path.basename(relpath)
        stem = os.path.splitext(filename)[0]
        folder = os.path.dirname(relpath)
        stat = os.stat(real)
        return {
            "id": relpath,
            "path": real,
            "filename": filename,
            "title": stem or filename,
            "folder": folder,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "captions": self._sidecar_captions(mount, folder, stem) if self.options.get("import_captions", True) else [],
        }

    def _sidecar_captions(self, mount, folder, stem):
        """Caption files beside a media file: name.vtt, name.srt, name.<lang>.vtt/.srt"""
        directory = os.path.join(mount, folder) if folder else mount
        try:
            names = sorted(os.listdir(directory))
        except OSError:
            return []

        found = {}
        for name in names:
            base, extension = os.path.splitext(name)
            if extension.lower() not in CAPTION_EXTENSIONS:
                continue
            if base == stem:
                language = DEFAULT_CAPTION_LANGUAGE
            elif base.startswith(stem + "."):
                language = base[len(stem) + 1 :]
                if not LANGUAGE_CODE.match(language):
                    continue
            else:
                continue

            real = os.path.realpath(os.path.join(directory, name))
            if not is_within(real, mount) or not os.path.isfile(real):
                continue
            # one caption per language, WebVTT preferred since it needs no conversion
            code = language.lower()
            if code not in found or (extension.lower() == ".vtt" and found[code]["extension"] != ".vtt"):
                found[code] = {"language": code, "path": real, "extension": extension.lower()}
        return list(found.values())

    def fetch_category(self, source_id):
        relpath = clean_relpath(source_id)
        parts = relpath.split("/")
        return {"id": relpath, "name": parts[-1], "parent": parts[-2] if len(parts) > 1 else ""}
