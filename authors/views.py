import markdown
from django.forms import BaseModelForm
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DetailView, ListView, TemplateView
from django.views import View
from django.http import HttpResponse, JsonResponse
from .models import Author, Post, Follow, FollowRequest, Like, Comment, CommentLike
from .forms import CommentForm

from .forms import AuthorCreationForm, AuthorProfileForm, PostForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


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
        if (self.get_object() == self.request.user):
            # If viewing own profile, show all posts
            context["posts"] = self.object.posts.all().order_by("-published")
        elif (self.request.user.is_authenticated and Follow.objects.filter(follower=self.request.user, following=self.get_object()).exists()):
            # If viewing an author that you follow, show their public and unlisted posts.
            context["posts"] = self.object.posts.filter(visibility="PUBLIC").order_by("-published")
        else:
            # If viewing another author's profile, show only public, non-unlisted posts
            context["posts"] = self.object.posts.filter(visibility="PUBLIC", unlisted=False).order_by("-published")

        
        # Determine if the current user follows this author
        user = self.request.user
        author = self.get_object()
        if user.is_authenticated and user != author:
            context['is_following'] = Follow.objects.filter(follower=user, following=author).exists()
            context['has_pending_request'] = FollowRequest.objects.filter(sender=user, receiver=author, status='PENDING').exists()
        else:
            context['is_following'] = False
            context['has_pending_request'] = False
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

