from django.db import models
from django.contrib.auth.models import AbstractUser

class Author(AbstractUser):
    displayName = models.CharField(max_length=255)
    github = models.URLField(blank=True, null=True)
    profileImage = models.URLField(blank=True, null=True) # URL to an image