import errno
import itertools
import os
import shutil
import tempfile
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from actions.models import MediaAction
from files import helpers, path_migrate, tasks
from files.methods import record_moderation_action
from files.models import Category, Encoding, Media, Subtitle
from files.models.utils import media_uid_dir
from files.path_migrate import (
    ALREADY_SHARDED_REASON,
    STATUS_FAILED,
    STATUS_MIGRATED,
    STATUS_SKIPPED,
    can_migrate_media_paths,
    migrate_media_paths,
)
from files.tests import create_account, create_media
from tests._support.legacy_media import (
    ORIGINAL_BYTES,
    SEGMENT_BYTES,
    build_legacy_media,
    clear_sharded_files,
    media_path,
    read_file,
    write_media_file,
)


class PathMigrateBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_account(username="path_migrate_owner", email="path_migrate_owner@example.com")
        cls.manager = create_account(username="path_migrate_manager", email="path_migrate_manager@example.com", is_manager=True)

    def setUp(self):
        self.archive_dir = tempfile.mkdtemp(prefix="path-migrate-archive-")
        self.addCleanup(shutil.rmtree, self.archive_dir, True)
        self.legacy = None

    def build(self, **kwargs):
        self.legacy = build_legacy_media(self.owner, **kwargs)
        self.addCleanup(self.cleanup_media, self.legacy.media)
        return self.legacy

    def cleanup_media(self, media):
        # the database rolls back with the test; only files need removing
        clear_sharded_files(media)

    def archive_file(self, name="lecture.png", data=ORIGINAL_BYTES):
        path = os.path.join(self.archive_dir, name)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def db_snapshot(self, media):
        row = Media.objects.get(pk=media.pk)
        return {
            "media": {name: getattr(row, name).name for name in path_migrate.MEDIA_FILE_FIELDS},
            "hls_file": row.hls_file,
            "preview_file_path": row.preview_file_path,
            "encodings": dict(Encoding.objects.filter(media=media).values_list("pk", "media_file")),
            "subtitles": dict(Subtitle.objects.filter(media=media).values_list("pk", "subtitle_file")),
        }

    def assert_legacy_intact(self, legacy):
        for attr in ("original", "poster", "thumbnail", "uploaded_poster", "uploaded_thumbnail", "sprites", "encoding", "preview", "chunk", "subtitle", "hls_master", "hls_segment", "chapter_file"):
            self.assertTrue(os.path.lexists(getattr(legacy, attr)), attr)

    def assert_no_sharded_files(self, media):
        for kind in ("original", "encoded", "thumbnails", "subtitles", "hls"):
            self.assertFalse(os.path.exists(media_uid_dir(kind, media.uid)), kind)


