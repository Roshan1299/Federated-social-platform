import requests
from django.conf import settings
from authors.models import Comment, Author, Like, CommentLike


def _resolve_remote_post_url(post):
    """
    Try to figure out the original REMOTE URL for this post.

    Priority:
    1) post.origin
    2) post.source
    3) construct from author's host + our post.id

    Returns a full http(s) URL or None.
    """
    # Try origin (usual place to store remote URL)
    post_url = (getattr(post, "origin", "") or "").strip()

    # Fallback: some projects store the remote URL in `source`
    if not post_url:
        post_url = (getattr(post, "source", "") or "").strip()

    # As a last resort, construct from author's host + our post.id
    if not post_url:
        host = (post.author.host or "").rstrip("/")
        if not host:
            return None
        post_url = f"{host}/api/authors/{post.author.id}/posts/{post.id}"

    if not post_url.startswith("http"):
        return None

    return post_url


def _safe_get_json(url, timeout=5):
    """
    Helper: GET a URL and parse JSON. Returns Python object or None.
    """
    try:
        resp = requests.get(url, timeout=timeout)
    except Exception:
        return None

    if resp.status_code >= 300:
        return None

    try:
        return resp.json()
    except Exception:
        return None


def sync_remote_comments_for_post(post):
    """
    Fetch comments from the remote node for this post
    and store/update them as Comment rows in our DB.

    Used so local users can see remote authors' comments on a remote post.
    """
    # 1) Figure out the *remote* post URL
    post_url = _resolve_remote_post_url(post)
    if not post_url:
        return

    # Remote comments endpoint: /comments/
    comments_url = post_url.rstrip("/") + "/comments/"

    data = _safe_get_json(comments_url, timeout=5)
    if data is None:
        return

    # Many nodes return: {"type": "comments", "items": [ ... ]}
    items = data.get("items", []) if isinstance(data, dict) else data

    for item in items:
        # Ignore anything that is not a dict
        if not isinstance(item, dict):
            continue

        # Only process "comment" type
        if item.get("type", "").lower() not in ("comment",):
            continue

        # Remote unique ID for this comment
        comment_id = item.get("id")
        if not comment_id:
            continue

        author_data = item.get("author") or {}
        content = item.get("comment") or item.get("content", "") or ""

        # 3) Get or create Author for the remote commenter
        author_url = author_data.get("id") or author_data.get("url")
        if not author_url:
            continue

        host = (author_data.get("host") or "").strip()
        display_name = (author_data.get("displayName") or "Remote Author").strip()
        username_guess = f"remote_{display_name[:10]}" if display_name else "remote_user"

        author_obj, _ = Author.objects.get_or_create(
            url=author_url,
            defaults={
                "displayName": display_name or "Remote Author",
                "host": host,
                "username": username_guess,
            },
        )

        defaults = {
            "post": post,
            "author": author_obj,
            "content": content,
        }

        # Use `origin` to dedupe by remote ID
        Comment.objects.update_or_create(
            origin=comment_id,
            defaults=defaults,
        )


def sync_remote_likes_for_post(post):
    """
    Fetch likes on this post from the remote node and store/update them
    as Like rows in our DB.

    Goal: local users see like counts on a REMOTE post.
    """
    post_url = _resolve_remote_post_url(post)
    if not post_url:
        return

    # Typical endpoint: /likes/
    likes_url = post_url.rstrip("/") + "/likes/"

    data = _safe_get_json(likes_url, timeout=5)
    if data is None:
        return

    # Many nodes: {"type": "likes", "items": [ ... ]}
    items = data.get("items", []) if isinstance(data, dict) else data

    for item in items:
        if not isinstance(item, dict):
            continue

        like_type = item.get("type", "").lower()
        if like_type not in ("like",):
            continue

        like_id = item.get("id")
        if not like_id:
            continue

        author_data = item.get("author") or {}
        author_url = author_data.get("id") or author_data.get("url")
        if not author_url:
            continue

        host = (author_data.get("host") or "").strip()
        display_name = (author_data.get("displayName") or "Remote Author").strip()
        username_guess = f"remote_{display_name[:10]}" if display_name else "remote_user"

        author_obj, _ = Author.objects.get_or_create(
            url=author_url,
            defaults={
                "displayName": display_name or "Remote Author",
                "host": host,
                "username": username_guess,
            },
        )

        defaults = {
            "post": post,
            "author": author_obj,
        }

        # Use origin on Like model to dedupe by remote like ID
        Like.objects.update_or_create(
            origin=like_id,
            defaults=defaults,
        )


def sync_remote_comment_likes_for_post(post):
    """
    For each COMMENT on this post, if that comment is remote (has a remote origin),
    fetch its likes from the remote node and store/update them as CommentLike rows.

    Goal: local users see comment-like counts for remote comments too.
    """
    local_host = (getattr(settings, "BASE_URL", "") or "").rstrip("/")

    # We look at ALL comments we currently have on this post (local + remote)
    comments = Comment.objects.filter(post=post)

    for comment in comments:
        comment_origin = (comment.origin or "").strip()
        if not comment_origin.startswith("http"):
            # Probably a local-only comment, or no remote ID → skip
            continue

        comment_host = (comment.author.host or "").rstrip("/")
        if not comment_host or comment_host == local_host:
            # Comment lives on our node, not a remote node → skip
            continue

        # Typical endpoint: comment_origin + "/likes/"
        likes_url = comment_origin.rstrip("/") + "/likes/"

        data = _safe_get_json(likes_url, timeout=5)
        if data is None:
            continue

        items = data.get("items", []) if isinstance(data, dict) else data

        for item in items:
            if not isinstance(item, dict):
                continue

            like_type = item.get("type", "").lower()
            if like_type not in ("like",):
                continue

            like_id = item.get("id")
            if not like_id:
                continue

            author_data = item.get("author") or {}
            author_url = author_data.get("id") or author_data.get("url")
            if not author_url:
                continue

            host = (author_data.get("host") or "").strip()
            display_name = (author_data.get("displayName") or "Remote Author").strip()
            username_guess = f"remote_{display_name[:10]}" if display_name else "remote_user"

            author_obj, _ = Author.objects.get_or_create(
                url=author_url,
                defaults={
                    "displayName": display_name or "Remote Author",
                    "host": host,
                    "username": username_guess,
                },
            )

            defaults = {
                "comment": comment,
                "author": author_obj,
            }

            CommentLike.objects.update_or_create(
                origin=like_id,
                defaults=defaults,
            )
