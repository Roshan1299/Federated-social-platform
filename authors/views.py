import markdown
from django.forms import BaseModelForm
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DetailView, ListView, TemplateView
from django.views import View
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from .models import Author, Post, Follow, FollowRequest, Like, Comment, CommentLike
from .forms import CommentForm

from .forms import AuthorCreationForm, AuthorProfileForm, PostForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


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
                # Friends see both PUBLIC + FRIENDS (but NOT unlisted)
                visibilities = ["PUBLIC", "FRIENDS"]
            else:
                # One-way followers only see PUBLIC posts
                visibilities = ["PUBLIC"]

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

        success_url = reverse('authors:author_profile', kwargs={'author_id': user.id})
        return redirect(success_url)
    
class AuthorAPIView(View):
    def get(self, request, author_id):
        author = Author.objects.get(id=author_id)
        web_url = reverse('authors:author_profile', kwargs={'author_id': author.id})
        data = {
            "type": "author",
            "id": author.url, 
            "host": author.host,
            "displayName": author.displayName,
            "github": author.github,
            "profileImage": author.profileImage.name,
            "web": request.scheme + "://" + request.get_host() + web_url,
        }
        return JsonResponse(data)

'''
AuthorsListAPIView: returns a JSON list of all authors.
Same format as AuthorAPIView but for multiple authors.
GET requests only.
'''
class AuthorsListAPIView(View):
    def get(self, request):
        authors = Author.objects.all()
        authors_data = []
        for author in authors:
            web_url = reverse('authors:author_profile', kwargs={'author_id': author.id})
            authors_data.append({
                "type": "author",
                "id": author.url,
                "host": author.host,
                "displayName": author.displayName,
                "github": author.github,
                "profileImage": author.profileImage.name,
                "web": request.scheme + "://" + request.get_host() + web_url,
            })
        return JsonResponse(authors_data, safe=False, json_dumps_params={'indent': 2}) # by default jsonresponse only accepts a dictionary


