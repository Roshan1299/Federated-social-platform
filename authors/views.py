import markdown
from django.forms import BaseModelForm
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DetailView, ListView, TemplateView
from django.core.paginator import Paginator
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.conf import settings
from .models import Author, Post, Follow, FollowRequest, Like, Comment, CommentLike, RemoteNode, InboxReceipt
from .forms import AuthorCreationForm, AuthorProfileForm, PostForm, RemoteNodeForm, NodeConfigurationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from .authentication import http_basic_auth_or_session
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from .forms import ImageUploadForm
from .models import Image
from .inbox_handlers import reopen_follow_request, get_or_create_author
from .utils.federation import notify_remote_new_post, notify_remote_edit_post, notify_remote_delete_post, send_unfollow_to_remote_author, notify_remote_comment, notify_remote_author_update
import uuid
import urllib.parse
import requests
import logging
from django.conf import settings
from .api_views import SingleFollowingAPIView
from authors.utils.remote_read import sync_remote_comments_for_post, sync_remote_likes_for_post, sync_remote_comment_likes_for_post, fetch_and_sync_remote_posts
from authors.utils.remote_read import sync_remote_comments_for_post, sync_remote_likes_for_post, sync_remote_comment_likes_for_post, fetch_and_sync_remote_posts
from authors.utils.federation import send_comment_to_post_owner, send_like_to_post_owner, send_comment_like_to_post_owner



def render_post_content(post):
    ''' Rendered HTML for markdown/plain posts. '''
    if getattr(post, "contentType", "text/plain") == "text/markdown":
        return markdown.markdown(post.content or "")
    else:
        return (post.content or "").replace("\n", "<br>")

class CustomLoginView(LoginView):
    """Custom login view that redirects to the user's stream page after login"""
    def get_success_url(self):
        # Redirect to the user's own stream page after successful login
        from django.urls import reverse
        # After successful login, redirect to the current user's stream
        if self.request.user.is_authenticated:
            return reverse('authors:author_stream', kwargs={'author_id': self.request.user.id})
        # Fallback if user is somehow not authenticated
        return reverse('authors:redirect_profile')  # redirect to profile as fallback
    
    def get(self, request, *args, **kwargs):
        """If user is already authenticated, redirect to their stream"""
        if request.user.is_authenticated:
            from django.urls import reverse
            return redirect(reverse('authors:author_stream', kwargs={'author_id': request.user.id}))
        return super().get(request, *args, **kwargs)


class SignUpView(CreateView):
    form_class = AuthorCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False

        host = self.request.scheme + "://" + self.request.get_host()
        user.host = host
        user.save()

        api_url = reverse('authors:author_api', kwargs={'author_id': user.id})
        user.url = host + api_url
        user.save(update_fields=['url'])

        return redirect(self.success_url)

class AuthorProfileView(DetailView):
    form_class = AuthorProfileForm
    model = Author
    template_name = "authors/profile.html"
    pk_url_kwarg = "author_id"
    context_object_name = "author"

    # Both AuthorProfileView and AuthorEditView extend profile_base.html. To distinguish between them, set 'editable' context.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editable'] = False

        author = self.get_object()
        user = self.request.user

        # If viewing own profile → show all (including unlisted)
        if author == user:
            context["posts"] = author.posts.filter(deleted=False).order_by("-published")

        # If viewing another author you follow
        elif user.is_authenticated and Follow.objects.filter(follower=user, following=author).exists():
            is_friend = (
                Follow.objects.filter(follower=user, following=author).exists() and
                Follow.objects.filter(follower=author, following=user).exists()
            )

            if is_friend:
                # Friends see both PUBLIC + FRIENDS and PUBLIC_UNLISTED
                visibilities = ["PUBLIC", "FRIENDS", "PUBLIC_UNLISTED"]
            else:
                # One-way followers only see PUBLIC and PUBLIC_UNLISTED posts
                visibilities = ["PUBLIC", "PUBLIC_UNLISTED"]

            context["posts"] = author.posts.filter(
                visibility__in=visibilities,
                deleted=False
            ).order_by("-published")

        # If not following → only PUBLIC
        else:
            context["posts"] = author.posts.filter(
                visibility="PUBLIC",
                deleted=False
            ).order_by("-published")

        # Render post content safely
        for p in context.get("posts", []):
            p.rendered_content = render_post_content(p)

        # Relationship flags
        if user.is_authenticated and user != author:
            context['is_following'] = Follow.objects.filter(follower=user, following=author).exists()
            context['has_pending_request'] = FollowRequest.objects.filter(sender=user, receiver=author, status='PENDING').exists()
            context['is_friends'] = (
                Follow.objects.filter(follower=user, following=author).exists() and
                Follow.objects.filter(follower=author, following=user).exists()
            )
        else:
            context['is_following'] = False
            context['has_pending_request'] = False
            context['is_friends'] = False

        context["is_admin_viewing"] = user.is_authenticated and user.is_superuser

        return context

'''
Allows editing author profile.
url: "authors/<uuid:author_id>/edit"
Extends LoginRequiredMixin and UserPassesTestMixin to ensure only the profile owner can edit.
'''
class AuthorEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = AuthorProfileForm
    model = Author
    template_name = "authors/edit_profile.html"
    pk_url_kwarg = "author_id"

    # Both AuthorProfileView and AuthorEditView extend profile_base.html. To distinguish between them, set 'editable' context.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editable'] = True
        return context

    def test_func(self):
        # Ensure only the profile owner can edit it
        author = self.get_object()
        return self.request.user == author
    
    def form_valid(self, form) -> HttpResponse:
        user = form.save(commit=False)
        # Don't deactivate the user when saving profile changes
        user.save()

        try:
            notify_remote_author_update(user)
        except Exception as e:
            print("Failed to notify remote on profile edit:", e)
            
        success_url = reverse('authors:author_profile', kwargs={'author_id': user.id})
        return redirect(success_url)
    


