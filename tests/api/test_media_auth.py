from io import BytesIO

from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.images import ImageFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from files.models import Category, Language, Media, MediaPermission, Subtitle
from files.models.utils import media_uid_shard_path
from files.tests import create_account
from rbac.models import RBACGroup, RBACMembership

MEDIA_AUTH_URL = '/api/v1/media-auth'


class MediaAuthTest(TestCase):
    fixtures = ["fixtures/categories.json", "fixtures/encoding_profiles.json"]

    def setUp(self):
        cache.clear()
        self.password = 'this_is_a_fake_password'
        self.owner = create_account(username='owner', password=self.password)
        self.other = create_account(username='other', password=self.password)

        with open('fixtures/test_image.png', 'rb') as fp:
            self.public_media = Media.objects.create(title='public image', user=self.other, media_file=File(fp))
        self.public_media.state = 'public'
        self.public_media.save()

        with open('fixtures/test_image.png', 'rb') as fp:
            self.private_media = Media.objects.create(title='private image', user=self.owner, media_file=File(fp))
        self.private_media.state = 'private'
        self.private_media.save()

        cache.clear()

    def _auth(self, uri, client=None):
        client = client or Client()
        return client.get(MEDIA_AUTH_URL, HTTP_X_ORIGINAL_URI=uri)

    @property
    def public_uid(self):
        return self.public_media.uid.hex

    @property
    def private_uid(self):
        return self.private_media.uid.hex

    def test_public_media_allowed_for_anonymous(self):
        uri = f'/media/encoded/{self.public_uid}/{self.public_uid}.mp4'
        self.assertEqual(self._auth(uri).status_code, 204)

    def test_private_media_denied_for_anonymous(self):
        uri = f'/media/encoded/23/owner/{self.private_uid}.mp4'
        self.assertEqual(self._auth(uri).status_code, 403)

    def test_private_media_allowed_for_owner(self):
        client = Client()
        client.login(username=self.owner.username, password=self.password)
        uri = f'/media/encoded/23/owner/{self.private_uid}.mp4'
        self.assertEqual(self._auth(uri, client).status_code, 204)

    def test_traversal_with_public_uid_is_denied(self):
        uri = f'/media/encoded/{self.public_uid}/..%2F23%2Fowner%2F{self.private_uid}.mp4'
        self.assertEqual(self._auth(uri).status_code, 403)

    def test_unencoded_traversal_is_denied(self):
        uri = f'/media/encoded/{self.public_uid}/../23/owner/{self.private_uid}.mp4'
        self.assertEqual(self._auth(uri).status_code, 403)

    def test_traversal_denied_even_for_authenticated_owner(self):
        client = Client()
        client.login(username=self.owner.username, password=self.password)
        uri = f'/media/encoded/{self.public_uid}/..%2F23%2Fowner%2F{self.private_uid}.mp4'
        self.assertEqual(self._auth(uri, client).status_code, 403)


