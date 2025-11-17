import requests
from urllib.parse import urlparse

from authors.utils.nodes import get_auth_for_base


def _get_base_url_from_origin(origin: str) -> str:
    """
    Take a full origin URL and return the base node URL.

    Example:
      origin = "https://team-green.herokuapp.com/api/authors/123/posts/abc/"
      -> "https://team-green.herokuapp.com"
    """
    if not origin:
        return ""

    parsed = urlparse(origin)
    if not parsed.scheme or not parsed.netloc:
        return ""

    return f"{parsed.scheme}://{parsed.netloc}"


def fetch_remote_comments_for_post(post):
    """
    Read-only helper: fetch comments directly from the REMOTE node.

    - Uses post.origin to build "<origin>/comments/"
    - Looks up username/password for that remote node
    - Does GET with Basic Auth
    - Returns a *simple list of dicts* ready for the template

    This does NOT write to our database.
    """
    origin = (post.origin or "").strip()
    if not origin:
        return []

    # Remote endpoint we expect:
    #   GET <post.origin>/comments/
    comments_url = origin.rstrip("/") + "/comments/"

    # Figure out which remote node this origin belongs to
    base_url = _get_base_url_from_origin(origin)
    if not base_url:
        return []

    # Get (username, password) for this remote node
    auth = get_auth_for_base(base_url)

    try:
        resp = requests.get(
            comments_url,
            auth=auth,      # can be None; requests handles that
            timeout=10,
        )
    except Exception:
        # Network / DNS / SSL / timeout issues
        return []

    if resp.status_code >= 300:
        return []

    try:
        data = resp.json()
    except Exception:
        return []

    # Most 404 starter code uses something like:
    # { "type": "comments", "items": [ ... ] }
    items = data.get("items") or data.get("comments") or []

    normalized = []
    for item in items:
        author_obj = item.get("author", {}) or {}

        normalized.append({
            "author_display": author_obj.get("displayName") or "Remote Author",
            "author_url": author_obj.get("id") or author_obj.get("url") or "",
            "content": item.get("comment") or item.get("content", ""),
            "published": item.get("published") or "",
        })

    return normalized