class SuccessfulMigrationTests(PathMigrateBase):
    def test_every_reference_moves_to_the_sharded_layout(self):
        legacy = self.build()
        media = legacy.media

        result = migrate_media_paths(media, user=self.manager)

        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        self.assertEqual(result.moved, 12)

        media.refresh_from_db()
        uid_path = f"{media.uid.hex[0:2]}/{media.uid.hex[2:4]}/{media.uid.hex}"
        self.assertEqual(media.media_file.name, f"original/{uid_path}/source.png")
        self.assertEqual(media.poster.name, f"thumbnails/{uid_path}/poster.jpg")
        self.assertEqual(media.thumbnail.name, f"thumbnails/{uid_path}/listing.jpg")
        self.assertEqual(media.uploaded_poster.name, f"thumbnails/{uid_path}/uploaded_poster.jpg")
        self.assertEqual(media.uploaded_thumbnail.name, f"thumbnails/{uid_path}/uploaded_listing.jpg")
        self.assertEqual(media.sprites.name, f"thumbnails/{uid_path}/sprites.jpg")

        profile_id = legacy.video_profile.id
        encodings = {encoding.media_file.name for encoding in Encoding.objects.filter(media=media)}
        self.assertIn(f"encoded/{uid_path}/{profile_id}.mp4", encodings)
        self.assertTrue(any(name.startswith(f"encoded/{uid_path}/{profile_id}.chunk.") for name in encodings))
        self.assertEqual(len(encodings), 3)
        self.assertTrue(media.preview_file_path.startswith(media_uid_dir("encoded", media.uid)))
        self.assertTrue(media.preview_file_path.endswith(".gif"))
        self.assertTrue(os.path.isfile(media.preview_file_path))
        self.assertEqual(Subtitle.objects.get(media=media).subtitle_file.name, f"subtitles/{uid_path}/en.vtt")
        self.assertEqual(media.hls_file, os.path.join(media_uid_dir("hls", media.uid), "master.m3u8"))
        self.assertEqual(read_file(os.path.join(media_uid_dir("hls", media.uid), "media-240", "seg0.ts")), SEGMENT_BYTES)

        self.assertEqual(read_file(media.media_file.path), ORIGINAL_BYTES)
        self.assertTrue(os.path.isfile(os.path.join(media_uid_dir("thumbnails", media.uid), "chapters", "c1.jpg")))

    def test_legacy_paths_are_removed_after_the_move(self):
        legacy = self.build()
        result = migrate_media_paths(legacy.media, user=self.manager)
        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        for attr in ("original", "poster", "thumbnail", "uploaded_poster", "uploaded_thumbnail", "sprites", "encoding", "preview", "chunk", "subtitle", "hls_segment", "chapter_file"):
            self.assertFalse(os.path.lexists(getattr(legacy, attr)), attr)
        self.assertFalse(os.path.exists(legacy.hls_dir))
        self.assertFalse(os.path.exists(legacy.chapters_dir))
        self.assertGreaterEqual(result.removed, 12)

    def test_audit_event_names_the_actor_and_the_move(self):
        legacy = self.build()
        migrate_media_paths(legacy.media, user=self.manager)
        event = MediaAction.objects.get(media=legacy.media, action="path_migrated")
        self.assertEqual(event.user_id, self.manager.pk)
        self.assertIn("original/user/path_migrate_owner/", event.extra_info)
        self.assertIn("/source.png", event.extra_info)
        self.assertFalse(MediaAction.objects.filter(media=legacy.media, action="integrity_warning").exists())

    def test_xaccel_caches_are_dropped_and_listing_tiles_follow_the_new_url(self):
        legacy = self.build()
        media = legacy.media
        category = Category.objects.create(title="path migrate tile two")
        Category.objects.filter(pk=category.pk).update(listings_thumbnail=helpers.url_from_path(legacy.uploaded_thumbnail))
        cache.set(f"xaccel:state:{media.uid.hex}", ("private", None, "x", False), 300)
        cache.set(f"xaccel:path:{legacy.names.subtitle}", media.uid.hex, 300)

        migrate_media_paths(media, user=self.manager)

        self.assertIsNone(cache.get(f"xaccel:state:{media.uid.hex}"))
        self.assertIsNone(cache.get(f"xaccel:path:{legacy.names.subtitle}"))
        category.refresh_from_db()
        media.refresh_from_db()
        self.assertEqual(category.listings_thumbnail, helpers.url_from_path(media.uploaded_thumbnail.path))

    def test_it_copies_when_hard_links_are_unavailable(self):
        legacy = self.build()
        with patch("files.path_migrate.os.link", side_effect=OSError(errno.EXDEV, "cross-device link")):
            result = migrate_media_paths(legacy.media, user=self.manager)
        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        media = Media.objects.get(pk=legacy.media.pk)
        self.assertEqual(read_file(media.media_file.path), ORIGINAL_BYTES)
        self.assertEqual(os.stat(media.media_file.path).st_nlink, 1)
        self.assertFalse(os.path.exists(legacy.original))

    def test_an_original_in_a_sharded_dir_with_a_django_collision_name_is_renamed(self):
        legacy = self.build()
        media = legacy.media
        collided = f"original/{media.uid.hex[0:2]}/{media.uid.hex[2:4]}/{media.uid.hex}/source_AbC123.png"
        path = write_media_file(collided, ORIGINAL_BYTES)
        os.remove(legacy.original)
        Media.objects.filter(pk=media.pk).update(media_file=collided)

        result = migrate_media_paths(media, user=self.manager)

        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        media.refresh_from_db()
        self.assertTrue(media.media_file.name.endswith("/source.png"))
        self.assertFalse(os.path.exists(path))
        self.assertEqual(read_file(media.media_file.path), ORIGINAL_BYTES)

    def test_files_another_media_still_references_are_not_deleted(self):
        legacy = self.build()
        other = create_media(self.owner, title="shares the poster")
        self.addCleanup(self.cleanup_media, other)
        Media.objects.filter(pk=other.pk).update(poster=legacy.names.poster)

        result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        self.assertTrue(os.path.isfile(legacy.poster))
        self.assertEqual(Media.objects.get(pk=other.pk).poster.name, legacy.names.poster)
        self.assertFalse(os.path.exists(legacy.thumbnail))


