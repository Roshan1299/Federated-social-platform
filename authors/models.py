import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Author(AbstractUser):
    """
    Author model - represents both local and federated users.
    
    Primary Key: id (UUID) - used for internal references and URL construction
    Unique Identifier: url - used for federation and cross-node identity
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.URLField(blank=True, null=True)
    url = models.URLField(unique=True, blank=True, null=True)  # UNIQUE constraint for federation
    displayName = models.CharField(max_length=255)
    github = models.URLField(blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    profileImage = models.ForeignKey(
        "Image",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="author_profile_images",
    )
    last_github_event_id = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        """Auto-populate url and host fields for local authors on creation"""
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


class Image(models.Model):
    id = models.AutoField(primary_key=True)
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    data = models.BinaryField()   

    def __str__(self):
        return self.file_name

    
class Post(models.Model):
    """
    Post/Entry model - represents content created by authors.
    
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
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    content = models.TextField()  # text or base64 image
    contentType = models.CharField(max_length=30, choices=CONTENT_TYPE_CHOICES, default='text/plain')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='PUBLIC')
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    # Federation fields - origin is the canonical identifier across nodes
    source = models.URLField(blank=True, null=True)  # Where post was copied from
    origin = models.URLField(unique=True, blank=True, null=True)  # UNIQUE - canonical URL
    
    image = models.ForeignKey(
        "Image",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="post_images",
    )
    deleted = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        """Auto-populate origin for local posts on creation"""
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
        return f"{self.title} by {self.author.displayName}"
    
    class Meta:
        ordering = ['-published']
        # Add index on origin for fast lookups during federation
        indexes = [
            models.Index(fields=['origin']),
        ]


class Follow(models.Model):
    follower = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower.displayName} follows {self.following.displayName}"


class FollowRequest(models.Model):
    sender = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='sent_follow_requests')
    receiver = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='received_follow_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('DENIED', 'Denied'),
        ],
        default='PENDING'
    )

    class Meta:
        unique_together = ('sender', 'receiver')

    def __str__(self):
        return f"{self.sender.displayName} requested to follow {self.receiver.displayName} ({self.status})"

    
class Like(models.Model):
    """
    Like model - represents an author liking a post.
    
    Primary Key: id (UUID)
    Unique Identifier: origin - the canonical URL of this like
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Add origin field for federation support
    origin = models.URLField(unique=True, blank=True, null=True)  # UNIQUE - canonical URL

    def save(self, *args, **kwargs):
        """Auto-populate origin for local likes on creation"""
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

    def __str__(self):
        return f"{self.author.displayName} likes {self.post.title}"


class Comment(models.Model):
    """
    Comment model - represents a comment on a post.
    
    Primary Key: id (UUID)
    Unique Identifier: origin - the canonical URL of this comment
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add origin field for federation support
    origin = models.URLField(unique=True, blank=True, null=True)  # UNIQUE - canonical URL

    def save(self, *args, **kwargs):
        """Auto-populate origin for local comments on creation"""
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

    def __str__(self):
        return f"Comment by {self.author.displayName} on {self.post.title}"


class CommentLike(models.Model):
    """
    CommentLike model - represents an author liking a comment.
    
    Primary Key: id (UUID)
    Unique Identifier: origin - the canonical URL of this comment like
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Add origin field for federation support
    origin = models.URLField(unique=True, blank=True, null=True)  # UNIQUE - canonical URL

    def save(self, *args, **kwargs):
        """Auto-populate origin for local comment likes on creation"""
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

    def __str__(self):
        return f"{self.author.displayName} likes a comment on {self.comment.post.title}"


class RemoteNode(models.Model):
    """
    RemoteNode model - stores credentials and connection details for another server.

    Primary Key: id (AutoField)
    Unique Identifier: base_url (one row per remote node)

    Used for:
      - Knowing where to deliver inbox items
      - Enabling/disabling communication with specific nodes
    """
    name = models.CharField(max_length=255)
    base_url = models.URLField(unique=True)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.base_url})"


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
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('recipient', 'post')
        indexes = [
            models.Index(fields=['recipient', 'post']),
            models.Index(fields=['received_at']),
        ]
    
    def __str__(self):
        return f"{self.post.title} → {self.recipient.displayName}'s inbox"

