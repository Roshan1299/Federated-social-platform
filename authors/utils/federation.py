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

# Get all remote followers and remote mutual friends
def get_remote_followers_and_friends(author):
    local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    results = {}  # Use a dict to avoid duplicates

    # Find remote followers
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

    # Find remote mutual friends
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

# Build the remote inbox URL for a remote author
def inbox_url_for_remote(node: RemoteNode, remote_author_url: str) -> str:
    author_id = remote_author_url.rstrip("/").split("/")[-1]
    return f"{node.base_url.rstrip('/')}/api/authors/{author_id}/inbox"

# ---------------------------------------------------------------------
# Payload Builders
# ---------------------------------------------------------------------

# Convert Post to JSON for remote sending
def build_post_payload(post: Post) -> dict:
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

# Convert a Comment into JSON for remote nodes
def build_comment_payload(comment: Comment) -> dict:
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

# Convert a Like into JSON for remote nodes
def build_like_payload(like: Like) -> dict:
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

def build_comment_like_payload(comment_like):
    """
    Convert a CommentLike into JSON for remote nodes.
    """
    return {
        "type": "like",
        "id": comment_like.origin,
        "object": comment_like.comment.origin,   # <--- 댓글의 origin
        "summary": f"{comment_like.author.displayName} likes your comment",
        "author": {
            "id": comment_like.author.url,
            "host": comment_like.author.host,
            "displayName": comment_like.author.displayName,
            "url": comment_like.author.url,
        },
    }



def send_to_remote_inboxes(author, payload: dict, post_visibility: str = 'PUBLIC'):
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
# Nofitications
# ---------------------------------------------------------------------

def notify_remote_new_post(post: Post):
    """
    Called when a post is created.
    Sends the post JSON to all remote followers and friends based on visibility.
    """
    payload = build_post_payload(post)
    send_to_remote_inboxes(post.author, payload, post.visibility)

# Called when a post is edited
def notify_remote_edit_post(post: Post):
    """
    Called when a post is edited.
    Re-sends the updated post JSON to all remote followers and friends based on visibility.
    """
    payload = build_post_payload(post)
    send_to_remote_inboxes(post.author, payload, post.visibility)

# Called when a post is deleted
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

# Called when a comment is created
def notify_remote_comment(comment: Comment):
    payload = build_comment_payload(comment)
    send_to_remote_inboxes(comment.author, payload)

# Called when a like is created
def notify_remote_like(like: Like):
    payload = build_like_payload(like)
    send_to_remote_inboxes(like.author, payload)

# Send a comment to the original author's remote inbox
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

# Send a like on a post to remote post owner
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

def send_comment_like_to_post_owner(comment_like) -> bool:
    # The comment being liked
    comment = comment_like.comment
    remote_author = comment.author

    # Find remote node for this comment author
    node = get_remote_node_for_author(remote_author)
    if not node:
        return False  # remote node not registered

    # Build inbox URL of comment author
    inbox_url = inbox_url_for_remote(node, remote_author.url)

    # Build payload
    payload = build_comment_like_payload(comment_like)

    # Send to remote node
    return remote_post(
        url=inbox_url,
        payload=payload,
        base_url=node.base_url,
    )