class CreatePostView(CreateView):
    form_class = PostForm
    template_name = "authors/create_post.html"
    
    def form_valid(self, form):
        import base64
        
        # Set the author to the current user
        form.instance.author = self.request.user
        
        # Handle image content type
        content_type = form.cleaned_data.get('contentType')
        if content_type == 'image':
            image_obj = form.cleaned_data.get('image')
            if image_obj:
                # Encode image data as base64
                image_data_bytes = bytes(image_obj.data)
                base64_encoded = base64.b64encode(image_data_bytes).decode('utf-8')
                
                # Set content to base64 string
                form.instance.content = base64_encoded
                
                # Set contentType based on image's content_type
                img_content_type = image_obj.content_type.lower()
                if 'png' in img_content_type:
                    form.instance.contentType = 'image/png;base64'
                elif 'jpeg' in img_content_type or 'jpg' in img_content_type:
                    form.instance.contentType = 'image/jpeg;base64'
                else:
                    form.instance.contentType = 'application/base64'

        # Let the generic view save the post first
        response = super().form_valid(form)

        # Notify remote followers about this new post
        notify_remote_new_post(self.object)

        return response
    
    def form_invalid(self, form):
        # Log validation errors to help debug silent 200 responses on POST
        logger = logging.getLogger(__name__)
        try:
            errors = form.errors.as_json()
        except Exception:
            errors = str(form.errors)

        # Partial cleaned_data may exist even when invalid; log keys only to avoid large binary dumps
        cleaned_keys = list(getattr(form, 'cleaned_data', {}).keys()) if getattr(form, 'cleaned_data', None) else None

        logger.error("CreatePostView.form_invalid: errors=%s cleaned_keys=%s POST_keys=%s", errors, cleaned_keys, list(self.request.POST.keys()))

        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('authors:author_profile', kwargs={'author_id': self.request.user.id})

'''
Allows editing a post.
url: "authors/<uuid:author_id>/posts/<uuid:post_id>/edit"
'''
class EditPostView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = "authors/edit_post.html"
    pk_url_kwarg = "post_id"

    def test_func(self):
        # Ensure only the post author can edit it
        post = self.get_object()
        return self.request.user == post.author
    
    def get_initial(self):
        initial = super().get_initial()
        post = self.get_object()
        
        # Convert actual contentType to form's simplified version
        if post.contentType and 'base64' in post.contentType:
            initial['contentType'] = 'image'
        
        return initial

    def get_success_url(self):
        return reverse("authors:post_detail", kwargs={"post_id": self.object.id})

    def form_valid(self, form):
        import base64
        
        # Handle image content type
        content_type = form.cleaned_data.get('contentType')
        if content_type == 'image':
            image_obj = form.cleaned_data.get('image')
            if image_obj:
                # Encode image data as base64
                image_data_bytes = bytes(image_obj.data)
                base64_encoded = base64.b64encode(image_data_bytes).decode('utf-8')
                
                # Set content to base64 string
                form.instance.content = base64_encoded
                
                # Set contentType based on image's content_type
                img_content_type = image_obj.content_type.lower()
                if 'png' in img_content_type:
                    form.instance.contentType = 'image/png;base64'
                elif 'jpeg' in img_content_type or 'jpg' in img_content_type:
                    form.instance.contentType = 'image/jpeg;base64'
                else:
                    form.instance.contentType = 'application/base64'
        
        # Call the parent form_valid to save the post
        response = super().form_valid(form)

        # Notify remote followers and friends about the edited post
        notify_remote_edit_post(self.object)

        return response


'''
Allows deleting a post.
url: "authors/<uuid:author_id>/posts/<uuid:post_id>/delete"
'''
class DeletePostView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        post = get_object_or_404(Post, id=self.kwargs['post_id'])
        return self.request.user == post.author

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if self.request.user == post.author:
            post.deleted = True
            post.save()

            # Notify remote followers about the deleted post
            notify_remote_delete_post(post)

            return redirect('authors:author_profile', author_id=self.request.user.id)
        return HttpResponse("Unauthorized", status=403)

    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if self.request.user == post.author:
            return render(request, "authors/delete_post.html", {"post": post})
        return HttpResponse("Unauthorized", status=403)
    

class PostDetailView(DetailView):
    model = Post
    template_name = "authors/post_detail.html"
    pk_url_kwarg = "post_id"
    
    def get(self, request, *args, **kwargs):
        post = self.get_object()
        # Don't allow access if post is deleted
        if post.deleted and not (request.user.is_authenticated and request.user.is_superuser):
            return HttpResponse("Not Found", status=404)
        
        # Only allow if post is PUBLIC/PUBLIC_UNLISTED, user is the author, or user is following the author (for Friends Only)
        if post.visibility == "FRIENDS" and request.user != post.author:
            is_friend = (
                Follow.objects.filter(follower=request.user, following=post.author).exists() and Follow.objects.filter(follower=post.author, following=request.user).exists()
            )
            if not is_friend:
                return HttpResponse("Forbidden", status=403)

        # PUBLIC_UNLISTED: if a logged-in non-follower opened the detail page,
        # mark session so they "have the link".
        if (
            post.visibility == "PUBLIC_UNLISTED" and
            request.user.is_authenticated and
            request.user != post.author
        ):
            is_follower = Follow.objects.filter(follower=request.user, following=post.author).exists()
            if not is_follower:
                request.session[f"unlisted_access_{post.id}"] = True

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = context['object']
        if post.contentType == 'text/markdown':
            # Convert markdown content to HTML
            context['content_html'] = markdown.markdown(post.content)
        else:
            if getattr(post, "contentType", "text/plain") == "text/markdown":
                context['content_html'] = markdown.markdown(post.content or "")
            else:
                context['content_html'] = (post.content or "").replace('\n', '<br>')

        
        # Add image context if image exists
        context['has_image'] = bool(post.image)
        # User will not have option to copy link if post is friends-only
        context['VISIBILITY_FRIENDS'] = "FRIENDS"

        user = self.request.user
        author = post.author

        local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
        post_host = (post.author.host or "").rstrip("/")

        # If the post's author lives on a remote node, pull their comments into our DB
        if post_host and post_host != local_host:
            sync_remote_comments_for_post(post) 
            sync_remote_likes_for_post(post)
            sync_remote_comment_likes_for_post(post)
        # relationship checks
        is_follower = user.is_authenticated and Follow.objects.filter(
            follower=user, following=author
        ).exists()
        is_followed_back = user.is_authenticated and Follow.objects.filter(
            follower=author, following=user
        ).exists()
        is_friend = is_follower and is_followed_back  # mutual follow
        has_link = bool(self.request.session.get(f"unlisted_access_{post.id}", False))

        # who can like / interact (show buttons, form, etc)
        can_interact = False
        can_like = False
        can_like_comments = False

        if user.is_authenticated:
            if user == author or user.is_superuser:
                can_interact = True
                can_like = True
                can_like_comments = True
            elif post.visibility == 'PUBLIC':
                can_interact = True
                can_like = True
                can_like_comments = True
            elif post.visibility == 'PUBLIC_UNLISTED':
                # follower OR has the link
                if is_follower or has_link:
                    can_interact = True
                    can_like = True
                    can_like_comments = True
            elif post.visibility == 'FRIENDS':
                if is_friend:
                    can_interact = True
                    can_like = True
                    can_like_comments = True

        context['can_like'] = can_like
        context['can_like_comments'] = can_like_comments
        context['like_count'] = post.likes.count()
        context['liked_by_me'] = user.is_authenticated and post.likes.filter(author=user).exists()
        context['can_interact'] = can_interact


        # expose if admin is viewing a deleted post
        context["is_deleted_and_admin_viewing"] = (
            post.deleted and user.is_authenticated and user.is_superuser
        )

  
        if can_interact:
            comments_qs = post.comments.all()
        else:
            if user.is_authenticated:
                comments_qs = post.comments.filter(author=user)
            else:
                comments_qs = post.comments.none()


        comments = (
            post.comments
                .select_related("author")
                .prefetch_related("likes")
                .all()
        )

        if user.is_authenticated:
            liked_comment_ids = set(
                CommentLike.objects
                .filter(author=user, comment__in=comments)
                .values_list("comment_id", flat=True)
            )
        else:
            liked_comment_ids = set()

        def compute_username_display(author):
            # Try the Django username first
            uname = (getattr(author, "username", "") or "").strip()
            if uname:
                return uname
            # Try to derive from GitHub URL if present
            gh = (getattr(author, "github", "") or "").strip()
            if gh:
                try:
                    last = gh.rstrip("/").split("/")[-1]
                    if last:
                        return last
                except Exception:
                    pass
            # Derive from displayName
            dn = (getattr(author, "displayName", "") or "").strip()
            if dn:
                return "".join(ch for ch in dn.lower() if ch.isalnum())  # simple slug
            return ""

        # Annotate each comment with liked_by_me + username_display
        for c in comments:
            c.liked_by_me = c.id in liked_comment_ids
            c.username_display = compute_username_display(c.author)

        context["comments"] = comments

        # Which comments did I like?
        if user.is_authenticated:
            liked_comment_ids = set(
                CommentLike.objects
                .filter(author=user, comment__in=comments)
                .values_list("comment_id", flat=True)
            )
        else:
            liked_comment_ids = set()

        for c in comments:
            c.liked_by_me = c.id in liked_comment_ids
            c.username_display = compute_username_display(c.author)

        context["comments"] = comments

        context["absolute_url"] = self.request.build_absolute_uri(
            reverse("authors:post_detail", kwargs={"post_id": post.id})
        )
        return context