class MediaAuthPathBindingTest(TestCase):
    """The decision must be bound to the file nginx will actually serve.

    nginx resolves the file from the path but hands this view the whole URI, query
    string included, so nothing outside the path may influence which media is
    authorized.
    """

    fixtures = ["fixtures/categories.json", "fixtures/encoding_profiles.json"]

    def setUp(self):
        cache.clear()
        self.password = "this_is_a_fake_password"
        self.owner = create_account(username="owner", password=self.password)
        self.stranger = create_account(username="stranger", password=self.password)
        self.hex_owner = create_account(username="f777c82f755df2d4bc9688d340b69292", password=self.password)

        with open("fixtures/test_image.png", "rb") as fp:
            self.public_media = Media.objects.create(title="public", user=self.stranger, media_file=File(fp))
        self.public_media.state = "public"
        self.public_media.save()

        with open("fixtures/test_image.png", "rb") as fp:
            self.private_media = Media.objects.create(title="private", user=self.owner, media_file=File(fp))
        self.private_media.state = "private"
        self.private_media.save()

        with open("fixtures/test_image.png", "rb") as fp:
            self.hex_media = Media.objects.create(title="migrated", user=self.hex_owner, media_file=File(fp))
        self.hex_media.state = "unlisted"
        self.hex_media.save()

        self.language = Language.objects.create(code="da", title="Danish")
        cache.clear()

    def _auth(self, uri, client=None):
        return (client or Client()).get(MEDIA_AUTH_URL, HTTP_X_ORIGINAL_URI=uri)

    def _login(self, user):
        client = Client()
        client.login(username=user.username, password=self.password)
        return client

    def _subtitle_for(self, media):
        subtitle = Subtitle(media=media, user=media.user, language=self.language)
        content = ContentFile(b"1\n00:00:01,000 --> 00:00:02,000\nhello\n")
        subtitle.subtitle_file.save(f"{media.friendly_token}-da.srt", content, save=False)
        subtitle.save()
        return subtitle

    def _legacy_subtitle_for(self, media):
        """A caption stored the way it was before sharding: original/subtitles/user/<owner>/..."""
        subtitle = self._subtitle_for(media)
        legacy_name = f"original/subtitles/user/{media.user.username}/{media.friendly_token}-da.srt"
        Subtitle.objects.filter(pk=subtitle.pk).update(subtitle_file=legacy_name)
        subtitle.refresh_from_db()
        return subtitle

    def test_a_uid_in_the_query_string_cannot_authorize_a_private_file(self):
        subtitle = self._subtitle_for(self.private_media)
        uri = f"/media/{subtitle.subtitle_file.name}?x={self.public_media.uid.hex}"
        self.assertEqual(self._auth(uri).status_code, 403)

    def test_a_uid_in_the_fragment_or_extra_segments_cannot_authorize(self):
        subtitle = self._subtitle_for(self.private_media)
        for suffix in [
            f"?{self.public_media.uid.hex}",
            f"?a=b&c={self.public_media.uid.hex}",
            f"?redirect=/media/encoded/23/stranger/{self.public_media.uid.hex}.mp4",
        ]:
            uri = f"/media/{subtitle.subtitle_file.name}{suffix}"
            self.assertEqual(self._auth(uri).status_code, 403, f"authorized via {suffix!r}")

    def test_a_query_string_does_not_change_an_honest_decision(self):
        uri = f"/media/encoded/23/stranger/{self.public_media.uid.hex}.mp4"
        self.assertEqual(self._auth(uri).status_code, 204)
        self.assertEqual(self._auth(f"{uri}?x={self.private_media.uid.hex}").status_code, 204)

    def test_a_private_path_stays_denied_however_the_url_is_dressed_up(self):
        base = f"/media/encoded/23/owner/{self.private_media.uid.hex}.mp4"
        for suffix in ["", f"?x={self.public_media.uid.hex}", f"#{self.public_media.uid.hex}"]:
            self.assertEqual(self._auth(base + suffix).status_code, 403, f"allowed via {suffix!r}")

    def test_a_username_that_looks_like_a_uid_is_not_read_as_one(self):
        """The reported 403: the owner's username is 32 hex characters and precedes
        the real uid in the path, so an unanchored search matched the username.
        """
        uri = f"/media/original/thumbnails/user/{self.hex_owner.username}/{self.hex_media.uid.hex}_Hp1Kdh8.jpg.jpg"
        self.assertEqual(self._auth(uri).status_code, 204)

    def test_a_hex_username_does_not_leak_a_private_media(self):
        private_hex = Media.objects.create(title="private migrated", user=self.hex_owner, media_file=self.hex_media.media_file)
        private_hex.state = "private"
        private_hex.save()
        cache.clear()
        uri = f"/media/original/thumbnails/user/{self.hex_owner.username}/{private_hex.uid.hex}_x.jpg.jpg"
        self.assertEqual(self._auth(uri).status_code, 403)
        self.assertEqual(self._auth(uri, self._login(self.hex_owner)).status_code, 204)

    def test_a_public_medias_subtitle_is_served(self):
        subtitle = self._subtitle_for(self.public_media)
        self.assertEqual(self._auth(f"/media/{subtitle.subtitle_file.name}").status_code, 204)

    def test_a_private_medias_subtitle_is_denied_for_anonymous(self):
        subtitle = self._subtitle_for(self.private_media)
        self.assertEqual(self._auth(f"/media/{subtitle.subtitle_file.name}").status_code, 403)

    def test_a_private_medias_subtitle_is_allowed_for_its_owner(self):
        subtitle = self._subtitle_for(self.private_media)
        uri = f"/media/{subtitle.subtitle_file.name}"
        self.assertEqual(self._auth(uri, self._login(self.owner)).status_code, 204)
        self.assertEqual(self._auth(uri, self._login(self.stranger)).status_code, 403)

    def test_an_invented_subtitle_path_is_denied(self):
        uri = "/media/original/subtitles/user/owner/does-not-exist-en.srt"
        self.assertEqual(self._auth(uri).status_code, 403)

    def test_a_legacy_subtitle_path_under_the_wrong_username_is_denied(self):
        subtitle = self._legacy_subtitle_for(self.public_media)
        self.assertEqual(self._auth(f"/media/{subtitle.subtitle_file.name}").status_code, 204)
        forged = subtitle.subtitle_file.name.replace("/stranger/", "/owner/")
        self.assertEqual(self._auth(f"/media/{forged}").status_code, 403)

    def test_an_hls_path_is_resolved_from_its_directory(self):
        uri = f"/media/hls/{self.public_media.uid.hex}/media-3/stream.m3u8"
        self.assertEqual(self._auth(uri).status_code, 204)

    def test_an_hls_path_of_a_private_media_is_denied(self):
        uri = f"/media/hls/{self.private_media.uid.hex}/media-3/stream.m3u8"
        self.assertEqual(self._auth(uri).status_code, 403)

    def test_an_original_file_is_resolved_from_its_filename(self):
        uri = f"/media/{self.public_media.media_file.name}"
        self.assertEqual(self._auth(uri).status_code, 204)

    def test_repeated_slashes_are_merged_like_nginx_does(self):
        for uri in [f"//media/{self.public_media.media_file.name}", f"/media//encoded/23/stranger/{self.public_media.uid.hex}.mp4"]:
            self.assertEqual(self._auth(uri).status_code, 204, uri)
        self.assertEqual(self._auth(f"//media/encoded/23/owner/{self.private_media.uid.hex}.mp4").status_code, 403)

    def test_an_unknown_uid_is_denied(self):
        self.assertEqual(self._auth(f"/media/encoded/23/owner/{'0' * 32}.mp4").status_code, 403)

    def test_a_path_with_no_resolvable_media_is_denied(self):
        for uri in [
            "/media/original/user/owner/not-a-uid.mp4",
            "/media/hls/not-a-uid/media-1/stream.m3u8",
            "/media/original/categories/abcdef1234567890.jpg",
            "/media/",
            "",
        ]:
            self.assertEqual(self._auth(uri).status_code, 403, f"allowed {uri!r}")


