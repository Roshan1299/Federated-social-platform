# authors/utils/image_sync.py
import requests
from django.conf import settings
from authors.models import Image

def fetch_and_store_remote_image(remote_url: str):
    """
    Downloads an image from a remote node's /image/<id>/ endpoint
    and stores it in our Image model.
    Returns: Image instance OR None
    """
    try:
        # 1. Download raw image bytes
        r = requests.get(remote_url, timeout=10)

        if r.status_code != 200:
            print(f"⚠️ Failed to fetch remote image {remote_url} (status {r.status_code})")
            return None

        content_type = r.headers.get("Content-Type", "application/octet-stream")

        # 2. Store in local DB
        image = Image.objects.create(
            file_name=remote_url.split("/")[-1],
            content_type=content_type,
            data=r.content,
        )

        print(f"📥 Saved remote image locally as ID {image.id}")
        return image

    except Exception as e:
        print(f"❌ Error fetching remote image {remote_url}: {e}")
        return None
