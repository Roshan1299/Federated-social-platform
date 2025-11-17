from django.conf import settings

from authors.models import Follow, RemoteNode, Post, Comment, Like, Author
from authors.utils.nodes import remote_post




def get_remote_node_for_author(author: Author):
    # Take the author's host (e.g. "https://team-green.herokuapp.com")
    host = (author.host or "").rstrip("/")
    if not host:
        return None

    # Try to find matching RemoteNode row in our DB
    try:
        # base_url is stored like "https://team-green.herokuapp.com"
        return RemoteNode.objects.get(base_url__icontains=host, enabled=True)
    except RemoteNode.DoesNotExist:
        return None
    
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


def send_to_remote_inboxes(author, payload: dict, post_visibility: str = 'PUBLIC'):
    """
    Send the given payload to every remote follower and friend's inbox,
    respecting post visibility settings.

    For each remote follower/friend:
        - Build inbox URL for that follower on their node
        - Call remote_post(url, payload, base_url=node.base_url)
        
    Visibility rules:
    - PUBLIC: Send to both followers and friends
    - FRIENDS: Send only to friends (mutual follows)
    - PUBLIC_UNLISTED: Do not send to any remote nodes (not pushed to inboxes)
    """
    # Don't send PUBLIC_UNLISTED posts to remote nodes at all
    if post_visibility == 'PUBLIC_UNLISTED':
        return  # Early return - don't send unlisted posts to remote nodes

    recipients = get_remote_followers_and_friends(author)

    for node, remote_author in recipients:
        # For FRIENDS posts, only send to friends (mutual follows), not to followers
        if post_visibility == 'FRIENDS':
            # Check if this is a mutual follow (friend relationship)
            # remote_author follows the post author, and post author follows remote_author
            is_friend = (
                # Check if remote_author follows the post author (they are in followers/friends list, so this is true)
                # AND check if post author follows remote_author back (mutual)
                Follow.objects.filter(follower=author, following=remote_author).exists()
            )
            
            if not is_friend:
                continue  # Skip non-friends for FRIENDS posts

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
    Sends the post JSON to all remote followers and friends based on visibility.
    """
    payload = build_post_payload(post)
    send_to_remote_inboxes(post.author, payload, post.visibility)


def notify_remote_edit_post(post: Post):
    """
    Called when a post is edited.
    Re-sends the updated post JSON to all remote followers and friends based on visibility.
    """
    payload = build_post_payload(post)
    send_to_remote_inboxes(post.author, payload, post.visibility)


def notify_remote_delete_post(post: Post):
    """
    Called when a post is deleted.
    Sends the post object marked as deleted to all remote followers/friends.
    This ensures they know the post has been deleted.
    """
    # Send the post with its current visibility but mark as deleted
    # This will trigger the remote node to update their local copy with deleted=True
    payload = {
        "type": "post",
        "id": post.origin,
        "source": post.source,
        "origin": post.origin,
        "title": post.title,
        "content": post.content,  # Content remains but will be hidden when viewed
        "contentType": post.contentType,
        "visibility": post.visibility,  # Keep original visibility
        "published": post.published.isoformat(),
        "updated": post.updated.isoformat(),
        "deleted": True,  # Explicitly mark as deleted for remote update
        "author": {
            "type": "author",
            "id": post.author.url,
            "host": post.author.host,
            "displayName": post.author.displayName,
            "url": post.author.url,
            "github": post.author.github,
        },
    }
    send_to_remote_inboxes(post.author, payload, post.visibility)


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


def send_comment_to_post_owner(comment: Comment) -> bool:
    # Get the post being commented on
    post = comment.post
    remote_author = post.author

    # Find which RemoteNode this author belongs to
    node = get_remote_node_for_author(remote_author)
    if not node:
        return False  # no matching remote node → cannot connect

    # Build inbox URL on that remote node for this author
    inbox_url = inbox_url_for_remote(node, remote_author.url)

    # Build JSON payload for this comment
    payload = build_comment_payload(comment)

    # Send payload to remote node using:
    #   - inbox_url
    #   - node.base_url (to find username/password in RemoteNode)
    return remote_post(
        url=inbox_url,
        payload=payload,
        base_url=node.base_url,
    )


def send_like_to_post_owner(like: Like) -> bool:
    # Get the post that was liked
    post = like.post
    remote_author = post.author

    # Find which RemoteNode owns this author
    node = get_remote_node_for_author(remote_author)
    if not node:
        return False  # cannot connect to this node

    # Build inbox URL on that remote node
    inbox_url = inbox_url_for_remote(node, remote_author.url)

    # Build JSON payload for this like
    payload = build_like_payload(like)

    # Send payload to remote node using base_url + username + password
    return remote_post(
        url=inbox_url,
        payload=payload,
        base_url=node.base_url,
    )