class IdempotencyTests(PathMigrateBase):
    def test_second_run_is_skipped_and_audited_once(self):
        legacy = self.build()
        first = migrate_media_paths(legacy.media, user=self.manager)
        names = self.db_snapshot(legacy.media)
        second = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(first.status, STATUS_MIGRATED, first.reason)
        self.assertEqual(second.status, STATUS_SKIPPED)
        self.assertEqual(second.reason, ALREADY_SHARDED_REASON)
        self.assertEqual(self.db_snapshot(legacy.media), names)
        self.assertEqual(MediaAction.objects.filter(media=legacy.media, action="path_migrated").count(), 1)
        self.assertEqual(can_migrate_media_paths(legacy.media), (False, ALREADY_SHARDED_REASON))

    def test_a_media_created_in_the_sharded_layout_is_already_migrated(self):
        media = create_media(self.owner, title="born sharded")
        self.addCleanup(self.cleanup_media, media)
        result = migrate_media_paths(media, user=self.manager)
        self.assertEqual(result.status, STATUS_SKIPPED)
        self.assertFalse(MediaAction.objects.filter(media=media, action="path_migrated").exists())


class VerifyFailureTests(PathMigrateBase):
    def test_a_failed_checksum_leaves_the_old_layout_and_database_untouched(self):
        legacy = self.build()
        before = self.db_snapshot(legacy.media)
        digests = itertools.count()

        with patch("files.path_migrate.os.link", side_effect=OSError(errno.EXDEV, "cross-device link")), patch("files.path_migrate._digest", side_effect=lambda path: str(next(digests))):
            result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("checksum mismatch", result.reason)
        self.assert_legacy_intact(legacy)
        self.assertEqual(read_file(legacy.original), ORIGINAL_BYTES)
        self.assertEqual(self.db_snapshot(legacy.media), before)
        self.assert_no_sharded_files(legacy.media)
        self.assertFalse(MediaAction.objects.filter(media=legacy.media, action="path_migrated").exists())
        self.assertTrue(MediaAction.objects.filter(media=legacy.media, action="integrity_warning", extra_info__contains="legacy files kept").exists())

    def test_a_staging_error_scrubs_what_was_staged(self):
        legacy = self.build()
        before = self.db_snapshot(legacy.media)
        real_copy = shutil.copyfileobj
        calls = itertools.count()

        def failing_copy(source, destination, length=0):
            if next(calls) == 2:
                raise OSError(errno.ENOSPC, "No space left on device")
            return real_copy(source, destination, length)

        with patch("files.path_migrate.os.link", side_effect=OSError(errno.EXDEV, "cross-device link")), patch("files.path_migrate.shutil.copyfileobj", side_effect=failing_copy):
            result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("No space left", result.reason)
        self.assert_legacy_intact(legacy)
        self.assertEqual(self.db_snapshot(legacy.media), before)
        self.assert_no_sharded_files(legacy.media)

    def test_a_failed_reverify_restores_the_names_and_keeps_the_old_files(self):
        legacy = self.build()
        before = self.db_snapshot(legacy.media)
        cache.set(f"xaccel:state:{legacy.media.uid.hex}", ("private", None, "x", False), 300)

        with patch("files.path_migrate._reverify", return_value=["original: boom"]):
            result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("re-verification failed", result.reason)
        self.assert_legacy_intact(legacy)
        self.assertEqual(read_file(legacy.original), ORIGINAL_BYTES)
        self.assertEqual(self.db_snapshot(legacy.media), before)
        self.assert_no_sharded_files(legacy.media)
        self.assertIsNone(cache.get(f"xaccel:state:{legacy.media.uid.hex}"))
        self.assertFalse(MediaAction.objects.filter(media=legacy.media, action="path_migrated").exists())
        self.assertTrue(MediaAction.objects.filter(media=legacy.media, action="integrity_warning").exists())

    def test_a_failed_rollback_keeps_every_file_in_place(self):
        legacy = self.build()

        with patch("files.path_migrate._reverify", return_value=["original: boom"]), patch("files.path_migrate._restore", side_effect=RuntimeError("db down")):
            result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("rollback also failed", result.reason)
        self.assert_legacy_intact(legacy)
        media = Media.objects.get(pk=legacy.media.pk)
        self.assertTrue(os.path.isfile(media.media_file.path))

    def test_a_media_changed_while_staging_is_not_overwritten(self):
        legacy = self.build()

        def edit_during_migration(plan):
            Media.objects.filter(pk=legacy.media.pk).update(poster=legacy.names.thumbnail)
            return []

        with patch("files.path_migrate._verify_all", side_effect=edit_during_migration):
            result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("poster changed", result.reason)
        self.assert_legacy_intact(legacy)
        self.assertEqual(Media.objects.get(pk=legacy.media.pk).poster.name, legacy.names.thumbnail)
        self.assert_no_sharded_files(legacy.media)


