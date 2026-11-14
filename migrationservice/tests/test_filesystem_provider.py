import os
import shutil
import tempfile

from django.test import Client, SimpleTestCase, TestCase, override_settings

from files.tests import create_account
from migrationservice.models import MigrationService
from migrationservice.providers import get_provider_class
from migrationservice.providers.filesystem import (
    FilesystemError,
    FilesystemProvider,
    clean_mount_name,
    clean_relpath,
    list_mounts,
    media_kind,
    place_original,
    resolve_mount,
)
from migrationservice.serializers import MigrationServiceSerializer

IMAGE = "fixtures/test_image.png"
API = "/api/v1/migrations/"


class LibraryTestCase(SimpleTestCase):
    """A temporary import root with one mount called 'lib' and a directory outside it"""

    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix="fs-import-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.root = os.path.join(self.base, "root")
        self.outside = os.path.join(self.base, "outside")
        os.makedirs(os.path.join(self.root, "lib"))
        os.makedirs(self.outside)
        override = override_settings(FILESYSTEM_IMPORT_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)

    def put(self, relpath, content=b"x", mount="lib"):
        path = os.path.join(self.root, mount, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as out:
            out.write(content)
        return path

    def provider(self, mount="lib", subpath="", **options):
        connection = {"mount": mount}
        if subpath:
            connection["subpath"] = subpath
        return FilesystemProvider(connection, options)

    def listing(self, provider, phase="media", page_size=1000):
        ids, _cursor = provider.list_page(phase, {}, page_size)
        return ids


class TestAllowlist(LibraryTestCase):
    def test_a_mount_is_one_directory_name_not_a_path(self):
        for bad in ("", " ", ".", "..", "../outside", "lib/sub", "/etc", "/", "a\\b", "lib\x00"):
            with self.assertRaises(FilesystemError, msg=repr(bad)):
                clean_mount_name(bad)
        self.assertEqual(clean_mount_name(" lib "), "lib")

    def test_a_mount_must_exist_under_the_import_root(self):
        self.assertTrue(resolve_mount("lib").endswith("/root/lib"))
        with self.assertRaises(FilesystemError):
            resolve_mount("missing")

    def test_a_mount_that_is_a_symlink_out_of_the_root_is_refused(self):
        os.symlink(self.outside, os.path.join(self.root, "sneaky"))
        with self.assertRaisesMessage(FilesystemError, "outside the import root"):
            resolve_mount("sneaky")

    def test_a_mount_that_is_a_symlink_to_another_place_in_the_root_is_refused_too(self):
        os.makedirs(os.path.join(self.root, "real", "deep"))
        os.symlink(os.path.join(self.root, "real", "deep"), os.path.join(self.root, "alias"))
        with self.assertRaises(FilesystemError):
            resolve_mount("alias")

    def test_a_mount_that_is_a_file_is_refused(self):
        open(os.path.join(self.root, "afile"), "w").close()
        with self.assertRaises(FilesystemError):
            resolve_mount("afile")

    def test_the_mount_listing_offers_real_directories_only(self):
        os.makedirs(os.path.join(self.root, "second"))
        os.makedirs(os.path.join(self.root, ".hidden"))
        open(os.path.join(self.root, "afile"), "w").close()
        os.symlink(self.outside, os.path.join(self.root, "sneaky"))
        self.assertEqual([mount["name"] for mount in list_mounts()], ["lib", "second"])

    def test_the_listing_is_empty_when_nothing_is_mounted(self):
        shutil.rmtree(self.root)
        self.assertEqual(list_mounts(), [])

    def test_relative_paths_cannot_climb_or_start_at_the_root(self):
        for bad in ("../x", "a/../../x", "/abs", "a/b/../../.."):
            with self.assertRaises(FilesystemError, msg=bad):
                clean_relpath(bad)
        self.assertEqual(clean_relpath("./a//b/"), "a/b")
        self.assertEqual(clean_relpath(""), "")

    def test_a_source_id_that_climbs_is_never_resolved(self):
        self.put("a.png")
        with open(os.path.join(self.outside, "secret.png"), "wb") as out:
            out.write(b"secret")
        provider = self.provider()
        for source_id in ("../../outside/secret.png", "/etc/passwd", "a.png/../../../outside/secret.png"):
            self.assertFalse(provider.source_exists(source_id), source_id)
            with self.assertRaises(FilesystemError):
                provider.fetch_media(source_id)

    def test_a_file_symlink_leaving_the_mount_is_neither_listed_nor_fetched(self):
        secret = os.path.join(self.outside, "secret.png")
        with open(secret, "wb") as out:
            out.write(b"secret")
        self.put("ok.png")
        os.symlink(secret, os.path.join(self.root, "lib", "leak.png"))
        provider = self.provider()

        self.assertEqual(self.listing(provider), ["ok.png"])
        self.assertFalse(provider.source_exists("leak.png"))
        with self.assertRaisesMessage(FilesystemError, "outside the mount"):
            provider.fetch_media("leak.png")

    def test_a_symlink_to_another_mount_is_refused_too(self):
        os.makedirs(os.path.join(self.root, "other"))
        other = self.put("o.png", mount="other")
        os.symlink(other, os.path.join(self.root, "lib", "borrowed.png"))
        self.assertEqual(self.listing(self.provider()), [])

    def test_a_symlink_staying_inside_the_mount_is_fine(self):
        real = self.put("real/clip.png")
        os.symlink(real, os.path.join(self.root, "lib", "alias.png"))
        provider = self.provider()
        self.assertEqual(self.listing(provider), ["alias.png", "real/clip.png"])
        self.assertEqual(provider.fetch_media("alias.png")["path"], real)

    def test_a_directory_symlink_is_not_followed(self):
        self.put("sub/a.png")
        os.symlink(os.path.join(self.root, "lib"), os.path.join(self.root, "lib", "sub", "loop"))
        os.symlink(self.outside, os.path.join(self.root, "lib", "out"))
        with open(os.path.join(self.outside, "x.png"), "wb") as out:
            out.write(b"x")
        self.assertEqual(self.listing(self.provider()), ["sub/a.png"])

    def test_a_subpath_may_not_leave_the_mount(self):
        connection = {"mount": "lib", "subpath": "../outside"}
        with self.assertRaises(FilesystemError):
            FilesystemProvider.validate_settings(connection, self.good_options())
        os.symlink(self.outside, os.path.join(self.root, "lib", "out"))
        with self.assertRaises(FilesystemError):
            FilesystemProvider.validate_settings({"mount": "lib", "subpath": "out"}, self.good_options())

    def good_options(self, **extra):
        options = dict(FilesystemProvider.default_options, fallback_username="admin")
        options.update(extra)
        return options


class TestListing(LibraryTestCase):
    def test_only_importable_files_are_listed_and_hidden_ones_are_not(self):
        for name in ("a.mp4", "b.PNG", "c.pdf", "d.mp3", "notes.txt", "e.srt", ".hidden.mp4", "f.mp4.part", "Thumbs.db", ".git/x.png", "@eaDir/y.png"):
            self.put(name)
        self.assertEqual(self.listing(self.provider()), ["a.mp4", "b.PNG", "c.pdf", "d.mp3"])

    def test_operator_ignore_patterns_match_names_and_paths(self):
        for name in ("keep.png", "skip.png", "drafts/x.png", "final/y.png"):
            self.put(name)
        provider = self.provider(ignore_patterns="skip.*\ndrafts/*")
        self.assertEqual(self.listing(provider), ["final/y.png", "keep.png"])

    def test_types_the_portal_does_not_allow_are_not_listed(self):
        self.put("a.mp4")
        self.put("b.png")
        with override_settings(ALLOWED_MEDIA_UPLOAD_TYPES=["image"]):
            self.assertEqual(self.listing(self.provider()), ["b.png"])

    def test_a_subpath_narrows_the_run_but_ids_stay_relative_to_the_mount(self):
        self.put("a.png")
        self.put("2024/b.png")
        provider = self.provider(subpath="2024")
        self.assertEqual(self.listing(provider), ["2024/b.png"])
        self.assertTrue(provider.within_selection("2024/b.png"))
        self.assertFalse(provider.within_selection("a.png"))
        self.assertFalse(provider.within_selection("2024-old/c.png"))

    def test_paging_resumes_without_gaps_or_repeats(self):
        names = ["a.png", "b/a.png", "b/b/z.png", "b/c.png", "b.png", "c/d/e/f.png", "c.png", "d.png"]
        for name in names:
            self.put(name)
        provider = self.provider()
        everything = self.listing(provider)

        seen, cursor = [], {}
        while True:
            page, cursor = provider.list_page("media", cursor, 3)
            if not page:
                break
            self.assertLessEqual(len(page), 3)
            seen.extend(page)
        self.assertEqual(seen, everything)
        self.assertEqual(sorted(seen), sorted(names))
        self.assertEqual(len(set(seen)), len(names))

    def test_the_cursor_holds_one_path_not_the_listing(self):
        for index in range(5):
            self.put(f"f{index}.png")
        _page, cursor = self.provider().list_page("media", {}, 2)
        self.assertEqual(cursor, {"after": "f1.png"})

    def test_categories_are_the_folders_that_directly_hold_media(self):
        self.put("top.png")
        self.put("a/one.png")
        self.put("a/b/two.png")
        self.put("empty/only/notes.txt")
        provider = self.provider()
        self.assertEqual(self.listing(provider, "categories"), ["a", "a/b"])
        self.assertEqual(provider.fetch_category("a/b"), {"id": "a/b", "name": "b", "parent": "a"})

    def test_folder_categories_can_be_switched_off(self):
        self.put("a/one.png")
        self.assertEqual(self.listing(self.provider(categories_from_folders=False), "categories"), [])

    def test_an_unreadable_start_ends_the_listing_with_an_error(self):
        provider = self.provider(mount="gone")
        with self.assertRaises(FilesystemError):
            provider.list_page("media", {}, 10)

    def test_an_unknown_phase_is_refused(self):
        with self.assertRaises(ValueError):
            self.provider().list_page("users", {}, 10)

    def test_check_connection_counts_what_a_run_would_take(self):
        self.put("a.png")
        self.put("x/b.png")
        result = self.provider().check_connection()
        self.assertTrue(result["ok"])
        self.assertEqual(result["stats"]["entries"], 2)
        self.assertEqual(result["stats"]["folders"], 1)

    def test_check_connection_explains_a_missing_mount(self):
        result = self.provider(mount="missing").check_connection()
        self.assertFalse(result["ok"])
        self.assertIn("missing", result["error"])

    def test_media_kinds_follow_the_extension(self):
        self.assertEqual([media_kind(name) for name in ("a.MP4", "b.jpeg", "c.flac", "d.pdf", "e.srt", "f")], ["video", "image", "audio", "pdf", None, None])


class TestSidecarCaptions(LibraryTestCase):
    def test_captions_beside_a_file_are_found_by_name_and_language(self):
        self.put("talk.mp4")
        self.put("talk.vtt", b"WEBVTT")
        self.put("talk.fr.srt", b"1")
        self.put("talk.not a lang.vtt")
        self.put("other.vtt")
        captions = self.provider().fetch_media("talk.mp4")["captions"]
        self.assertEqual([(caption["language"], caption["extension"]) for caption in captions], [("fr", ".srt"), ("en", ".vtt")])

    def test_webvtt_wins_over_srt_for_one_language(self):
        self.put("talk.mp4")
        self.put("talk.srt")
        self.put("talk.vtt")
        captions = self.provider().fetch_media("talk.mp4")["captions"]
        self.assertEqual([caption["extension"] for caption in captions], [".vtt"])

    def test_a_caption_symlinked_out_of_the_mount_is_ignored(self):
        self.put("talk.mp4")
        secret = os.path.join(self.outside, "secret.vtt")
        open(secret, "w").close()
        os.symlink(secret, os.path.join(self.root, "lib", "talk.vtt"))
        self.assertEqual(self.provider().fetch_media("talk.mp4")["captions"], [])

    def test_captions_can_be_switched_off(self):
        self.put("talk.mp4")
        self.put("talk.vtt")
        self.assertEqual(self.provider(import_captions=False).fetch_media("talk.mp4")["captions"], [])


class TestPlacement(LibraryTestCase):
    def test_ingest_hardlinks_when_it_can(self):
        source = self.put("a.png", b"bytes")
        destination = os.path.join(self.base, "dest", "source.png")
        self.assertEqual(place_original(source, destination, "ingest"), "hardlink")
        self.assertEqual(os.stat(source).st_ino, os.stat(destination).st_ino)

    def test_ingest_copies_when_linking_is_not_possible(self):
        source = self.put("a.png", b"bytes")
        destination = os.path.join(self.base, "dest", "source.png")
        from unittest import mock

        with mock.patch("os.link", side_effect=OSError("cross-device")):
            self.assertEqual(place_original(source, destination, "ingest"), "copy")
        self.assertNotEqual(os.stat(source).st_ino, os.stat(destination).st_ino)
        with open(destination, "rb") as handle:
            self.assertEqual(handle.read(), b"bytes")

    def test_preserve_links_to_the_real_file(self):
        source = self.put("a.png", b"bytes")
        destination = os.path.join(self.base, "dest", "source.png")
        self.assertEqual(place_original(source, destination, "preserve"), "symlink")
        self.assertTrue(os.path.islink(destination))
        self.assertEqual(os.path.realpath(destination), os.path.realpath(source))

    def test_an_existing_destination_is_never_overwritten(self):
        source = self.put("a.png")
        destination = self.put("b.png")
        with self.assertRaises(FileExistsError):
            place_original(source, destination, "ingest")


class TestRegistration(SimpleTestCase):
    def test_the_provider_is_registered_with_a_mount_scoped_identity(self):
        self.assertIs(get_provider_class("filesystem"), FilesystemProvider)
        self.assertEqual(FilesystemProvider.source_system({"mount": " lib "}), "filesystem:lib")

    def test_no_owner_is_assumed(self):
        self.assertEqual(FilesystemProvider.default_options["fallback_username"], "")
        self.assertEqual(FilesystemProvider.default_options["storage_mode"], "ingest")


class TestSerializer(LibraryTestCase, TestCase):
    def setUp(self):
        super().setUp()
        self.admin = create_account(username="admin")
        self.owner = create_account(username="librarian")

    def data(self, connection=None, options=None, **extra):
        payload = {
            "name": "Archive",
            "provider": "filesystem",
            "connection": {"mount": "lib"} if connection is None else connection,
            "options": {"fallback_username": "librarian"} if options is None else options,
        }
        payload.update(extra)
        return payload

    def errors(self, **kwargs):
        serializer = MigrationServiceSerializer(data=self.data(**kwargs))
        self.assertFalse(serializer.is_valid())
        return serializer.errors

    def test_a_valid_library_is_accepted_with_ingest_as_the_default_mode(self):
        serializer = MigrationServiceSerializer(data=self.data())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["options"]["storage_mode"], "ingest")
        self.assertEqual(serializer.validated_data["connection"], {"mount": "lib", "subpath": ""})

    def test_an_owner_is_required_and_not_filled_in(self):
        for options in ({}, {"fallback_username": ""}, {"fallback_username": "  "}):
            self.assertIn("options", self.errors(options=options), options)
        # omitting options altogether does not fall back to the creating admin either
        serializer = MigrationServiceSerializer(data={"name": "x", "provider": "filesystem", "connection": {"mount": "lib"}})
        self.assertFalse(serializer.is_valid())

    def test_the_owner_must_be_an_existing_user(self):
        self.assertIn("options", self.errors(options={"fallback_username": "nobody"}))

    def test_the_storage_mode_must_be_known(self):
        self.assertIn("options", self.errors(options={"fallback_username": "librarian", "storage_mode": "move"}))
        for mode in ("ingest", "preserve"):
            serializer = MigrationServiceSerializer(data=self.data(options={"fallback_username": "librarian", "storage_mode": mode}))
            self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_the_mount_must_sit_under_the_import_root(self):
        for mount in ("../outside", "/etc", "missing", "lib/sub", ""):
            self.assertIn("connection", self.errors(connection={"mount": mount}), mount)
        os.symlink(self.outside, os.path.join(self.root, "sneaky"))
        self.assertIn("connection", self.errors(connection={"mount": "sneaky"}))

    def test_no_free_absolute_path_can_be_smuggled_in_through_the_connection(self):
        self.assertIn("connection", self.errors(connection={"mount": "lib", "path": "/etc"}))
        self.assertIn("connection", self.errors(connection={"mount": "lib", "subpath": "/etc"}))

    def test_an_unknown_option_is_refused_as_for_every_provider(self):
        self.assertIn("options", self.errors(options={"fallback_username": "librarian", "skip_transcoding": True}))

    def test_max_items_must_be_a_positive_whole_number(self):
        for value in (0, -1, "many"):
            self.assertIn("options", self.errors(options={"fallback_username": "librarian", "max_items": value}), value)

    def test_editing_only_the_name_does_not_revalidate_the_library(self):
        service = MigrationService.objects.create(name="Archive", provider="filesystem", connection={"mount": "lib", "subpath": ""}, options={"fallback_username": "librarian"})
        shutil.rmtree(os.path.join(self.root, "lib"))
        serializer = MigrationServiceSerializer(service, data={"name": "Renamed"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestApi(LibraryTestCase, TestCase):
    password = "this_is_a_fake_password"

    def setUp(self):
        super().setUp()
        self.admin = create_account(username="admin", password=self.password, is_superuser=True)
        self.editor = create_account(username="editor", password=self.password, is_editor=True)
        create_account(username="librarian")
        self.client = Client()

    def test_only_a_superuser_can_list_mounts(self):
        self.client.login(username="editor", password=self.password)
        self.assertEqual(self.client.get(f"{API}filesystem_mounts/").status_code, 403)
        self.client.login(username="admin", password=self.password)
        response = self.client.get(f"{API}filesystem_mounts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"mounts": [{"name": "lib", "readable": True}]})

    def test_create_validates_the_library(self):
        self.client.login(username="admin", password=self.password)
        body = {"name": "Archive", "provider": "filesystem", "connection": {"mount": "lib"}, "options": {}}
        response = self.client.post(API, data=body, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("options", response.json())

        body["options"] = {"fallback_username": "librarian", "storage_mode": "preserve"}
        response = self.client.post(API, data=body, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(MigrationService.objects.get(pk=response.json()["id"]).source_system, "filesystem:lib")
        self.assertEqual(response.json()["options"]["storage_mode"], "preserve")
        self.assertEqual(response.json()["options"]["initiated_by"], "admin")

    def test_the_check_button_answers_for_a_filesystem_library(self):
        self.put("a.png")
        self.client.login(username="admin", password=self.password)
        response = self.client.post(f"{API}check_connection/", data={"provider": "filesystem", "connection": {"mount": "lib"}, "options": {}}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["stats"]["entries"], 1)
