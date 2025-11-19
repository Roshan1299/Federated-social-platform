import requests
from authors.models import Image

def fetch_and_store_remote_image(url: str):
    """Download an image from a remote node and save it locally."""
    try:
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            print(f"⚠️ Failed to fetch remote image: {resp.status_code}")
            return None

        content_type = resp.headers.get("Content-Type", "application/octet-stream")
        file_name = url.strip("/").split("/")[-1]

        image = Image.objects.create(
            file_name=file_name,
            content_type=content_type,
            data=resp.content
        )
        return image

    except Exception as e:
        print(f"❌ Error downloading remote image: {e}")
        return None
