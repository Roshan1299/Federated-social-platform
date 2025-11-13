import urllib.parse
from django.test import TestCase, Client
from unittest.mock import patch, Mock

from authors.models import Author, FollowRequest, Follow


class SingleFollowingPutTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a local follower (the actor) and local target
        self.follower = Author.objects.create_user(username='follower', password='pass')
        self.follower.displayName = 'Follower'
        self.follower.url = f"http://testserver/api/authors/{self.follower.id}/"
        self.follower.host = 'http://testserver'
        self.follower.save()

        self.local_target = Author.objects.create_user(username='local_target', password='pass')
        self.local_target.displayName = 'Local Target'
        self.local_target.url = f"http://testserver/api/authors/{self.local_target.id}/"
        self.local_target.host = 'http://testserver'
        self.local_target.save()

        # Remote target that exists in DB (different host)
        self.remote_target = Author.objects.create_user(username='remote_target', password='pass')
        self.remote_target.displayName = 'Remote Target'
        self.remote_target.url = f"http://remote.example.com/api/authors/{self.remote_target.id}/"
        self.remote_target.host = 'http://remote.example.com'
        self.remote_target.save()

    def test_put_local_target_creates_follow_request(self):
        # Login as follower
        self.client.force_login(self.follower)

        following_fqid = self.local_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        self.assertIn(resp.status_code, (200, 201))

        fr = FollowRequest.objects.filter(sender=self.follower, receiver=self.local_target).first()
        self.assertIsNotNone(fr)
        self.assertEqual(fr.status, 'PENDING')

    @patch('authors.api_views.requests.post')
    def test_put_remote_target_sends_inbox_and_creates_follow_request(self, mock_post):
        # Simulate successful remote inbox response
        mock_resp = Mock()
        mock_resp.status_code = 201
        mock_resp.text = 'Created'
        mock_post.return_value = mock_resp

        self.client.force_login(self.follower)

        following_fqid = self.remote_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        # Expect remote inbox to be contacted
        self.assertTrue(mock_post.called)
        self.assertEqual(resp.status_code, 201)

        # treats the relationship as followed immediately.
        follow = Follow.objects.filter(follower=self.follower, following=self.remote_target).first()
        self.assertIsNotNone(follow)

    def test_put_unauthenticated_returns_401(self):
        # Do not login
        following_fqid = self.local_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        # Decorator should require authentication
        self.assertEqual(resp.status_code, 401)

    def test_put_wrong_author_forbidden(self):
        # Logged in as someone else trying to act on behalf of follower
        self.client.force_login(self.local_target)

        following_fqid = self.local_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        self.assertEqual(resp.status_code, 403)

    @patch('authors.api_views.requests.post')
    def test_put_remote_inbox_exception_returns_502(self, mock_post):
        mock_post.side_effect = Exception('network error')
        self.client.force_login(self.follower)

        following_fqid = self.remote_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        self.assertEqual(resp.status_code, 502)

    @patch('authors.api_views.requests.post')
    def test_put_remote_inbox_returns_error_code_forwarded(self, mock_post):
        mock_resp = Mock()
        mock_resp.status_code = 404
        mock_resp.text = 'Not Found'
        mock_post.return_value = mock_resp

        self.client.force_login(self.follower)

        following_fqid = self.remote_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        self.assertEqual(resp.status_code, 404)

    def test_refollow_after_denied_reopens_follow_request(self):
        # Create a previously denied follow request
        fr = FollowRequest.objects.create(sender=self.follower, receiver=self.local_target, status='DENIED')

        # Sender (follower) re-sends follow request via following PUT
        self.client.force_login(self.follower)
        following_fqid = self.local_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        self.assertIn(resp.status_code, (200, 201))

        fr.refresh_from_db()
        self.assertEqual(fr.status, 'PENDING')

    def test_refollow_after_approved_reopens_follow_request_and_preserves_follow(self):
        # Create a previously approved follow request and an active Follow
        fr = FollowRequest.objects.create(sender=self.follower, receiver=self.local_target, status='APPROVED')
        Follow.objects.create(follower=self.follower, following=self.local_target)

        # Sender re-sends follow request
        self.client.force_login(self.follower)
        following_fqid = self.local_target.url
        quoted = urllib.parse.quote(following_fqid, safe='')
        url = f"/api/authors/{self.follower.id}/following/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        self.assertIn(resp.status_code, (200, 201))

        fr.refresh_from_db()
        self.assertEqual(fr.status, 'PENDING')
        # Existing Follow record should still exist
        self.assertTrue(Follow.objects.filter(follower=self.follower, following=self.local_target).exists())

    def test_accept_follow_request_put_approves_and_creates_follow(self):
        # Create a pending follow request: follower -> local_target
        fr = FollowRequest.objects.create(sender=self.follower, receiver=self.local_target, status='PENDING')

        # local_target (receiver) should accept
        self.client.force_login(self.local_target)

        follower_fqid = self.follower.url
        quoted = urllib.parse.quote(follower_fqid, safe='')
        url = f"/api/authors/{self.local_target.id}/followers/{quoted}"

        resp = self.client.put(url, content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        # FollowRequest should be APPROVED and Follow created
        fr.refresh_from_db()
        self.assertEqual(fr.status, 'APPROVED')
        self.assertTrue(Follow.objects.filter(follower=self.follower, following=self.local_target).exists())

    def test_delete_denies_pending_follow_request(self):
        # Create a pending follow request: follower -> local_target
        fr = FollowRequest.objects.create(sender=self.follower, receiver=self.local_target, status='PENDING')

        # Receiver denies via DELETE
        self.client.force_login(self.local_target)
        follower_fqid = self.follower.url
        quoted = urllib.parse.quote(follower_fqid, safe='')
        url = f"/api/authors/{self.local_target.id}/followers/{quoted}"

        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)

        # FollowRequest should be removed
        self.assertFalse(FollowRequest.objects.filter(id=fr.id).exists())

    def test_delete_revokes_existing_follow(self):
        # Create an existing follow relationship
        Follow.objects.create(follower=self.follower, following=self.local_target)

        # Receiver revokes via DELETE
        self.client.force_login(self.local_target)
        follower_fqid = self.follower.url
        quoted = urllib.parse.quote(follower_fqid, safe='')
        url = f"/api/authors/{self.local_target.id}/followers/{quoted}"

        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, 204)

        # Follow should be removed
        self.assertFalse(Follow.objects.filter(follower=self.follower, following=self.local_target).exists())


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
