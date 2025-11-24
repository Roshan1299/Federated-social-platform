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
    """
    POST a JSON payload to a remote node's inbox using Basic Auth.
    Accepts any 2xx response as success.
    Logs FULL diagnostics for debugging cross-node federation.
    """
    auth = get_auth_for_base(base_url)

    if auth is None:
        print(f"❌ No RemoteNode credentials found for base_url={base_url}")
        return False

    print(f"\n🌐 Sending federation request → {url}")
    print(f"   Base URL: {base_url}")
    print(f"   Payload type: {payload.get('type')}")
    print(f"   Auth user: {auth[0]}")

    try:
        resp = requests.post(
            url,
            json=payload,
            auth=auth,
            timeout=10
        )
    except Exception as e:
        print(f"❌ Network error when sending to {url}: {e}")
        return False

    print(f"   ↳ Response status: {resp.status_code}")

    # Log errors with body preview
    if not (200 <= resp.status_code < 300):
        print("   ❌ Non-2xx response from remote node:")
        try:
            print("   ↳ Body preview:", resp.text[:400])
        except Exception:
            print("   ↳ Could not decode body")
        return False

    # Try JSON, but don't require it
    try:
        _ = resp.json()
        print("   ↳ Remote responded with JSON.")
    except ValueError:
        print("   ↳ Remote did NOT return JSON (this is fine).")

    print("   ✅ Federation POST succeeded.\n")
    return True
