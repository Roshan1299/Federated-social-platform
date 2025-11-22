import uuid
import requests
from urllib.parse import urlparse
from django.conf import settings
from authors.models import RemoteNode, Image

def fetch_and_store_remote_image(remote_image_url: str):
    """
    Fetch an image from a remote node using that node's Basic Auth credentials
    and store it in the local Image table.
    Returns the Image instance or None on failure.
    """
    if not remote_image_url:
        print("fetch_and_store_remote_image called with empty URL")
        return None

    try:
        parsed = urlparse(remote_image_url)
    except Exception as e:
        print("Invalid image URL:", remote_image_url, "error:", e)
        return None

    remote_netloc = parsed.netloc.lower()
    print("FETCH IMAGE:", remote_image_url)
    print("  Parsed netloc:", remote_netloc)

    # Find the RemoteNode by host, ignoring scheme (http/https)
    node = None
    for candidate in RemoteNode.objects.filter(enabled=True):
        try:
            c_parsed = urlparse(candidate.base_url)
            c_netloc = c_parsed.netloc.lower()
        except Exception:
            continue

        if c_netloc == remote_netloc:
            node = candidate
            break

    print(
        "  Using RemoteNode:",
        getattr(node, "base_url", None),
        "username:", getattr(node, "username", None),
    )

    # If schemes differ and RemoteNode uses https, upgrade the URL
    if node:
        try:
            node_parsed = urlparse(node.base_url)
            if parsed.scheme != node_parsed.scheme and node_parsed.scheme in ("https", "http"):
                # Replace scheme+netloc at the start of the URL
                original_prefix = f"{parsed.scheme}://{parsed.netloc}"
                new_prefix = f"{node_parsed.scheme}://{node_parsed.netloc}"
                if remote_image_url.startswith(original_prefix):
                    new_url = remote_image_url.replace(original_prefix, new_prefix, 1)
                    print("  Upgrading image URL:", remote_image_url, "→", new_url)
                    remote_image_url = new_url
        except Exception as e:
            print("  ⚠️ Failed to normalize scheme for image URL:", e)

    auth = None
    if node and node.username and node.password:
        auth = (node.username, node.password)

    try:
        resp = requests.get(remote_image_url, auth=auth, timeout=10)
    except Exception as e:
        print("  ❌ Exception while fetching image:", e)
        return None

    print("  ↳ Status:", resp.status_code)
    if resp.status_code != 200:
        try:
            print("  ↳ Body preview:", resp.text[:200])
        except Exception:
            pass
        return None

    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    print("  ↳ Content-Type:", content_type)

    ext = "bin"
    if "png" in content_type:
        ext = "png"
    elif "jpeg" in content_type or "jpg" in content_type:
        ext = "jpg"
    elif "gif" in content_type:
        ext = "gif"

    image = Image.objects.create(
        file_name=f"remote_{uuid.uuid4()}.{ext}",
        content_type=content_type,
        data=resp.content,
    )

    print("  ✅ Stored remote image as Image id:", image.id)
    return image
