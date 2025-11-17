# authors/utils/remote_read.py
import requests
from django.conf import settings
from authors.models import Comment, Author

def sync_remote_comments_for_post(post):
    """
    Fetch comments from the remote node for this post
    and store/update them as Comment rows in our DB.
    """

    # 1) Figure out the *remote* post URL

    # Try origin (usual place to store remote URL)
    post_url = (getattr(post, "origin", "") or "").strip()

    # Fallback: some projects store the remote URL in `source`
    if not post_url:
        post_url = (getattr(post, "source", "") or "").strip()

    # As a last resort, construct from author's host + our post.id
    # Adjust this if your remote uses a different pattern.
    if not post_url:
        host = (post.author.host or "").rstrip("/")
        # Typical Social Distribution style, adjust if your remote uses something else:
        post_url = f"{host}/api/authors/{post.author.id}/posts/{post.id}"

    if not post_url.startswith("http"):
        return

    comments_url = post_url.rstrip("/") + "/comments/"

    try:
        resp = requests.get(comments_url, timeout=5)
    except Exception:
        return

    if resp.status_code >= 300:
        return

    try:
        data = resp.json()
    except Exception:
        return

    # Many nodes return: {"type": "comments", "items": [ ... ]}
    items = data.get("items", []) if isinstance(data, dict) else data

    for item in items:
        if not isinstance(item, dict):
            continue

        if item.get("type", "").lower() not in ("comment",):
            continue

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
