import os
import re
import shutil
import tempfile
import uuid
from types import SimpleNamespace

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import SimpleTestCase, TestCase

from files import helpers, tasks
from files.models import EncodeProfile, Encoding, Language, Media, Subtitle
from files.models.utils import (
    category_thumb_path,
    encoding_media_file_path,
    media_listing_thumbnail_file_path,
    media_poster_file_path,
    media_sprites_file_path,
    media_uid_dir,
    media_uid_shard_path,
    media_uploaded_listing_thumbnail_file_path,
    media_uploaded_poster_file_path,
    original_media_file_path,
    subtitles_file_path,
)
from files.tests import create_account, create_media

UID = uuid.UUID("a1b2c3d4e5f60718293a4b5c6d7e8f90")
SHARD = "a1/b2/a1b2c3d4e5f60718293a4b5c6d7e8f90"


def media_stub(uid=UID, username="someone"):
    return SimpleNamespace(uid=uid, user=SimpleNamespace(username=username))


class ShardPathHelperTests(SimpleTestCase):
    def test_shard_path_is_two_hex_levels_then_the_uid(self):
        self.assertEqual(media_uid_shard_path(UID), SHARD)

    def test_shard_path_accepts_a_uuid_or_its_string_forms(self):
        self.assertEqual(media_uid_shard_path(UID.hex), SHARD)
        self.assertEqual(media_uid_shard_path(str(UID)), SHARD)

    def test_shards_are_the_first_four_hex_digits(self):
        shard1, shard2, leaf = media_uid_shard_path(uuid.uuid4()).split("/")
        self.assertEqual((len(shard1), len(shard2), len(leaf)), (2, 2, 32))
        self.assertEqual(leaf[0:2], shard1)
        self.assertEqual(leaf[2:4], shard2)

    def test_uid_dir_is_absolute_under_media_root(self):
        self.assertEqual(media_uid_dir("hls", UID), os.path.join(settings.MEDIA_ROOT, "hls", SHARD))
        self.assertEqual(media_uid_dir("thumbnails/", UID), os.path.join(settings.MEDIA_ROOT, "thumbnails", SHARD))

    def test_original_is_source_with_a_sanitized_extension(self):
        self.assertEqual(original_media_file_path(media_stub(), "dir/clip.MP4"), f"original/{SHARD}/source.mp4")
        self.assertEqual(original_media_file_path(media_stub(), "no_extension"), f"original/{SHARD}/source")
        self.assertEqual(original_media_file_path(media_stub(), "evil.mp4/../x"), f"original/{SHARD}/source")
        self.assertEqual(original_media_file_path(media_stub(), "a.p<h>p;"), f"original/{SHARD}/source.php")

    def test_original_path_has_no_username_or_client_filename(self):
        path = original_media_file_path(media_stub(username="alice"), "Holiday Video.mp4")
        self.assertNotIn("alice", path)
        self.assertNotIn("Holiday", path)

    def test_encoding_is_profile_id_and_extension(self):
        encoding = SimpleNamespace(media=media_stub(), profile=SimpleNamespace(id=7), chunk=False)
        self.assertEqual(encoding_media_file_path(encoding, "whatever.name.mp4"), f"encoded/{SHARD}/7.mp4")
        self.assertEqual(encoding_media_file_path(encoding, "x.gif"), f"encoded/{SHARD}/7.gif")

    def test_chunk_encodings_never_claim_the_final_profile_name(self):
        chunk = SimpleNamespace(media=media_stub(), profile=SimpleNamespace(id=7), chunk=True)
        first = encoding_media_file_path(chunk, "00_abc_source.mp4.mkv.mp4")
        second = encoding_media_file_path(chunk, "01_abc_source.mp4.mkv.mp4")
        self.assertEqual(first, f"encoded/{SHARD}/7.chunk.00_abc_source.mp4.mkv.mp4")
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, f"encoded/{SHARD}/7.mp4")

    def test_thumbnail_kinds_have_fixed_opaque_names(self):
        instance = media_stub()
        self.assertEqual(media_poster_file_path(instance, "any.png"), f"thumbnails/{SHARD}/poster.jpg")
        self.assertEqual(media_listing_thumbnail_file_path(instance, "any.png"), f"thumbnails/{SHARD}/listing.jpg")
        self.assertEqual(media_sprites_file_path(instance, "any.png"), f"thumbnails/{SHARD}/sprites.jpg")
        self.assertEqual(media_uploaded_poster_file_path(instance, "any.png"), f"thumbnails/{SHARD}/uploaded_poster.jpg")
        self.assertEqual(media_uploaded_listing_thumbnail_file_path(instance, "any.png"), f"thumbnails/{SHARD}/uploaded_listing.jpg")

    def test_subtitles_are_named_by_language_code(self):
        subtitle = SimpleNamespace(media=media_stub(), language=SimpleNamespace(code="pt-BR"))
        self.assertEqual(subtitles_file_path(subtitle, "client.srt"), f"subtitles/{SHARD}/pt-BR.srt")
        self.assertEqual(subtitles_file_path(subtitle, "noext"), f"subtitles/{SHARD}/pt-BR.vtt")
        subtitle.language = SimpleNamespace(code="../x")
        self.assertNotIn("..", subtitles_file_path(subtitle, "a.vtt"))
        self.assertTrue(subtitles_file_path(subtitle, "a.vtt").startswith(f"subtitles/{SHARD}/"))

    def test_category_thumbnails_are_sharded_by_the_category_uid(self):
        category = SimpleNamespace(uid="abc123")
        path = category_thumb_path(category, "dir/Pic.JPG")
        self.assertRegex(path, r"^categories/[0-9a-f]{2}/[0-9a-f]{2}/abc123\.jpg$")
        # stable: the same uid always lands in the same shard
        self.assertEqual(path, category_thumb_path(SimpleNamespace(uid="abc123"), "other.jpg"))

    def test_a_category_uid_that_is_a_media_style_hex_uses_its_own_digits(self):
        category = SimpleNamespace(uid=UID.hex)
        self.assertEqual(category_thumb_path(category, "x.png"), f"categories/a1/b2/{UID.hex}.png")

    def test_shard_fan_out_is_even_enough(self):
        buckets = {media_uid_shard_path(uuid.uuid4()).rsplit("/", 1)[0] for _ in range(2000)}
        self.assertGreater(len(buckets), 1500)


