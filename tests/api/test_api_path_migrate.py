import os
import uuid

from django.contrib import admin
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from actions.models import MediaAction
from files.models import Media
from files.tests import create_account
from tests._support.legacy_media import build_legacy_media, clear_sharded_files

BULK_URL = "/api/v1/manage_media/migrate_paths"


def single_url(media):
    return f"/api/v1/manage_media/{media.friendly_token}/migrate_paths"


def make_user(**kwargs):
    name = uuid.uuid4().hex[:12]
    return create_account(username=f"pm{name}", email=f"{name}@example.com", **kwargs)


def logged_in(user):
    client = Client()
    client.force_login(user)
    return client


def migrated(media):
    return "/user/" not in Media.objects.get(pk=media.pk).media_file.name


class PathMigrateApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user()
        cls.regular = make_user()
        cls.editor = make_user(is_editor=True)
        cls.manager = make_user(is_manager=True)
        cls.admin = make_user(is_superuser=True)

    def build(self, **kwargs):
        legacy = build_legacy_media(self.owner, **kwargs)
        self.addCleanup(clear_sharded_files, legacy.media)
        return legacy


class PathMigrateApiAccessTests(PathMigrateApiTestCase):
    def test_anonymous_and_regular_users_are_denied(self):
        legacy = self.build()
        for client in (Client(), logged_in(self.regular), logged_in(self.owner)):
            for method, url in (("get", single_url(legacy.media)), ("post", single_url(legacy.media)), ("post", BULK_URL)):
                with self.subTest(method=method, url=url):
                    response = getattr(client, method)(url, {"tokens": [legacy.media.friendly_token]}, content_type="application/json") if method == "post" else client.get(url)
                    self.assertEqual(response.status_code, 403)
        self.assertFalse(migrated(legacy.media))

    def test_editors_are_denied_because_this_deletes_files(self):
        legacy = self.build()
        client = logged_in(self.editor)
        self.assertEqual(client.get(single_url(legacy.media)).status_code, 403)
        self.assertEqual(client.post(single_url(legacy.media), content_type="application/json").status_code, 403)
        self.assertEqual(client.post(BULK_URL, {"tokens": [legacy.media.friendly_token]}, content_type="application/json").status_code, 403)
        self.assertFalse(migrated(legacy.media))
        self.assertTrue(os.path.isfile(legacy.original))