class AuthorPostsView(ListView):
    model = Post
    template_name = "authors/author_posts.html"
    context_object_name = "posts"
    paginate_by = 10  # optional, consistent with stream

    def get_queryset(self):
        author_id = self.kwargs["author_id"]
        current_user = self.request.user
        author = get_object_or_404(Author, id=author_id)

        # Viewing own posts → show all (not deleted)
        if current_user.is_authenticated and current_user == author:
            queryset = Post.objects.filter(author=author, deleted=False)
        # Viewing someone you follow → show PUBLIC + PUBLIC_UNLISTED + FRIENDS
        elif current_user.is_authenticated and Follow.objects.filter(follower=current_user, following=author).exists():
            queryset = Post.objects.filter(
                author=author,
                visibility__in=["PUBLIC", "PUBLIC_UNLISTED", "FRIENDS"],
                deleted=False
            )
        # Otherwise → only PUBLIC
        else:
            queryset = Post.objects.filter(author=author, visibility="PUBLIC", deleted=False)

        queryset = queryset.order_by("-updated")

        # Preprocess rendered content for display (like in stream)
        for post in queryset:
            post.rendered_content = render_post_content(post)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        author = get_object_or_404(Author, id=self.kwargs["author_id"])
        context["author"] = author
        return context


class AuthorDeletedPostsAdminView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Post
    template_name = "authors/author_deleted_posts_admin.html"
    context_object_name = "posts"

    def test_func(self):
        # Only superusers (node admins) can access this page
        return self.request.user.is_superuser

    def get_queryset(self):
        author_id = self.kwargs['author_id']
        author = get_object_or_404(Author, id=author_id)
        # show *only* deleted posts from that author
        return Post.objects.filter(author=author, deleted=True).order_by('-updated')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # include which author we're inspecting
        ctx["target_author"] = get_object_or_404(Author, id=self.kwargs['author_id'])
        return ctx

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['author'] = get_object_or_404(Author, id=self.kwargs['author_id'])
        return context


class PostAPIView(View):
    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        
        # Don't return deleted posts
        if post.deleted and not (request.user.is_authenticated and request.user.is_superuser):
            return HttpResponse("Not Found", status=404)
        
        # Check visibility permissions before returning the post
        # Only allow if post is PUBLIC/PUBLIC_UNLISTED, user is the author, or user is following the author (for Friends Only)
        if post.visibility == "FRIENDS" and request.user != post.author:
            # Check if user is authenticated first
            if not request.user.is_authenticated:
                return HttpResponse("Forbidden", status=403)
            
            is_friend = (
                Follow.objects.filter(follower=request.user, following=post.author).exists() and
                Follow.objects.filter(follower=post.author, following=request.user).exists()
            )
            if not is_friend:
                return HttpResponse("Forbidden", status=403)

        # --- profile image handling ---
        profile_image_url = None
        profile_image = getattr(post.author, "profileImage", None)
        if profile_image:
            # If it's your custom Image model, use serve_image
            try:
                profile_image_url = request.build_absolute_uri(
                    reverse('authors:serve_image', args=[profile_image.id])
                )
            except AttributeError:
                # Fallback in case profileImage is some other type (e.g. a bare URL string)
                profile_image_url = profile_image

        data = {
            "type": "post",
            "id": request.build_absolute_uri(
                reverse('authors:post_detail', kwargs={'post_id': post.id})
            ),
            "author": {
                "type": "author",
                "id": post.author.url,
                "host": post.author.host,
                "displayName": post.author.displayName,
                "url": post.author.url,
                "github": post.author.github,
                "profileImage": profile_image_url,
            },
            "title": post.title,
            "contentType": post.contentType,
            "content": post.content,
            "visibility": post.visibility,
            "published": post.published.isoformat(),
            "updated": post.updated.isoformat(),
        }

        # --- post image handling ---
        image_url = None
        if getattr(post, "image", None):
            try:
                image_url = request.build_absolute_uri(
                    reverse('authors:serve_image', args=[post.image.id])
                )
            except AttributeError:
                # If for some reason image is stored differently, fail soft
                image_url = None

        data["image"] = image_url
        
        return JsonResponse(data)
    

