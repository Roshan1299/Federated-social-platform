import logging
import requests
from django.conf import settings
from authors.models import Comment, Post
from authors.inbox_handlers import get_or_create_author

logger = logging.getLogger(__name__)

def sync_remote_comments_for_post(post: Post):
    """
    Fetch comments for this post from the remote node
    and STORE them as local Comment rows.

    After this runs, post.comments.all() will include
    both local and remote comments (as long as the remote
    node exposes them via its /comments endpoint).
    """
    origin = (post.origin or "").rstrip("/")
    if not origin:
        return

    # Typical remote comments endpoint: <post-origin>/comments
    url = origin + "/comments"

    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            logger.warning("Remote comments fetch failed: %s %s", resp.status_code, url)
            return

        data = resp.json()
        items = data.get("items") if isinstance(data, dict) else data

        if not isinstance(items, list):
            return

        for c in items:
            try:
                comment_origin = c.get("id") or c.get("origin")
                if not comment_origin:
                    continue

                # Build / reuse author (stub) for remote commenter
                author_data = c.get("author") or {}
                author = get_or_create_author(author_data)

                content = c.get("comment") or c.get("content", "")

                # Upsert: if we already have this origin, update content; else create
                Comment.objects.update_or_create(
                    origin=comment_origin,
                    defaults={
                        "post": post,
                        "author": author,
                        "content": content,
                    },
                )
            except Exception as inner:
                logger.warning("Failed to sync one remote comment: %s", inner)

    except Exception as e:
        logger.exception("Error syncing remote comments: %s", e)
        return
