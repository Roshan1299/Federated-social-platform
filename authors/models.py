import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class Author(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.URLField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    displayName = models.CharField(max_length=255)
    github = models.URLField(blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    profileImage = models.ImageField(blank=True, null=True, upload_to="user_images/") # Store images in media/user_images/


class Post(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('text/plain', 'Plain Text'),
        ('text/markdown', 'Markdown/ CommonMark'),
    ]
    
    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('PUBLIC_UNLISTED', 'Public Unlisted'),
        ('FRIENDS', 'Friends Only'),
        # Future: SERVER_ONLY, etc.
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True, null=True)  # Short description or summary
    content = models.TextField()  # The actual post content
    contentType = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='text/plain')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='PUBLIC')
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    # Optional image for the post
    source = models.URLField(blank=True, null=True)  # Where the post originated from
    origin = models.URLField(blank=True, null=True)  # Original source URL
    # Image field for image posts
    image = models.ImageField(upload_to="post_images/", blank=True, null=True)
    # Track if the post is deleted
    deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.title} by {self.author.displayName}"
    
    class Meta:
        ordering = ['-published']

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('author', 'post')

    def __str__(self):
        return f"{self.author.displayName} likes {self.post.title}"

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.displayName} on {self.post.title}"

class CommentLike(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('author', 'comment')

    def __str__(self):
        return f"{self.author.displayName} likes a comment on {self.comment.post.title}"

