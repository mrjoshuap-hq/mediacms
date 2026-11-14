"""Sparse config × role × surface access matrix for permission alignment."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from files.models import Category, MediaPermission
from files.tests import create_account, create_media
from rbac.models import RBACGroup, RBACMembership

MEDIA_LIST_URL = "/api/v1/media"
SEARCH_URL = "/api/v1/search"


@override_settings(MEDIA_IS_REVIEWED=False)
class MediaIsReviewedListingSurfacesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_account()
        cls.stranger = create_account()
        cls.shared = create_account()
        cls.editor = create_account(is_editor=True)
        cls.category = Category.objects.create(title="review matrix category")
        cls.media = create_media(
            cls.owner,
            title="unreviewed matrix media",
            state="public",
            encoding_status="success",
            is_reviewed=False,
            category=[cls.category],
        )
        cls.media.update_search_vector()
        MediaPermission.objects.create(owner_user=cls.owner, user=cls.shared, media=cls.media, permission="viewer")

    def test_unreviewed_media_is_absent_from_anonymous_list_and_search(self):
        self.assertFalse(self.media.listable)
        listing = APIClient().get(MEDIA_LIST_URL)
        self.assertNotIn(self.media.title, [item["title"] for item in listing.data["results"]])
        search = APIClient().get(SEARCH_URL, {"q": "unreviewed matrix"})
        self.assertEqual(search.status_code, 200)
        titles = [item["title"] for item in search.data.get("results", [])]
        self.assertNotIn(self.media.title, titles)

    def test_unreviewed_media_is_absent_from_category_search_for_strangers(self):
        search = APIClient().get(SEARCH_URL, {"c": self.category.uid})
        self.assertEqual(search.status_code, 200)
        titles = [item["title"] for item in search.data.get("results", [])]
        self.assertNotIn(self.media.title, titles)

    def test_owner_and_shared_and_editor_can_open_unreviewed_media(self):
        detail = f"/api/v1/media/{self.media.friendly_token}"
        for user in (self.owner, self.shared, self.editor):
            client = APIClient()
            client.force_authenticate(user)
            with self.subTest(user=user.username):
                self.assertEqual(client.get(detail).status_code, 200)

    def test_manager_can_review_like_editor(self):
        manager = create_account(is_manager=True)
        client = APIClient()
        client.force_authenticate(manager)
        response = client.post(f"/api/v1/media/{self.media.friendly_token}", {"type": "review", "result": "true"}, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.media.refresh_from_db()
        self.assertTrue(self.media.is_reviewed)
        self.assertTrue(self.media.listable)


@override_settings(USERS_NEEDS_TO_BE_APPROVED=True, CAN_ADD_MEDIA="all", CAN_COMMENT="all")
class PendingWriteMatrixTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pending = create_account()
        cls.pending.is_approved = False
        cls.pending.save()
        cls.owner = create_account()
        cls.owner.is_approved = True
        cls.owner.save()
        cls.media = create_media(cls.owner, title="pending write target", state="public")

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.pending)

    def test_pending_cannot_comment(self):
        response = self.client.post(f"/api/v1/media/{self.media.friendly_token}/comments", {"text": "nope"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_pending_cannot_like(self):
        response = self.client.post(f"/api/v1/media/{self.media.friendly_token}/actions", {"type": "like"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_pending_cannot_delete_media(self):
        own = create_media(self.pending, title="pending owned", state="private")
        response = self.client.delete(f"/api/v1/media/{own.friendly_token}")
        self.assertEqual(response.status_code, 403)

    def test_pending_editor_cannot_open_manage_apis(self):
        editor = create_account(is_editor=True)
        editor.is_approved = False
        editor.save()
        client = APIClient()
        client.force_authenticate(editor)
        self.assertEqual(client.get("/api/v1/manage_media").status_code, 403)
        self.assertEqual(client.get("/api/v1/manage_comments").status_code, 403)


@override_settings(USE_RBAC=True)
class RbacWriteMatrixTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = create_account()
        cls.member = create_account()
        cls.contributor = create_account()
        cls.manager = create_account()
        cls.category = Category.objects.create(title="rbac write category", is_rbac_category=True)
        cls.media = create_media(cls.owner, title="rbac write media", state="private", category=[cls.category])
        group = RBACGroup.objects.create(name="rbac write group")
        group.categories.add(cls.category)
        RBACMembership.objects.create(user=cls.member, rbac_group=group, role="member")
        RBACMembership.objects.create(user=cls.contributor, rbac_group=group, role="contributor")
        RBACMembership.objects.create(user=cls.manager, rbac_group=group, role="manager")

    def detail(self):
        return f"/api/v1/media/{self.media.friendly_token}"

    def test_member_can_read_but_not_put_or_delete(self):
        client = APIClient()
        client.force_authenticate(self.member)
        self.assertEqual(client.get(self.detail()).status_code, 200)
        self.assertIn(client.put(self.detail(), {"title": "member edit"}, format="multipart").status_code, (400, 401))
        self.assertIn(client.delete(self.detail()).status_code, (400, 401))

    def test_contributor_can_put_but_not_delete_or_change_state(self):
        client = APIClient()
        client.force_authenticate(self.contributor)
        self.assertEqual(client.put(self.detail(), {"title": "contributor edit"}, format="multipart").status_code, 201)
        self.assertEqual(client.put(self.detail(), {"state": "unlisted"}, format="multipart").status_code, 400)
        self.assertIn(client.delete(self.detail()).status_code, (400, 401))

    def test_rbac_manager_can_put_and_delete(self):
        client = APIClient()
        client.force_authenticate(self.manager)
        self.assertEqual(client.put(self.detail(), {"title": "manager edit"}, format="multipart").status_code, 201)
        media = create_media(self.owner, title="rbac delete target", state="private", category=[self.category])
        self.assertEqual(client.delete(f"/api/v1/media/{media.friendly_token}").status_code, 204)
