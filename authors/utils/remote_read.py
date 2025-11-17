import requests
from urllib.parse import urlparse
from django.conf import settings

from authors.utils.nodes import get_auth_for_base
from authors.models import Post


# Helper: pull "https://host" part from a full URL
def _get_host_from_url(url: str) -> str:
    # Try to parse URL into parts
    parsed = urlparse(url or "")
    if parsed.scheme and parsed.netloc:
        # Rebuild just "scheme://host"
        return f"{parsed.scheme}://{parsed.netloc}"
    return ""


# Fetch comments from a REMOTE node for this post (READ ONLY)
def fetch_remote_comments_for_post(post: Post):
    # If post has no origin/source URL, we can't contact remote
    origin = post.origin or post.source
    if not origin:
        return []

    # Build the remote /comments URL for this post
    # Example:
    #   origin:  https://their-node/api/authors/123/posts/abc
    #   we call: https://their-node/api/authors/123/posts/abc/comments
    base = origin.rstrip("/")
    comments_url = base + "/comments"

    # Figure out which host to use for auth
    # Prefer post.author.host; if empty, derive from origin URL
    host = (post.author.host or "").rstrip("/")
    if not host:
        host = _get_host_from_url(origin)

    # Ask nodes.py for username/password for this remote node
    auth = None
    if host:
        auth = get_auth_for_base(host)

    # Use timeout from settings if present, otherwise 10 seconds
    timeout = getattr(settings, "REQUESTS_TIMEOUT", 10)

    try:
        # Connect to remote node and READ its comments for this post
        # If auth is None → send request without login
        response = requests.get(
            comments_url,
            auth=auth,
            timeout=timeout,
        )

        # If remote node gives error (>= 300), just return empty list
        if response.status_code >= 300:
            return []

        data = response.json()

    except Exception:
        # Any network / JSON error → act like there are no remote comments
        return []

    # Some nodes wrap comments in {"items": [...]}, some just give a list
    if isinstance(data, dict):
        items = data.get("items", [])
    elif isinstance(data, list):
        items = data
    else:
        items = []

    if not isinstance(items, list):
        return []

    normalized = []

    for c in items:
        if not isinstance(c, dict):
            continue

        author_data = c.get("author", {}) or {}

        # Try to pick a reasonable display name for the author
        author_display = (
            author_data.get("displayName")
            or author_data.get("github")
            or author_data.get("id")
            or "remote user"
        )

        # Build a small, clean object for templates
        normalized.append({
            # remote comment id / origin
            "id": c.get("id") or c.get("origin"),
            # text of the comment
            "content": c.get("comment") or c.get("content", ""),
            # published timestamp string
            "published": c.get("published"),
            # human-readable author name
            "author_display": author_display,
            # raw author object in case you want more data later
            "author": author_data,
        })

    return normalized