class AuthorStreamView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "authors/author_stream.html"
    context_object_name = "posts"
    paginate_by = 20
    login_url = '/accounts/login/'   # Redirect unauthenticated users to login
    redirect_field_name = 'next'  # Standard Django behavior

    def get_queryset(self):
        '''
        Returns posts for the author's stream:
        - Public posts from all authors (anyone can see in stream)
        - Friends-only posts from mutual friends (with inbox receipt tracking for remote posts)
        - Unlisted posts from followed authors (with inbox receipt tracking for remote posts)
        - All posts from the author themselves

        Inbox receipt logic:
        - For LOCAL posts (friends-only & unlisted): Use Follow relationships (always current)
        - For REMOTE posts (friends-only & unlisted): Only show if received in user's inbox
          (solves the stale Follow relationship problem in distributed systems)

        This prevents scenarios where:
        - Remote author unfollows a local author but our node doesn't know
        - Local author would still see unlisted/friends-only posts through stale Follow data
        '''
        user = self.request.user
        local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")

        # Get the visibility filter from the request
        visibility_filter = self.request.GET.get('filter', '').lower()

        # Get all mutual friends (both follow each other)
        followed_by_user = Follow.objects.filter(follower=user).values_list('following', flat=True)
        follows_user = Follow.objects.filter(following=user).values_list('follower', flat=True)
        mutual_friends = followed_by_user.intersection(follows_user)

        followed_authors = Follow.objects.filter(follower=user).values_list('following', flat=True)

        # All public posts should appear in everyone's stream
        public_posts = Post.objects.filter(visibility='PUBLIC', deleted=False)

        # Friends-only posts logic with inbox receipt tracking:
        # SPLIT INTO LOCAL and REMOTE queries

        # 1. Local friends-only posts from mutual friends (trust Follow relationships)
        local_mutual_friends = Author.objects.filter(
            id__in=mutual_friends,
            host=local_host
        ).values_list('id', flat=True)

        friends_posts_local = Post.objects.filter(
            visibility='FRIENDS',
            author__in=local_mutual_friends,
            deleted=False
        )

        # 2. Remote friends-only posts (only if received in inbox)
        # Get posts that were delivered to this user's inbox
        inbox_post_ids = InboxReceipt.objects.filter(
            recipient=user
        ).values_list('post_id', flat=True)

        friends_posts_remote = Post.objects.filter(
            id__in=inbox_post_ids,
            visibility='FRIENDS',
            deleted=False
        ).exclude(author__host=local_host)

        # User's own friends-only posts
        friends_posts_author = Post.objects.filter(
            visibility='FRIENDS',
            author=user,
            deleted=False
        )

        # Unlisted posts logic with inbox receipt tracking:
        # SPLIT INTO LOCAL and REMOTE queries

        # 1. Local unlisted posts from followed authors (trust Follow relationships)
        local_followed_authors = Author.objects.filter(
            id__in=followed_authors,
            host=local_host
        ).values_list('id', flat=True)

        unlisted_posts_local = Post.objects.filter(
            visibility='PUBLIC_UNLISTED',
            author__in=local_followed_authors,
            deleted=False
        ).exclude(author=user)

        # 2. Remote unlisted posts (only if received in inbox)
        # Since we now push PUBLIC_UNLISTED posts to remote followers' inboxes,
        # they should appear here if the user is a follower
        unlisted_posts_remote = Post.objects.filter(
            id__in=inbox_post_ids,
            visibility='PUBLIC_UNLISTED',
            deleted=False
        ).exclude(author__host=local_host).exclude(author=user)

        # All posts from the author themselves (they should see their own posts regardless of visibility)
        my_posts = Post.objects.filter(author=user, deleted=False)

        # Combine all posts
        queryset = (
            public_posts |
            friends_posts_local |
            friends_posts_remote |
            friends_posts_author |
            unlisted_posts_local |
            unlisted_posts_remote |
            my_posts
        ).distinct().order_by('-updated')

        # Apply visibility filter if specified
        if visibility_filter == 'public':
            queryset = queryset.filter(visibility='PUBLIC')
        elif visibility_filter == 'friends':
            queryset = queryset.filter(visibility='FRIENDS')
        elif visibility_filter == 'unlisted':
            queryset = queryset.filter(visibility='PUBLIC_UNLISTED')
        elif visibility_filter == 'remote':
            # Filter for posts from remote authors
            local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
            queryset = queryset.exclude(author__host=local_host)

        return queryset

    def get_context_data(self, **kwargs):
        # Get the existing context
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get the visibility filter from the request
        visibility_filter = self.request.GET.get('filter', '').lower()
        context["current_filter"] = visibility_filter

        # No longer organizing into separate sections - all posts in main stream
        for p in context["posts"]:
            p.rendered_content = render_post_content(p)

        # Pass the authenticated user's ID, not from URL kwargs
        context["author_id"] = user.id
        return context


class ExploreView(ListView):
    model = Post
    template_name = "authors/explore.html"
    context_object_name = "posts"
    paginate_by = 15

    def get_queryset(self):
        """Fetch remote posts and return only remote public, non-deleted posts."""
        fetch_and_sync_remote_posts()

        # Get the current node's base URL
        from django.conf import settings
        current_host = getattr(settings, 'BASE_URL', '').rstrip('/')

        # Filter for posts where the author's host is different from the current node's host
        # This ensures we only show remote posts
        queryset = Post.objects.filter(
            visibility='PUBLIC',
            deleted=False,
            # Include only posts from authors whose host is different from the current node
            # and not null (i.e., remote posts)
            author__host__isnull=False
        ).exclude(
            # Exclude posts where the author's host matches the current node's host
            # (i.e., exclude local posts)
            author__host=current_host
        ).order_by('-published')

        for post in queryset:
            post.rendered_content = render_post_content(post)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Explore Remote Posts"
        context["subtitle"] = "Discover content from other nodes"

        # Include current author's id for the follow-remote form
        if self.request.user.is_authenticated:
            context["current_author_id"] = self.request.user.id

        return context


class StreamRedirectView(TemplateView):
    """Redirect view to send user to their personalized stream"""
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('authors:author_stream', author_id=request.user.id)
        else:
            # If not authenticated, redirect to login
            return redirect('login')

'''
View to list incoming follow requests for the logged-in user.
'''
class FollowRequestsView(LoginRequiredMixin, ListView):
    model = FollowRequest
    template_name = "authors/follow_requests.html"
    context_object_name = "requests"

    def get_queryset(self):  # filter requests for the logged-in user
        return FollowRequest.objects.filter(receiver=self.request.user, status='PENDING').select_related('sender')

