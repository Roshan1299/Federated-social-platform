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
        print("🌐 fetch_and_store_remote_image called with empty URL")
        return None

    try:
        parsed = urlparse(remote_image_url)
    except Exception as e:
        print("🌐 Invalid image URL:", remote_image_url, "error:", e)
        return None

    remote_host = f"{parsed.scheme}://{parsed.netloc}".rstrip("/") + "/"

    # Find the RemoteNode for this host
    node = (
        RemoteNode.objects
        .filter(base_url__startswith=remote_host, enabled=True)
        .order_by("id")
        .first()
    )

    print("🌐 FETCH IMAGE:", remote_image_url)
    print("  Resolved remote_host:", remote_host)
    print("  Using RemoteNode:",
          node.base_url if node else None,
          "username:", getattr(node, "username", None))

    auth = None
    if node and node.username and node.password:
        auth = (node.username, node.password)

    try:
        resp = requests.get(remote_image_url, auth=auth, timeout=10)
    except Exception as e:
        print("  ❌ Exception while fetching image:", e)
        return None

    print("  ↳ Status:", resp.status_code)
    # If it's not 200, log a short preview of the body
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
