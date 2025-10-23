"""
API Tests for User Stories 28, 29
28. As an author, I want to comment on entries that I can access, so I can make a witty reply.
29. As an author, I want to like comments that I can access, so I can show my appreciation.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from authors.models import Author, Post, Comment, CommentLike

class CommentsAPITests(TestCase):
    def setUp(self):
        # Users
        self.alice = Author.objects.create_user(
            username="alice", password="pw", displayName="Alice"
        )
        self.bob = Author.objects.create_user(
            username="bob", password="pw", displayName="Bob"
        )

        # Posts
        self.public_post = Post.objects.create(
            author=self.bob,
            title="Public Post",
            description="Visible to all",
            content="Hello public",
            contentType="text/plain",
            visibility="PUBLIC",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.bobs_private_post = Post.objects.create(
            author=self.bob,
            title="Bob Private",
            description="Private post",
            content="Secret",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.alices_private_post = Post.objects.create(
            author=self.alice,
            title="Alice Private",
            description="Private post",
            content="Alice Secret",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )

        # A comment on the public post (by Bob) – used for like tests
        self.public_comment = Comment.objects.create(
            post=self.public_post,
            author=self.bob,
            content="Thanks for reading!"
        )

        # A comment on Bob's private post (by Bob)
        self.private_comment_bob = Comment.objects.create(
            post=self.bobs_private_post,
            author=self.bob,
            content="Private thoughts"
        )

        # A comment on Alice's private post (by Alice)
        self.private_comment_alice = Comment.objects.create(
            post=self.alices_private_post,
            author=self.alice,
            content="Alice's private thoughts"
        )

        self.client = Client()

    # ---------------------------
    # US-28: Comment on entries I can access
    # ---------------------------

    def test_comment_on_public_post_creates_comment_and_redirects(self):
        """Authenticated user can comment on PUBLIC post; view redirects back to post detail."""
        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": self.public_post.id})
        resp = self.client.post(url, data={"content": "Nice post!"})
        self.assertEqual(resp.status_code, 302)

        # Redirect target should be post detail
        expected = reverse("authors:post_detail", kwargs={"post_id": self.public_post.id})
        self.assertTrue(resp["Location"].endswith(expected))

        # Comment created
        self.assertTrue(
            Comment.objects.filter(post=self.public_post, author=self.alice, content="Nice post!").exists()
        )

    def test_comment_on_private_post_forbidden_if_not_owner(self):
        """Non-owner cannot comment on PRIVATE post (403)."""
        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": self.bobs_private_post.id})
        resp = self.client.post(url, data={"content": "I should not be allowed"})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            Comment.objects.filter(post=self.bobs_private_post, author=self.alice).exists()
        )

    def test_comment_on_private_post_allowed_for_owner(self):
        """Owner can comment on their own PRIVATE post; redirects back to detail."""
        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": self.alices_private_post.id})
        resp = self.client.post(url, data={"content": "My private note"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(post=self.alices_private_post, author=self.alice, content="My private note").exists()
        )

    # ---------------------------
    # US-29: Like comments I can access
    # ---------------------------

    def test_like_comment_on_public_post_creates_like_and_redirects(self):
        """Authenticated user can like a comment on a PUBLIC post; view redirects to post detail."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like", kwargs={"comment_id": self.public_comment.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        expected = reverse("authors:post_detail", kwargs={"post_id": self.public_post.id})
        self.assertTrue(resp["Location"].endswith(expected))

        # Like created
        self.assertTrue(
            CommentLike.objects.filter(author=self.alice, comment=self.public_comment).exists()
        )

    def test_like_comment_toggle_unlike_on_second_call(self):
        """Second toggle removes the like and redirects; count returns to zero."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like", kwargs={"comment_id": self.public_comment.id})

        # First call: like
        self.client.post(url)
        self.assertTrue(
            CommentLike.objects.filter(author=self.alice, comment=self.public_comment).exists()
        )

        # Second call: unlike
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(
            CommentLike.objects.filter(author=self.alice, comment=self.public_comment).exists()
        )

    def test_like_comment_on_private_post_forbidden_if_not_owner(self):
        """Non-owner cannot like a comment on a PRIVATE post (403)."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like", kwargs={"comment_id": self.private_comment_bob.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            CommentLike.objects.filter(author=self.alice, comment=self.private_comment_bob).exists()
        )

    def test_like_comment_on_private_post_allowed_for_owner(self):
        """Owner can like a comment on their own PRIVATE post."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like", kwargs={"comment_id": self.private_comment_alice.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CommentLike.objects.filter(author=self.alice, comment=self.private_comment_alice).exists()
        )
