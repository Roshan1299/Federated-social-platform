"""
Tools for sending data to remote nodes.

Remote requests:
- always return True/False
- ignore unknown or unreachable nodes
"""


import requests
from authors.models import RemoteNode


def get_auth_for_base(base_url: str):
    """
    Look up stored authentication credentials for a remote node.

    Parameters:
        base_url (str): The base URL of the remote node.

    Returns:
        tuple(username, password) if found,
        None if the node is not registered or disabled.
    """
    base = base_url.rstrip("/")  # normalize

    try:
        node = RemoteNode.objects.get(base_url__icontains=base, enabled=True)
        return (node.username, node.password)
    except RemoteNode.DoesNotExist:
        return None


def remote_post(url, payload, base_url):
    """
    Send JSON data to a remote node's inbox using HTTP Basic Auth.

    This function NEVER throws an exception.
    It returns:
        True  → request was sent successfully (status 200–299)
        False → unknown node, network failure, timeout, or bad status code

    Parameters:
        url (str): Remote inbox URL
        payload (dict): Data to send
        base_url (str): Remote node base URL used to find credentials
    """
    auth = get_auth_for_base(base_url)

    if auth is None:
        # We don't know this node → silently fail
        return False

    try:
        response = requests.post(
            url,
            json=payload,
            auth=auth,
            timeout=10
        )
        return response.status_code < 300

    except Exception:
        # Network errors, timeouts, SSL errors, etc.
        return False