'''
View to list followers of a given author.
'''
class FollowersListView(LoginRequiredMixin, ListView):
    model = Follow
    template_name = "authors/followers_list.html"
    context_object_name = "followers"

    def get_queryset(self):
        """Get all followers of the given author."""
        author = get_object_or_404(Author, id=self.kwargs["author_id"])
        return Follow.objects.filter(following=author).select_related("follower")

    def get_context_data(self, **kwargs):
        """Add author info and follower count."""
        context = super().get_context_data(**kwargs)
        author = get_object_or_404(Author, id=self.kwargs["author_id"])
        context["author"] = author
        context["follower_count"] = Follow.objects.filter(following=author).count()
        return context

'''
List view to show users that I'm following.
'''
class FollowingListView(LoginRequiredMixin, ListView):
    model = Follow
    template_name = "authors/following_list.html"
    context_object_name = "following"

    def get_queryset(self):
        """Get all authors this user is following."""
        author = get_object_or_404(Author, id=self.kwargs["author_id"])
        return Follow.objects.filter(follower=author).select_related("following")

    def get_context_data(self, **kwargs):
        """Add author info and following count."""
        context = super().get_context_data(**kwargs)
        author = get_object_or_404(Author, id=self.kwargs["author_id"])
        context["author"] = author
        context["following_count"] = Follow.objects.filter(follower=author).count()
        return context


@login_required
@require_POST
def follow_author(request, author_id):
    """
    Send a follow request to another author.

    - If the target is LOCAL → create/refresh a FollowRequest (current behaviour).
    - If the target is REMOTE → use SingleFollowingAPIView.put to send a federated
      Follow to their inbox (same logic as the "enter remote URL" flow).
    """
    author_to_follow = get_object_or_404(Author, id=author_id)

    if author_to_follow == request.user:  # Prevent following oneself
        messages.error(request, "You cannot follow yourself.")
        return redirect("authors:author_profile", author_id=author_id)

    # Already following?
    if Follow.objects.filter(follower=request.user, following=author_to_follow).exists():
        messages.info(request, f"You are already following {author_to_follow.displayName}.")
        return redirect("authors:author_profile", author_id=author_id)

    # 🔹 Case 1: remote author → use the same federation path as FollowRemoteAuthorView
    if hasattr(author_to_follow, "is_remote") and author_to_follow.is_remote():
        remote_author_url = author_to_follow.url
        if not remote_author_url:
            messages.error(
                request,
                "This remote author does not have a URL configured, so a follow cannot be sent.",
            )
            return redirect("authors:author_profile", author_id=author_id)

        # Reuse SingleFollowingAPIView.put just like FollowRemoteAuthorView
        api_view = SingleFollowingAPIView()
        api_response = api_view.put(
            request,
            author_id=str(request.user.id),
            following_fqid=remote_author_url,
        )

        if 200 <= api_response.status_code < 300:
            # SingleFollowingAPIView already creates the Follow row on success
            messages.success(
                request,
                f"Follow request sent to remote author {author_to_follow.displayName}.",
            )
        else:
            error_msg = getattr(api_response, "content", b"").decode(errors="ignore")
            messages.error(
                request,
                f"Failed to follow remote author (status {api_response.status_code}). {error_msg}",
            )

        return redirect("authors:author_profile", author_id=author_id)

    # 🔹 Case 2: local author → keep existing FollowRequest behaviour
    follow_request, created = FollowRequest.objects.get_or_create(
        sender=request.user,
        receiver=author_to_follow,
        defaults={"status": "PENDING"},
    )

    if not created:
        # If it exists and was denied or approved before, reset to pending
        if reopen_follow_request(follow_request):
            messages.info(
                request,
                f"Follow request re-sent to {author_to_follow.displayName}.",
            )
        else:
            messages.info(
                request,
                f"Follow request to {author_to_follow.displayName} is already pending.",
            )
    else:
        messages.success(
            request,
            f"Follow request sent to {author_to_follow.displayName}!",
        )

    return redirect("authors:author_profile", author_id=author_id)


@login_required
def cancel_follow_request(request, author_id):
    """
    Cancel a pending follow request sent by the logged-in user.
    """
    author_to_cancel = get_object_or_404(Author, id=author_id)
    follow_request = FollowRequest.objects.filter(
        sender=request.user,
        receiver=author_to_cancel,
        status='PENDING'
    ).first()

    if follow_request:
        follow_request.delete()
        messages.info(request, f"Follow request to {author_to_cancel.displayName} has been cancelled.")
    else:
        messages.warning(request, "No pending follow request to cancel.")

    return redirect('authors:author_profile', author_id=author_id)

@login_required
@require_POST
def unfollow_author(request, author_id):
    '''
    Unfollow an author.
    '''
    author_to_unfollow = get_object_or_404(Author, id=author_id)

    # Remove local follow relationship
    Follow.objects.filter(follower=request.user, following=author_to_unfollow).delete()

    # If this is a remote author, notify their node so they stop
    # treating us as a follower / friend.
    try:
        if author_to_unfollow.is_remote():
            send_unfollow_to_remote_author(request.user, author_to_unfollow)
    except Exception:
        pass

    messages.success(request, f"You have unfollowed {author_to_unfollow.displayName}.")
    return redirect('authors:author_profile', author_id=author_id)

@login_required
def approve_follow_request(request, request_id):
    '''
    Approve a follow request.
    '''
    follow_request = get_object_or_404(FollowRequest, id=request_id, receiver=request.user)  # Ensure the request is for the logged-in user
    Follow.objects.get_or_create(follower=follow_request.sender, following=request.user)  # Create follow relationship
    follow_request.status = 'APPROVED'
    follow_request.save()
    messages.success(request, f"You approved {follow_request.sender.displayName}'s follow request.")
    return redirect('authors:follow_requests')


@login_required
def deny_follow_request(request, request_id):
    '''
    Deny a follow request.
    '''
    follow_request = get_object_or_404(FollowRequest, id=request_id, receiver=request.user)
    follow_request.status = 'DENIED'
    follow_request.save()
    messages.warning(request, f"You denied {follow_request.sender.displayName}'s follow request.")
    return redirect('authors:follow_requests')
    

