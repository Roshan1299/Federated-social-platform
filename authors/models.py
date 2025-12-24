"""
Database models for the Federated Social Platform.

This module defines all the core data models for the social platform,
including users, posts, comments, likes, and relationships between them.
The models support federation by including fields for cross-node identification
and communication.
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Author(AbstractUser):
    """
    Author model - represents both local and federated users.

    This model extends Django's AbstractUser to provide social networking
    functionality. Each author has a unique identifier that remains consistent
    across the federated network, along with profile information and settings.

    Primary Key: id (UUID) - used for internal references and URL construction
    Unique Identifier: url - used for federation and cross-node identity
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.URLField(blank=True, null=True, help_text="The host URL of this author's node")
    url = models.URLField(unique=True, blank=True, null=True, help_text="The canonical URL for this author across all nodes")
    displayName = models.CharField(max_length=255, help_text="The display name for this author")
    github = models.URLField(blank=True, null=True, help_text="GitHub profile URL")
    description = models.CharField(max_length=500, blank=True, null=True, help_text="Author's profile description")
    profileImage = models.ForeignKey(
        "Image",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="author_profile_images",
        help_text="Profile image for this author"
    )
    last_github_event_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="ID of the last processed GitHub event for automatic post generation"
    )

    def save(self, *args, **kwargs):
        """Auto-populate url and host fields for local authors on creation."""
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only set url/host if not already set (for local authors)
        if is_new and not self.url:
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            self.url = f"{base_url}/api/authors/{self.id}/"
            self.host = base_url
            # Save again to persist url/host
            super().save(update_fields=['url', 'host'])

    def is_remote(self) -> bool:
        """Determine if this author is remote based on their host."""
        local_node = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
        author_host = (self.host or "").rstrip("/")
        return (author_host != "" and author_host != local_node)

    def __str__(self):
        """String representation of the Author."""
        return f"{self.displayName} ({self.id})"


class Image(models.Model):
    """
    Image model - stores binary image data with metadata.

    This model is used for storing profile images and post images.
    Images are stored as binary data in the database.
    """
    id = models.AutoField(primary_key=True)
    file_name = models.CharField(max_length=255, help_text="Name of the image file")
    content_type = models.CharField(max_length=100, help_text="MIME type of the image")
    data = models.BinaryField(help_text="Binary image data")

    def __str__(self):
        """String representation of the Image."""
        return self.file_name


class Post(models.Model):
    """
    Post/Entry model - represents content created by authors.

    This model represents posts or entries that authors create.
    It includes support for different content types, visibility levels,
    and federation through canonical URLs.

    Primary Key: id (UUID) - used for internal references and URL construction
    Unique Identifier: origin - the canonical URL of this post, unique across all nodes
    """
    CONTENT_TYPE_CHOICES = [
        ('text/plain', 'Plain Text'),
        ('text/markdown', 'Markdown/ CommonMark'),
        ('image', 'Image'),
        ('image/png;base64', 'Image (PNG)'),
        ('image/jpeg;base64', 'Image (JPEG)'),
        ('application/base64', 'Image (Other)'),
    ]

    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('PUBLIC_UNLISTED', 'Public Unlisted'),
        ('FRIENDS', 'Friends Only'),
        ('DELETED', 'Deleted'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='posts',
        help_text="The author who created this post"
    )
    title = models.CharField(max_length=255, help_text="Title of the post")
    description = models.TextField(blank=True, null=True, help_text="Description or summary of the post")
    content = models.TextField(help_text="The main content of the post (text or base64 image)")  # text or base64 image
    contentType = models.CharField(
        max_length=30, 
        choices=CONTENT_TYPE_CHOICES, 
        default='text/plain',
        help_text="The type of content in this post"
    )
    visibility = models.CharField(
        max_length=20, 
        choices=VISIBILITY_CHOICES, 
        default='PUBLIC',
        help_text="Who can see this post"
    )
    published = models.DateTimeField(auto_now_add=True, help_text="When the post was first published")
    updated = models.DateTimeField(auto_now=True, help_text="When the post was last updated")

    # Federation fields - origin is the canonical identifier across nodes
    source = models.URLField(blank=True, null=True, help_text="Where post was copied from")  # Where post was copied from
    origin = models.URLField(unique=True, blank=True, null=True, help_text="Canonical URL across all nodes")  # UNIQUE - canonical URL

    image = models.ForeignKey(
        "Image",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="post_images",
        help_text="Associated image for this post"
    )
    deleted = models.BooleanField(default=False, help_text="Whether this post has been marked as deleted")

    def save(self, *args, **kwargs):
        """Auto-populate origin for local posts on creation."""
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only set origin if not already set (for local posts)
        if is_new and not self.origin:
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            self.origin = f"{base_url}/api/authors/{self.author.id}/entries/{self.id}"
            self.source = self.origin
            # Save again to persist origin/source
            super().save(update_fields=['origin', 'source'])

    def __str__(self):
        """String representation of the Post."""
        return f"{self.title} by {self.author.displayName}"

    class Meta:
        ordering = ['-published']
        # Add index on origin for fast lookups during federation
        indexes = [
            models.Index(fields=['origin']),
        ]


