import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class Author(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.URLField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    displayName = models.CharField(max_length=255)
    github = models.URLField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    profileImage = models.URLField(blank=True, null=True) # URL to an image