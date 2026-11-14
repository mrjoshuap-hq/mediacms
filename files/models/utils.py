import hashlib
import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string

from .. import helpers

# this is used by Media and Encoding models
# reflects media encoding status for objects
MEDIA_ENCODING_STATUS = (
    ("pending", "Pending"),
    ("running", "Running"),
    ("fail", "Fail"),
    ("success", "Success"),
)

# the media state of a Media object
# this is set by default according to the portal workflow
MEDIA_STATES = (
    ("private", "Private"),
    ("public", "Public"),
    ("unlisted", "Unlisted"),
)

# each uploaded Media gets a media_type hint
# by helpers.get_file_type

MEDIA_TYPES_SUPPORTED = (
    ("video", "Video"),
    ("image", "Image"),
    ("pdf", "Pdf"),
    ("audio", "Audio"),
)

ENCODE_EXTENSIONS = (
    ("mp4", "mp4"),
    ("webm", "webm"),
    ("gif", "gif"),
)

ENCODE_RESOLUTIONS = (
    (2160, "2160"),
    (1440, "1440"),
    (1080, "1080"),
    (720, "720"),
    (480, "480"),
    (360, "360"),
    (240, "240"),
    (144, "144"),
)

CODECS = (
    ("h265", "h265"),
    ("h264", "h264"),
    ("vp9", "vp9"),
)

ENCODE_EXTENSIONS_KEYS = [extension for extension, name in ENCODE_EXTENSIONS]
ENCODE_RESOLUTIONS_KEYS = [resolution for resolution, name in ENCODE_RESOLUTIONS]

PREVIEW_PROFILE_NAME = "preview"

EDITOR_VIDEO_RESOLUTION = 720


def generate_uid():
    return get_random_string(length=16)


# Media-owned files are keyed by Media.uid.hex under a two-level hex shard fan-out
# (256 x 256 leaf buckets): <kind>/<aa>/<bb>/<uid.hex>/<fixed basename>. The depth is
# fixed at 2; changing it would need a path migration, so it is not a runtime setting.
MEDIA_PATH_SHARD_DEPTH = 2
CATEGORIES_DIR = "categories/"
MAX_EXTENSION_LENGTH = 10


def _uid_hex(uid):
    """The 32 char lowercase hex of a UUID (or of its string form)"""
    return getattr(uid, "hex", None) or str(uid).replace("-", "").lower()


def _shard_hex(key):
    """The hex digits shards are cut from.

    A media uid already is 32 hex characters. Anything else (a category uid is a short
    random string) is hashed so it still fans out evenly.
    """
    value = _uid_hex(key)
    if len(value) == 32 and all(char in "0123456789abcdef" for char in value):
        return value
    return hashlib.md5(str(key).encode("utf-8")).hexdigest()


def media_uid_shard_path(uid):
    """Relative '<aa>/<bb>/<uid.hex>' directory for a media uid (no kind prefix)"""
    value = _uid_hex(uid)
    return "/".join([value[0:2], value[2:4], value])


def media_uid_dir(kind, uid):
    """Absolute directory holding one media's files of a kind (original, encoded, hls, ...)"""
    return os.path.join(settings.MEDIA_ROOT, kind.strip("/"), media_uid_shard_path(uid))


def _safe_extension(filename):
    """Lowercase extension of a client supplied filename, stripped to [a-z0-9] ('.mp4' or '')"""
    extension = os.path.splitext(helpers.get_file_name(filename))[1].lower()
    extension = re.sub(r"[^a-z0-9]", "", extension)[:MAX_EXTENSION_LENGTH]
    return f".{extension}" if extension else ""


def _under(base_dir, *parts):
    return "/".join([base_dir.strip("/")] + [part.strip("/") for part in parts])


def original_media_file_path(instance, filename):
    """Helper function to place original media file: original/aa/bb/<uid>/source.<ext>"""
    return _under(settings.MEDIA_UPLOAD_DIR, media_uid_shard_path(instance.uid), f"source{_safe_extension(filename)}")


def encoding_media_file_path(instance, filename):
    """Helper function to place encoded media file: encoded/aa/bb/<uid>/<profile_id>.<ext>

    Intermediate chunk encodings (several per profile, removed after concatenation) keep
    their segment name so they never claim the final <profile_id>.<ext> name.
    """
    shard_dir = media_uid_shard_path(instance.media.uid)
    if getattr(instance, "chunk", False):
        segment = re.sub(r"[^A-Za-z0-9._-]", "_", helpers.get_file_name(filename)) or "segment"
        return _under(settings.MEDIA_ENCODING_DIR, shard_dir, f"{instance.profile.id}.chunk.{segment}")
    return _under(settings.MEDIA_ENCODING_DIR, shard_dir, f"{instance.profile.id}{_safe_extension(filename)}")


def _thumbnail_path(instance, basename):
    return _under(settings.THUMBNAIL_UPLOAD_DIR, media_uid_shard_path(instance.uid), basename)


def original_thumbnail_file_path(instance, filename):
    """Generic thumbnails/aa/bb/<uid>/ placement that keeps a sanitized basename.

    Media image fields use the fixed-name helpers below; this stays importable because
    the initial migration references it.
    """
    return _thumbnail_path(instance, re.sub(r"[^A-Za-z0-9._-]", "_", helpers.get_file_name(filename)) or "thumbnail.jpg")


def media_poster_file_path(instance, filename):
    """thumbnails/aa/bb/<uid>/poster.jpg (Media.poster)"""
    return _thumbnail_path(instance, "poster.jpg")


def media_listing_thumbnail_file_path(instance, filename):
    """thumbnails/aa/bb/<uid>/listing.jpg (Media.thumbnail)"""
    return _thumbnail_path(instance, "listing.jpg")


def media_uploaded_poster_file_path(instance, filename):
    """thumbnails/aa/bb/<uid>/uploaded_poster.jpg (Media.uploaded_poster)

    Kept apart from poster.jpg so an upload never collides with the generated poster.
    """
    return _thumbnail_path(instance, "uploaded_poster.jpg")


def media_uploaded_listing_thumbnail_file_path(instance, filename):
    """thumbnails/aa/bb/<uid>/uploaded_listing.jpg (Media.uploaded_thumbnail)"""
    return _thumbnail_path(instance, "uploaded_listing.jpg")


def media_sprites_file_path(instance, filename):
    """thumbnails/aa/bb/<uid>/sprites.jpg (Media.sprites)"""
    return _thumbnail_path(instance, "sprites.jpg")


def subtitles_file_path(instance, filename):
    """Helper function to place subtitle file: subtitles/aa/bb/<uid>/<lang>.<ext>"""
    language = re.sub(r"[^A-Za-z0-9_-]", "_", str(getattr(instance.language, "code", "") or "")) or "subtitle"
    return _under(settings.SUBTITLES_UPLOAD_DIR, media_uid_shard_path(instance.media.uid), f"{language}{_safe_extension(filename) or '.vtt'}")


def category_thumb_path(instance, filename):
    """Helper function to place category thumbnail file: categories/aa/bb/<category_uid>.<ext>"""
    shard = _shard_hex(instance.uid)
    return _under(CATEGORIES_DIR, shard[0:2], shard[2:4], f"{instance.uid}{_safe_extension(filename)}")


def validate_rating(value):
    if -1 >= value or value > 5:
        raise ValidationError("score has to be between 0 and 5")
