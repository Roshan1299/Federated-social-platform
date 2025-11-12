import urllib.parse
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Author, FollowRequest, Follow


class FollowersFQIDAPITest(TestCase):
    def setUp(self):
        # Create local author (receiver) and foreign author (sender)
        self.local = Author.objects.create_user(username='local', password='pass')
        self.local.displayName = 'Local'
        self.local.save()

        self.foreign = Author.objects.create_user(username='foreign', password='pass')
        self.foreign.displayName = 'Foreign'
        # Set a remote-style FQID for the foreign author
        self.foreign.url = f"http://example-remote.local/api/authors/{self.foreign.id}/"
        self.foreign.host = 'http://example-remote.local'
        self.foreign.save(update_fields=['url', 'host'])

        # Create a pending follow request from foreign -> local
        self.fr = FollowRequest.objects.create(sender=self.foreign, receiver=self.local, status='PENDING')

        self.client = Client()
        # another local user who is NOT the receiver (used to assert 403)
        self.other = Author.objects.create_user(username='other', password='pass')
        self.other.displayName = 'Other'
        self.other.save()

    def _followers_path(self):
        # Percent-encode the FQID for inclusion in the URL path
        enc = urllib.parse.quote(self.foreign.url, safe='')
        return f"/api/authors/{self.local.id}/followers/{enc}"

    def test_put_approves_follow_request(self):
        # Login as the local author (session auth)
        self.client.force_login(self.local)

        path = self._followers_path()
        response = self.client.put(path, content_type='application/json')

        self.assertIn(response.status_code, (200,))

        # FollowRequest should be approved
        fr = FollowRequest.objects.get(id=self.fr.id)
        self.assertEqual(fr.status, 'APPROVED')

        # Follow relationship should exist
        self.assertTrue(Follow.objects.filter(follower=self.foreign, following=self.local).exists())

    def test_delete_denies_pending_follow_request(self):
        # Ensure pending exists
        self.assertTrue(FollowRequest.objects.filter(sender=self.foreign, receiver=self.local, status='PENDING').exists())

        self.client.force_login(self.local)
        path = self._followers_path()
        response = self.client.delete(path)

        # Expect 204
        self.assertIn(response.status_code, (204,))

        # Pending follow request should be removed
        self.assertFalse(FollowRequest.objects.filter(sender=self.foreign, receiver=self.local).exists())

    def test_delete_revoke_existing_follow(self):
        # Approve first to create a follow
        fr = FollowRequest.objects.get(id=self.fr.id)
        fr.status = 'APPROVED'
        fr.save()
        Follow.objects.create(follower=self.foreign, following=self.local)

        self.client.force_login(self.local)
        path = self._followers_path()
        response = self.client.delete(path)

        self.assertIn(response.status_code, (204,))

        # Follow relationship should be removed
        self.assertFalse(Follow.objects.filter(follower=self.foreign, following=self.local).exists())

    # ---------- Negative tests ----------
    def test_put_forbidden_if_not_author(self):
        """Non-author cannot accept a follow request (403) """
        self.client.force_login(self.other)
        path = self._followers_path()
        response = self.client.put(path, content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_delete_forbidden_if_not_author(self):
        """Non-author cannot deny/revoke (403)"""
        self.client.force_login(self.other)
        path = self._followers_path()
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 403)

    def test_put_not_found_when_no_pending(self):
        """PUT should return 404 if no pending follow request exists"""
        # remove pending
        FollowRequest.objects.filter(id=self.fr.id).delete()
        self.client.force_login(self.local)
        path = self._followers_path()
        response = self.client.put(path, content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_delete_not_found_when_nothing_to_remove(self):
        """DELETE should return 404 when there's neither pending request nor a follower"""
        # ensure none exist
        FollowRequest.objects.filter(sender=self.foreign, receiver=self.local).delete()
        Follow.objects.filter(follower=self.foreign, following=self.local).delete()
        self.client.force_login(self.local)
        path = self._followers_path()
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 404)

    def test_get_requires_authentication(self):
        """GET without session or basic auth should return 401"""
        path = self._followers_path()
        # use unauthenticated client
        unauth_client = Client()
        response = unauth_client.get(path)
        self.assertEqual(response.status_code, 401)