class GateTests(PathMigrateBase):
    def assert_blocked(self, legacy, fragment):
        before = self.db_snapshot(legacy.media)
        eligible, reason = can_migrate_media_paths(legacy.media)
        self.assertFalse(eligible)
        self.assertIn(fragment, reason)
        result = migrate_media_paths(legacy.media, user=self.manager)
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn(fragment, result.reason)
        self.assertEqual(self.db_snapshot(legacy.media), before)
        self.assert_no_sharded_files(legacy.media)
        self.assertFalse(MediaAction.objects.filter(media=legacy.media, action="path_migrated").exists())

    def test_a_missing_referenced_file_blocks_the_media(self):
        legacy = self.build()
        os.remove(legacy.sprites)
        self.assert_blocked(legacy, "file missing on disk")

    def test_a_missing_original_blocks_the_media(self):
        legacy = self.build()
        os.remove(legacy.original)
        self.assert_blocked(legacy, "file missing on disk")

    def test_an_unreadable_file_blocks_the_media(self):
        legacy = self.build()
        with patch("files.path_migrate.os.access", return_value=False):
            eligible, reason = can_migrate_media_paths(legacy.media)
        self.assertFalse(eligible)
        self.assertIn("not readable", reason)

    def test_a_dangling_symlink_blocks_the_media(self):
        legacy = self.build(original_symlink_to=os.path.join(self.archive_dir, "gone.png"))
        self.assert_blocked(legacy, "symlink target is missing")

    def test_a_missing_hls_playlist_blocks_the_media(self):
        legacy = self.build()
        os.remove(legacy.hls_master)
        self.assert_blocked(legacy, "master playlist missing")

    def test_a_pending_or_running_encode_blocks_the_media(self):
        for status in ("pending", "running"):
            with self.subTest(status=status):
                legacy = self.build()
                Encoding.objects.filter(media=legacy.media, chunk=False).exclude(profile__name="preview").update(status=status)
                self.assert_blocked(legacy, status)

    def test_a_running_media_encoding_status_blocks_the_media(self):
        legacy = self.build()
        Media.objects.filter(pk=legacy.media.pk).update(encoding_status="running")
        self.assert_blocked(legacy, "encoding is running")

    def test_hls_packaging_in_progress_blocks_the_media(self):
        legacy = self.build()
        lock_key = tasks._hls_lock_key(legacy.media.uid.hex)
        cache.set(lock_key, "1", timeout=60)
        self.addCleanup(cache.delete, lock_key)
        self.assert_blocked(legacy, "HLS packaging is in progress")

    def test_a_foreign_file_at_a_destination_blocks_the_media(self):
        legacy = self.build()
        destination = write_media_file(f"thumbnails/{legacy.media.uid.hex[0:2]}/{legacy.media.uid.hex[2:4]}/{legacy.media.uid.hex}/poster.jpg", b"someone else")
        eligible, reason = can_migrate_media_paths(legacy.media)
        self.assertFalse(eligible)
        self.assertIn("destination already exists", reason)
        result = migrate_media_paths(legacy.media, user=self.manager)
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertEqual(read_file(destination), b"someone else")
        self.assert_legacy_intact(legacy)

    def test_two_references_that_map_to_one_destination_block_the_media(self):
        legacy = self.build()
        legacy_copy_name = f"encoded/{legacy.video_profile.id}/path_migrate_owner/{legacy.media.uid.hex}.second.mp4"
        write_media_file(legacy_copy_name, b"encoded-mp4-" * 128)
        Encoding.objects.bulk_create([Encoding(media=legacy.media, profile=legacy.video_profile, status="success", progress=100, media_file=legacy_copy_name)])
        self.assert_blocked(legacy, "destination collides")

    def test_a_preview_that_matches_no_encoding_blocks_the_media(self):
        legacy = self.build()
        stray = write_media_file("encoded/stray/preview.gif", b"GIF89a")
        self.addCleanup(os.remove, stray)
        Media.objects.filter(pk=legacy.media.pk).update(preview_file_path=stray)
        self.assert_blocked(legacy, "preview_file_path does not match")

    def test_a_hls_tree_outside_the_known_layouts_blocks_the_media(self):
        legacy = self.build()
        odd = write_media_file("hls/odd-place/master.m3u8", b"#EXTM3U\n")
        self.addCleanup(shutil.rmtree, os.path.dirname(odd), True)
        Media.objects.filter(pk=legacy.media.pk).update(hls_file=odd)
        self.assert_blocked(legacy, "unexpected HLS directory")

    def test_a_concurrent_migration_is_refused(self):
        legacy = self.build()
        lock_key = f"path_migrate_lock_{legacy.media.uid.hex}"
        cache.set(lock_key, "1", timeout=60)
        self.addCleanup(cache.delete, lock_key)
        result = migrate_media_paths(legacy.media, user=self.manager)
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertIn("already running", result.reason)
        self.assert_legacy_intact(legacy)

    def test_a_failed_encode_whose_file_is_gone_does_not_block(self):
        legacy = self.build()
        profile = legacy.video_profile
        gone = f"encoded/{profile.id}/path_migrate_owner/{legacy.media.uid.hex}.failed.mp4"
        Encoding.objects.bulk_create([Encoding(media=legacy.media, profile=profile, status="fail", progress=100, media_file=gone)])
        result = migrate_media_paths(legacy.media, user=self.manager)
        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        self.assertEqual(Encoding.objects.get(media=legacy.media, status="fail").media_file.name, gone)


