"""Build a media whose files sit in the legacy (pre-sharding) layout, for path-migrate tests."""

import os
from types import SimpleNamespace

from django.conf import settings

from files import helpers
from files.models import EncodeProfile, Encoding, Language, Media, Subtitle
from files.models.utils import PREVIEW_PROFILE_NAME, media_uid_dir
from files.tests import create_media

ORIGINAL_BYTES = b"original-bytes-" * 512
SEGMENT_BYTES = b"hls-segment-" * 256


def media_path(relative):
    return os.path.join(settings.MEDIA_ROOT, relative)


def write_media_file(relative, data):
    path = media_path(relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)
    return path


def read_file(path):
    with open(path, "rb") as handle:
        return handle.read()


def clear_sharded_files(media):
    for kind in ("original", "encoded", "thumbnails", "subtitles", "hls"):
        helpers.rm_dir(media_uid_dir(kind, media.uid))


def build_legacy_media(owner, *, original_symlink_to=None, hls_symlink_to=None, **fields):
    """A media with every kind of reference in the old layout.

    Returns a namespace with the Media and every legacy absolute path. Rows are written
    with bulk_create/update so no model signal (encode, HLS, search vector) fires.
    """
    media = create_media(owner, **fields)
    clear_sharded_files(media)
    uid = media.uid.hex
    user = owner.username
    token = media.friendly_token

    names = SimpleNamespace(
        original=f"original/user/{user}/{uid}.clip.png",
        poster=f"original/thumbnails/user/{user}/{uid}.poster.jpg",
        thumbnail=f"original/thumbnails/user/{user}/{uid}.thumb.jpg",
        uploaded_poster=f"original/thumbnails/user/{user}/uploaded_poster_{token}.jpg",
        uploaded_thumbnail=f"original/thumbnails/user/{user}/uploaded_thumb_{token}.jpg",
        sprites=f"original/thumbnails/user/{user}/{uid}.sprites.jpg",
        subtitle=f"original/subtitles/user/{user}/{uid}_en.vtt",
    )

    paths = SimpleNamespace(media=media, names=names)
    if original_symlink_to:
        os.makedirs(os.path.dirname(media_path(names.original)), exist_ok=True)
        os.symlink(original_symlink_to, media_path(names.original))
        paths.original = media_path(names.original)
    else:
        paths.original = write_media_file(names.original, ORIGINAL_BYTES)
    for attr in ("poster", "thumbnail", "uploaded_poster", "uploaded_thumbnail", "sprites"):
        setattr(paths, attr, write_media_file(getattr(names, attr), f"{attr}-bytes".encode() * 64))

    video_profile, _ = EncodeProfile.objects.get_or_create(name="path-migrate-240", defaults={"extension": "mp4", "resolution": 240, "codec": "h264"})
    preview_profile, _ = EncodeProfile.objects.get_or_create(name=PREVIEW_PROFILE_NAME, defaults={"extension": "gif", "resolution": None})
    names.encoding = f"encoded/{video_profile.id}/{user}/{uid}.clip.png.mp4"
    names.preview = f"encoded/{preview_profile.id}/{user}/{uid}.clip.png.gif"
    names.chunk = f"encoded/{video_profile.id}/{user}/{uid}.chunk0.mp4"
    paths.encoding = write_media_file(names.encoding, b"encoded-mp4-" * 128)
    paths.preview = write_media_file(names.preview, b"GIF89a-preview-" * 32)
    paths.chunk = write_media_file(names.chunk, b"chunk-bytes-" * 32)
    Encoding.objects.bulk_create(
        [
            Encoding(media=media, profile=video_profile, status="success", progress=100, media_file=names.encoding),
            Encoding(media=media, profile=preview_profile, status="success", progress=100, media_file=names.preview),
            Encoding(media=media, profile=video_profile, status="success", progress=100, chunk=True, media_file=names.chunk),
        ]
    )
    paths.video_profile = video_profile

    language, _ = Language.objects.get_or_create(code="en", defaults={"title": "English"})
    paths.subtitle = write_media_file(names.subtitle, b"WEBVTT\n\n00:00.000 --> 00:01.000\nhello\n")
    Subtitle.objects.bulk_create([Subtitle(media=media, user=owner, language=language, subtitle_file=names.subtitle)])

    paths.hls_dir = media_path(f"hls/{uid}")
    paths.hls_master = write_media_file(f"hls/{uid}/master.m3u8", b"#EXTM3U\nmedia-240/stream.m3u8\n")
    write_media_file(f"hls/{uid}/media-240/stream.m3u8", b"#EXTM3U\nseg0.ts\n")
    paths.hls_segment = write_media_file(f"hls/{uid}/media-240/seg0.ts", SEGMENT_BYTES)
    if hls_symlink_to:
        paths.hls_link = os.path.join(paths.hls_dir, "media-240", "archive.ts")
        os.symlink(hls_symlink_to, paths.hls_link)

    paths.chapters_dir = media_path(f"original/thumbnails/{user}/{token}_chapters")
    paths.chapter_file = write_media_file(f"original/thumbnails/{user}/{token}_chapters/c1.jpg", b"chapter-1" * 16)

    Media.objects.filter(pk=media.pk).update(
        media_file=names.original,
        poster=names.poster,
        thumbnail=names.thumbnail,
        uploaded_poster=names.uploaded_poster,
        uploaded_thumbnail=names.uploaded_thumbnail,
        sprites=names.sprites,
        hls_file=paths.hls_master,
        preview_file_path=paths.preview,
        encoding_status="success",
    )
    paths.media = Media.objects.get(pk=media.pk)
    return paths