class CategoryPosterAuthTest(TestCase):
    """A category poster belongs to no media, so it is decided against its category"""

    fixtures = ["fixtures/categories.json", "fixtures/encoding_profiles.json"]

    def setUp(self):
        cache.clear()
        self.password = "this_is_a_fake_password"
        self.member = create_account(username="member", password=self.password)
        self.stranger = create_account(username="stranger", password=self.password)

        self.plain = Category.objects.create(title="Botany", thumbnail=self._poster())
        self.restricted = Category.objects.create(title="Staff only", thumbnail=self._poster(), is_rbac_category=True)

        group = RBACGroup.objects.create(uid="staff", name="Staff")
        group.categories.add(self.restricted)
        RBACMembership.objects.create(user=self.member, rbac_group=group, role="member")
        cache.clear()

    def _poster(self):
        with open("fixtures/test_image.png", "rb") as fp:
            return ImageFile(BytesIO(fp.read()), name="poster.png")

    def _auth(self, uri, client=None):
        return (client or Client()).get(MEDIA_AUTH_URL, HTTP_X_ORIGINAL_URI=uri)

    def _login(self, user):
        client = Client()
        client.login(username=user.username, password=self.password)
        return client

    def test_a_poster_is_served_to_anyone(self):
        self.assertEqual(self._auth(f"/media/{self.plain.thumbnail.name}").status_code, 204)

    def test_a_query_string_does_not_change_the_decision(self):
        uri = f"/media/{self.plain.thumbnail.name}?v=2"
        self.assertEqual(self._auth(uri).status_code, 204)

    def test_a_poster_no_category_holds_is_denied(self):
        self.assertEqual(self._auth("/media/original/categories/845689.made_up.jpg").status_code, 403)

    def test_traversal_out_of_the_posters_directory_is_denied(self):
        self.assertEqual(self._auth("/media/original/categories/../user/owner/secret.mp4").status_code, 403)

    @override_settings(USE_RBAC=True)
    def test_an_rbac_categorys_poster_follows_its_group(self):
        uri = f"/media/{self.restricted.thumbnail.name}"
        self.assertEqual(self._auth(uri).status_code, 403)
        cache.clear()
        self.assertEqual(self._auth(uri, self._login(self.stranger)).status_code, 403)
        cache.clear()
        self.assertEqual(self._auth(uri, self._login(self.member)).status_code, 204)

    @override_settings(USE_RBAC=False)
    def test_an_rbac_categorys_poster_is_public_with_rbac_off(self):
        self.assertEqual(self._auth(f"/media/{self.restricted.thumbnail.name}").status_code, 204)


