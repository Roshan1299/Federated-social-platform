"""
connect to remote nodes with url, username, and password.

- When we send posts/comments/likes to that node:
    1. We use the BASE URL to find that node in our database
    2. We get the stored USERNAME + PASSWORD for that node
    3. We log in using Basic Auth (username + password)
    4. We send JSON data to the node's /inbox URL

If the login is correct → the remote node accepts the data.
If the login is wrong → the remote node rejects the data.
"""
import requests
from authors.models import RemoteNode

# Looks up remote node login information
def get_auth_for_base(base_url: str):
    # Normalize the base URL so matching works
    base = base_url.rstrip("/")
    # Look up remote node login info in our DB
    # Checking if we know this node
    try:
        node = RemoteNode.objects.get(base_url__icontains=base, enabled=True)
        # Return username and password if we found this node
        return (node.username, node.password)
    # Return none if not found
    except RemoteNode.DoesNotExist:
        return None


def remote_post(url, payload, base_url):
    # Get username and password for this remote node
    auth = get_auth_for_base(base_url)

    # If we do not have a RemoteNode saved for this BASE URL
    # then we cannot connect to that remote node
    if auth is None:
        return False

    # Try connecting to remote node using url, username, and password
    # url = the inbox URL
    # auth = username and password

    try:
        response = requests.post(
            url,
            json=payload,
            auth=auth,
            timeout=10
        )
        # Connection was successful if we got a 300 > status code
        return response.status_code < 300

    except Exception:
        # Any network or server error means we could not connect
        return False