class CreatePostView(CreateView):
    form_class = PostForm
    template_name = "authors/create_post.html"
    
    def form_valid(self, form):
        # Set the author to the current user
        form.instance.author = self.request.user
        return super().form_valid(form)
    
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

    def get_success_url(self):
        return reverse("authors:post_detail", kwargs={"post_id": self.object.id})


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
        if post.deleted:
            return HttpResponse("Not Found", status=404)
        
        # Only allow if post is PUBLIC/PUBLIC_UNLISTED, user is the author, or user is following the author (for Friends Only)
        if post.visibility == "FRIENDS" and request.user != post.author:
            is_friend = (
                Follow.objects.filter(follower=request.user, following=post.author).exists() and Follow.objects.filter(follower=post.author, following=request.user).exists()
            )
            if not is_friend:
                return HttpResponse("Forbidden", status=403)

        # PUBLIC_UNLISTED posts are always viewable by link

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
        context['has_image'] = post.image and post.image.url
        # User will not have option to copy link if post is friends-only
        context['VISIBILITY_FRIENDS'] = "FRIENDS"

        user = self.request.user
        context['like_count'] = post.likes.count()
        context['liked_by_me'] = user.is_authenticated and post.likes.filter(author=user).exists()
        context['can_like'] = user.is_authenticated and (
            post.visibility in ['PUBLIC', 'PUBLIC_UNLISTED'] or 
            (post.visibility == 'FRIENDS' and Follow.objects.filter(follower=user, following=post.author).exists()) or 
            user == post.author
        )

        user = self.request.user
        context['can_interact'] = user.is_authenticated and (
            post.visibility in ['PUBLIC', 'PUBLIC_UNLISTED'] or 
            (post.visibility == 'FRIENDS' and Follow.objects.filter(follower=user, following=post.author).exists()) or 
            user == post.author
        )

        context["comment_form"] = CommentForm()

        comments = (
            post.comments
                .select_related("author")
                .prefetch_related("likes")
                .all()
        )

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
            # As a last resort, show nothing (template will skip the @ block)
            return ""

        user = self.request.user

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
    
    def get_queryset(self):
        author_id = self.kwargs['author_id']
        current_user = self.request.user
        author = get_object_or_404(Author, id=author_id)
        
        # If user is viewing their own profile, show all posts that aren't deleted
        if current_user.is_authenticated and current_user == author:
            return Post.objects.filter(author_id=author_id, deleted=False).order_by('-published')

        # If viewing an author you follow, show public and friends-only posts (NOT unlisted)
        elif current_user.is_authenticated and Follow.objects.filter(follower=current_user, following=author).exists():
            return Post.objects.filter(
                author_id=author_id,
                visibility__in=["PUBLIC", "FRIENDS"],
                deleted=False
            ).order_by('-published')
        # Otherwise, show only public posts that aren't deleted
        else:
            return Post.objects.filter(author_id=author_id, visibility='PUBLIC', deleted=False).order_by('-published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['author'] = get_object_or_404(Author, id=self.kwargs['author_id'])
        return context


class PostAPIView(View):
    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        # Don't return deleted posts
        if post.deleted:
            return HttpResponse("Not Found", status=404)
        
        # Check visibility permissions before returning the post
        if post.visibility == "FRIENDS" and request.user != post.author and not Follow.objects.filter(follower=request.user, following=post.author).exists():
            return HttpResponse("Forbidden", status=403)
        
        data = {
            "type": "post",
            "id": request.build_absolute_uri(reverse('authors:post_detail', kwargs={'post_id': post.id})),
            "author": {
                "type": "author",
                "id": post.author.url,
                "host": post.author.host,
                "displayName": post.author.displayName,
                "url": post.author.url,
                "github": post.author.github,
                "profileImage": post.author.profileImage.name if post.author.profileImage else None,
            },
            "title": post.title,
            "description": post.description,
            "contentType": post.contentType,
            "content": post.content,
            "visibility": post.visibility,
            "published": post.published.isoformat(),
            "updated": post.updated.isoformat(),
        }
        
        # Include image URL if the post has an image
        if post.image:
            data["image"] = request.build_absolute_uri(post.image.url)
        
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
        - Public posts from all authors
        - Friends-only posts from mutual friends
        - All posts from the author themselves
        '''
        user = self.request.user

        # Get all mutual friends (both follow each other)
        mutual_friends = Follow.objects.filter(
            follower=user,
            following__in=Follow.objects.filter(follower__in=[user]).values_list('follower', flat=True)
        ).values_list('following', flat=True)

        public_posts = Post.objects.filter(visibility='PUBLIC', deleted=False)
        friends_posts = Post.objects.filter(
            visibility='FRIENDS',
            author__in=mutual_friends,
            deleted=False
        )
        my_posts = Post.objects.filter(author=user, deleted=False)

        queryset = (public_posts | friends_posts | my_posts).distinct().order_by('-updated')
        return queryset

    def get_context_data(self, **kwargs):
        # Get the existing context
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Fetch followed authors and their recent posts
        followed_authors = Follow.objects.filter(follower=user).select_related("following")
        followed_data = []
        for follow in followed_authors:
            author = follow.following
            is_friend = (
                Follow.objects.filter(follower=user, following=author).exists() and Follow.objects.filter(follower=author, following=user).exists()
            )
            visible_visibilities = ['PUBLIC']
            if is_friend:
                visible_visibilities.append('FRIENDS')

            posts = Post.objects.filter(
                author=author,
                visibility__in=visible_visibilities,
                deleted=False
            ).order_by('-updated')[:5]  # Get recent 5 posts

            for p in posts:
                p.rendered_content = render_post_content(p)
            if posts.exists():
                followed_data.append({
                    "author": author,
                    "posts": posts
                })
        context["followed_data"] = followed_data

        for p in context["posts"]:
            p.rendered_content = render_post_content(p)

        # Pass the authenticated user's ID, not from URL kwargs
        context["author_id"] = user.id
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


@login_required
@require_POST
def follow_author(request, author_id):
    '''
     Send a follow request to another author.
     '''
    author_to_follow = get_object_or_404(Author, id=author_id)
    if author_to_follow == request.user:  # Prevent following oneself
        messages.error(request, "You cannot follow yourself.")
        return redirect('authors:author_profile', author_id=author_id)

    existing_follow = Follow.objects.filter(follower=request.user, following=author_to_follow).exists()
    if existing_follow:  # Already following
        messages.info(request, f"You are already following {author_to_follow.displayName}.")
        return redirect('authors:author_profile', author_id=author_id)

    # Either create or update the existing follow request
    follow_request, created = FollowRequest.objects.get_or_create(
        sender=request.user,
        receiver=author_to_follow,
        defaults={'status': 'PENDING'}
    )

    if not created:
        # If it exists and was denied or approved before, reset to pending
        # Chose this method rather than because delete and recreate to preserve history
        if follow_request.status != 'PENDING':
            follow_request.status = 'PENDING'
            follow_request.save()
            messages.info(request, f"Follow request re-sent to {author_to_follow.displayName}.")
        else:
            messages.info(request, f"Follow request already pending.")
    else:
        messages.success(request, f"Follow request sent to {author_to_follow.displayName}!")

    return redirect('authors:author_profile', author_id=author_id)

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
    Follow.objects.filter(follower=request.user, following=author_to_unfollow).delete()  # Remove follow relationship
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
    
@login_required
def redirect_to_profile(request):
    return redirect('authors:author_profile', author_id=request.user.id)

@login_required
@require_POST
def toggle_like(request, post_id):
    # Get the post by ID, or show 404 if not found
    post = get_object_or_404(Post, id=post_id)
    can_like = (
        post.visibility in ['PUBLIC', 'PUBLIC_UNLISTED'] or 
        (post.visibility == 'FRIENDS' and Follow.objects.filter(follower=request.user, following=post.author).exists()) or
        request.user == post.author
    )
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

        # Permission check
        is_owner = self.request.user == post.author
        is_follower = Follow.objects.filter(follower=self.request.user, following=post.author).exists()
        # Allow viewing likes only if post is public, is friends-only and user follows author, or owned by current user
        if (post.visibility == 'FRIENDS' and not is_follower and not is_owner) or (post.visibility not in ['PUBLIC', 'PUBLIC_UNLISTED'] and not is_owner):
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

    # allow commenting only if post is PUBLIC/PUBLIC_UNLISTED (anyone can comment), or is friends-only and user follows author/owns post
    if post.visibility == 'FRIENDS' and post.author != request.user and not Follow.objects.filter(follower=request.user, following=post.author).exists():
        return HttpResponse("Forbidden", status=403)
    # Process submitted comment form
    form = CommentForm(request.POST)
    if form.is_valid():
        # Create and save comment
        Comment.objects.create(
            post=post,
            author=request.user,
            content=form.cleaned_data["content"]
        )
        messages.success(request, "Comment posted!")
    else:
        messages.error(request, "Could not post comment.")
    return redirect('authors:post_detail', post_id=post.id)


@login_required
@require_POST
def toggle_comment_like(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    post = comment.post

    # allow liking comment only if post is PUBLIC/PUBLIC_UNLISTED (anyone can like), or is friends-only and user follows author/owns post
    if post.visibility == 'FRIENDS' and post.author != request.user and not Follow.objects.filter(follower=request.user, following=post.author).exists():
        return HttpResponse("Forbidden", status=403)

    like, created = CommentLike.objects.get_or_create(author=request.user, comment=comment)
    if not created:
        # Already liked -> unlike
        like.delete()
        messages.info(request, "Unliked comment.")
    else:
        messages.success(request, "Liked comment.")

    return redirect('authors:post_detail', post_id=post.id)