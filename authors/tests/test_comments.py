"""
API Tests for User Stories 28, 29

28. As an author, I want to comment on entries that I can access,
    so I can make a witty reply.

29. As an author, I want to like comments that I can access,
    so I can show my appreciation.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from authors.models import Author, Post, Follow, Comment, CommentLike


class CommentsAPITests(TestCase):
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
        # Alice and Bob are mutual friends
        Follow.objects.create(follower=self.alice, following=self.bob)
        Follow.objects.create(follower=self.bob, following=self.alice)

        # ── Posts ───────────────────────────────────────────────────────────────
        self.public_post = Post.objects.create(
            author=self.bob,
            title="Public Post",
            content="Hello public",
            contentType="text/plain",
            visibility="PUBLIC",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.unlisted_post = Post.objects.create(
            author=self.bob,
            title="Unlisted Post",
            content="Hello unlisted",
            contentType="text/plain",
            visibility="PUBLIC_UNLISTED",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.bobs_friends_post = Post.objects.create(
            author=self.bob,
            title="Bob Friends Post",
            content="Bob's friends-only",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )
        self.alices_friends_post = Post.objects.create(
            author=self.alice,
            title="Alice Friends Post",
            content="Alice's friends-only",
            contentType="text/plain",
            visibility="FRIENDS",
            published=timezone.now(),
            updated=timezone.now(),
        )

        # ── Existing comments for like tests ────────────────────────────────────
        self.public_comment = Comment.objects.create(
            post=self.public_post, author=self.bob, content="Public thanks!"
        )
        self.unlisted_comment = Comment.objects.create(
            post=self.unlisted_post, author=self.bob, content="Unlisted thanks!"
        )
        self.bobs_friends_comment = Comment.objects.create(
            post=self.bobs_friends_post, author=self.bob, content="Friends only!"
        )

        self.client = Client()

    # ───────────────────────────────────────────────────────────────────────────
    # US-28: Comment on entries I can access
    # ───────────────────────────────────────────────────────────────────────────

    def test_comment_public_any_authenticated(self):
        """PUBLIC: any logged-in user can comment (302 and row created)."""
        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": self.public_post.id})
        resp = self.client.post(url, data={"content": "Nice public!"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(
                post=self.public_post, author=self.alice, content="Nice public!"
            ).exists()
        )

    def test_comment_unlisted_non_follower_without_link_forbidden(self):
        """
        PUBLIC_UNLISTED: non-follower WITHOUT link → 403 (no session flag set).
        Carol is a follower of Bob in setUp. Use a non-follower: Alice unfollows Bob first.
        """
        # Remove Alice↔Bob to simulate true non-follower w/o link
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": self.unlisted_post.id})
        # Direct POST (no detail GET) => should fail
        resp = self.client.post(url, data={"content": "should fail (no link)"})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            Comment.objects.filter(
                post=self.unlisted_post, author=self.alice
            ).exists()
        )

    def test_comment_unlisted_non_follower_with_link_allowed(self):
        """
        PUBLIC_UNLISTED: non-follower WITH link → allowed.
        We simulate "has the link" by GETing the detail first (session flag set).
        """
        # Make Alice a true non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)

        # Visit detail page first to set session flag unlisted_access_<id>=True
        detail = reverse("authors:post_detail", kwargs={"post_id": self.unlisted_post.id})
        self.client.get(detail)

        url = reverse("authors:add_comment", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.post(url, data={"content": "now I have the link"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(
                post=self.unlisted_post, author=self.alice, content="now I have the link"
            ).exists()
        )

    def test_comment_unlisted_follower_allowed(self):
        """PUBLIC_UNLISTED: follower can comment without visiting detail first."""
        self.client.force_login(self.carol)  # Carol follows Bob (one-way)
        url = reverse("authors:add_comment", kwargs={"post_id": self.unlisted_post.id})
        resp = self.client.post(url, data={"content": "follower can comment"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(
                post=self.unlisted_post, author=self.carol, content="follower can comment"
            ).exists()
        )

    def test_comment_friends_requires_mutual_or_owner(self):
        """
        FRIENDS:
          - Carol (one-way follower) → 403
          - Alice (mutual) → 302
          - Bob (owner) → 302
        """
        url = reverse("authors:add_comment", kwargs={"post_id": self.bobs_friends_post.id})

        self.client.force_login(self.carol)
        r1 = self.client.post(url, data={"content": "carol nope"})
        self.assertEqual(r1.status_code, 403)

        self.client.force_login(self.alice)
        r2 = self.client.post(url, data={"content": "alice ok"})
        self.assertEqual(r2.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(
                post=self.bobs_friends_post, author=self.alice, content="alice ok"
            ).exists()
        )

        self.client.force_login(self.bob)
        r3 = self.client.post(url, data={"content": "owner ok"})
        self.assertEqual(r3.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(
                post=self.bobs_friends_post, author=self.bob, content="owner ok"
            ).exists()
        )

    def test_owner_can_always_comment_on_own_post(self):
        """Owner sanity check on FRIENDS."""
        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": self.alices_friends_post.id})
        resp = self.client.post(url, data={"content": "my note"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(
                post=self.alices_friends_post, author=self.alice, content="my note"
            ).exists()
        )

    # ───────────────────────────────────────────────────────────────────────────
    # US-29: Like comments that I can access
    # ───────────────────────────────────────────────────────────────────────────

    def test_like_comment_public_any_authenticated(self):
        """PUBLIC comment: any logged-in user can like (302 & row created)."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like",
                      kwargs={"comment_id": self.public_comment.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CommentLike.objects.filter(author=self.alice,
                                       comment=self.public_comment).exists()
        )

    def test_like_comment_unlisted_non_follower_without_link_forbidden(self):
        """UNLISTED comment: non-follower without link → 403."""
        # Make Alice a true non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like",
                      kwargs={"comment_id": self.unlisted_comment.id})
        resp = self.client.post(url)  # no detail visit => no session flag
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(
            CommentLike.objects.filter(author=self.alice,
                                       comment=self.unlisted_comment).exists()
        )

    def test_like_comment_unlisted_non_follower_with_link_allowed(self):
        """UNLISTED comment: non-follower with link (detail GET first) → allowed."""
        # Make Alice a true non-follower
        Follow.objects.filter(follower=self.alice, following=self.bob).delete()
        Follow.objects.filter(follower=self.bob, following=self.alice).delete()

        self.client.force_login(self.alice)
        # GET detail to set session flag
        self.client.get(reverse("authors:post_detail",
                                kwargs={"post_id": self.unlisted_post.id}))

        url = reverse("authors:toggle_comment_like",
                      kwargs={"comment_id": self.unlisted_comment.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CommentLike.objects.filter(author=self.alice,
                                       comment=self.unlisted_comment).exists()
        )

    def test_like_comment_unlisted_follower_allowed(self):
        """UNLISTED comment: follower (Carol) can like without link."""
        self.client.force_login(self.carol)  # Carol follows Bob
        url = reverse("authors:toggle_comment_like",
                      kwargs={"comment_id": self.unlisted_comment.id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            CommentLike.objects.filter(author=self.carol,
                                       comment=self.unlisted_comment).exists()
        )

    def test_like_comment_friends_requires_mutual_or_owner(self):
        """
        FRIENDS comment:
          - Carol (one-way) → 403
          - Alice (mutual) → 302
          - Bob (owner) → 302
        """
        url = reverse("authors:toggle_comment_like",
                      kwargs={"comment_id": self.bobs_friends_comment.id})

        self.client.force_login(self.carol)
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, 403)

        self.client.force_login(self.alice)
        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 302)
        self.assertTrue(
            CommentLike.objects.filter(author=self.alice,
                                       comment=self.bobs_friends_comment).exists()
        )

        self.client.force_login(self.bob)
        r3 = self.client.post(url)
        self.assertEqual(r3.status_code, 302)
        self.assertTrue(
            CommentLike.objects.filter(author=self.bob,
                                       comment=self.bobs_friends_comment).exists()
        )

    def test_like_comment_toggle_cycle_public(self):
        """Toggle like/unlike on PUBLIC comment."""
        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like",
                      kwargs={"comment_id": self.public_comment.id})
        # like
        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, 302)
        self.assertTrue(CommentLike.objects.filter(author=self.alice,
                                                   comment=self.public_comment).exists())
        # unlike
        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 302)
        self.assertFalse(CommentLike.objects.filter(author=self.alice,
                                                    comment=self.public_comment).exists())