class FollowRemoteAuthorView(LoginRequiredMixin, View):
    """
    Let a local author follow a remote author by pasting the remote author's FQID/URL.
    Uses the same logic as SingleFollowingAPIView.put to send a Follow to the remote inbox.
    """
    template_name = "authors/follow_remote_author.html"

    def get(self, request, author_id):
        # Only allow a user to open this page for themselves
        if str(request.user.id) != str(author_id):
            return HttpResponse("Forbidden", status=403)
        return render(request, self.template_name, {})

    def post(self, request, author_id):
        # Only allow a user to submit for themselves
        if str(request.user.id) != str(author_id):
            return HttpResponse("Forbidden", status=403)

        remote_author_url = (request.POST.get("remote_author_url") or "").strip()
        if not remote_author_url:
            messages.error(request, "Please enter a remote author URL.")
            return redirect("authors:follow_remote_author", author_id=author_id)

        # Very basic URL sanity check
        try:
            parsed = urllib.parse.urlparse(remote_author_url)
        except Exception:
            parsed = None

        if not parsed or not parsed.scheme or not parsed.netloc:
            messages.error(request, "That doesn't look like a valid URL.")
            return redirect("authors:follow_remote_author", author_id=author_id)

        '''
        # If this URL already matches a local Author, just reuse it,
        # otherwise create a stub remote Author.
        author_defaults = {
            "username": f"remote_{uuid.uuid4().hex[:8]}",
            "displayName": remote_author_url,  # you can customize later
            "host": f"{parsed.scheme}://{parsed.netloc}",
        }

        # Use shared normalization + deduping logic
        author_data = {"id": remote_author_url}
        remote_author = get_or_create_author(author_data)

        if remote_author.id == request.user.id:
            messages.error(request, "You cannot follow yourself.")
            return redirect("authors:follow_remote_author", author_id=author_id)
        '''

        # Reuse the existing API logic to send the Follow request to the remote inbox.
        # This runs SingleFollowingAPIView.put with the current request object.
        api_view = SingleFollowingAPIView()
        api_response = api_view.put(
            request,
            author_id=str(author_id),
            following_fqid=remote_author_url,
        )

        if 200 <= api_response.status_code < 300:
            # Your SingleFollowingAPIView returns 200 or 201 on success
            messages.success(request, "Follow request sent to remote author.")
        else:
            # Try to extract error message if JSON, otherwise generic
            error_msg = getattr(api_response, "content", b"").decode(errors="ignore")
            messages.error(
                request,
                f"Failed to follow remote author (status {api_response.status_code}). {error_msg}",
            )

        # Redirect back to their stream or following list
        return redirect("authors:author_stream", author_id=author_id)


class FederationGuideView(LoginRequiredMixin, View):
    """
    A guide page that explains how to connect with other nodes
    """
    template_name = "authors/federation_guide.html"

    def get(self, request):
        context = {
            'current_user': request.user,
            'remote_nodes': RemoteNode.objects.all(),
            'base_url': getattr(settings, 'BASE_URL', request.build_absolute_uri('/').rstrip('/')),
        }
        return render(request, self.template_name, context)



@login_required
def redirect_to_profile(request):
    return redirect('authors:author_profile', author_id=request.user.id)

@login_required
@require_POST
def toggle_like(request, post_id):
    # Get the post by ID, or show 404 if not found
    post = get_object_or_404(Post, id=post_id)
    # If parent post is deleted, treat this as gone.
    if getattr(post, "deleted", False):
        return HttpResponse("Not Found", status=404)
    
    viewer = request.user
    author = post.author

    if not (post.content or "").strip():
        return HttpResponse("Forbidden", status=403)

    # Check if viewer follows the post author
    is_follower = Follow.objects.filter(follower=viewer, following=author).exists()
    # Check if post author follows viewer back (mutual)
    is_followed_back = Follow.objects.filter(follower=author, following=viewer).exists()
    # Check if both users follow each other mutual follow means friends
    is_friend = is_follower and is_followed_back
    # Check if viewer has the unlisted link access
    has_link = bool(request.session.get(f"unlisted_access_{post.id}", False))

    can_like = False
    if viewer == author or viewer.is_superuser:
        can_like = True # Owner or admin can always like
    elif post.visibility == 'PUBLIC':
        can_like = True # Anyone logged in can like
    elif post.visibility == 'PUBLIC_UNLISTED':
        can_like = is_follower or has_link # Follower or has link only
    elif post.visibility == 'FRIENDS':
        can_like = is_friend # Only mutual friends can like

    # If not allowed --> return 403 Forbidden
    if not can_like:
        return HttpResponse("Forbidden", status=403)

    like, created = Like.objects.get_or_create(author=request.user, post=post)
    if not created:
        # User already liked -> unlike
        like.delete()
        liked = False
        messages.info(request, "Unliked.")
    else:
        # New like
        liked = True
        messages.success(request, "Liked!")

        # if this is a remote post, send the like to that node
        local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
        post_host = (post.author.host or "").rstrip("/")

        if post_host and post_host != local_host:
            send_like_to_post_owner(like)
            
    if request.headers.get('HX-Request') or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'count': post.likes.count()})
    return redirect('authors:post_detail', post_id=post.id)

class PostLikesView(LoginRequiredMixin, TemplateView):
    """
    Simple HTML page showing like count and times.
    """
    template_name = "authors/post_likes.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post = get_object_or_404(Post, id=self.kwargs["post_id"])
        # Deleted post → show an error in context (tests expect 200 + error)
        if getattr(post, "deleted", False):
            ctx["error"] = "This post no longer exists."
            return ctx

        user = self.request.user
        is_owner = user == post.author
        is_follower = Follow.objects.filter(follower=user, following=post.author).exists()
        is_followed_back = Follow.objects.filter(follower=post.author, following=user).exists()
        is_friend = is_follower and is_followed_back
        has_link = bool(self.request.session.get(f"unlisted_access_{post.id}", False))

        # FRIENDS: only owner or mutual friends can view likes
        if post.visibility == 'FRIENDS' and not (is_owner or is_friend):
            ctx["error"] = "You don't have permission to view likes for this post."
            return ctx

        # UNLISTED: owner or follower or has_link (session)
        if post.visibility == 'PUBLIC_UNLISTED' and not (is_owner or is_follower or has_link):
            ctx["error"] = "You don't have permission to view likes for this post."
            return ctx

        likes = post.likes.select_related("author").order_by("-created_at")
        # Compute display username for each liker
        def compute_username_display(author):
            uname = (getattr(author, "username", "") or "").strip()
            if uname:
                return uname
            gh = (getattr(author, "github", "") or "").strip()
            if gh:
                try:
                    last = gh.rstrip("/").split("/")[-1]
                    if last:
                        return last
                except Exception:
                    pass
            dn = (getattr(author, "displayName", "") or "").strip()
            if dn:
                return "".join(ch for ch in dn.lower() if ch.isalnum())
            return ""

        for like in likes:
            like.username_display = compute_username_display(like.author)

        ctx["post"] = post
        ctx["likes"] = likes
        ctx["like_count"] = likes.count()
        return ctx
    
