from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import Author, Post

class AuthorAdmin(UserAdmin):
    model = Author
    list_display = ('username', 'displayName', 'email', 'is_staff', 'is_active')
    readonly_fields = ("id", "host", "url",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Profile info"), {"fields": ("displayName", "id", "host", "url", "github", "description", "profileImage")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'contentType', 'visibility', 'published', 'updated')
    list_filter = ('contentType', 'visibility', 'published')
    search_fields = ('title', 'content', 'author__displayName')
    readonly_fields = ('id', 'published', 'updated')

admin.site.register(Author, AuthorAdmin)
admin.site.register(Post, PostAdmin)