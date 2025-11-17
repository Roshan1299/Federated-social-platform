import base64
from django.conf import settings


def authenticate_node_request(request):
    """
    Validate Basic Auth for remote nodes.
    Returns True if authenticated, False otherwise.
    """

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        return False

    try:
        encoded = auth_header.split(" ")[1]
        decoded = base64.b64decode(encoded).decode()
        username, password = decoded.split(":", 1)
    except Exception:
        return False

    # match with remote nodes defined in settings
    for node in getattr(settings, "REMOTE_NODES", []):
        if (
            username == node.get("service_username")
            and password == node.get("service_password")
        ):
            return True

    return False