@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    # If the post is marked deleted, treat it as gone
    if getattr(post, "deleted", False):
        return HttpResponse("Not Found", status=404)

    viewer = request.user
    author = post.author

    # relationship checks
    is_follower = Follow.objects.filter(follower=viewer, following=author).exists()
    is_followed_back = Follow.objects.filter(follower=author, following=viewer).exists()
    is_friend = is_follower and is_followed_back  # mutual follow
    has_link = bool(request.session.get(f"unlisted_access_{post.id}", False))

    # decide if viewer is allowed to comment on this post
    can_comment = False

    if viewer == author:
        # post owner can always comment
        can_comment = True

    elif post.visibility == 'PUBLIC':
        # any logged-in user
        can_comment = True

    elif post.visibility == 'PUBLIC_UNLISTED':
        # following the person or has link
        can_comment = is_follower or has_link

    elif post.visibility == 'FRIENDS':
        # mutual follow only
        if is_friend:
            can_comment = True

    if not can_comment:
        return HttpResponse("Forbidden", status=403)

    # grab content directly from POST (not relying on form.is_valid())
    content_text = request.POST.get("content", "").strip()
    if not content_text:
        messages.error(request, "Comment cannot be empty.")
        return redirect('authors:post_detail', post_id=post.id)

    comment = Comment.objects.create(
        post=post,
        author=viewer,
        content=content_text,
    )
    # Figure out hosts
    local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    post_host = (post.author.host or "").rstrip("/")
    viewer_host = (getattr(getattr(viewer, "author", None), "host", "") or "").rstrip("/")
    # if your request.user *is* Author, then:
    if not viewer_host and hasattr(viewer, "host"):
        viewer_host = (viewer.host or "").rstrip("/")

    # 1) If this is a REMOTE post, send the comment TO THE POST OWNER'S NODE
    if post_host and post_host != local_host:
        # e.g. you comment on a Team-Green post -> send to Team-Green inbox
        send_comment_to_post_owner(comment)

    # 2) If THIS commenter is LOCAL, fan out to THEIR remote followers
    #    (so when YOU comment on YOUR local post, your remote followers see it)
    if (not viewer_host) or (viewer_host == local_host):
        notify_remote_comment(comment)

    return redirect('authors:post_detail', post_id=post.id)


@login_required
@require_POST
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    post = comment.post
    # If parent post is deleted, treat this as gone.
    if getattr(post, "deleted", False):
        return HttpResponse("Not Found", status=404)
    
    viewer = request.user
    author = post.author

    # Do not allow likes on empty comments
    if not (comment.content or "").strip():
        return HttpResponse("Forbidden", status=403)

    # Check if viewer follows the post author
    is_follower = Follow.objects.filter(follower=viewer, following=author).exists()
    # Check if post author follows viewer back (mutual)
    is_followed_back = Follow.objects.filter(follower=author, following=viewer).exists()
    # Check if both users follow each other mutual follow means friends
    is_friend = is_follower and is_followed_back
    # Check if viewer has the unlisted link access
    has_link = bool(request.session.get(f"unlisted_access_{post.id}", False))

    can_like = False
    if viewer == author or viewer.is_superuser:
        can_like = True # Owner or admin can always like
    elif post.visibility == 'PUBLIC':
        can_like = True # Anyone logged in can like
    elif post.visibility == 'PUBLIC_UNLISTED':
        can_like = is_follower or has_link # Follower or has link only
    elif post.visibility == 'FRIENDS':
        can_like = is_friend # Only mutual friends can like

    # If not allowed --> return 403 Forbidden
    if not can_like:
        return HttpResponse("Forbidden", status=403)

    comment_like, created = CommentLike.objects.get_or_create(author=viewer, comment=comment)
    if not created:
        # If already liked → remove like
        comment_like.delete()
        messages.info(request, "Unliked comment.")
    else:
        # If new like --> add it
        messages.success(request, "Liked comment.")

    # If this post belongs to a REMOTE node, notify that node
    local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    comment_host = (comment.author.host or "").rstrip("/")

    if comment_host and comment_host != local_host:
        send_comment_like_to_post_owner(comment_like)
        

    return redirect('authors:post_detail', post_id=post.id)

def push_image_to_remote_nodes(image_obj):
    REMOTE_NODES = getattr(settings, "REMOTE_NODES", [])

    for node in REMOTE_NODES:
        try:
            url = f"{node['host'].rstrip('/')}/api/images/"
            headers = {
                "Content-Type": image_obj.content_type,
                "Authorization": f"Basic {node['auth']}",
            }

            resp = requests.post(url, headers=headers, data=image_obj.data)

            if resp.status_code in (200, 201):
                print(f"✅ Sent image to {node['host']}")
            else:
                print(f"⚠️ Failed to send image to {node['host']} ({resp.status_code})")

        except Exception as e:
            print(f"❌ Error sending to {node['host']}: {e}")



def upload_image(request):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            img_file = request.FILES["image"]

            image = Image.objects.create(
                file_name=img_file.name,
                content_type=img_file.content_type,
                data=img_file.read(),
            )

            if request.user.is_authenticated:
                request.user.profileImage = image
                request.user.save(update_fields=["profileImage"])
                try:
                    notify_remote_author_update(request.user)
                except Exception as e:
                    print("Failed to notify remote on profile image change:", e)

            # Go back where the user came from
            if next_url:
                return redirect(next_url)

            # fallback: go to edit profile
            return redirect("authors:edit_profile", request.user.id)

    else:
        form = ImageUploadForm()

    return render(request, "authors/upload_image.html", {
        "form": form,
        "next": next_url,
    })


def serve_image(request, image_id):
    try:
        img = Image.objects.get(pk=image_id)
    except Image.DoesNotExist:
        raise Http404("Image not found")

    return HttpResponse(
        img.data,
        content_type=img.content_type
    )

@csrf_exempt
def receive_image_api(request):
    """
    Receives an image pushed from a remote node.
    """
    if request.method != "POST":
        return HttpResponse("Method Not Allowed", status=405)

    # --- Authenticate remote node ---
    if "HTTP_AUTHORIZATION" not in request.META:
        return HttpResponse("Unauthorized", status=401)

    auth_header = request.META["HTTP_AUTHORIZATION"].replace("Basic ", "")
    import base64
    username, password = base64.b64decode(auth_header).decode().split(":", 1)
    user = authenticate(username=username, password=password)
    if not user:
        return HttpResponse("Unauthorized", status=401)

    # --- Save the image ---
    content_type = request.headers.get("Content-Type", "application/octet-stream")
    file_name = request.headers.get("X-Filename", f"remote_{uuid.uuid4().hex[:8]}.bin")
    data = request.body

    image = Image.objects.create(
        file_name=file_name,
        content_type=content_type,
        data=data
    )
    print(f"✅ Received remote image {image.id} from {username}")
    return JsonResponse({"status": "ok", "image_id": image.id}, status=201)


class NodeManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Landing page for all node-related admin actions.
    Accessible only to superusers (node admins).
    """
    template_name = "authors/node_management.html"

    def test_func(self):
        return self.request.user.is_superuser
    

class NodeConfigurationView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "authors/node_configuration.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request):
        initial_data = {}
        # Prefer settings.BASE_URL if present
        if hasattr(settings, "BASE_URL"):
            initial_data["base_url"] = getattr(settings, "BASE_URL")

        form = NodeConfigurationForm(initial=initial_data)

        context = {
            "form": form,
            "current_config": {
                "base_url": getattr(settings, "BASE_URL", ""),
                "service_username": request.user.username if hasattr(request, "user") else "",
                "remote_nodes": RemoteNode.objects.all(),
            },
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = NodeConfigurationForm(request.POST)

        if form.is_valid():
            base_url = form.cleaned_data["base_url"].rstrip("/")
            service_username = form.cleaned_data["service_username"]
            service_password = form.cleaned_data["service_password"]

            # 1) Create or update the service user
            service_user, created = Author.objects.get_or_create(
                username=service_username,
                defaults={
                    "displayName": f"Node Service User ({service_username})",
                    "is_active": True,
                    "is_staff": True,      # often useful for service accounts
                },
            )
            # Update password & display name every time in case they changed
            service_user.set_password(service_password)
            service_user.displayName = f"Node Service User ({service_username})"
            service_user.host = base_url
            service_user.url = f"{base_url}/api/authors/{service_user.id}/"
            service_user.save(update_fields=["password", "displayName", "host", "url"])

            # 2) Update the current admin user's host/url to match this node
            current_user = request.user
            current_user.host = base_url
            current_user.url = f"{base_url}/api/authors/{current_user.id}/"
            current_user.save(update_fields=["host", "url"])

            # 3) Normalize any local authors that still point at localhost
            from django.db.models import Q

            Author.objects.filter(
                Q(host__isnull=True)
                | Q(host__exact="")
                | Q(host__icontains="localhost")
            ).update(host=base_url)

            # For authors that have the correct host but missing url, fill it in
            for author in Author.objects.filter(host=base_url, url__isnull=True):
                author.url = f"{base_url}/api/authors/{author.id}/"
                author.save(update_fields=["url"])

                try:
                    notify_remote_author_update(author)
                except Exception as e:
                    print("Failed to notify remote on profile edit:", e)

            # Re-authenticate current user to keep them logged in
            from django.contrib.auth import login
            login(request, current_user)

            messages.success(
                request,
                f"Node configuration updated. "
                f"Service user '{service_username}' is ready for federation."
            )
            return redirect("authors:node_config")

        else:
            messages.error(request, "Please correct the errors below.")

        context = {
            "form": form,
            "current_config": {
                "base_url": getattr(settings, "BASE_URL", ""),
                "service_username": request.user.username if hasattr(request, "user") else "",
                "remote_nodes": RemoteNode.objects.all(),
            },
        }
        return render(request, self.template_name, context)


class ConfigureRemoteNodeView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    A view to help users add remote nodes through the UI
    """
    template_name = "authors/configure_remote_node.html"

    def test_func(self):
        # Only allow superusers (node admins) to access this view
        return self.request.user.is_superuser

    def get(self, request):
        form = RemoteNodeForm()
        context = {
            'form': form,
            'remote_nodes': RemoteNode.objects.all()
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = RemoteNodeForm(request.POST)

        if form.is_valid():
            remote_node = form.save()
            messages.success(request, f"Remote node '{remote_node.name}' added successfully!")
            return redirect('authors:configure_remote_node')
        else:
            messages.error(request, "Please correct the errors below.")

        context = {
            'form': form,
            'remote_nodes': RemoteNode.objects.all()
        }
        return render(request, self.template_name, context)


# Views for Node Admin Management of Remote Nodes
class RemoteNodeListView(LoginRequiredMixin, ListView):
    """
    List all configured remote nodes
    Only accessible to superusers (node admins)
    """
    model = RemoteNode
    template_name = "authors/remote_nodes_list.html"
    context_object_name = "remote_nodes"

    def dispatch(self, request, *args, **kwargs):
        # Only allow superusers (node admins) to access this view
        if not request.user.is_superuser:
            return redirect('authors:author_profile', author_id=request.user.id)
        return super().dispatch(request, *args, **kwargs)


class AddRemoteNodeView(LoginRequiredMixin, CreateView):
    """
    Add a new remote node to connect with
    Only accessible to superusers (node admins)
    """
    model = RemoteNode
    form_class = RemoteNodeForm
    template_name = "authors/add_remote_node.html"
    success_url = reverse_lazy('authors:remote_nodes_list')

    def dispatch(self, request, *args, **kwargs):
        # Only allow superusers (node admins) to access this view
        if not request.user.is_superuser:
            return redirect('authors:author_profile', author_id=request.user.id)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Successfully added remote node: {form.instance.name}")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Error adding remote node. Please check the form data.")
        return super().form_invalid(form)


class EditRemoteNodeView(LoginRequiredMixin, UpdateView):
    """
    Edit an existing remote node configuration
    Only accessible to superusers (node admins)
    """
    model = RemoteNode
    form_class = RemoteNodeForm
    template_name = "authors/edit_remote_node.html"
    success_url = reverse_lazy('authors:remote_nodes_list')
    pk_url_kwarg = "node_id"


    def dispatch(self, request, *args, **kwargs):
        # Only allow superusers (node admins) to access this view
        if not request.user.is_superuser:
            return redirect('authors:author_profile', author_id=request.user.id)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Successfully updated remote node: {form.instance.name}")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Error updating remote node. Please check the form data.")
        return super().form_invalid(form)


class DeleteRemoteNodeView(LoginRequiredMixin, View):
    """
    Delete a remote node connection
    Only accessible to superusers (node admins)
    """
    def dispatch(self, request, *args, **kwargs):
        # Only allow superusers (node admins) to access this view
        if not request.user.is_superuser:
            return redirect('authors:author_profile', author_id=request.user.id)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, node_id):
        try:
            # Use integer ID (node_id from URL)
            node = RemoteNode.objects.get(id=node_id)
            node_name = node.name
            node.delete()
            messages.success(request, f"Successfully removed remote node: {node_name}")
        except RemoteNode.DoesNotExist:
            messages.error(request, "Remote node not found.")

        return redirect('authors:remote_nodes_list')