class SymlinkSafetyTests(PathMigrateBase):
    def test_a_symlinked_original_is_recreated_with_the_same_target(self):
        archive = self.archive_file()
        legacy = self.build(original_symlink_to=archive)

        result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        media = Media.objects.get(pk=legacy.media.pk)
        self.assertTrue(media.media_file.name.endswith("/source.png"))
        self.assertTrue(os.path.islink(media.media_file.path))
        self.assertEqual(os.readlink(media.media_file.path), archive)
        self.assertEqual(read_file(media.media_file.path), ORIGINAL_BYTES)
        self.assertFalse(os.path.lexists(legacy.original))
        self.assertEqual(read_file(archive), ORIGINAL_BYTES)

    def test_a_relative_symlink_target_is_made_absolute_not_broken(self):
        archive = self.archive_file()
        legacy = self.build()
        os.remove(legacy.original)
        os.symlink(os.path.relpath(archive, os.path.dirname(legacy.original)), legacy.original)

        result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        media = Media.objects.get(pk=legacy.media.pk)
        self.assertEqual(os.readlink(media.media_file.path), archive)
        self.assertEqual(read_file(media.media_file.path), ORIGINAL_BYTES)

    def test_removing_the_legacy_layout_never_follows_a_symlink_to_the_archive(self):
        archive = self.archive_file()
        archive_segment = self.archive_file("segment.ts", SEGMENT_BYTES)
        legacy = self.build(original_symlink_to=archive, hls_symlink_to=archive_segment)

        result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        self.assertEqual(read_file(archive), ORIGINAL_BYTES)
        self.assertEqual(read_file(archive_segment), SEGMENT_BYTES)
        self.assertFalse(os.path.exists(legacy.hls_dir))
        moved_link = os.path.join(media_uid_dir("hls", legacy.media.uid), "media-240", "archive.ts")
        self.assertTrue(os.path.islink(moved_link))
        self.assertEqual(os.readlink(moved_link), archive_segment)

    def test_a_failed_migration_leaves_the_symlink_and_the_archive_alone(self):
        archive = self.archive_file()
        legacy = self.build(original_symlink_to=archive)

        with patch("files.path_migrate._reverify", return_value=["boom"]):
            result = migrate_media_paths(legacy.media, user=self.manager)

        self.assertEqual(result.status, STATUS_FAILED)
        self.assertTrue(os.path.islink(legacy.original))
        self.assertEqual(os.readlink(legacy.original), archive)
        self.assertEqual(read_file(archive), ORIGINAL_BYTES)
        self.assert_no_sharded_files(legacy.media)

    def test_a_symlink_that_already_staged_is_reused_not_clobbered(self):
        archive = self.archive_file()
        legacy = self.build(original_symlink_to=archive)
        media = legacy.media
        staged = media_path(f"original/{media.uid.hex[0:2]}/{media.uid.hex[2:4]}/{media.uid.hex}/source.png")
        os.makedirs(os.path.dirname(staged))
        os.symlink(archive, staged)

        result = migrate_media_paths(media, user=self.manager)

        self.assertEqual(result.status, STATUS_MIGRATED, result.reason)
        self.assertEqual(os.readlink(staged), archive)


