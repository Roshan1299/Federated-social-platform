# authors/utils/remote_read.py
import requests
from django.conf import settings
from authors.models import Comment, Author

def sync_remote_comments_for_post(post):
    """
    Fetch comments from the remote node for this post
    and store/update them as Comment rows in our DB.
    """
    post_origin = post.origin          # remote post URL
    if not post_origin:
        return

    # Example: remote comments endpoint (adjust to your spec)
    comments_url = f"{post_origin.rstrip('/')}/comments"

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

    # Adjust this according to the remote JSON format
    items = data.get("items", []) if isinstance(data, dict) else data

    for item in items:
        # Skip if wrong type
        if item.get("type") != "comment":
            continue

        comment_id = item.get("id")
        author_data = item.get("author") or {}
        content = item.get("comment") or item.get("content", "")
        published = item.get("published")

        if not comment_id:
            continue

        # 1) Get or create remote Author
        author_url = author_data.get("id") or author_data.get("url")
        host = author_data.get("host") or ""
        display_name = author_data.get("displayName") or "Remote Author"

        if not author_url:
            continue

        author_obj, _ = Author.objects.get_or_create(
            url=author_url,
            defaults={
                "displayName": display_name,
                "host": host,
                "username": f"remote_{display_name[:10]}",
            },
        )

        # 2) Get or create Comment by origin (remote ID)
        defaults = {
            "post": post,
            "author": author_obj,
            "content": content,
        }
        if published:
            defaults["created_at"] = published  # if your field allows raw string, else parse

        Comment.objects.update_or_create(
            origin=comment_id,
            defaults=defaults,
        )
