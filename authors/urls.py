from django.urls import path
from .views import SignUpView, redirect_to_profile, StreamRedirectView, AuthorProfileView, AuthorsListAPIView, AuthorAPIView, AuthorEditView, CreatePostView, PostDetailView, EditPostView, DeletePostView, AuthorPostsView, PostAPIView, AuthorStreamView, follow_author, cancel_follow_request, unfollow_author, FollowRequest, FollowRequestsView, approve_follow_request, deny_follow_request, toggle_like, PostLikesView, add_comment, toggle_comment_like, FollowersListView

app_name = "authors"
urlpatterns = [
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/profile/", redirect_to_profile, name="redirect_profile"),
    path("authors/<uuid:author_id>/", AuthorProfileView.as_view(), name="author_profile"),
    path("authors/<uuid:author_id>/edit", AuthorEditView.as_view(), name="edit_profile"),
    path("authors/<uuid:author_id>/posts/", AuthorPostsView.as_view(), name="author_posts"),
    path("authors/<uuid:author_id>/stream", AuthorStreamView.as_view(), name="author_stream"),

    path("authors/<uuid:author_id>/follow/", follow_author, name="follow_author"),
    path("authors/<uuid:author_id>/unfollow/", unfollow_author, name="unfollow_author"),
    path("authors/follow_requests/", FollowRequestsView.as_view(), name="follow_requests"),
    path("authors/<uuid:author_id>/cancel_follow_request/", cancel_follow_request, name="cancel_follow_request"),
    path("authors/<uuid:author_id>/followers/", FollowersListView.as_view(), name="followers_list"),

    path("authors/follow_request/<int:request_id>/approve/", approve_follow_request, name="approve_follow_request"),
    path("authors/follow_request/<int:request_id>/deny/", deny_follow_request, name="deny_follow_request"),


    path("posts/create/", CreatePostView.as_view(), name="create_post"),
    path("posts/<uuid:post_id>/", PostDetailView.as_view(), name="post_detail"),
    path("posts/<uuid:post_id>/edit/", EditPostView.as_view(), name="edit_post"),
    path("posts/<uuid:post_id>/delete/", DeletePostView.as_view(), name="delete_post"),
    path("posts/<uuid:post_id>/like/", toggle_like, name="toggle_like"),
    path("posts/<uuid:post_id>/comments/add/", add_comment, name="add_comment"),
    path("comments/<uuid:comment_id>/like/", toggle_comment_like, name="toggle_comment_like"),
    path("api/posts/<uuid:post_id>/likes/", PostLikesView.as_view(), name="post_likes_page"),
    path("api/authors/<uuid:author_id>/", AuthorAPIView.as_view(), name="author_api"),
    path("api/authors/", AuthorsListAPIView.as_view(), name="authors_api"),
    path("api/posts/<uuid:post_id>/", PostAPIView.as_view(), name="post_api"),
]