class BulkTaskTests(PathMigrateBase):
    def test_the_task_migrates_one_media_and_reports_the_result(self):
        legacy = self.build()
        outcome = tasks.migrate_media_paths_task(legacy.media.friendly_token, self.manager.pk)
        self.assertEqual(outcome["status"], STATUS_MIGRATED)
        self.assertEqual(outcome["friendly_token"], legacy.media.friendly_token)
        event = MediaAction.objects.get(media=legacy.media, action="path_migrated")
        self.assertEqual(event.user_id, self.manager.pk)

    def test_the_task_reports_a_missing_media_without_raising(self):
        outcome = tasks.migrate_media_paths_task("does-not-exist")
        self.assertEqual(outcome["status"], STATUS_FAILED)

    def test_bulk_fans_out_and_one_failure_does_not_stop_the_rest(self):
        good = self.build()
        broken = build_legacy_media(self.owner, title="broken")
        self.addCleanup(self.cleanup_media, broken.media)
        os.remove(broken.sprites)
        other = build_legacy_media(self.owner, title="another good")
        self.addCleanup(self.cleanup_media, other.media)

        outcome = tasks.migrate_media_paths_bulk([good.media.friendly_token, broken.media.friendly_token, other.media.friendly_token, good.media.friendly_token], self.manager.pk)

        self.assertEqual(outcome, {"queued": 3})
        self.assertTrue(Media.objects.get(pk=good.media.pk).media_file.name.endswith("/source.png"))
        self.assertTrue(Media.objects.get(pk=other.media.pk).media_file.name.endswith("/source.png"))
        self.assertIn("/user/", Media.objects.get(pk=broken.media.pk).media_file.name)
        self.assertTrue(os.path.exists(broken.original))


class RecordedActionTests(PathMigrateBase):
    def test_path_migrated_is_a_moderation_action(self):
        media = create_media(self.owner, title="action check")
        self.addCleanup(self.cleanup_media, media)
        self.assertIsNotNone(record_moderation_action(self.manager, media, "path_migrated", extra_info="x"))