class SettingsAndNginxTests(SimpleTestCase):
    def test_upload_dirs_are_top_level_kinds(self):
        self.assertEqual(settings.THUMBNAIL_UPLOAD_DIR, "thumbnails/")
        self.assertEqual(settings.SUBTITLES_UPLOAD_DIR, "subtitles/")

    def test_new_kinds_are_protected(self):
        for kind in ("encoded", "hls", "original", "thumbnails", "subtitles", "categories"):
            self.assertIn(kind, settings.X_ACCEL_PROTECTED_PATHS)

    def test_filesystem_import_root_default(self):
        self.assertEqual(settings.FILESYSTEM_IMPORT_ROOT, "/external-media_files")

    def test_nginx_gates_every_protected_kind_with_auth_request(self):
        path = os.path.join(settings.BASE_DIR, "deploy", "docker", "nginx_http_only.conf")
        with open(path, encoding="utf-8") as handle:
            conf = handle.read()
        for location in (
            r"location ~ \^/media/original/\(\.\*\)\$",
            r"location ~ \^/media/\(encoded\|hls\)/\(\.\*\)\$",
            r"location ~ \^/media/\(thumbnails\|categories\)/\(\.\*\)\$",
            r"location ~ \^/media/subtitles/\(\.\*\)\$",
        ):
            match = re.search(location + r" \{(.*?)\n    \}", conf, re.S)
            self.assertIsNotNone(match, location)
            self.assertIn("auth_request /_media_auth;", match.group(1), location)
        for kind in settings.X_ACCEL_PROTECTED_PATHS:
            self.assertRegex(conf, rf"/media/(\(?[a-z|]*\b{kind}\b[a-z|)]*)/", kind)


class HlsPermanentDirTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_account(username="hls_paths_user", email="hls_paths@example.com")

    def test_new_media_use_a_sharded_hls_dir(self):
        media = create_media(self.user)
        self.assertEqual(tasks.hls_permanent_dir(media.uid), os.path.join(settings.HLS_DIR, media_uid_shard_path(media.uid)))

    def test_media_with_a_legacy_hls_tree_keep_merging_into_it(self):
        media = create_media(self.user)
        legacy = os.path.join(settings.HLS_DIR, media.uid.hex)
        os.makedirs(legacy)
        self.addCleanup(shutil.rmtree, legacy, True)
        self.assertEqual(tasks.hls_permanent_dir(media.uid), legacy)


