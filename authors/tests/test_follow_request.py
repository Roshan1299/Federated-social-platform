"""
API Tests for User Story:
As an author, I want to be able to approve or deny other authors following me,
so that I don't get followed by people I don't like.

Run: python3 manage.py test authors.tests.test_follow_request
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from authors.models import Follow, FollowRequest

User = get_user_model()

class FollowRequestAPITests(TestCase):
    """Test follow request creation, approval, and denial functionality."""

    def setUp(self):
        """Set up test users and authenticated client"""
        self.client = Client()
        self.alice = User.objects.create_user(
            username='alice', password='pass123', displayName='Alice'
        )
        self.bob = User.objects.create_user(
            username='bob', password='pass123', displayName='Bob'
        )
        self.client.login(username='bob', password='pass123')  # Bob will send requests

    def test_follow_request_creation(self):
        """Test that a user can send a follow request to another user"""
        url = reverse('authors:follow_author', kwargs={'author_id': self.alice.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            FollowRequest.objects.filter(sender=self.bob, receiver=self.alice).exists(),
            "FollowRequest should be created when Bob follows Alice."
        )

        follow_req = FollowRequest.objects.get(sender=self.bob, receiver=self.alice)
        self.assertEqual(follow_req.status, 'PENDING')

    def test_cannot_follow_self(self):
        """Ensure users cannot follow themselves"""
        url = reverse('authors:follow_author', kwargs={'author_id': self.bob.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(FollowRequest.objects.filter(sender=self.bob, receiver=self.bob).exists())

    def test_duplicate_follow_request(self):
        """Test that duplicate follow requests are not created"""
        FollowRequest.objects.create(sender=self.bob, receiver=self.alice)
        url = reverse('authors:follow_author', kwargs={'author_id': self.alice.id})
        self.client.post(url)

        # Should still be only one pending request
        count = FollowRequest.objects.filter(sender=self.bob, receiver=self.alice).count()
        self.assertEqual(count, 1, "Duplicate follow requests should not be created.")

    def test_approve_follow_request(self):
        """Test that a receiver can approve a follow request"""
        follow_req = FollowRequest.objects.create(sender=self.bob, receiver=self.alice)
        approve_url = reverse('authors:approve_follow_request', kwargs={'request_id': follow_req.id})

        # Alice approves
        self.client.logout()
        self.client.login(username='alice', password='pass123')
        response = self.client.post(approve_url)

        self.assertEqual(response.status_code, 302)
        follow_req.refresh_from_db()
        self.assertEqual(follow_req.status, 'APPROVED', "Follow request should be approved.")

        # Verify that a Follow relationship was created
        self.assertTrue(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists(),
            "A Follow record should be created after approval."
        )

    def test_deny_follow_request(self):
        """Test that a receiver can deny a follow request"""
        follow_req = FollowRequest.objects.create(sender=self.bob, receiver=self.alice)
        deny_url = reverse('authors:deny_follow_request', kwargs={'request_id': follow_req.id})

        self.client.logout()
        self.client.login(username='alice', password='pass123')
        response = self.client.post(deny_url)

        self.assertEqual(response.status_code, 302)
        follow_req.refresh_from_db()
        self.assertEqual(follow_req.status, 'DENIED', "Follow request should be denied.")
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists(),
            "No Follow relationship should be created after denial."
        )

    def test_follow_requests_page_lists_pending(self):
        """Test that pending follow requests appear in the receiver’s follow requests page"""
        FollowRequest.objects.create(sender=self.bob, receiver=self.alice)

        self.client.logout()
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('authors:follow_requests'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bob")
        self.assertTemplateUsed(response, "authors/follow_requests.html")

    def test_non_receiver_cannot_approve_or_deny(self):
        """Ensure only the intended receiver can approve/deny follow requests"""
        follow_req = FollowRequest.objects.create(sender=self.bob, receiver=self.alice)

        # A random user tries to approve
        charlie = User.objects.create_user(username='charlie', password='pass123', displayName='Charlie')
        self.client.logout()
        self.client.login(username='charlie', password='pass123')

        approve_url = reverse('authors:approve_follow_request', kwargs={'request_id': follow_req.id})
        deny_url = reverse('authors:deny_follow_request', kwargs={'request_id': follow_req.id})

        response_approve = self.client.post(approve_url)
        response_deny = self.client.post(deny_url)

        # Should return 404 (not authorized)
        self.assertEqual(response_approve.status_code, 404)
        self.assertEqual(response_deny.status_code, 404)

        follow_req.refresh_from_db()
        self.assertEqual(follow_req.status, 'PENDING', "Request should remain pending if unauthorized user acts.")