class DeletePostView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        post = get_object_or_404(Post, id=self.kwargs['post_id'])
        return self.request.user == post.author

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        if self.request.user == post.author:
            post.delete()
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
        # Only allow if post is PUBLIC or user is the author
        if (post.visibility =="PRIVATE" and request.user != post.author):
            return HttpResponse("Forbidden", status=403)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = context['object']
        if post.contentType == 'text/markdown':
            # Convert markdown content to HTML
            context['content_html'] = markdown.markdown(post.content)
        else:
            context['content_html'] = post.content.replace('\n', '<br>')  # Basic line breaks for plain text
        
        # Add image context if image exists
        context['has_image'] = post.image and post.image.url
        # User will not have option to copy link if post is private
        context['VISIBILITY_PRIVATE'] = "PRIVATE"

        user = self.request.user
        context['like_count'] = post.likes.count()
        context['liked_by_me'] = user.is_authenticated and post.likes.filter(author=user).exists()
        context['can_like'] = user.is_authenticated and (
            post.visibility == 'PUBLIC' or user == post.author
        )

        user = self.request.user
        context['can_interact'] = user.is_authenticated and (
        post.visibility == 'PUBLIC' or user == post.author
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
        return Post.objects.filter(author_id=author_id, visibility='PUBLIC').order_by('-published')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['author'] = get_object_or_404(Author, id=self.kwargs['author_id'])
        return context


class PostAPIView(View):
    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
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

'''
class AuthorStreamView(ListView):
    """
    HTML stream page for an author.
    Shows public, non-unlisted posts, ordered by most recent 'updated' timestamp.
    Only the author can view their personal stream page
    """
    model = Post
    template_name = "authors/author_stream.html"
    context_object_name = "posts"
    paginate_by = 20  # paginate the stream

    def get_queryset(self):
        # Oosts the node knows about, exclude deleted (removed from DB)
        # Order by -updated (for most recently edited/created entries)
        return (
            Post.objects
            .filter(visibility='PUBLIC', unlisted=False)
            .order_by('-updated')
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # extra context (author info)
        context['author_id'] = self.kwargs['author_id']
        return context
'''

class AuthorStreamView(ListView):
    model = Post
    template_name = "authors/author_stream.html"
    context_object_name = "posts"
    paginate_by = 20

    def get_queryset(self):
        # Keep existing logic: show all public, non-unlisted posts ordered by latest
        return (
            Post.objects
            .filter(visibility='PUBLIC', unlisted=False)
            .order_by('-updated')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_authenticated:
            followed_authors = Follow.objects.filter(follower=user).select_related("following")
            followed_data = []
            for follow in followed_authors:
                author = follow.following
                posts = Post.objects.filter(
                    author=author,
                    visibility='PUBLIC',
                    unlisted=False
                ).order_by('-updated')[:5]  # show latest 5 per author
                if posts.exists():
                    followed_data.append({
                        "author": author,
                        "posts": posts
                    })
            context["followed_data"] = followed_data
        else:
            context["followed_data"] = []

        # Pass the authenticated user's ID, not from URL kwargs
        context["author_id"] = user.id if user.is_authenticated else None
        return context


class StreamRedirectView(TemplateView):
    """Redirect view to send user to their personalized stream"""
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('authors:author_stream', author_id=request.user.id)
        else:
            # If not authenticated, redirect to login
            return redirect('login')

class FollowRequestsView(LoginRequiredMixin, ListView):
    model = FollowRequest
    template_name = "authors/follow_requests.html"
    context_object_name = "requests"

    def get_queryset(self):
        return FollowRequest.objects.filter(receiver=self.request.user, status='PENDING').select_related('sender')


@login_required
def follow_author(request, author_id):
    author_to_follow = get_object_or_404(Author, id=author_id)
    if author_to_follow == request.user:
        messages.error(request, "You cannot follow yourself.")
        return redirect('authors:author_profile', author_id=author_id)

    existing_follow = Follow.objects.filter(follower=request.user, following=author_to_follow).exists()
    if existing_follow:
        messages.info(request, f"You are already following {author_to_follow.displayName}.")
        return redirect('authors:author_profile', author_id=author_id)

    # Check if request already sent
    existing_request = FollowRequest.objects.filter(sender=request.user, receiver=author_to_follow, status='PENDING').exists()
    if existing_request:
        messages.info(request, f"Follow request already sent to {author_to_follow.displayName}.")
    else:
        FollowRequest.objects.create(sender=request.user, receiver=author_to_follow)
        messages.success(request, f"Follow request sent to {author_to_follow.displayName}!")

    return redirect('authors:author_profile', author_id=author_id)


@login_required
def unfollow_author(request, author_id):
    author_to_unfollow = get_object_or_404(Author, id=author_id)
    Follow.objects.filter(follower=request.user, following=author_to_unfollow).delete()
    messages.success(request, f"You have unfollowed {author_to_unfollow.displayName}.")
    return redirect('authors:author_profile', author_id=author_id)

@login_required
def approve_follow_request(request, request_id):
    follow_request = get_object_or_404(FollowRequest, id=request_id, receiver=request.user)
    Follow.objects.get_or_create(follower=follow_request.sender, following=request.user)
    follow_request.status = 'APPROVED'
    follow_request.save()
    messages.success(request, f"You approved {follow_request.sender.displayName}'s follow request.")
    return redirect('authors:follow_requests')


@login_required
def deny_follow_request(request, request_id):
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
    can_like = (post.visibility == 'PUBLIC') or (request.user == post.author)
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
        # Allow viewing likes only if post is public or owned by current user
        if post.visibility != 'PUBLIC' and not is_owner:
            ctx["error"] = "You don’t have permission to view likes for this post."
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

    # allow commenting only if post is PUBLIC or owned by current user
    if post.visibility != 'PUBLIC' and post.author != request.user:
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

    # allow liking comment only if post is PUBLIC or owned by current user
    if post.visibility != 'PUBLIC' and post.author != request.user:
        return HttpResponse("Forbidden", status=403)

    like, created = CommentLike.objects.get_or_create(author=request.user, comment=comment)
    if not created:
        # Already liked -> unlike
        like.delete()
        messages.info(request, "Unliked comment.")
    else:
        messages.success(request, "Liked comment.")

    return redirect('authors:post_detail', post_id=post.id)