class SinglePathMigrateApiTests(PathMigrateApiTestCase):
    def test_get_reports_eligibility_without_changing_anything(self):
        legacy = self.build()
        response = logged_in(self.manager).get(single_url(legacy.media))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"friendly_token": legacy.media.friendly_token, "eligible": True, "already_migrated": False, "reason": ""})
        self.assertFalse(migrated(legacy.media))

    def test_post_migrates_and_reports_the_move(self):
        legacy = self.build()
        for user in (self.manager, self.admin):
            with self.subTest(user=user.username):
                fresh = self.build()
                response = logged_in(user).post(single_url(fresh.media), content_type="application/json")
                self.assertEqual(response.status_code, 200, response.content)
                body = response.json()
                self.assertEqual((body["status"], body["moved"]), ("migrated", 12))
                self.assertTrue(migrated(fresh.media))
                self.assertFalse(os.path.exists(fresh.original))
                self.assertEqual(MediaAction.objects.get(media=fresh.media, action="path_migrated").user_id, user.pk)
        self.assertFalse(migrated(legacy.media))

    def test_posting_again_is_a_skip_and_get_says_already_migrated(self):
        legacy = self.build()
        client = logged_in(self.manager)
        client.post(single_url(legacy.media), content_type="application/json")
        response = client.post(single_url(legacy.media), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "skipped")
        report = client.get(single_url(legacy.media)).json()
        self.assertEqual((report["eligible"], report["already_migrated"]), (False, True))

    def test_a_blocked_media_is_a_409_and_stays_on_the_old_layout(self):
        legacy = self.build()
        os.remove(legacy.sprites)
        client = logged_in(self.manager)
        response = client.post(single_url(legacy.media), content_type="application/json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["status"], "failed")
        self.assertIn("file missing on disk", response.json()["reason"])
        self.assertFalse(migrated(legacy.media))
        self.assertTrue(os.path.isfile(legacy.original))
        report = client.get(single_url(legacy.media)).json()
        self.assertFalse(report["eligible"])

    def test_unknown_media_is_a_404(self):
        client = logged_in(self.manager)
        self.assertEqual(client.get("/api/v1/manage_media/nope/migrate_paths").status_code, 404)
        self.assertEqual(client.post("/api/v1/manage_media/nope/migrate_paths", content_type="application/json").status_code, 404)


class BulkPathMigrateApiTests(PathMigrateApiTestCase):
    def test_bulk_queues_one_task_per_media_and_migrates_them(self):
        first = self.build()
        second = self.build()
        response = logged_in(self.manager).post(
            BULK_URL,
            {"tokens": [first.media.friendly_token, second.media.friendly_token, first.media.friendly_token, "missing-token"]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 202, response.content)
        body = response.json()
        self.assertEqual(body["queued"], 2)
        self.assertEqual(body["unknown"], ["missing-token"])
        self.assertTrue(body["task_id"])
        self.assertTrue(migrated(first.media))
        self.assertTrue(migrated(second.media))
        self.assertEqual(MediaAction.objects.filter(action="path_migrated", user=self.manager).count(), 2)

    def test_bulk_failures_leave_that_media_on_the_old_layout(self):
        good = self.build()
        broken = self.build()
        os.remove(broken.hls_master)
        response = logged_in(self.admin).post(BULK_URL, {"tokens": [good.media.friendly_token, broken.media.friendly_token]}, content_type="application/json")
        self.assertEqual(response.status_code, 202)
        self.assertTrue(migrated(good.media))
        self.assertFalse(migrated(broken.media))
        self.assertTrue(os.path.isfile(broken.original))

    def test_bulk_rejects_bad_bodies(self):
        client = logged_in(self.manager)
        for body in ({}, {"tokens": []}, {"tokens": "abc"}, {"tokens": [1, 2]}, {"tokens": [""]}, [1]):
            with self.subTest(body=body):
                self.assertEqual(client.post(BULK_URL, body, content_type="application/json").status_code, 400)

    def test_bulk_caps_the_batch_size(self):
        tokens = [f"t{i}" for i in range(501)]
        response = logged_in(self.manager).post(BULK_URL, {"tokens": tokens}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_bulk_with_only_unknown_tokens_queues_nothing(self):
        response = logged_in(self.manager).post(BULK_URL, {"tokens": ["a-missing", "b-missing"]}, content_type="application/json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["queued"], 0)


@override_settings(SECURE_SSL_REDIRECT=False)
class PathMigrateAdminActionTests(PathMigrateApiTestCase):
    def test_action_is_for_managers_and_superusers_only(self):
        model_admin = admin.site._registry[Media]
        for user, expected in ((self.editor, False), (self.regular, False), (self.manager, True), (self.admin, True)):
            request = RequestFactory().get("/admin/")
            request.user = user
            with self.subTest(user=user.username):
                self.assertEqual("migrate_media_paths" in model_admin.get_actions(request), expected)

    def test_confirmation_page_lists_what_can_and_cannot_migrate(self):
        ready = self.build()
        blocked = self.build()
        os.remove(blocked.sprites)
        response = logged_in(self.admin).post(
            reverse("admin:files_media_changelist"),
            {"action": "migrate_media_paths", "_selected_action": [ready.media.pk, blocked.media.pk]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, ready.media.friendly_token)
        self.assertContains(response, "file missing on disk")
        self.assertFalse(migrated(ready.media))

    def test_applying_queues_the_eligible_media_and_migrates_them(self):
        ready = self.build()
        blocked = self.build()
        os.remove(blocked.sprites)
        response = logged_in(self.admin).post(
            reverse("admin:files_media_changelist"),
            {"action": "migrate_media_paths", "apply": "1", "_selected_action": [ready.media.pk, blocked.media.pk]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(migrated(ready.media))
        self.assertFalse(migrated(blocked.media))
        self.assertEqual(MediaAction.objects.get(media=ready.media, action="path_migrated").user_id, self.admin.pk)

    def test_applying_with_nothing_eligible_changes_nothing(self):
        blocked = self.build()
        os.remove(blocked.sprites)
        response = logged_in(self.admin).post(
            reverse("admin:files_media_changelist"),
            {"action": "migrate_media_paths", "apply": "1", "_selected_action": [blocked.media.pk]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(migrated(blocked.media))
