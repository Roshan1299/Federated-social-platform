from django.conf import settings

from authors.models import Follow, RemoteNode, Post, Comment, Like, Author
from authors.utils.nodes import remote_post
from django.urls import reverse
from urllib.parse import urlparse

def _base_from_url(url: str) -> str:
    """
    Given something like:
      - 'https://crimson-node-utsha-...herokuapp.com/api/'
    return:
      - 'https://crimson-node-utsha-...herokuapp.com'
    """
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return url.rstrip("/")


def notify_remote_author_update(author: Author):
    payload = {
        "type": "author",
        "id": author.url,
        "host": author.host,
        "displayName": author.displayName,
        "url": author.url,
        "github": author.github,
        "description": author.description,
        "profileImage": build_profile_image_url(author),
    }
    send_to_remote_inboxes(author, payload)


def get_remote_node_for_author(author: Author):
    host = _base_from_url(author.host or "")
    if not host:
        return None
    try:
        return RemoteNode.objects.get(base_url__icontains=host, enabled=True)
    except RemoteNode.DoesNotExist:
        return None

# Get all remote followers and remote mutual friends
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

    # Find remote followers
    followers = Follow.objects.filter(following=author).select_related("follower")
    for f in followers:
        follower = f.follower
        follower_host_raw = (follower.host or "").rstrip("/")
        follower_host = _base_from_url(follower_host_raw)

        if follower_host and follower_host != local_host:
            try:
                node = RemoteNode.objects.get(
                    base_url__icontains=follower_host,
                    enabled=True,
                )
                results[follower.id] = (node, follower)
            except RemoteNode.DoesNotExist:
                continue

    # Find remote mutual friends
    following = Follow.objects.filter(follower=author).select_related("following")
    for f in following:
        followed_author = f.following
        if Follow.objects.filter(follower=followed_author, following=author).exists():
            followed_host_raw = (followed_author.host or "").rstrip("/")
            followed_host = _base_from_url(followed_host_raw)

            if followed_host and followed_host != local_host:
                try:
                    node = RemoteNode.objects.get(
                        base_url__icontains=followed_host,
                        enabled=True,
                    )
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

# Minimal Author representation for follow/unfollow payloads
def build_minimal_author_dict(author: Author) -> dict:
    """
    Minimal author representation suitable for follow/unfollow payloads.
    """
    return {
        "id": author.url,
        "host": author.host,
        "displayName": author.displayName,
        "url": author.url,
        "github": author.github,
        "description": author.description,
    }

def build_profile_image_url(author):
    """
    Build full profile image URL for federation payloads.
    Returns None if author has no profile image.
    """
    if not author.profileImage_id:
        return None

    # Build absolute URL for /api/authors/<id>/image/
    path = reverse("authors:author_image_api", args=[author.id])

    # Use author's host (remote nodes expect consistency)
    return f"{author.host.rstrip('/')}{path}"

# Convert Post to JSON for remote sending
def build_post_payload(post: Post) -> dict:
    # Convert PUBLIC_UNLISTED to UNLISTED for remote nodes
    visibility = post.visibility
    if visibility == "PUBLIC_UNLISTED":
        visibility = "UNLISTED"
    
    payload = {
        "type": "entry",
        "id": post.origin,
        "source": post.source,
        "origin": post.origin,
        "title": post.title,
        "description": post.description if post.description else "", 
        "content": post.content,
        "contentType": post.contentType,
        "visibility": visibility,
        "published": post.published.isoformat(),
        "updated": post.updated.isoformat(),
        "author": {
            "type": "author",
            "id": post.author.url,
            "host": post.author.host,
            "displayName": post.author.displayName,
            "url": post.author.url,
            "github": post.author.github,
            "profileImage": build_profile_image_url(post.author),
        },
    }

    # Safely build image URL using the origin's host
    if post.image_id:
        # Try to get scheme+host from the origin first
        host_base = ""
        if post.origin:
            parsed = urlparse(post.origin)
            if parsed.scheme and parsed.netloc:
                host_base = f"{parsed.scheme}://{parsed.netloc}"

        # Fallback to BASE_URL if origin is missing or weird
        if not host_base:
            host_base = (getattr(settings, "BASE_URL", "") or "").rstrip("/")

        image_path = reverse("authors:image_entry_api", args=[post.author.id, post.id])
        payload["image"] = f"{host_base}{image_path}"

    return payload


# Convert a Comment into JSON for remote nodes
def build_comment_payload(comment: Comment) -> dict:
    return {
        "type": "comment",
        "id": comment.origin,
        "comment": comment.content,
        "entry": comment.post.origin,
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
    # PUBLIC_UNLISTED posts should be sent to followers' inboxes like PUBLIC posts
    # Only FRIENDS posts have special restrictions
    if post_visibility == 'FRIENDS':
        # Will be handled by the friend-specific logic below
        pass  # Continue to processing
    elif post_visibility == 'PUBLIC_UNLISTED':
        # Send to all followers (both local and remote), same as PUBLIC
        pass  # Continue to processing  
    elif post_visibility == 'PUBLIC':
        # Send to all followers (both local and remote)
        pass  # Continue to processing
    else:
        return  # For any other unexpected visibilities

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
        print(f"Sending to remote inbox: {inbox_url}")
        print(f"Payload: {payload}")

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
        "type": "entry",
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

# Send an unfollow notification to a remote author
def send_unfollow_to_remote_author(local_author: Author, remote_author: Author) -> bool:
    """
    Notify a remote node that local_author has unfollowed remote_author.
    The remote node will remove Follow(local_author_stub -> remote_author).
    """
    node = get_remote_node_for_author(remote_author)
    if not node:
        return False  # remote node not configured

    inbox_url = inbox_url_for_remote(node, remote_author.url)

    payload = {
        "type": "unfollow",
        "actor": build_minimal_author_dict(local_author),
        "object": build_minimal_author_dict(remote_author),
    }

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
