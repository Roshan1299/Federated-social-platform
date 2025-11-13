"""
API Tests for User Stories 28, 29, 44

28. As an author, I want to comment on entries that I can access,
    so I can make a witty reply.

29. As an author, I want to like comments that I can access,
    so I can show my appreciation.

44. As an author, comments on my friends-only entries are visible only to my friends and the comment's author.

These tests cover
- Any logged-in user can comment on a PUBLIC post
- Non-followers without the link can’t comment on an UNLISTED post
- Non-followers with the link can comment on an UNLISTED post
- Followers can comment on an UNLISTED post even without the link
- On FRIENDS-only posts, only mutual followers or the post owner can comment; one-way followers are blocked
- Post owner can always comment on their own FRIENDS-only post
- Any logged-in user can like a PUBLIC comment
- Non-followers without the link can’t like an UNLISTED comment
- Non-followers with the link can like an UNLISTED comment
- Followers can like an UNLISTED comment
- Only mutual friends or the owner can like comments on FRIENDS-only posts
- Liking a PUBLIC comment twice toggles like/unlike properly

Edge cases
- Empty or whitespace-only comments are rejected (validates input)
- Unauthenticated users can’t comment or like (redirect to login)
- Comments with empty content can’t be liked
- liking a comment that was deleted should give error
- Adding a comment on a deleted post should be blocked (404).
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
        """Any logged-in user can comment on a PUBLIC post"""
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
        Non-followers without the link can’t comment on an UNLISTED post
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
        Non-followers with the link can comment on an UNLISTED post
        We simulate "has the link" by GETing the detail first.
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
        """Followers can comment on an UNLISTED post even without the link"""
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
        On FRIENDS-only posts, only mutual followers or the post owner can comment; one-way followers are blocked
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
        """Post owner can always comment on their own FRIENDS-only post"""
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
        """Any logged-in user can like a PUBLIC comment"""
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
        """Non-followers without the link can’t like an UNLISTED comment"""
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
        """Non-followers with the link can like an UNLISTED comment"""
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
        """Followers can like an UNLISTED comment"""
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
        Only mutual friends or the owner can like comments on FRIENDS-only posts
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
        """Liking a PUBLIC comment twice toggles like/unlike properly"""
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
    # ───────────────────────────────────────────────────────────────────────────
    # Some Extra Edge Cases test
    # ───────────────────────────────────────────────────────────────────────────

    def test_comment_empty_content_rejected(self):
        """
        Empty or whitespace-only comments are rejected (validates input)
        """
        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": self.public_post.id})

        r1 = self.client.post(url, data={"content": ""})
        r2 = self.client.post(url, data={"content": "   "})

        # both attempts redirect back, but no comment rows are created
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(r2.status_code, 302)
        self.assertFalse(
            Comment.objects.filter(post=self.public_post, author=self.alice, content="").exists()
        )
        self.assertFalse(
            Comment.objects.filter(post=self.public_post, author=self.alice, content="   ").exists()
        )

    def test_unauthenticated_cannot_comment_or_like(self):
        """
        Unauthenticated users that are not logged in can’t comment or like (redirect to login)
        """
        url_comment = reverse("authors:add_comment", kwargs={"post_id": self.public_post.id})
        url_like_comment = reverse("authors:toggle_comment_like",
                                   kwargs={"comment_id": self.public_comment.id})

        # Not logged in
        resp_comment = self.client.post(url_comment, data={"content": "hi"})
        resp_like = self.client.post(url_like_comment)

        # Django default: redirect to login page
        self.assertEqual(resp_comment.status_code, 302)
        self.assertEqual(resp_like.status_code, 302)

        # And no side effects
        self.assertFalse(
            Comment.objects.filter(post=self.public_post, content="hi").exists()
        )
        self.assertFalse(
            CommentLike.objects.filter(comment=self.public_comment).exists()
        )
    def test_cannot_like_empty_comment(self):
        """
        Comments with empty content can’t be liked
        """
        # Create an empty comment manually
        empty_comment = Comment.objects.create(
            post=self.public_post, author=self.bob, content=""
        )

        self.client.force_login(self.alice)
        url = reverse("authors:toggle_comment_like",
                      kwargs={"comment_id": empty_comment.id})

        resp = self.client.post(url)

        # Expect forbidden (403) or redirect blocked
        self.assertIn(resp.status_code, (403, 400))
        self.assertFalse(
            CommentLike.objects.filter(author=self.alice, comment=empty_comment).exists()
        )

    def test_like_deleted_comment_returns_404(self):
        """
        liking a comment that was deleted should give error
        """
        self.client.force_login(self.alice)

        # Create and delete comment
        temp_comment = Comment.objects.create(
            post=self.public_post, author=self.bob, content="temp"
        )
        temp_id = temp_comment.id
        temp_comment.delete()

        # Attempt to like deleted comment
        url = reverse("authors:toggle_comment_like", kwargs={"comment_id": temp_id})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)
    def test_cannot_comment_on_deleted_post(self):
        """
        Adding a comment on a deleted post should be blocked (404).
        """
        # Make a deleted PUBLIC post owned by Bob
        deleted_post = Post.objects.create(
            author=self.bob,
            title="Dead post",
            content="nope",
            contentType="text/plain",
            visibility="PUBLIC",
            published=timezone.now(),
            updated=timezone.now(),
            deleted=True,  # soft-deleted
        )

        self.client.force_login(self.alice)
        url = reverse("authors:add_comment", kwargs={"post_id": deleted_post.id})
        resp = self.client.post(url, data={"content": "should not be saved"})

        # Expect Not Found and no comment created
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(
            Comment.objects.filter(post=deleted_post, author=self.alice).exists()
        )
