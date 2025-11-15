"""
Federation fan-out helpers.

These functions:
- Find remote followers of an author
- Build JSON payloads for posts / comments / likes
- Send them to remote inboxes using remote_post
"""

from django.conf import settings

from authors.models import Follow, RemoteNode, Post, Comment, Like
from authors.utils.nodes import remote_post


def get_remote_followers(author):
    """
    Get a list of RemoteNode objects for remote followers of the given author.

    Logic:
        - Find all Follow rows where following = author
        - Check follower.host
        - If follower.host != our BASE_URL, they are remote
        - Match follower.host to a RemoteNode by base_url
    """
    local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    remote_nodes = []

    # All followers of this author
    followers = Follow.objects.filter(following=author).select_related("follower")

    for f in followers:
        follower = f.follower
        # Only treat as remote if host is set and different from local host
        if follower.host:
            follower_host = follower.host.rstrip("/")
            if follower_host != local_host:
                try:
                    node = RemoteNode.objects.get(
                        base_url__icontains=follower_host,
                        enabled=True,
                    )
                    remote_nodes.append(node)
                except RemoteNode.DoesNotExist:
                    # We don't have credentials for this host
                    continue

    return remote_nodes


def inbox_url_for_remote(node: RemoteNode, remote_author_url: str) -> str:
    """
    Build the inbox URL for the remote author.

    Example:
        node.base_url        = "https://team-green.herokuapp.com"
        remote_author_url    = "https://team-green.herokuapp.com/api/authors/1234/"

        inbox URL result:
        "https://team-green.herokuapp.com/api/authors/1234/inbox"
    """
    author_id = remote_author_url.rstrip("/").split("/")[-1]
    return f"{node.base_url.rstrip('/')}/api/authors/{author_id}/inbox"


def build_post_payload(post: Post) -> dict:
    """
    Convert a Post into JSON for remote nodes.

    Only basic fields are included.
    """
    return {
        "type": "post",
        "id": post.origin,
        "source": post.source,
        "origin": post.origin,
        "title": post.title,
        "content": post.content,
        "contentType": post.contentType,
        "visibility": post.visibility,
        "published": post.published.isoformat(),
        "updated": post.updated.isoformat(),
        "author": {
            "type": "author",
            "id": post.author.url,
            "host": post.author.host,
            "displayName": post.author.displayName,
            "url": post.author.url,
            "github": post.author.github,
        },
    }


def build_comment_payload(comment: Comment) -> dict:
    """
    Convert a Comment into JSON for remote nodes.
    """
    return {
        "type": "comment",
        "id": comment.origin,
        "comment": comment.content,
        "post": comment.post.origin,
        "published": comment.created_at.isoformat(),
        "author": {
            "type": "author",
            "id": comment.author.url,
            "host": comment.author.host,
            "displayName": comment.author.displayName,
            "url": comment.author.url,
        },
    }


def build_like_payload(like: Like) -> dict:
    """
    Convert a Like into JSON for remote nodes.
    """
    return {
        "type": "like",
        "id": like.origin,
        "object": like.post.origin,
        "summary": f"{like.author.displayName} likes your post",
        "author": {
            "type": "author",
            "id": like.author.url,
            "host": like.author.host,
            "displayName": like.author.displayName,
            "url": like.author.url,
        },
    }


def send_to_remote_followers(author, payload: dict):
    """
    Send the given payload to every remote follower's inbox.

    For each RemoteNode:
        - Build inbox URL for this author
        - Call remote_post(url, payload, base_url=node.base_url)
    """
    nodes = get_remote_followers(author)

    for node in nodes:
        inbox_url = inbox_url_for_remote(node, author.url)
        # We don't care about the return value here; failure is non-fatal
        remote_post(
            url=inbox_url,
            payload=payload,
            base_url=node.base_url,
        )


# ---------------------------------------------------------------------
# Public helpers: call these from your views
# ---------------------------------------------------------------------

def notify_remote_new_post(post: Post):
    """
    Called when a post is created.
    Sends the post JSON to all remote followers.
    """
    payload = build_post_payload(post)
    send_to_remote_followers(post.author, payload)


def notify_remote_edit_post(post: Post):
    """
    Called when a post is edited.
    Re-sends the updated post JSON to all remote followers.
    """
    payload = build_post_payload(post)
    send_to_remote_followers(post.author, payload)


def notify_remote_delete_post(post: Post):
    """
    Called when a post is deleted.
    Sends a simple delete notification.
    """
    payload = {
        "type": "delete",
        "id": post.origin,
        "author": post.author.url,
    }
    send_to_remote_followers(post.author, payload)


def notify_remote_comment(comment: Comment):
    """
    Called when a comment is created.
    Sends the comment JSON to remote followers.
    """
    payload = build_comment_payload(comment)
    send_to_remote_followers(comment.author, payload)


def notify_remote_like(like: Like):
    """
    Called when a like is created.
    Sends the like JSON to remote followers.
    """
    payload = build_like_payload(like)
    send_to_remote_followers(like.author, payload)