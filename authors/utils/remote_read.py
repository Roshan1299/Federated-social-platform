import requests
from authors.utils.nodes import get_auth_for_base 


def fetch_remote_comments_for_post(post):
    # If we don't know where this post came from, give up
    origin = (post.origin or "").rstrip("/")
    if not origin:
        return []

    # Extract base host from the post author
    host = (post.author.host or "").rstrip("/")
    if not host:
        return []

    # Many 404 spec teams use: <post-origin>/comments
    comments_url = origin + "/comments"

    # Get username/password for that host from RemoteNode using your existing helper
    auth = get_auth_for_base(host)

    try:
        resp = requests.get(comments_url, auth=auth, timeout=5)
    except Exception:
        # Remote node down, wrong URL, network error, etc.
        return []

    if resp.status_code >= 300:
        # Remote node returned error, do nothing
        return []

    try:
        data = resp.json()
    except ValueError:
        return []

    # Different teams structure output differently:
    # Some use {"type": "comments", "items": [...]}
    # Some use {"comments": [...]}
    items = data.get("items") or data.get("comments") or []

    result = []
    for item in items:
        author = item.get("author", {}) or {}
        result.append({
            "id": item.get("id") or item.get("origin") or "",
            "text": item.get("comment") or item.get("content") or "",
            "author_display": author.get("displayName") or author.get("id") or "",
            "published": item.get("published") or "",
        })
    return result
