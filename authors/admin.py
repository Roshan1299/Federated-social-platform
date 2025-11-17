from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import Author, Post, Follow, Comment, Like, FollowRequest, CommentLike, RemoteNode
from .models import Image

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

class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')
    readonly_fields = ('id', 'created_at')
    search_fields = ('follower__displayName', 'following__displayName')

class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'created_at', 'updated_at')
    readonly_fields = ('id', 'created_at', 'updated_at')
    search_fields = ('author__displayName', 'post__title', 'content')

class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'created_at')
    readonly_fields = ('id', 'created_at')
    search_fields = ('author__displayName', 'post__title')

class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'receiver', 'status', 'created_at')
    readonly_fields = ('id', 'created_at')
    list_filter = ('status',)
    search_fields = ('sender__displayName', 'receiver__displayName')

class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'comment', 'created_at')
    readonly_fields = ('id', 'created_at')
    search_fields = ('author__displayName',)

class RemoteNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'enabled', 'created_at')
    list_filter = ('enabled', 'created_at')
    search_fields = ('name', 'base_url')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(Author, AuthorAdmin)
admin.site.register(Post, PostAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Like, LikeAdmin)
admin.site.register(FollowRequest, FollowRequestAdmin)
admin.site.register(CommentLike, CommentLikeAdmin)
admin.site.register(RemoteNode, RemoteNodeAdmin)
admin.site.register(Image)