from django.urls import path
from .views import SignUpView, AuthorProfileView, AuthorsListAPIView, AuthorAPIView, AuthorEditView, CreatePostView, PostDetailView, AuthorPostsView, PostAPIView

app_name = "authors"
urlpatterns = [
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("authors/<uuid:author_id>/", AuthorProfileView.as_view(), name="author_profile"),
    path("authors/<uuid:author_id>/edit", AuthorEditView.as_view(), name="edit_profile"),
    path("authors/<uuid:author_id>/posts/", AuthorPostsView.as_view(), name="author_posts"),
    path("posts/create/", CreatePostView.as_view(), name="create_post"),
    path("posts/<uuid:post_id>/", PostDetailView.as_view(), name="post_detail"),
    path("api/authors/<uuid:author_id>/", AuthorAPIView.as_view(), name="author_api"),
    path("api/authors/", AuthorsListAPIView.as_view(), name="authors_api"),
    path("api/posts/<uuid:post_id>/", PostAPIView.as_view(), name="post_api"),
]