@override_settings(USE_X_ACCEL_REDIRECT=False, SHOW_ORIGINAL_MEDIA=True)
class PdfViewTest(TestCase):
    fixtures = ["fixtures/categories.json", "fixtures/encoding_profiles.json"]
    content = b"%PDF-1.7\nexample document bytes\n%%EOF"

    def setUp(self):
        cache.clear()
        self.owner = create_account(username="pdfowner", password="test-password")
        self.stranger = create_account(username="pdfstranger", password="test-password")
        with open("fixtures/test_image.png", "rb") as file:
            self.media = Media.objects.create(title="document", user=self.owner, media_file=File(file))
        self.media.media_file.save("document.txt", ContentFile(self.content), save=False)
        Media.objects.filter(pk=self.media.pk).update(media_type="pdf", state="public", media_file=self.media.media_file.name)
        self.url = reverse("view_pdf", kwargs={"friendly_token": self.media.friendly_token})

    def test_pdf_mime_is_independent_of_filename(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn(".pdf", response["Content-Disposition"])
        self.assertTrue(response["Content-Disposition"].startswith("inline;"))
        self.assertEqual(response["Cache-Control"], "private")
        self.assertEqual(b"".join(response.streaming_content), self.content)

    def test_html_named_upload_is_served_as_pdf(self):
        self.media.media_file.save("payload.html", ContentFile(b"%PDF<script>alert(1)</script>"), save=False)
        Media.objects.filter(pk=self.media.pk).update(media_file=self.media.media_file.name)
        response = self.client.get(self.url)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertNotIn(".html", response["Content-Disposition"])
        list(response.streaming_content)

    def test_private_pdf_requires_permission_even_when_acceleration_is_disabled(self):
        Media.objects.filter(pk=self.media.pk).update(state="private")
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        list(response.streaming_content)

    def test_shared_private_pdf_is_accessible(self):
        Media.objects.filter(pk=self.media.pk).update(state="private")
        MediaPermission.objects.create(owner_user=self.owner, user=self.stranger, media=self.media, permission="viewer")
        self.client.force_login(self.stranger)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        list(response.streaming_content)

    @override_settings(USE_X_ACCEL_REDIRECT=True, DEVELOPMENT_MODE=True)
    def test_pdf_checks_current_visibility_after_public_access_is_cached(self):
        response = self.client.get(MEDIA_AUTH_URL, HTTP_X_ORIGINAL_URI=f"/media/{self.media.media_file.name}")
        self.assertEqual(response.status_code, 204)
        Media.objects.filter(pk=self.media.pk).update(state="private")
        self.assertEqual(self.client.get(self.url).status_code, 403)

    @override_settings(USE_RBAC=True)
    def test_rbac_member_can_view_private_pdf(self):
        Media.objects.filter(pk=self.media.pk).update(state="private")
        category = Category.objects.create(title="PDF staff", is_rbac_category=True)
        self.media.category.add(category)
        group = RBACGroup.objects.create(uid="pdf-staff", name="PDF staff")
        group.categories.add(category)
        RBACMembership.objects.create(user=self.stranger, rbac_group=group, role="member")
        self.client.force_login(self.stranger)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        list(response.streaming_content)

    @override_settings(USE_X_ACCEL_REDIRECT=True, DEVELOPMENT_MODE=False)
    def test_acceleration_uses_internal_pdf_location(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["X-Accel-Redirect"].startswith("/_protected_pdf/original/"))
        self.assertEqual(response["Content-Type"], "application/pdf")

    @override_settings(USE_X_ACCEL_REDIRECT=True, DEVELOPMENT_MODE=True)
    def test_development_streams_pdf_without_nginx(self):
        response = self.client.get(self.url)
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertEqual(b"".join(response.streaming_content), self.content)

    @override_settings(SHOW_ORIGINAL_MEDIA=False)
    def test_original_file_setting_is_respected(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_non_pdf_and_missing_file_are_not_served(self):
        Media.objects.filter(pk=self.media.pk).update(media_type="image")
        self.assertEqual(self.client.get(self.url).status_code, 404)
        Media.objects.filter(pk=self.media.pk).update(media_type="pdf", media_file="original/missing.pdf")
        self.assertEqual(self.client.get(self.url).status_code, 404)


class ShardedMediaAuthTest(TestCase):
    """New writes live at <kind>/<aa>/<bb>/<uid.hex>/<file>; legacy URLs must keep working"""

    fixtures = ["fixtures/categories.json", "fixtures/encoding_profiles.json"]

    def setUp(self):
        cache.clear()
        self.password = "this_is_a_fake_password"
        self.owner = create_account(username="owner", password=self.password)
        self.stranger = create_account(username="stranger", password=self.password)
        # a username that is itself a valid uid must never be read as the media's uid
        self.hex_owner = create_account(username="f777c82f755df2d4bc9688d340b69292", password=self.password)

        self.public_media = self._media("public", self.stranger, "public")
        self.unlisted_media = self._media("unlisted", self.stranger, "unlisted")
        self.private_media = self._media("private", self.owner, "private")
        self.language = Language.objects.create(code="en", title="English")
        cache.clear()

    def _media(self, title, user, state):
        with open("fixtures/test_image.png", "rb") as fp:
            media = Media.objects.create(title=title, user=user, media_file=File(fp))
        media.state = state
        media.save()
        return media

    def _auth(self, uri, client=None):
        return (client or Client()).get(MEDIA_AUTH_URL, HTTP_X_ORIGINAL_URI=uri)

    def _login(self, user):
        client = Client()
        client.login(username=user.username, password=self.password)
        return client

    @staticmethod
    def _sharded(kind, media, tail):
        return f"/media/{kind}/{media_uid_shard_path(media.uid)}/{tail}"

    def test_new_uploads_land_in_the_sharded_layout(self):
        media = self.public_media
        self.assertEqual(media.media_file.name, f"original/{media_uid_shard_path(media.uid)}/source.png")
        self.assertEqual(media.thumbnail.name, f"thumbnails/{media_uid_shard_path(media.uid)}/listing.jpg")
        self.assertEqual(media.poster.name, f"thumbnails/{media_uid_shard_path(media.uid)}/poster.jpg")

    def test_sharded_paths_of_every_kind_authorize_by_media_state(self):
        for kind, tail in [
            ("original", "source.mp4"),
            ("encoded", "3.mp4"),
            ("hls", "master.m3u8"),
            ("hls", "media-3/stream.m3u8"),
            ("thumbnails", "poster.jpg"),
            ("thumbnails", "listing.jpg"),
            ("thumbnails", "sprites.jpg"),
            ("thumbnails", "chapters/1.jpg"),
            ("subtitles", "en.vtt"),
        ]:
            for media in (self.public_media, self.unlisted_media):
                self.assertEqual(self._auth(self._sharded(kind, media, tail)).status_code, 204, f"{kind}/{tail}")
            uri = self._sharded(kind, self.private_media, tail)
            self.assertEqual(self._auth(uri).status_code, 403, f"anonymous allowed {kind}/{tail}")
            self.assertEqual(self._auth(uri, self._login(self.stranger)).status_code, 403, f"stranger allowed {kind}/{tail}")
            self.assertEqual(self._auth(uri, self._login(self.owner)).status_code, 204, f"owner denied {kind}/{tail}")
            cache.clear()

    def test_the_real_stored_names_of_a_private_media_are_gated(self):
        media = self.private_media
        for name in (media.media_file.name, media.thumbnail.name, media.poster.name):
            self.assertEqual(self._auth(f"/media/{name}").status_code, 403, name)
            self.assertEqual(self._auth(f"/media/{name}", self._login(self.owner)).status_code, 204, name)

    def test_a_stored_caption_is_resolved_by_its_sharded_directory(self):
        subtitle = Subtitle(media=self.private_media, user=self.owner, language=self.language)
        subtitle.subtitle_file.save("whatever.vtt", ContentFile(b"WEBVTT\n"), save=False)
        subtitle.save()
        self.assertEqual(subtitle.subtitle_file.name, f"subtitles/{media_uid_shard_path(self.private_media.uid)}/en.vtt")
        uri = f"/media/{subtitle.subtitle_file.name}"
        self.assertEqual(self._auth(uri).status_code, 403)
        self.assertEqual(self._auth(uri, self._login(self.owner)).status_code, 204)

    @staticmethod
    def _other_shard(shard):
        """A two-hex shard guaranteed to differ from `shard`"""
        return f"{(int(shard, 16) + 1) % 256:02x}"

    def test_shards_that_do_not_match_the_uid_are_denied(self):
        uid = self.public_media.uid.hex
        aa, bb = uid[0:2], uid[2:4]
        wrong_aa, wrong_bb = self._other_shard(aa), self._other_shard(bb)
        # swapped slots are only a mismatch when the two slots differ
        swapped = f"{bb}/{aa}" if aa != bb else f"{wrong_aa}/{bb}"
        uris = [
            f"/media/original/{wrong_aa}/{bb}/{uid}/source.png",
            f"/media/original/{aa}/{wrong_bb}/{uid}/source.png",
            f"/media/hls/{wrong_aa}/{wrong_bb}/{uid}/master.m3u8",
            f"/media/thumbnails/{wrong_aa}/{bb}/{uid}/poster.jpg",
            f"/media/subtitles/{swapped}/{uid}/en.vtt",
        ]
        real = f"{aa}/{bb}/{uid}/"
        for uri in uris:
            self.assertNotIn(real, uri, "test bug: URI uses the real shard path")
            self.assertEqual(self._auth(uri).status_code, 403, uri)

    def test_a_sharded_path_cannot_borrow_a_uid_from_another_segment(self):
        public, private = self.public_media.uid.hex, self.private_media.uid.hex
        shard = media_uid_shard_path(self.private_media.uid)
        for uri in [
            # public uid in the wrong place of a private media's directory
            f"/media/original/{shard}/{public}.png",
            f"/media/encoded/{shard}/{public}.mp4",
            # the uid directory missing, a uid-looking file name instead
            f"/media/thumbnails/{private[0:2]}/{private[2:4]}/{private}.jpg",
            f"/media/subtitles/{private[0:2]}/{private[2:4]}/{private}.vtt",
            # new-layout kinds without shards name no media
            f"/media/thumbnails/{private}_x.jpg",
            f"/media/thumbnails/user/owner/{private}_x.jpg",
            f"/media/subtitles/user/owner/{private}.srt",
        ]:
            self.assertEqual(self._auth(uri).status_code, 403, uri)

    def test_a_public_uid_in_the_query_string_cannot_authorize_a_private_sharded_file(self):
        uri = self._sharded("thumbnails", self.private_media, "poster.jpg") + f"?x={self.public_media.uid.hex}"
        self.assertEqual(self._auth(uri).status_code, 403)

    def test_traversal_out_of_a_sharded_directory_is_denied(self):
        public_dir = self._sharded("original", self.public_media, "")
        private = self.private_media
        for uri in [
            f"{public_dir}../{private.uid.hex}/source.png",
            f"{public_dir}..%2F..%2F{private.uid.hex[0:2]}/{private.uid.hex[2:4]}/{private.uid.hex}/source.png",
            f"{public_dir}%2e%2e/x",
        ]:
            self.assertEqual(self._auth(uri).status_code, 403, uri)

    def test_unknown_sharded_uid_is_denied(self):
        zero = "0" * 32
        self.assertEqual(self._auth(f"/media/original/00/00/{zero}/source.png").status_code, 403)

    def test_sharded_category_images_follow_their_category(self):
        with open("fixtures/test_image.png", "rb") as fp:
            plain = Category.objects.create(title="Botany", thumbnail=ImageFile(BytesIO(fp.read()), name="poster.png"))
        with open("fixtures/test_image.png", "rb") as fp:
            restricted = Category.objects.create(title="Staff", thumbnail=ImageFile(BytesIO(fp.read()), name="poster.png"), is_rbac_category=True)
        self.assertTrue(plain.thumbnail.name.startswith("categories/"))
        self.assertEqual(self._auth(f"/media/{plain.thumbnail.name}").status_code, 204)
        cache.clear()
        with override_settings(USE_RBAC=True):
            self.assertEqual(self._auth(f"/media/{restricted.thumbnail.name}").status_code, 403)
        cache.clear()
        self.assertEqual(self._auth("/media/categories/00/00/nobody.jpg").status_code, 403)
        self.assertEqual(self._auth("/media/categories/../original/x").status_code, 403)

    # Legacy layouts stay readable until an operator migrates them -------------------------

    def _legacy(self, **fields):
        Media.objects.filter(pk=fields.pop("pk")).update(**fields)
        cache.clear()

    def test_legacy_original_and_encoded_urls_still_authorize(self):
        for media, user in ((self.public_media, None), (self.private_media, self.owner)):
            uid = media.uid.hex
            original = f"/media/original/user/{media.user.username}/{uid}.test_image.png"
            encoded = f"/media/encoded/3/{media.user.username}/{uid}.test_image.png.mp4"
            for uri in (original, encoded):
                if user is None:
                    self.assertEqual(self._auth(uri).status_code, 204, uri)
                else:
                    self.assertEqual(self._auth(uri).status_code, 403, uri)
                    self.assertEqual(self._auth(uri, self._login(user)).status_code, 204, uri)

    def test_legacy_unsharded_hls_urls_still_authorize(self):
        public = f"/media/hls/{self.public_media.uid.hex}/master.m3u8"
        private = f"/media/hls/{self.private_media.uid.hex}/media-1/stream.m3u8"
        self.assertEqual(self._auth(public).status_code, 204)
        self.assertEqual(self._auth(private).status_code, 403)
        self.assertEqual(self._auth(private, self._login(self.owner)).status_code, 204)

    def test_legacy_thumbnail_urls_are_resolved_by_their_stored_path(self):
        for media in (self.public_media, self.private_media):
            legacy_name = f"original/thumbnails/user/{media.user.username}/{media.uid.hex}_abc.jpg"
            arbitrary_name = f"original/thumbnails/user/{media.user.username}/holiday.jpg"
            self._legacy(pk=media.pk, thumbnail=legacy_name, uploaded_poster=arbitrary_name)
        public = self.public_media
        private = self.private_media
        self.assertEqual(self._auth(f"/media/original/thumbnails/user/stranger/{public.uid.hex}_abc.jpg").status_code, 204)
        self.assertEqual(self._auth("/media/original/thumbnails/user/stranger/holiday.jpg").status_code, 204)
        self.assertEqual(self._auth("/media/original/thumbnails/user/owner/holiday.jpg").status_code, 403)
        self.assertEqual(self._auth("/media/original/thumbnails/user/owner/holiday.jpg", self._login(self.owner)).status_code, 204)
        self.assertEqual(self._auth(f"/media/original/thumbnails/user/owner/{private.uid.hex}_abc.jpg").status_code, 403)

    def test_legacy_category_urls_still_authorize(self):
        category = Category.objects.create(title="Legacy")
        Category.objects.filter(pk=category.pk).update(thumbnail="original/categories/abc123.legacy.jpg")
        cache.clear()
        self.assertEqual(self._auth("/media/original/categories/abc123.legacy.jpg").status_code, 204)
        self.assertEqual(self._auth("/media/original/categories/unknown.jpg").status_code, 403)

    def test_a_hex_username_in_a_legacy_path_is_not_a_shard_or_uid(self):
        media = self._media("hexed", self.hex_owner, "private")
        uri = f"/media/original/user/{self.hex_owner.username}/{media.uid.hex}.x.png"
        self.assertEqual(self._auth(uri).status_code, 403)
        self.assertEqual(self._auth(uri, self._login(self.hex_owner)).status_code, 204)