class Follow(models.Model):
    """
    Follow model - represents a follow relationship between authors.

    This model represents a one-way follow relationship where one author
    follows another. This is the foundation of the social network's
    connection system.
    """
    follower = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='following',
        help_text="The author who is following"
    )
    following = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='followers',
        help_text="The author being followed"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the follow relationship was created")

    class Meta:
        unique_together = ('follower', 'following')
        verbose_name = 'Follow Relationship'
        verbose_name_plural = 'Follow Relationships'

    def __str__(self):
        """String representation of the Follow relationship."""
        return f"{self.follower.displayName} follows {self.following.displayName}"


class FollowRequest(models.Model):
    """
    FollowRequest model - represents a pending follow request.

    When one author wants to follow another, a follow request is created.
    The target author can then approve or deny the request.
    """
    sender = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='sent_follow_requests',
        help_text="The author requesting to follow"
    )
    receiver = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='received_follow_requests',
        help_text="The author being requested to follow"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the follow request was created")
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('DENIED', 'Denied'),
        ],
        default='PENDING',
        help_text="Status of the follow request"
    )

    class Meta:
        unique_together = ('sender', 'receiver')
        verbose_name = 'Follow Request'
        verbose_name_plural = 'Follow Requests'

    def __str__(self):
        """String representation of the FollowRequest."""
        return f"{self.sender.displayName} requested to follow {self.receiver.displayName} ({self.status})"


class Like(models.Model):
    """
    Like model - represents an author liking a post.

    This model represents when an author likes a post. It supports
    federation by including an origin field for cross-node identification.

    Primary Key: id (UUID)
    Unique Identifier: origin - the canonical URL of this like
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='likes',
        help_text="The author who created the like"
    )
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='likes',
        help_text="The post being liked"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the like was created")

    # Add origin field for federation support
    origin = models.URLField(unique=True, blank=True, null=True, help_text="Canonical URL across all nodes")  # UNIQUE - canonical URL

    def save(self, *args, **kwargs):
        """Auto-populate origin for local likes on creation."""
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only set origin if not already set (for local likes)
        if is_new and not self.origin:
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            self.origin = f"{base_url}/api/authors/{self.author.id}/liked/{self.id}"
            # Save again to persist origin
            super().save(update_fields=['origin'])

    class Meta:
        unique_together = ('author', 'post')
        indexes = [
            models.Index(fields=['origin']),
        ]
        verbose_name = 'Like'
        verbose_name_plural = 'Likes'

    def __str__(self):
        """String representation of the Like."""
        return f"{self.author.displayName} likes {self.post.title}"


class Comment(models.Model):
    """
    Comment model - represents a comment on a post.

    This model represents comments that authors make on posts.
    It supports federation by including an origin field for cross-node identification.

    Primary Key: id (UUID)
    Unique Identifier: origin - the canonical URL of this comment
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments',
        help_text="The post being commented on"
    )
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='comments',
        help_text="The author who made the comment"
    )
    content = models.TextField(max_length=2000, help_text="The content of the comment")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the comment was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="When the comment was last updated")

    # Add origin field for federation support
    origin = models.URLField(unique=True, blank=True, null=True, help_text="Canonical URL across all nodes")  # UNIQUE - canonical URL

    def save(self, *args, **kwargs):
        """Auto-populate origin for local comments on creation."""
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only set origin if not already set (for local comments)
        if is_new and not self.origin:
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            self.origin = f"{base_url}/api/authors/{self.author.id}/commented/{self.id}"
            # Save again to persist origin
            super().save(update_fields=['origin'])

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['origin']),
        ]
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'

    def __str__(self):
        """String representation of the Comment."""
        return f"Comment by {self.author.displayName} on {self.post.title}"


