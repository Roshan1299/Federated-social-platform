import markdown
from django.forms import BaseModelForm
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DetailView, ListView
from django.views import View
from django.http import HttpResponse, JsonResponse
from .models import Author, Post, Follow, FollowRequest

from .forms import AuthorCreationForm, AuthorProfileForm, PostForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages


class SignUpView(CreateView):
    form_class = AuthorCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user = form.save(commit=False)
        # For now, make users active so they can log in immediately
        user.is_active = True

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

class AuthorEditView(UpdateView):
    form_class = AuthorProfileForm
    model = Author
    template_name = "authors/edit_profile.html"
    pk_url_kwarg = "author_id"

    # Both AuthorProfileView and AuthorEditView extend profile_base.html. To distinguish between them, set 'editable' context.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editable'] = True
        return context
    
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
        return context


class AuthorPostsView(ListView):
    model = Post
    template_name = "authors/author_posts.html"
    context_object_name = "posts"
    
    def get_queryset(self):
        author_id = self.kwargs['author_id']
        return Post.objects.filter(author_id=author_id, visibility='PUBLIC').order_by('-published')


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

        context["author_id"] = self.kwargs.get("author_id", None)
        return context

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