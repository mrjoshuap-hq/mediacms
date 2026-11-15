"""Server enforcement for media action feature flags."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from files.tests import create_account, create_media


class MediaActionFeatureFlagsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_account()
        cls.media = create_media(cls.user, title="feature flag media", state="public")

    def post_action(self, action):
        client = APIClient()
        client.force_authenticate(self.user)
        return client.post(f"/api/v1/media/{self.media.friendly_token}/actions", {"type": action}, format="json")

    @override_settings(CAN_LIKE_MEDIA=False)
    def test_like_is_refused_when_disabled(self):
        self.assertEqual(self.post_action("like").status_code, 400)

    @override_settings(CAN_DISLIKE_MEDIA=False)
    def test_dislike_is_refused_when_disabled(self):
        self.assertEqual(self.post_action("dislike").status_code, 400)

    @override_settings(CAN_REPORT_MEDIA=False)
    def test_report_is_refused_when_disabled(self):
        self.assertEqual(self.post_action("report").status_code, 400)

    @override_settings(CAN_LIKE_MEDIA=True)
    def test_like_is_accepted_when_enabled(self):
        self.assertEqual(self.post_action("like").status_code, 201)