class CommentLike(models.Model):
    """
    CommentLike model - represents an author liking a comment.

    This model represents when an author likes a comment. It supports
    federation by including an origin field for cross-node identification.

    Primary Key: id (UUID)
    Unique Identifier: origin - the canonical URL of this comment like
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='comment_likes',
        help_text="The author who liked the comment"
    )
    comment = models.ForeignKey(
        Comment, 
        on_delete=models.CASCADE, 
        related_name='likes',
        help_text="The comment being liked"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the like was created")

    # Add origin field for federation support
    origin = models.URLField(unique=True, blank=True, null=True, help_text="Canonical URL across all nodes")  # UNIQUE - canonical URL

    def save(self, *args, **kwargs):
        """Auto-populate origin for local comment likes on creation."""
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only set origin if not already set (for local comment likes)
        if is_new and not self.origin:
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            # Note: Comment likes might use a different URL structure
            self.origin = f"{base_url}/api/authors/{self.author.id}/liked/{self.id}"
            # Save again to persist origin
            super().save(update_fields=['origin'])

    class Meta:
        unique_together = ('author', 'comment')
        indexes = [
            models.Index(fields=['origin']),
        ]
        verbose_name = 'Comment Like'
        verbose_name_plural = 'Comment Likes'

    def __str__(self):
        """String representation of the CommentLike."""
        return f"{self.author.displayName} likes a comment on {self.comment.post.title}"


class RemoteNode(models.Model):
    """
    RemoteNode model - stores credentials and connection details for another server.

    This model stores information about other federated nodes that this
    node can communicate with. It includes authentication credentials and
    connection settings.

    Primary Key: id (AutoField)
    Unique Identifier: base_url (one row per remote node)

    Used for:
      - Knowing where to deliver inbox items
      - Enabling/disabling communication with specific nodes
    """
    name = models.CharField(max_length=255, help_text="Display name for this remote node")
    base_url = models.URLField(unique=True, help_text="Base URL of the remote node")
    username = models.CharField(max_length=255, help_text="Username for authentication with this node")
    password = models.CharField(max_length=255, help_text="Password for authentication with this node")
    enabled = models.BooleanField(default=True, help_text="Whether communication with this node is enabled")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When this remote node was added")
    updated_at = models.DateTimeField(auto_now=True, help_text="When this remote node configuration was last updated")

    def __str__(self):
        """String representation of the RemoteNode."""
        return f"{self.name} ({self.base_url})"

    class Meta:
        verbose_name = 'Remote Node'
        verbose_name_plural = 'Remote Nodes'


class InboxReceipt(models.Model):
    """
    InboxReceipt model - tracks which posts were delivered to which author's inbox.

    This model solves the problem of stale Follow relationships in distributed systems:
    - When a remote node sends a post to an author's inbox, we create a receipt
    - The stream view uses receipts to determine if friends-only remote posts should be visible
    - For local posts, we rely on Follow relationships (always current)
    - For remote posts, we trust the sending node's visibility decision (captured in receipt)

    Example scenario:
    1. Local author A and B both follow remote author R
    2. R follows both A and B back (mutual friends)
    3. R unfollows A (but doesn't notify our node)
    4. R creates friends-only post, R's node sends to B's inbox (correctly)
    5. Without receipts: Both A and B see the post (wrong - stale Follow data)
    6. With receipts: Only B sees it (correct - only B received it in inbox)
    """
    id = models.AutoField(primary_key=True)
    recipient = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='inbox_receipts',
        help_text="The author who received this post in their inbox"
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='inbox_receipts',
        help_text="The post that was delivered to the inbox"
    )
    received_at = models.DateTimeField(auto_now_add=True, help_text="When the post was received in the inbox")

    class Meta:
        unique_together = ('recipient', 'post')
        indexes = [
            models.Index(fields=['recipient', 'post']),
            models.Index(fields=['received_at']),
        ]
        verbose_name = 'Inbox Receipt'
        verbose_name_plural = 'Inbox Receipts'

    def __str__(self):
        """String representation of the InboxReceipt."""
        return f"{self.post.title} → {self.recipient.displayName}'s inbox"