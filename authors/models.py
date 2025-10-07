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
    profileImage = models.ImageField(blank=True, null=True, upload_to="user_images/")


class Post(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('text/plain', 'Plain Text'),
        ('text/markdown', 'Markdown/ CommonMark'),
        ('image/png', 'PNG Image'),
        ('image/jpeg', 'JPEG Image'),
        ('image/gif', 'GIF Image'),
        ('image/bmp', 'BMP Image'),
        ('image/webp', 'WebP Image'),
    ]
    
    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('PRIVATE', 'Private'),
        # Future: FRIENDS, SERVER_ONLY, etc.
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True, null=True)  # Short description or summary
    content = models.TextField()  # The actual post content
    contentType = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES, default='text/plain')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='PUBLIC')
    unlisted = models.BooleanField(default=False)  # If True, post is public but not shown in public feeds
    published = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    # Optional image for the post
    source = models.URLField(blank=True, null=True)  # Where the post originated from
    origin = models.URLField(blank=True, null=True)  # Original source URL
    # Image field for image posts
    image = models.ImageField(upload_to="post_images/", blank=True, null=True)
    
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
