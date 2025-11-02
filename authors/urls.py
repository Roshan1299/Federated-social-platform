from django.urls import path, re_path
from .views import (
    SignUpView, redirect_to_profile, StreamRedirectView, AuthorProfileView, 
    AuthorsListAPIView, AuthorAPIView, AuthorEditView, CreatePostView, 
    PostDetailView, EditPostView, DeletePostView, AuthorPostsView, PostAPIView, 
    AuthorStreamView, follow_author, cancel_follow_request, unfollow_author, 
    FollowRequest, FollowRequestsView, approve_follow_request, deny_follow_request, 
    toggle_like, PostLikesView, add_comment, toggle_comment_like, 
    FollowersListView, FollowingListView, AuthorDeletedPostsAdminView
)

# Import new API views
from .api_views import (
    InboxAPIView, FollowersAPIView, SingleFollowerAPIView, EntriesAPIView,
    SingleEntryAPIView, CommentsAPIView, LikesAPIView, LikedAPIView, ImageEntryAPIView,
    CommentLikesAPIView
)

app_name = "authors"
urlpatterns = [
    # ========== UI Routes (HTML Views) ==========
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("accounts/profile/", redirect_to_profile, name="redirect_profile"),
    path("authors/<uuid:author_id>/", AuthorProfileView.as_view(), name="author_profile"),
    path("authors/<uuid:author_id>/edit", AuthorEditView.as_view(), name="edit_profile"),
    path("authors/<uuid:author_id>/posts/", AuthorPostsView.as_view(), name="author_posts"),
    path("authors/<uuid:author_id>/stream", AuthorStreamView.as_view(), name="author_stream"),

    # Follow/Unfollow UI routes
    path("authors/<uuid:author_id>/follow/", follow_author, name="follow_author"),
    path("authors/<uuid:author_id>/unfollow/", unfollow_author, name="unfollow_author"),
    path("authors/follow_requests/", FollowRequestsView.as_view(), name="follow_requests"),
    path("authors/<uuid:author_id>/cancel_follow_request/", cancel_follow_request, name="cancel_follow_request"),
    path("authors/<uuid:author_id>/followers/", FollowersListView.as_view(), name="followers_list"),
    path("authors/<uuid:author_id>/following/", FollowingListView.as_view(), name="following_list"),
    path("authors/<uuid:author_id>/deleted_posts/", AuthorDeletedPostsAdminView.as_view(), name="author_deleted_posts_admin"),


    path("authors/follow_request/<int:request_id>/approve/", approve_follow_request, name="approve_follow_request"),
    path("authors/follow_request/<int:request_id>/deny/", deny_follow_request, name="deny_follow_request"),

    # Post UI routes
    path("posts/create/", CreatePostView.as_view(), name="create_post"),
    path("posts/<uuid:post_id>/", PostDetailView.as_view(), name="post_detail"),
    path("posts/<uuid:post_id>/edit/", EditPostView.as_view(), name="edit_post"),
    path("posts/<uuid:post_id>/delete/", DeletePostView.as_view(), name="delete_post"),
    path("posts/<uuid:post_id>/like/", toggle_like, name="toggle_like"),
    path("posts/<uuid:post_id>/comments/add/", add_comment, name="add_comment"),
    path("comments/<uuid:comment_id>/like/", toggle_comment_like, name="toggle_comment_like"),
    path("api/posts/<uuid:post_id>/likes/", PostLikesView.as_view(), name="post_likes_page"),
    

    # ========== REST API Routes (JSON) ==========
    # Note: Trailing slashes are optional for API endpoints
    
    # Authors API
    path("api/authors/", AuthorsListAPIView.as_view(), name="authors_api"),
    path("api/authors/<uuid:author_id>/", AuthorAPIView.as_view(), name="author_api"),

    # Inbox API (important)
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/inbox/?$', InboxAPIView.as_view(), name="inbox_api"),
    
    # Followers API
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/followers/?$', FollowersAPIView.as_view(), name="followers_api"),
    # to support FQID in addition to UUID
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/followers/(?P<follower_id>.+)$', 
            SingleFollowerAPIView.as_view(), name="single_follower_api"),
    
    # Entries/Posts API 
    # List/create endpoint
    path("api/authors/<uuid:author_id>/entries/", EntriesAPIView.as_view(), name="entries_api"),
    # Single entry
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/entries/(?P<entry_id>[0-9a-f-]+)/?$', SingleEntryAPIView.as_view(), name="single_entry_api"),
    
    # Image Entry API
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/entries/(?P<entry_id>[0-9a-f-]+)/image/?$', ImageEntryAPIView.as_view(), name="image_entry_api"),
    
    # Comments API
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/entries/(?P<entry_id>[0-9a-f-]+)/comments/?$', CommentsAPIView.as_view(), name="comments_api"),
    
    # Commented API - List of comments by author (UUID)
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/commented/?$', CommentsAPIView.as_view(), name="commented_api"),
    
    # Single Comment by SERIAL (UUID)
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/commented/(?P<comment_id>[0-9a-f-]+)/?$', CommentsAPIView.as_view(), name="single_comment_api"),
    
    # Comment Likes API
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/entries/(?P<entry_id>[0-9a-f-]+)/comments/(?P<comment_id>[0-9a-f-]+)/likes/?$', CommentLikesAPIView.as_view(), name="comment_likes_api"),
    
    # Likes API
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/entries/(?P<entry_id>[0-9a-f-]+)/likes/?$', LikesAPIView.as_view(), name="entry_likes_api"),
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/liked/?$', LikedAPIView.as_view(), name="liked_api"),
    
    # Single Like by SERIAL (UUID)
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/liked/(?P<like_id>[0-9a-f-]+)/?$', LikedAPIView.as_view(), name="single_like_api"),
    
    # ========== FQID Routes (for cross-node federation) ==========
    # Accept percent-encoded full URLs as parameters
    # NOTE: After UUID-based routes to avoid conflicts
    
    # Entries API with FQID
    re_path(r'^api/entries/(?P<entry_fqid>.+)/image$', ImageEntryAPIView.as_view(), name="entry_fqid_image_api"),
    re_path(r'^api/entries/(?P<entry_fqid>.+)/comments$', CommentsAPIView.as_view(), name="entry_fqid_comments_api"),
    re_path(r'^api/entries/(?P<entry_fqid>.+)/likes$', LikesAPIView.as_view(), name="entry_fqid_likes_api"),
    re_path(r'^api/entries/(?P<entry_fqid>.+)$', SingleEntryAPIView.as_view(), name="entry_fqid_api"),
    
    # Comment with FQID in path
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/entries/(?P<entry_id>[0-9a-f-]+)/comment/(?P<comment_fqid>.+)$', 
            CommentsAPIView.as_view(), name="remote_comment_api"),
    
    # Comment Likes with FQID
    re_path(r'^api/authors/(?P<author_id>[0-9a-f-]+)/entries/(?P<entry_id>[0-9a-f-]+)/comments/(?P<comment_fqid>.+)/likes$', 
            CommentLikesAPIView.as_view(), name="comment_fqid_likes_api"),
    
    # Commented API with FQID
    re_path(r'^api/authors/(?P<author_fqid>.+)/commented$', CommentsAPIView.as_view(), name="author_fqid_commented_api"),
    re_path(r'^api/commented/(?P<comment_fqid>.+)$', CommentsAPIView.as_view(), name="comment_fqid_api"),
    
    # Liked API with FQID
    re_path(r'^api/authors/(?P<author_fqid>.+)/liked/?$', LikedAPIView.as_view(), name="author_fqid_liked_api"),
    re_path(r'^api/liked/(?P<like_fqid>.+)$', LikedAPIView.as_view(), name="like_fqid_api"),
    
    # Single Author API with FQID (remote nodes can query by full URL) - MUST BE LAST
    re_path(r'^api/authors/(?P<author_fqid>.+)/$', AuthorAPIView.as_view(), name="author_fqid_api"),
    
    # ========== Legacy API Routes (kept for backwards compatibility) ==========
    path("api/posts/<uuid:post_id>/", PostAPIView.as_view(), name="post_api"),
]
