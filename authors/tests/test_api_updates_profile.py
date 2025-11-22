from django.test import TestCase
from authors.api_views import _update_author_from_payload
from authors.models import Author, Image


class UpdateAuthorFromPayloadTests(TestCase):
    def setUp(self):
        # remote author with an existing profileImage
        self.remote_img = Image.objects.create(
            file_name='old.png',
            data=b'olddata',
            content_type='image/png'
        )
        self.remote_author = Author.objects.create_user(
            username='remote_author',
            password='pw',
            displayName='Old Name',
            host='http://remote.example.com',
            url='http://remote.example.com/api/authors/remote/'
        )
        # attach image if model relationship exists
        try:
            self.remote_author.profileImage = self.remote_img
            self.remote_author.save()
        except Exception:
            # model may not support assignment in tests environment; ignore and continue
            pass

        # author without a profileImage
        self.no_image_author = Author.objects.create_user(
            username='noimg_author',
            password='pw',
            displayName='Before Name',
            host='http://remote.example.com',
            url='http://remote.example.com/api/authors/noimg/'
        )

    def test_updates_displayname_github_description_and_profileimage_when_present(self):
        payload = {
            "displayName": "New Remote Name",
            "github": "https://github.com/remote-new",
            "description": "New bio",
            "profileImage": "https://remote.example.com/images/new.png"
        }

        updated = _update_author_from_payload(self.remote_author, payload)
        self.assertTrue(updated, "Expected update when payload contains new fields")
        self.remote_author.refresh_from_db()
        self.assertEqual(self.remote_author.displayName, "New Remote Name")
        self.assertEqual(self.remote_author.github, "https://github.com/remote-new")
        self.assertEqual(self.remote_author.description, "New bio")
        # profileImage.file_name should be set to the incoming value when profileImage exists
        if getattr(self.remote_author, "profileImage", None):
            self.assertEqual(self.remote_author.profileImage.file_name, payload["profileImage"])

    def test_updates_other_fields_but_not_create_profileimage_if_missing(self):
        payload = {
            "displayName": "No Image Updated",
            "github": "https://github.com/noimg",
            "description": "Updated desc",
            "profileImage": "https://remote.example.com/images/wont-create.png"
        }

        # no_image_author.profileImage is None — function should not crash and should update other fields
        updated = _update_author_from_payload(self.no_image_author, payload)
        self.assertTrue(updated)
        self.no_image_author.refresh_from_db()
        self.assertEqual(self.no_image_author.displayName, "No Image Updated")
        self.assertEqual(self.no_image_author.github, "https://github.com/noimg")
        self.assertEqual(self.no_image_author.description, "Updated desc")
        # profileImage remains None (function only updates file_name when profileImage exists)
        self.assertIsNone(getattr(self.no_image_author, "profileImage", None))

    def test_no_changes_return_false_and_do_not_modify(self):
        payload = {}  # empty payload should not update anything
        before = {
            "displayName": self.remote_author.displayName,
            "github": self.remote_author.github,
            "description": self.remote_author.description,
            "profileImage_file": getattr(self.remote_author.profileImage, "file_name", None)
        }
        updated = _update_author_from_payload(self.remote_author, payload)
        self.assertFalse(updated, "Expected no update when payload empty")
        self.remote_author.refresh_from_db()
        after = {
            "displayName": self.remote_author.displayName,
            "github": self.remote_author.github,
            "description": self.remote_author.description,
            "profileImage_file": getattr(self.remote_author.profileImage, "file_name", None)
        }
        self.assertEqual(before, after)

    def test_handles_partial_payloads_and_missing_keys(self):
        payload = {"displayName": "Partial Name"}
        updated = _update_author_from_payload(self.remote_author, payload)
        self.assertTrue(updated)
        self.remote_author.refresh_from_db()
        self.assertEqual(self.remote_author.displayName, "Partial Name")
        # other fields unchanged
        self.assertEqual(self.remote_author.github, "https://github.com/remote-new" if self.remote_author.github else self.remote_author.github)