"""
API Tests for User Stories 26, 27

26. As an author, I want to like entries that I can access,
    so I can show my appreciation.

27. As an author, when someone sends me a public entry I want to see the likes,
    so I can tell if it's good or not.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from authors.models import Author, Post, Follow, Like


class LikesAPITests(TestCase):
    def setUp(self):
        # ── Users ───────────────────────────────────────────────────────────────
        self.alice = Author.objects.create_user(
            username="alice", password="pw", displayName="Alice"
        )
        self.bob = Author.objects.create_user(
            username="bob", password="pw", displayName="Bob"
        )
        self.carol = Author.objects.create_user(
            username="carol", password="pw", displayName="Carol"
        )

        # ── Relationships ───────────────────────────────────────────────────────
        # Carol follows Bob (one-way)
        Follow.objects.create(follower=self.carol, following=self.bob)
        # Alice and Bob are mutual
        Follow.objects.create(follower=self.alice, following=self.bob)
        Follow.objects.create(follower=self.bob, following=self.alice)

        # ── Posts ───────────────────────────────────────────────────────────────
        self.public_post = Post.objects.create(
            author=self.bob,
            title="Public Post",
            content="Hello world",
            contentType="text/plain",
            visibility="PUBLIC",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.unlisted_post = Post.objects.create(
            author=self.bob,
            title="Unlisted Post",
            content="Hidden link",
            contentType="text/plain",
            visibility="PUBLIC_UNLISTED",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.friends_post = Post.objects.create(
            author=self.bob,
            title="Friends Post",
            content="Friends area",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.alice_friends_post = Post.objects.create(
            author=self.alice,
            title="Alice Friends",
            content="Alice's area",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )

        self.client = Client()

    # ───────────────────────────────────────────────────────────────────────────
    # US-26: Like entries I can access
    # ───────────────────────────────────────────────────────────────────────────

    def test_like_public_ajax_returns_json(self):
        """PUBLIC: like via AJAX returns JSON and increments count."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.public_post.id})
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": True, "count": 1})
        self.assertTrue(Like.objects.filter(author=self.alice, post=self.public_post).exists())

    def test_like_public_toggle_unlike(self):
        """PUBLIC: second AJAX toggle unlikes and count decrements."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.public_post.id})
        self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")  # like
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")  # unlike
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": False, "count": 0})
        self.assertFalse(Like.objects.filter(author=self.alice, post=self.public_post).exists())

    def test_like_unlisted_non_follower_without_link_forbidden(self):
        """UNLISTED: non-follower without link → 403."""
        # Remove Alice↔Bob so Alice is non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.post(url)  # normal POST, no detail GET
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Like.objects.filter(author=self.alice, post=self.unlisted_post).exists())

    def test_like_unlisted_non_follower_with_link_allowed(self):
        """UNLISTED: non-follower with link (detail GET sets session) → allowed."""
        # Remove Alice↔Bob so Alice is non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        # Visit detail first to set unlisted_access_<id>=True
        self.client.get(reverse("authors:post_detail", kwargs={"post_id": self.unlisted_post.id}))

        url = reverse("authors:toggle_like", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Like.objects.filter(author=self.alice, post=self.unlisted_post).exists())

    def test_like_unlisted_follower_allowed(self):
        """UNLISTED: follower (Carol) can like without link."""
        self.client.force_login(self.carol)  # Carol follows Bob
        url = reverse("authors:toggle_like", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Like.objects.filter(author=self.carol, post=self.unlisted_post).exists())

    def test_like_friends_requires_mutual_or_owner(self):
        """
        FRIENDS:
          - Carol (one-way) → 403
          - Alice (mutual) → 302
          - Bob (owner) → 302
        """
        url = reverse("authors:toggle_like", kwargs={"post_id": self.friends_post.id})

        self.client.force_login(self.carol)
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, 403)

        self.client.force_login(self.alice)
        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 302)
        self.assertTrue(Like.objects.filter(author=self.alice, post=self.friends_post).exists())

        self.client.force_login(self.bob)
        r3 = self.client.post(url)
        self.assertEqual(r3.status_code, 302)
        self.assertTrue(Like.objects.filter(author=self.bob, post=self.friends_post).exists())

    def test_like_owner_can_like_own_friends_post(self):
        """Owner sanity check (FRIENDS)."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.alice_friends_post.id})
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": True, "count": 1})

    # ───────────────────────────────────────────────────────────────────────────
    # US-27: View likes on a public entry (and access on unlisted/friends)
    # ───────────────────────────────────────────────────────────────────────────

    def test_view_likes_public_post_lists_likers(self):
        """PUBLIC: authenticated users can see likes page with likers."""
        Like.objects.create(author=self.alice, post=self.public_post)
        self.client.force_login(self.bob)
        url = reverse("authors:post_likes_page", kwargs={"post_id": self.public_post.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("like_count", resp.context)
        self.assertEqual(resp.context["like_count"], 1)
        likers = [lk.author.displayName for lk in resp.context["likes"]]
        self.assertIn("Alice", likers)
        self.assertNotIn("error", resp.context or {})

    def test_view_likes_unlisted_non_follower_without_link_gets_error(self):
        """UNLISTED: non-follower w/o link → page returns 200 with error in context."""
        # Remove Alice↔Bob to make Alice a non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        url = reverse("authors:post_likes_page", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.get(url)  # no detail GET first, so no session flag
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.context)

    def test_view_likes_unlisted_non_follower_with_link_allowed(self):
        """UNLISTED: non-follower with link (detail GET first) → allowed."""
        # Remove Alice↔Bob to make Alice a non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        # GET detail to set session flag
        self.client.get(reverse("authors:post_detail", kwargs={"post_id": self.unlisted_post.id}))

        url = reverse("authors:post_likes_page", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("error", resp.context or {})

    def test_view_likes_friends_non_mutual_gets_error(self):
        """FRIENDS: non-mutual (Carol) sees error; owner can view."""
        self.client.force_login(self.carol)
        url = reverse("authors:post_likes_page", kwargs={"post_id": self.friends_post.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.context)

        self.client.force_login(self.bob)
        resp2 = self.client.get(url)
        self.assertEqual(resp2.status_code, 200)
        self.assertNotIn("error", resp2.context or {})
