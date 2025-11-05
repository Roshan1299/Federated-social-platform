"""
API Tests for User Stories 26, 27

26. As an author, I want to like entries that I can access,
    so I can show my appreciation.

27. As an author, when someone sends me a public entry I want to see the likes,
    so I can tell if it's good or not.

These tests cover
- Any logged-in user can like a PUBLIC post
- Liking a PUBLIC post twice toggles like → unlike correctly
- Non-followers without the link can’t like an UNLISTED post
- Non-followers with the link to the post can like an UNLISTED post
- Followers can like an UNLISTED post even without visiting the link
- On FRIENDS_only posts, only mutual followers or the post owner can like; one-way followers are blocked
- Post owner can like their own FRIENDS_only post
- Authenticated users can view the likes page for a PUBLIC post and see who liked it
- For UNLISTED posts, non-followers without the link can open the likes page but get an error in context
- For UNLISTED posts, non-followers with the link can view the likes page normally
- For FRIENDS_only posts, non-mutual followers get an error on the likes page, but the owner can view it

Edge cases
- Liking a post with empty content is rejected (forbidden / bad request)
- Unauthenticated users can’t like (they get redirected to login)
- Trying to like a deleted post returns 404, so you can’t interact with removed content
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
        """Any logged-in user can like a PUBLIC post"""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.public_post.id})
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": True, "count": 1})
        self.assertTrue(Like.objects.filter(author=self.alice, post=self.public_post).exists())

    def test_like_public_toggle_unlike(self):
        """Liking a PUBLIC post twice toggles like → unlike correctly"""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.public_post.id})
        self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")  # like
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")  # unlike
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": False, "count": 0})
        self.assertFalse(Like.objects.filter(author=self.alice, post=self.public_post).exists())

    def test_like_unlisted_non_follower_without_link_forbidden(self):
        """Non-followers without the link can’t like an UNLISTED post"""
        # Remove Alice↔Bob so Alice is non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.post(url)  # normal POST, no detail GET
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Like.objects.filter(author=self.alice, post=self.unlisted_post).exists())

    def test_like_unlisted_non_follower_with_link_allowed(self):
        """Non-followers with the link to the post can like an UNLISTED post"""
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
        """Followers can like an UNLISTED post even without visiting the link"""
        self.client.force_login(self.carol)  # Carol follows Bob
        url = reverse("authors:toggle_like", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Like.objects.filter(author=self.carol, post=self.unlisted_post).exists())

    def test_like_friends_requires_mutual_or_owner(self):
        """
        On FRIENDS_only posts, only mutual followers or the post owner can like; one-way followers are blocked
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
        """Post owner can like their own FRIENDS_only post"""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": self.alice_friends_post.id})
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content.decode(), {"liked": True, "count": 1})

    # ───────────────────────────────────────────────────────────────────────────
    # US-27: View likes on a public entry (and access on unlisted/friends)
    # ───────────────────────────────────────────────────────────────────────────

    def test_view_likes_public_post_lists_likers(self):
        """Authenticated users that are logged in can view the likes page for a PUBLIC post and see who liked it"""
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
        """For UNLISTED posts, non-followers without the link can open the likes page but get an error in context"""
        # Remove Alice↔Bob to make Alice a non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        url = reverse("authors:post_likes_page", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.get(url)  # no detail GET first, so no session flag
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.context)

    def test_view_likes_unlisted_non_follower_with_link_allowed(self):
        """For UNLISTED posts, non-followers with the link can view the likes page normally"""
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
        """For FRIENDS_only posts, non-mutual followers get an error on the likes page, but the owner can view it"""
        self.client.force_login(self.carol)
        url = reverse("authors:post_likes_page", kwargs={"post_id": self.friends_post.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.context)

        self.client.force_login(self.bob)
        resp2 = self.client.get(url)
        self.assertEqual(resp2.status_code, 200)
        self.assertNotIn("error", resp2.context or {})

    # ───────────────────────────────────────────────────────────────────────────
    # Some extra edge cases for like post
    # ───────────────────────────────────────────────────────────────────────────

    def test_cannot_like_empty_post(self):
        """
        Liking a post with empty content is rejected (forbidden / bad request)
        """
        # Make Bob’s post empty
        empty_post = Post.objects.create(
            author=self.bob,
            title="Empty Post",
            content="",
            contentType="text/plain",
            visibility="PUBLIC",
            published=timezone.now(),
            updated=timezone.now(),
        )

        self.client.force_login(self.alice)
        url = reverse("authors:toggle_like", kwargs={"post_id": empty_post.id})
        resp = self.client.post(url)
        # Expect forbidden or bad request, not redirect
        self.assertIn(resp.status_code, (403, 400))
        self.assertFalse(Like.objects.filter(post=empty_post).exists())

    def test_like_requires_login(self):
        """
        Unauthenticated users that are not logged in can’t like (they get redirected to login)
        """
        url = reverse("authors:toggle_like", kwargs={"post_id": self.public_post.id})
        resp = self.client.post(url)  # no login
        # Django login_required usually 302s to /accounts/login/?next=...
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login", resp["Location"])
        # and no like should be created
        self.assertFalse(
            Like.objects.filter(author__username="anonymous", post=self.public_post).exists()
        )

    def test_like_deleted_post_returns_404(self):
        """
        Trying to like a deleted post returns 404, so you can’t interact with removed content
        """
        self.client.force_login(self.alice)

        # Create a post and then delete it
        temp_post = Post.objects.create(
            author=self.bob,
            title="Temporary",
            content="to be deleted",
            visibility="PUBLIC",
            published=timezone.now(),
            updated=timezone.now(),
        )
        temp_id = temp_post.id
        temp_post.delete()

        # Try to like deleted post
        url = reverse("authors:toggle_like", kwargs={"post_id": temp_id})
        resp = self.client.post(url)

        # Should return 404 (post not found)
        self.assertEqual(resp.status_code, 404)

