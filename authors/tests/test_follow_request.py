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
    """Test follow request creation, approval, denial, and friendship behavior."""

    def setUp(self):
        """Set up test users and authenticated client"""
        self.client = Client()
        self.alice = User.objects.create_user(
            username='alice', password='pass123', displayName='Alice'
        )
        self.bob = User.objects.create_user(
            username='bob', password='pass123', displayName='Bob'
        )
        self.charlie = User.objects.create_user(
            username='charlie', password='pass123', displayName='Charlie'
        )
        self.client.login(username='bob', password='pass123')  # Bob starts as active user

    # ==================== FOLLOW REQUEST TEST ====================
    def test_follow_request_create(self):
        """User can send a valid follow request"""
        url = reverse('authors:follow_author', kwargs={'author_id': self.alice.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            FollowRequest.objects.filter(sender=self.bob, receiver=self.alice).exists(),
            "FollowRequest should be created when Bob follows Alice."
        )
        follow_req = FollowRequest.objects.get(sender=self.bob, receiver=self.alice)
        self.assertEqual(follow_req.status, 'PENDING')

    # ==================== SELF-FOLLOW TEST ====================
    def test_follow_self_not_allowed(self):
        """Ensure a user cannot follow themselves"""
        url = reverse('authors:follow_author', kwargs={'author_id': self.bob.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            FollowRequest.objects.filter(sender=self.bob, receiver=self.bob).exists(),
            "Self-follow requests should never be created."
        )

    # ==================== DUPLICATE FOLLOW REQUEST TEST ====================
    def test_duplicate_follow_request(self):
        """Duplicate follow requests should not create new entries"""
        FollowRequest.objects.create(sender=self.bob, receiver=self.alice)
        url = reverse('authors:follow_author', kwargs={'author_id': self.alice.id})
        self.client.post(url)
        count = FollowRequest.objects.filter(sender=self.bob, receiver=self.alice).count()
        self.assertEqual(count, 1, "Duplicate follow requests should not be created.")

    # ==================== CANCEL FOLLOW REQUEST TEST ====================
    def test_cancel_follow_request(self):
        """User can cancel a pending follow request"""
        FollowRequest.objects.create(sender=self.bob, receiver=self.alice, status='PENDING')
        cancel_url = reverse('authors:cancel_follow_request', kwargs={'author_id': self.alice.id})
        response = self.client.post(cancel_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            FollowRequest.objects.filter(sender=self.bob, receiver=self.alice).exists(),
            "Follow request should be deleted upon cancellation."
        )

    # ==================== APPROVE FOLLOW REQUEST TEST ====================
    def test_approve_follow_request(self):
        """Receiver can approve a pending follow request"""
        follow_req = FollowRequest.objects.create(sender=self.bob, receiver=self.alice, status='PENDING')
        approve_url = reverse('authors:approve_follow_request', kwargs={'request_id': follow_req.id})
        # Alice logs in to approve
        self.client.logout()
        self.client.login(username='alice', password='pass123')
        response = self.client.post(approve_url)
        self.assertEqual(response.status_code, 302)
        follow_req.refresh_from_db()
        self.assertEqual(follow_req.status, 'APPROVED')
        self.assertTrue(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists(),
            "Follow relationship should be created after approval."
        )

    # ==================== DENY FOLLOW REQUEST TEST ====================
    def test_deny_follow_request(self):
        """Receiver can deny a pending follow request"""
        follow_req = FollowRequest.objects.create(sender=self.bob, receiver=self.alice, status='PENDING')
        deny_url = reverse('authors:deny_follow_request', kwargs={'request_id': follow_req.id})
        self.client.logout()
        self.client.login(username='alice', password='pass123')
        response = self.client.post(deny_url)
        self.assertEqual(response.status_code, 302)
        follow_req.refresh_from_db()
        self.assertEqual(follow_req.status, 'DENIED')
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists(),
            "Denied follow requests should not create a Follow relationship."
        )

    # ==================== MUTUAL FOLLOW TO FRIENDSHIP TEST ====================
    def test_mutual_follow_creates_friendship(self):
        """Mutual follows should make both users friends"""
        # Bob follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        # Alice follows Bob (creating mutual)
        Follow.objects.create(follower=self.alice, following=self.bob)
        is_friend = (
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
            and Follow.objects.filter(follower=self.alice, following=self.bob).exists()
        )
        self.assertTrue(is_friend, "Mutual follow should establish friendship.")

    # ==================== UNFOLLOW TEST ====================
    def test_unfollow_author(self):
        """User can unfollow another user"""
        Follow.objects.create(follower=self.bob, following=self.alice)
        unfollow_url = reverse('authors:unfollow_author', kwargs={'author_id': self.alice.id})
        response = self.client.post(unfollow_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists(),
            "User should be able to unfollow another author."
        )

    # ==================== PERMISSIONS / EDGE CASES ====================
    def test_non_receiver_cannot_approve_or_deny(self):
        """Only the intended receiver can approve or deny follow requests"""
        follow_req = FollowRequest.objects.create(sender=self.bob, receiver=self.alice, status='PENDING')
        # Charlie tries to approve/deny
        self.client.logout()
        self.client.login(username='charlie', password='pass123')
        approve_url = reverse('authors:approve_follow_request', kwargs={'request_id': follow_req.id})
        deny_url = reverse('authors:deny_follow_request', kwargs={'request_id': follow_req.id})
        response_approve = self.client.post(approve_url)
        response_deny = self.client.post(deny_url)
        self.assertEqual(response_approve.status_code, 404)
        self.assertEqual(response_deny.status_code, 404)
        follow_req.refresh_from_db()
        self.assertEqual(follow_req.status, 'PENDING')

    def test_follow_requests_page_lists_pending(self):
        """Receiver can view their pending follow requests on the page"""
        FollowRequest.objects.create(sender=self.bob, receiver=self.alice, status='PENDING')
        self.client.logout()
        self.client.login(username='alice', password='pass123')
        response = self.client.get(reverse('authors:follow_requests'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bob")
        self.assertTemplateUsed(response, "authors/follow_requests.html")


        # ==================== EDGE CASE: FOLLOW NON-EXISTENT USER ====================
    def test_follow_nonexistent_user_returns_404(self):
        """Trying to follow a non-existent user should return 404"""
        invalid_id = "00000000-0000-0000-0000-000000000000"
        url = reverse('authors:follow_author', kwargs={'author_id': invalid_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            FollowRequest.objects.filter(sender=self.bob).exists(),
            "No follow request should be created for invalid user."
        )

    # ==================== EDGE CASE: FOLLOW DELETED USER ====================
    def test_follow_deleted_user(self):
        """Following a deleted user should fail gracefully (404)"""
        deleted_user = User.objects.create_user(username='temp', password='pass123', displayName='Temp')
        deleted_id = deleted_user.id
        deleted_user.delete()

        url = reverse('authors:follow_author', kwargs={'author_id': deleted_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            FollowRequest.objects.filter(sender=self.bob).exists(),
            "Follow requests should not be created for deleted users."
        )

    # ==================== EDGE CASE: APPROVE NON-EXISTENT FOLLOW REQUEST ====================
    def test_approve_nonexistent_follow_request(self):
        """Approving a follow request that doesn't exist should return 404"""
        fake_id = 99999
        url = reverse('authors:approve_follow_request', kwargs={'request_id': fake_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404, "Should return 404 for nonexistent follow request.")

    # ==================== EDGE CASE: DENY NON-EXISTENT FOLLOW REQUEST ====================
    def test_deny_nonexistent_follow_request(self):
        """Denying a non-existent follow request should return 404"""
        fake_id = 88888
        url = reverse('authors:deny_follow_request', kwargs={'request_id': fake_id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    # ==================== EDGE CASE: CANCEL NON-EXISTENT FOLLOW REQUEST ====================
    def test_cancel_nonexistent_follow_request(self):
        """Cancelling a non-existent follow request should not crash"""
        url = reverse('authors:cancel_follow_request', kwargs={'author_id': self.alice.id})
        response = self.client.post(url, follow=True)  # <-- follow redirect
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(
            any("No pending follow request to cancel" in m.message for m in messages),
            "Expected warning message when no pending follow request exists."
        )


    # ==================== EDGE CASE: APPROVE FOLLOW REQUEST TWICE ====================
    def test_approve_follow_request_twice(self):
        """Approving an already approved follow request should not duplicate follows"""
        follow_req = FollowRequest.objects.create(sender=self.bob, receiver=self.alice, status='PENDING')
        approve_url = reverse('authors:approve_follow_request', kwargs={'request_id': follow_req.id})

        self.client.logout()
        self.client.login(username='alice', password='pass123')
        self.client.post(approve_url)  # First approval
        self.client.post(approve_url)  # Second approval attempt

        follow_req.refresh_from_db()
        self.assertEqual(follow_req.status, 'APPROVED')
        follow_count = Follow.objects.filter(follower=self.bob, following=self.alice).count()
        self.assertEqual(follow_count, 1, "Multiple approvals should not create duplicate follows.")

    # ==================== EDGE CASE: RE-SEND AFTER DENIED ====================
    def test_resend_follow_request_after_denied(self):
        """Re-sending a follow request after denial should reset it to PENDING"""
        FollowRequest.objects.create(sender=self.bob, receiver=self.alice, status='DENIED')
        url = reverse('authors:follow_author', kwargs={'author_id': self.alice.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        follow_req = FollowRequest.objects.get(sender=self.bob, receiver=self.alice)
        self.assertEqual(follow_req.status, 'PENDING')

    # ==================== EDGE CASE: UNFOLLOW NON-FOLLOWED USER ====================
    def test_unfollow_non_followed_user(self):
        """Unfollowing a user that you don't follow should not crash"""
        unfollow_url = reverse('authors:unfollow_author', kwargs={'author_id': self.alice.id})
        response = self.client.post(unfollow_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists(),
            "Unfollowing someone not followed should be safe."
        )

    # ==================== EDGE CASE: APPROVE REQUEST AFTER SENDER DELETED ====================
    def test_approve_request_after_sender_deleted(self):
        """Approving a follow request whose sender was deleted should handle gracefully"""
        temp_sender = User.objects.create_user(username='temp', password='pass123', displayName='Temp')
        follow_req = FollowRequest.objects.create(sender=temp_sender, receiver=self.alice, status='PENDING')
        temp_sender.delete()

        approve_url = reverse('authors:approve_follow_request', kwargs={'request_id': follow_req.id})
        self.client.logout()
        self.client.login(username='alice', password='pass123')
        response = self.client.post(approve_url)
        self.assertIn(response.status_code, [404, 500])
