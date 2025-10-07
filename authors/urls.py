from django.urls import path
from .views import SignUpView, redirect_to_profile, AuthorProfileView, AuthorsListAPIView, AuthorAPIView, AuthorEditView, CreatePostView, PostDetailView, EditPostView, DeletePostView, AuthorPostsView, PostAPIView, AuthorStreamView

app_name = "authors"
urlpatterns = [
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/profile/", redirect_to_profile, name="redirect_profile"),
    path("authors/<uuid:author_id>/", AuthorProfileView.as_view(), name="author_profile"),
    path("authors/<uuid:author_id>/edit", AuthorEditView.as_view(), name="edit_profile"),
    path("authors/<uuid:author_id>/posts/", AuthorPostsView.as_view(), name="author_posts"),
    path("authors/<uuid:author_id>/stream", AuthorStreamView.as_view(), name="author_stream"),
    path("posts/create/", CreatePostView.as_view(), name="create_post"),
    path("posts/<uuid:post_id>/", PostDetailView.as_view(), name="post_detail"),
    path("posts/<uuid:post_id>/edit/", EditPostView.as_view(), name="edit_post"),
    path("posts/<uuid:post_id>/delete/", DeletePostView.as_view(), name="delete_post"),
    path("api/authors/<uuid:author_id>/", AuthorAPIView.as_view(), name="author_api"),
    path("api/authors/", AuthorsListAPIView.as_view(), name="authors_api"),
    path("api/posts/<uuid:post_id>/", PostAPIView.as_view(), name="post_api"),
]
