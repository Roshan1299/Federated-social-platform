"""
API Tests for User Stories 26, 27
26. As an author, I want to like entries that I can access, so I can show my appreciation.
27. As an author, when someone sends me a public entry I want to see the likes, so I can tell if it's good or not.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from authors.models import Author, Post, Like

class LikesAPITests(TestCase):
    def setUp(self):
        # Test users
        self.alice = Author.objects.create_user(
            username="alice", password="pw", displayName="Alice"
        )
        self.bob = Author.objects.create_user(
            username="bob", password="pw", displayName="Bob"
        )

        # Public post by Bob (Alice can like/view likes)
        self.public_post = Post.objects.create(
            author=self.bob,
            title="Public Post",
            description="Public desc",
            content="Hello world",
            contentType="text/plain",
            visibility="PUBLIC",
            published=timezone.now(),
            updated=timezone.now(),
        )

        # Private post by Bob (Alice cannot like/view likes list)
        self.private_post = Post.objects.create(
            author=self.bob,
            title="Private Post",
            description="Private desc",
            content="Secret",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )

        # Private post by Alice (Alice can like/view likes)
        self.alice_private_post = Post.objects.create(
            author=self.alice,
            title="Alice Private",
            description="Alice only",
            content="Alice secret",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )

        self.client = Client()

    # ---------------------------
    # US-26: Like entries I can access
    # ---------------------------

    def test_like_public_post_returns_json_and_increments_count_when_ajax(self):
        """Alice can like Bob's PUBLIC post; AJAX should return JSON with updated count."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.public_post.id})
        resp = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",  # triggers JSON branch
        )
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(
            resp.content.decode(),
            {"liked": True, "count": 1},
        )
        self.assertTrue(
            Like.objects.filter(author=self.alice, post=self.public_post).exists()
        )

    def test_like_toggle_unlike_on_second_call(self):
        """Second toggle removes the like and JSON shows decreased count."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.public_post.id})

        # Like
        self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        # Unlike
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": False, "count": 0})
        self.assertFalse(
            Like.objects.filter(author=self.alice, post=self.public_post).exists()
        )

    def test_like_private_post_forbidden_if_not_owner(self):
        """Alice cannot like Bob's PRIVATE post (403)."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.private_post.id})
        resp = self.client.post(url)  # non-AJAX path should still 403
        self.assertEqual(resp.status_code, 403)

    def test_like_private_post_allowed_for_owner(self):
        """Alice can like her own PRIVATE post."""
        self.client.force_login(self.alice)
        url = reverse(
            "authors:toggle_like", kwargs={"post_id": self.alice_private_post.id}
        )
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": True, "count": 1})
        self.assertTrue(
            Like.objects.filter(author=self.alice, post=self.alice_private_post).exists()
        )

    # ---------------------------
    # US-27: View likes on a public entry
    # ---------------------------

    def test_view_likes_public_post_lists_likers(self):
        """Any authenticated user can view likes page for PUBLIC post."""
        # Bob has 1 like from Alice
        Like.objects.create(author=self.alice, post=self.public_post)
        self.client.force_login(self.bob)

        url = reverse("authors:post_likes_page", kwargs={"post_id": self.public_post.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # Template context checks
        self.assertIn("like_count", resp.context)
        self.assertEqual(resp.context["like_count"], 1)
        self.assertIn("likes", resp.context)
        likers = [lk.author.displayName for lk in resp.context["likes"]]
        self.assertIn("Alice", likers)
        # No error flag for PUBLIC post
        self.assertNotIn("error", resp.context or {})

    def test_view_likes_private_post_non_owner_sees_error(self):
        """Non-owner of PRIVATE post should get an error message in context (not 403)."""
        # Bob owns the private post; Alice is not the owner
        self.client.force_login(self.alice)
        url = reverse("authors:post_likes_page", kwargs={"post_id": self.private_post.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # The view sets an 'error' context instead of raising 403
        self.assertIn("error", resp.context)
        self.assertIn("permission", resp.context["error"].lower())

    def test_view_likes_private_post_owner_can_view(self):
        """Owner of PRIVATE post can view likes list normally."""
        # Owner is Bob
        self.client.force_login(self.bob)
        url = reverse("authors:post_likes_page", kwargs={"post_id": self.private_post.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("like_count", resp.context)
        self.assertNotIn("error", resp.context or {})