class SymlinkSafeRemovalTests(SimpleTestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="symlink-removal-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.archive = os.path.join(self.root, "archive")
        os.makedirs(self.archive)
        self.archive_file = os.path.join(self.archive, "lecture.mp4")
        with open(self.archive_file, "wb") as handle:
            handle.write(b"archive bytes")

    def test_rm_file_unlinks_a_symlink_but_keeps_its_target(self):
        link = os.path.join(self.root, "link.mp4")
        os.symlink(self.archive_file, link)
        self.assertTrue(helpers.rm_file(link))
        self.assertFalse(os.path.lexists(link))
        self.assertTrue(os.path.isfile(self.archive_file))

    def test_rm_file_removes_a_dangling_symlink(self):
        link = os.path.join(self.root, "dangling.mp4")
        os.symlink(os.path.join(self.root, "gone.mp4"), link)
        self.assertTrue(helpers.rm_file(link))
        self.assertFalse(os.path.lexists(link))

    def test_rm_file_never_removes_a_directory_symlink_target(self):
        link = os.path.join(self.root, "dirlink")
        os.symlink(self.archive, link)
        self.assertTrue(helpers.rm_file(link))
        self.assertTrue(os.path.isfile(self.archive_file))

    def test_rm_dir_does_not_follow_a_symlinked_directory(self):
        with self.settings(MEDIA_ROOT=self.root + "/"):
            link = os.path.join(self.root, "dirlink")
            os.symlink(self.archive, link)
            self.assertTrue(helpers.rm_dir(link))
            self.assertFalse(os.path.lexists(link))
            self.assertTrue(os.path.isfile(self.archive_file))

    def test_rm_dir_unlinks_symlinks_inside_a_tree_without_touching_targets(self):
        with self.settings(MEDIA_ROOT=self.root + "/"):
            uid_dir = os.path.join(self.root, "original", SHARD)
            os.makedirs(uid_dir)
            os.symlink(self.archive_file, os.path.join(uid_dir, "source.mp4"))
            os.symlink(self.archive, os.path.join(uid_dir, "archive-dir"))
            self.assertTrue(helpers.rm_dir(uid_dir))
            self.assertFalse(os.path.exists(uid_dir))
            self.assertTrue(os.path.isfile(self.archive_file))

    def test_rm_dir_still_refuses_directories_outside_project_and_media(self):
        self.assertFalse(helpers.rm_dir(self.archive))
        self.assertTrue(os.path.isdir(self.archive))


class SharedMediaDeleteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_account(username="delete_paths_user", email="delete_paths@example.com")

    def test_deleting_media_removes_its_sharded_dirs_and_nothing_else(self):
        media = create_media(self.user)
        other = create_media(self.user)
        language = Language.objects.create(code="en", title="English")
        subtitle = Subtitle(media=media, user=self.user, language=language)
        subtitle.subtitle_file.save("c.vtt", ContentFile(b"WEBVTT\n"), save=False)
        subtitle.save()
        profile = EncodeProfile.objects.create(name="paths-240", extension="mp4", resolution=240, codec="h264")
        encoding = Encoding(media=media, profile=profile, status="success", progress=100)
        encoding.media_file.save("x.mp4", ContentFile(b"video"), save=False)
        encoding.save()
        hls_dir = os.path.join(settings.HLS_DIR, media_uid_shard_path(media.uid))
        os.makedirs(hls_dir)
        with open(os.path.join(hls_dir, "master.m3u8"), "w") as handle:
            handle.write("#EXTM3U\n")
        Media.objects.filter(pk=media.pk).update(hls_file=os.path.join(hls_dir, "master.m3u8"))
        media.refresh_from_db()

        uid_dirs = [media_uid_dir(kind, media.uid) for kind in ("original", "encoded", "thumbnails", "subtitles", "hls")]
        for uid_dir in uid_dirs:
            self.assertTrue(os.path.isdir(uid_dir), uid_dir)

        media.delete()

        for uid_dir in uid_dirs:
            self.assertFalse(os.path.exists(uid_dir), uid_dir)
        self.assertTrue(os.path.isfile(other.media_file.path))
        self.assertTrue(os.path.isdir(media_uid_dir("thumbnails", other.uid)))

    def test_deleting_a_media_whose_original_is_a_symlink_keeps_the_archive(self):
        archive = tempfile.mkdtemp(prefix="external-archive-")
        self.addCleanup(shutil.rmtree, archive, True)
        archive_file = os.path.join(archive, "lecture.png")
        with open("fixtures/test_image.png", "rb") as source, open(archive_file, "wb") as target:
            target.write(source.read())

        media = create_media(self.user)
        link_path = media.media_file.path
        os.remove(link_path)
        os.symlink(archive_file, link_path)
        self.assertTrue(os.path.islink(link_path))

        media.delete()

        self.assertFalse(os.path.lexists(link_path))
        self.assertTrue(os.path.isfile(archive_file))
