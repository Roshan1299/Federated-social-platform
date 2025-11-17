from django.conf import settings

from authors.models import Follow, RemoteNode, Post, Comment, Like
from authors.utils.nodes import remote_post


from django.conf import settings

from authors.models import Follow, RemoteNode, Post, Comment, Like
from authors.utils.nodes import remote_post


def get_remote_followers_and_friends(author):
    """
    Get a list of (RemoteNode, remote_author) tuples for remote followers 
    and friends of the given author.

    Logic:
        - Find all Follow rows where following = author (followers)
        - Find all Follow rows where follower = author (following)
        - A "friend" is a mutual follow (A follows B and B follows A)
        - If a follower/friend's host != our BASE_URL -> treat as remote
        - Match the remote host to a RemoteNode by base_url
    
    Note: When posts are sent to remote inboxes, the receiving node will
    create InboxReceipt records. This allows the receiving node to correctly
    display friends-only posts even if Follow relationships become stale.
    """
    local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    results = {}  # Use a dict to avoid duplicates

    # Get followers
    followers = Follow.objects.filter(following=author).select_related("follower")
    for f in followers:
        follower = f.follower
        follower_host = (follower.host or "").rstrip("/")
        if follower_host and follower_host != local_host:
            try:
                node = RemoteNode.objects.get(base_url__icontains=follower_host, enabled=True)
                results[follower.id] = (node, follower)
            except RemoteNode.DoesNotExist:
                continue

    # Get friends (mutual follows)
    following = Follow.objects.filter(follower=author).select_related("following")
    for f in following:
        followed_author = f.following
        # Check for mutual follow
        if Follow.objects.filter(follower=followed_author, following=author).exists():
            followed_host = (followed_author.host or "").rstrip("/")
            if followed_host and followed_host != local_host:
                try:
                    node = RemoteNode.objects.get(base_url__icontains=followed_host, enabled=True)
                    results[followed_author.id] = (node, followed_author)
                except RemoteNode.DoesNotExist:
                    continue
    
    return list(results.values())


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


def send_to_remote_inboxes(author, payload: dict):
    """
    Send the given payload to every remote follower and friend's inbox.

    For each remote follower/friend:
        - Build inbox URL for that follower on their node
        - Call remote_post(url, payload, base_url=node.base_url)
    """
    recipients = get_remote_followers_and_friends(author)

    for node, remote_author in recipients:
        # Build inbox URL using the remote author's canonical author URL
        inbox_url = inbox_url_for_remote(node, remote_author.url)

        # Fire-and-forget; if a remote node fails, local behaviour is unaffected
        try:
            remote_post(
                url=inbox_url,
                payload=payload,
                base_url=node.base_url,
            )
        except Exception:
            # Don't crash if a remote node is down
            continue


# ---------------------------------------------------------------------
# Public helpers: call these from your views
# ---------------------------------------------------------------------

def notify_remote_new_post(post: Post):
    """
    Called when a post is created.
    Sends the post JSON to all remote followers and friends.
    """
    payload = build_post_payload(post)
    send_to_remote_inboxes(post.author, payload)


def notify_remote_edit_post(post: Post):
    """
    Called when a post is edited.
    Re-sends the updated post JSON to all remote followers and friends.
    """
    payload = build_post_payload(post)
    send_to_remote_inboxes(post.author, payload)


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
    send_to_remote_inboxes(post.author, payload)


def notify_remote_comment(comment: Comment):
    """
    Called when a comment is created.
    Sends the comment JSON to remote followers and friends.
    """
    payload = build_comment_payload(comment)
    send_to_remote_inboxes(comment.author, payload)


def notify_remote_like(like: Like):
    """
    Called when a like is created.
    Sends the like JSON to remote followers and friends.
    """
    payload = build_like_payload(like)
    send_to_remote_inboxes(like.author, payload)