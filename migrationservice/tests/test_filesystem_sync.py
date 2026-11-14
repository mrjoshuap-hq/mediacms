import os
import shutil
import tempfile
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from actions.models import MediaAction
from files.models import Category, EncodeProfile, Encoding, Media, Subtitle
from files.tests import create_account
from migrationservice.models import MigrationRecord, MigrationService
from migrationservice.providers.filesystem import FilesystemProvider
from migrationservice.tasks import (
    ReconcileAborted,
    create_encoding,
    list_reconcile_page,
    migrate_item,
    restart_migration,
    start_migration,
)

IMAGE = os.path.join(settings.BASE_DIR, "fixtures", "test_image.png")
IMAGE2 = os.path.join(settings.BASE_DIR, "fixtures", "test_image2.jpg")
VIDEO = os.path.join(settings.BASE_DIR, "fixtures", "small_video.mp4")
VTT = b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello\n"


class SyncTestCase(TestCase):
    fixtures = ["fixtures/encoding_profiles.json"]

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="fs-sync-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.root = os.path.join(self.base, "root")
        self.mount = os.path.join(self.root, "lib")
        os.makedirs(self.mount)
        override = override_settings(FILESYSTEM_IMPORT_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)

        self.admin = create_account(username="admin")
        self.owner = create_account(username="librarian")
        self.starter = create_account(username="starter", is_superuser=True)

    def put(self, relpath, source=IMAGE):
        path = os.path.join(self.mount, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        shutil.copyfile(source, path)
        return path

    def service(self, **options):
        defaults = {"fallback_username": "librarian", "initiated_by": "starter"}
        defaults.update(options)
        return MigrationService.objects.create(name="Archive", provider="filesystem", connection={"mount": "lib", "subpath": ""}, options=defaults)

    def run_sync(self, service, rerun=False):
        (restart_migration if rerun else start_migration)(service)
        service.refresh_from_db()
        return service

    def records(self, service, **filters):
        return MigrationRecord.objects.filter(service=service, object_type="media", **filters)

    def original_path(self, media):
        return os.path.join(settings.MEDIA_ROOT, media.media_file.name)

    def media_for(self, source_id, service):
        return Media.objects.get(pk=self.records(service).get(source_id=source_id).target_id)


class TestIngest(SyncTestCase):
    def test_a_library_is_imported_into_sharded_paths_with_an_explicit_title(self):
        self.put("Lecture One.png")
        service = self.run_sync(self.service())

        self.assertEqual(service.status, "success")
        media = Media.objects.get()
        self.assertEqual(media.title, "Lecture One")
        self.assertEqual(media.user, self.owner)
        shard = media.uid.hex
        self.assertEqual(media.media_file.name, f"original/{shard[0:2]}/{shard[2:4]}/{shard}/source.png")
        self.assertTrue(os.path.isfile(self.original_path(media)))
        self.assertNotIn("lib", media.media_file.name)
        record = self.records(service).get()
        self.assertEqual((record.source_id, record.status, record.target_id), ("Lecture One.png", "success", media.id))
        self.assertEqual(service.source_system, "filesystem:lib")

    def test_ingest_shares_the_bytes_when_it_can_and_never_touches_the_source_on_delete(self):
        source = self.put("a.png")
        service = self.run_sync(self.service())
        media = Media.objects.get()
        path = self.original_path(media)

        self.assertFalse(os.path.islink(path))
        self.assertEqual(os.stat(path).st_ino, os.stat(source).st_ino)

        media.delete()
        self.assertFalse(os.path.exists(path))
        self.assertTrue(os.path.isfile(source))
        self.assertEqual(os.stat(source).st_size, os.stat(IMAGE).st_size)
        self.assertEqual(service.status, "success")

    def test_ingest_falls_back_to_a_copy_and_deleting_it_leaves_the_source(self):
        source = self.put("a.png")
        with mock.patch("os.link", side_effect=OSError("cross-device link")):
            self.run_sync(self.service())
        media = Media.objects.get()
        path = self.original_path(media)

        self.assertNotEqual(os.stat(path).st_ino, os.stat(source).st_ino)
        self.assertIn("(copy)", self.records(MigrationService.objects.get()).get().log)
        media.delete()
        self.assertFalse(os.path.exists(path))
        self.assertTrue(os.path.isfile(source))

    def test_the_owner_is_required_and_nobody_else_is_substituted(self):
        self.put("a.png")
        service = self.service(fallback_username="")
        service = self.run_sync(service)

        self.assertEqual(Media.objects.count(), 0)
        self.assertEqual(self.records(service, status="failed").count(), 1)
        self.assertIn("no owner", self.records(service).get().log)

    def test_an_owner_who_no_longer_exists_fails_the_item(self):
        self.put("a.png")
        service = self.service(fallback_username="ghost")
        service = self.run_sync(service)
        self.assertEqual(Media.objects.count(), 0)
        self.assertIn("not a MediaCMS user", self.records(service).get().log)

    def test_the_import_is_audited_to_whoever_started_it(self):
        self.put("a.png")
        service = self.run_sync(self.service())
        action = MediaAction.objects.get(action="fs_imported")
        self.assertEqual(action.media, Media.objects.get())
        self.assertEqual(action.user, self.starter)
        self.assertIn("filesystem:lib:a.png", action.extra_info)
        self.assertEqual(service.counted_totals()["media_migrated"], 1)

    def test_the_audit_has_no_actor_when_nobody_started_it(self):
        self.put("a.png")
        service = self.service()
        MigrationService.objects.filter(pk=service.pk).update(options={"fallback_username": "librarian"})
        self.run_sync(service)
        self.assertIsNone(MediaAction.objects.get(action="fs_imported").user)

    def test_no_admin_notification_is_sent(self):
        self.put("a.png")
        with mock.patch("files.methods.notify_users") as notify:
            self.run_sync(self.service())
        notify.assert_not_called()
        self.assertEqual(Media.objects.count(), 1)

    def test_sidecar_captions_are_attached_as_subtitles(self):
        self.put("talk.png")
        with open(os.path.join(self.mount, "talk.vtt"), "wb") as out:
            out.write(VTT)
        self.run_sync(self.service())
        subtitle = Subtitle.objects.get()
        shard = subtitle.media.uid.hex
        self.assertEqual(subtitle.language.code, "en")
        self.assertEqual(subtitle.subtitle_file.name, f"subtitles/{shard[0:2]}/{shard[2:4]}/{shard}/en.vtt")
        self.assertEqual(MigrationRecord.objects.filter(object_type="caption").count(), 1)

    def test_a_broken_caption_does_not_lose_the_media(self):
        self.put("talk.png")
        with open(os.path.join(self.mount, "talk.srt"), "wb") as out:
            out.write(b"1")
        with mock.patch("files.models.subtitle.Subtitle.convert_to_srt", side_effect=Exception("bad subs")):
            service = self.run_sync(self.service())
        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(Subtitle.objects.count(), 0)
        self.assertIn("caption failed", service.log)

    def test_categories_follow_the_folders_and_the_owner_owns_them(self):
        self.put("top.png")
        self.put("Physics/one.png", IMAGE2)
        service = self.run_sync(self.service())

        category = Category.objects.get(title="Physics")
        self.assertEqual(category.user, self.owner)
        self.assertEqual(category.description, "")
        self.assertEqual(list(self.media_for("Physics/one.png", service).category.all()), [category])
        self.assertEqual(self.media_for("top.png", service).category.count(), 0)
        self.assertEqual(MigrationRecord.objects.filter(service=service, object_type="category", status="success").count(), 1)

    def test_categories_can_be_switched_off(self):
        self.put("Physics/one.png")
        self.run_sync(self.service(categories_from_folders=False))
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(Media.objects.count(), 1)

    def test_a_folder_name_already_taken_gets_a_distinct_category(self):
        Category.objects.create(title="Physics")
        self.put("Physics/one.png")
        self.run_sync(self.service())
        self.assertEqual(Category.objects.count(), 2)
        self.assertEqual(Category.objects.exclude(title="Physics").count(), 1)

    def test_max_items_caps_new_imports(self):
        for name in ("a.png", "b.png", "c.png"):
            self.put(name)
        service = self.run_sync(self.service(max_items=2))
        self.assertEqual(service.status, "success")
        self.assertEqual(Media.objects.count(), 2)


class TestEncoding(SyncTestCase):
    def video_sync(self, **settings_override):
        self.put("clip.mp4", VIDEO)
        with override_settings(**settings_override), mock.patch.object(Media, "encode") as encode, mock.patch.object(Media, "set_thumbnail"), mock.patch.object(Media, "produce_sprite_from_video"):
            self.run_sync(self.service())
        return Media.objects.get(), encode

    def test_a_video_goes_through_the_normal_pipeline(self):
        media, encode = self.video_sync()
        encode.assert_called_once()
        self.assertFalse(getattr(media, "_do_not_transcode", False))
        self.assertEqual(media.media_type, "video")
        self.assertNotEqual(media.encoding_status, "success")

    def test_only_the_global_setting_skips_encoding(self):
        media, encode = self.video_sync(DO_NOT_TRANSCODE_VIDEO=True)
        encode.assert_not_called()
        self.assertEqual(media.encoding_status, "success")

    def test_the_title_is_never_the_stored_name(self):
        media, _encode = self.video_sync()
        self.assertEqual(media.title, "clip")
        self.assertTrue(media.media_file.name.endswith("/source.mp4"))


class TestPreserve(SyncTestCase):
    def test_preserve_symlinks_to_the_source_and_deleting_the_media_leaves_it(self):
        source = self.put("a.png")
        service = self.run_sync(self.service(storage_mode="preserve"))
        media = Media.objects.get()
        path = self.original_path(media)

        self.assertTrue(os.path.islink(path))
        self.assertEqual(os.path.realpath(path), os.path.realpath(source))
        self.assertIn("(symlink)", self.records(service).get().log)
        self.assertTrue(os.path.basename(path).startswith("source"))

        media.delete()
        self.assertFalse(os.path.lexists(path))
        self.assertTrue(os.path.isfile(source))
        self.assertEqual(os.stat(source).st_size, os.stat(IMAGE).st_size)

    def test_preserve_refuses_a_source_that_escapes_the_mount(self):
        outside = os.path.join(self.base, "outside.png")
        shutil.copyfile(IMAGE, outside)
        os.symlink(outside, os.path.join(self.mount, "leak.png"))
        self.put("fine.png")
        self.run_sync(self.service(storage_mode="preserve"))
        self.assertEqual([media.title for media in Media.objects.all()], ["fine"])
        self.assertTrue(os.path.isfile(outside))

    def test_a_forged_source_id_cannot_reach_outside_the_mount(self):
        outside = os.path.join(self.base, "outside.png")
        shutil.copyfile(IMAGE, outside)
        service = self.service(storage_mode="preserve")
        MigrationService.objects.filter(pk=service.pk).update(status="running")
        result = migrate_item(service.pk, "media", "../../outside.png")
        self.assertEqual(result, "failed")
        self.assertEqual(Media.objects.count(), 0)
        self.assertTrue(os.path.isfile(outside))


class TestIdempotentRerun(SyncTestCase):
    def test_running_again_creates_no_duplicates(self):
        self.put("a.png")
        self.put("sub/b.png", IMAGE2)
        service = self.run_sync(self.service())
        before = sorted(Media.objects.values_list("pk", flat=True))
        records = list(MigrationRecord.objects.filter(service=service).order_by("pk").values_list("pk", "object_type", "source_id", "target_id"))

        for _ in range(2):
            service = self.run_sync(service, rerun=True)
            self.assertEqual(service.status, "success")

        self.assertEqual(sorted(Media.objects.values_list("pk", flat=True)), before)
        self.assertEqual(list(MigrationRecord.objects.filter(service=service).order_by("pk").values_list("pk", "object_type", "source_id", "target_id")), records)
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(MediaAction.objects.filter(action="fs_imported").count(), 2)

    def test_a_rerun_takes_only_the_new_files(self):
        self.put("a.png")
        service = self.run_sync(self.service())
        first = Media.objects.get()

        self.put("b.png", IMAGE2)
        service = self.run_sync(service, rerun=True)

        self.assertEqual(Media.objects.count(), 2)
        self.assertTrue(Media.objects.filter(pk=first.pk).exists())
        self.assertEqual(MediaAction.objects.filter(action="fs_imported").count(), 2)
        self.assertEqual(service.counted_totals()["media_migrated"], 2)

    def test_a_second_migration_over_the_same_mount_does_not_duplicate_either(self):
        self.put("a.png")
        self.run_sync(self.service())
        second = self.run_sync(self.service())
        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(self.records(second, status="skipped").count(), 1)

    def test_a_media_deleted_in_mediacms_is_imported_again_while_the_file_remains(self):
        self.put("a.png")
        service = self.run_sync(self.service())
        Media.objects.get().delete()

        self.run_sync(service, rerun=True)
        self.assertEqual(Media.objects.count(), 1)
        self.assertEqual(self.records(service).get().status, "success")

    def test_a_failed_item_is_retried(self):
        self.put("a.png")
        service = self.service(fallback_username="ghost")
        self.run_sync(service)
        self.assertEqual(self.records(service, status="failed").count(), 1)

        MigrationService.objects.filter(pk=service.pk).update(options={"fallback_username": "librarian"})
        service.refresh_from_db()
        self.run_sync(service, rerun=True)
        self.assertEqual(self.records(service, status="success").count(), 1)
        self.assertEqual(Media.objects.count(), 1)


class TestPrunePolicy(SyncTestCase):
    def synced(self, mode="ingest", source=IMAGE):
        path = self.put("a.png", source)
        # a library that still holds something: with nothing left reconcile refuses to prune
        self.keeper = self.put("keeper.png", IMAGE2)
        service = self.run_sync(self.service(storage_mode=mode))
        return service, path

    def add_playable_encoding(self, media):
        profile = EncodeProfile.objects.get(name="h264-720")
        return create_encoding(media, profile, VIDEO)

    def test_a_missing_source_with_no_encodings_deletes_the_media(self):
        service, source = self.synced()
        media = self.media_for("a.png", service)
        path = self.original_path(media)
        token = media.friendly_token
        os.remove(source)

        with mock.patch("migrationservice.tasks.record_moderation_action") as audit:
            service = self.run_sync(service, rerun=True)

        self.assertEqual([item.title for item in Media.objects.all()], ["keeper"])
        self.assertFalse(os.path.exists(path))
        audit.assert_called_once()
        self.assertEqual(audit.call_args.args[2], "fs_pruned")
        self.assertEqual(audit.call_args.args[0], self.starter)
        self.assertIn(token, service.log)
        record = self.records(service).get(source_id="a.png")
        self.assertEqual((record.status, record.target_id), ("skipped", None))
        self.assertTrue(record.log.startswith("fs_pruned"))
        totals = service.counted_totals()
        self.assertEqual((totals["media_pruned"], totals["media_skipped"], totals["media_original_gone"], totals["media_migrated"]), (1, 0, 0, 1))

    def test_pruning_a_preserve_import_never_touches_the_archive(self):
        service, source = self.synced(mode="preserve")
        self.assertEqual(Media.objects.count(), 2)
        os.remove(source)

        self.run_sync(service, rerun=True)
        self.assertEqual([media.title for media in Media.objects.all()], ["keeper"])
        self.assertTrue(os.path.isfile(self.keeper))
        self.assertEqual(os.stat(self.keeper).st_size, os.stat(IMAGE2).st_size)

    def test_a_pruned_file_that_comes_back_is_imported_again(self):
        service, source = self.synced()
        os.remove(source)
        service = self.run_sync(service, rerun=True)
        self.assertEqual(Media.objects.count(), 1)

        self.put("a.png")
        service = self.run_sync(service, rerun=True)
        self.assertEqual(Media.objects.count(), 2)
        self.assertEqual(self.records(service).get(source_id="a.png").status, "success")
        self.assertEqual(service.counted_totals()["media_pruned"], 0)

    def test_a_missing_source_with_playable_encodings_keeps_the_media(self):
        service, source = self.synced(mode="preserve")
        media = self.media_for("a.png", service)
        encoding = self.add_playable_encoding(media)
        path = self.original_path(media)
        os.remove(source)
        self.assertTrue(os.path.islink(path) and not os.path.exists(path))

        service = self.run_sync(service, rerun=True)

        self.assertEqual(Media.objects.count(), 2)
        self.assertTrue(Encoding.objects.filter(pk=encoding.pk, status="success").exists())
        self.assertTrue(os.path.isfile(encoding.media_file.path))
        # the dangling link was MediaCMS's own and is cleared, the archive was never involved
        self.assertFalse(os.path.lexists(path))
        action = MediaAction.objects.get(media=media, action="fs_original_gone")
        self.assertEqual(action.user, self.starter)
        record = self.records(service).get(source_id="a.png")
        self.assertEqual(record.status, "success")
        self.assertEqual(record.target_id, media.id)
        self.assertTrue(record.log.startswith("fs_original_gone"))
        totals = service.counted_totals()
        self.assertEqual((totals["media_original_gone"], totals["media_pruned"]), (1, 0))

    def test_original_gone_is_recorded_once_not_on_every_run(self):
        service, source = self.synced()
        self.add_playable_encoding(self.media_for("a.png", service))
        os.remove(source)
        for _ in range(3):
            service = self.run_sync(service, rerun=True)
        self.assertEqual(MediaAction.objects.filter(action="fs_original_gone").count(), 1)
        self.assertEqual(Media.objects.count(), 2)

    def test_an_ingested_copy_is_kept_untouched_when_the_media_is_kept(self):
        service, source = self.synced()
        media = self.media_for("a.png", service)
        self.add_playable_encoding(media)
        path = self.original_path(media)
        os.remove(source)
        self.run_sync(service, rerun=True)
        self.assertTrue(os.path.isfile(path))

    def test_a_non_playable_encoding_does_not_save_the_media(self):
        service, source = self.synced()
        media = self.media_for("a.png", service)
        # a preview and a failed encode are not something a viewer can play
        preview = EncodeProfile.objects.get(name="preview", extension="mp4")
        create_encoding(media, preview, VIDEO)
        failed = Encoding.objects.create(media=media, profile=EncodeProfile.objects.get(name="h264-480"), status="pending")
        Encoding.objects.filter(pk=failed.pk).update(status="fail")
        os.remove(source)

        self.run_sync(service, rerun=True)
        self.assertEqual([item.title for item in Media.objects.all()], ["keeper"])

    def test_a_pending_encode_defers_the_decision(self):
        service, source = self.synced()
        media = self.media_for("a.png", service)
        pending = Encoding.objects.create(media=media, profile=EncodeProfile.objects.get(name="h264-480"), status="pending")
        os.remove(source)

        service = self.run_sync(service, rerun=True)
        self.assertEqual(Media.objects.count(), 2)
        self.assertEqual(MediaAction.objects.filter(action__in=("fs_pruned", "fs_original_gone")).count(), 0)

        Encoding.objects.filter(pk=pending.pk).delete()
        self.run_sync(service, rerun=True)
        self.assertEqual([item.title for item in Media.objects.all()], ["keeper"])

    def test_files_outside_the_selected_subpath_are_not_pruned(self):
        self.put("a.png")
        self.put("keep/b.png", IMAGE2)
        service = self.run_sync(self.service())
        os.remove(os.path.join(self.mount, "a.png"))

        narrowed = self.service(initiated_by="starter")
        MigrationService.objects.filter(pk=narrowed.pk).update(connection={"mount": "lib", "subpath": "keep"})
        narrowed.refresh_from_db()
        # adopt the first run's records, as a second migration of the same mount would
        MigrationRecord.objects.filter(service=service).update(service=narrowed)
        self.run_sync(narrowed)
        self.assertEqual(Media.objects.count(), 2)


class TestEmptyMountAbort(SyncTestCase):
    def test_an_emptied_mount_prunes_nothing_and_the_run_ends_in_error(self):
        self.put("a.png")
        self.put("b.png", IMAGE2)
        service = self.run_sync(self.service())
        for name in ("a.png", "b.png"):
            os.remove(os.path.join(self.mount, name))

        service = self.run_sync(service, rerun=True)

        self.assertEqual(service.status, "error")
        self.assertIn("reconcile aborted, nothing was pruned", service.log)
        self.assertEqual(Media.objects.count(), 2)
        self.assertEqual(MediaAction.objects.filter(action__in=("fs_pruned", "fs_original_gone")).count(), 0)
        self.assertEqual(self.records(service, status="success").count(), 2)

    def test_a_mount_that_vanished_prunes_nothing(self):
        self.put("a.png")
        service = self.run_sync(self.service())
        shutil.rmtree(self.mount)

        service = self.run_sync(service, rerun=True)
        self.assertEqual(service.status, "error")
        self.assertEqual(Media.objects.count(), 1)

    def test_reconcile_itself_refuses_an_empty_mount(self):
        self.put("a.png")
        service = self.run_sync(self.service())
        os.remove(os.path.join(self.mount, "a.png"))
        provider = FilesystemProvider({"mount": "lib"}, {})
        with self.assertRaisesMessage(ReconcileAborted, "holds no media"):
            list_reconcile_page(service, provider, {}, 10)

    def test_reconcile_itself_refuses_an_unreadable_mount(self):
        self.put("a.png")
        service = self.run_sync(self.service())
        shutil.rmtree(self.mount)
        provider = FilesystemProvider({"mount": "lib"}, {})
        with self.assertRaisesMessage(ReconcileAborted, "cannot be read"):
            list_reconcile_page(service, provider, {}, 10)

    def test_an_empty_mount_with_nothing_imported_is_not_an_error(self):
        service = self.run_sync(self.service())
        self.assertEqual(service.status, "success")

    def test_a_mount_with_only_some_files_gone_does_prune_those(self):
        self.put("a.png")
        self.put("b.png", IMAGE2)
        service = self.run_sync(self.service())
        os.remove(os.path.join(self.mount, "a.png"))
        service = self.run_sync(service, rerun=True)
        self.assertEqual(service.status, "success")
        self.assertEqual([media.title for media in Media.objects.all()], ["b"])

    def test_the_cap_on_new_files_does_not_cancel_reconcile(self):
        self.put("a.png")
        self.put("b.png", IMAGE2)
        service = self.run_sync(self.service(max_items=2))
        os.remove(os.path.join(self.mount, "a.png"))
        service = self.run_sync(service, rerun=True)
        self.assertEqual(service.status, "success")
        self.assertEqual([media.title for media in Media.objects.all()], ["b"])
