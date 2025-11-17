"""
TEST SUITE: Connect to Remote Nodes with URL, Username, and Password (Part 3–5)

1. RemoteNode Authentication Lookup (get_auth_for_base)
   - Normal case: successfully finds correct username/password.
   - Handles URL normalization (trailing slashes).
   - Edge case: base URL not registered → returns None.
   - Edge case: RemoteNode exists but enabled=False → also returns None.

2. Remote POST Delivery (remote_post)
   - Success case: POST is sent with proper Basic Auth and returns True.
   - Edge case: unknown base URL → no HTTP request is sent; returns False.
   - Edge case: network failure (timeout/connection error/etc.) → returns False.

"""

from django.test import TestCase
from unittest.mock import patch, MagicMock

from authors.models import RemoteNode
from authors.utils.nodes import get_auth_for_base, remote_post


class RemoteNodeConnectionTests(TestCase):
    """
    Tests for: Connect to Remote Nodes with URL, Username, and Password
    (Part 3–5 only)
    """

    def setUp(self):
        # Common remote node we can reuse in tests
        self.node = RemoteNode.objects.create(
            name="Team Green",
            base_url="https://team-green.herokuapp.com/",
            username="service_user",
            password="secret_pass",
            enabled=True,
        )

    # ---------------------------
    # get_auth_for_base tests
    # ---------------------------

    def test_get_auth_for_base_normalizes_trailing_slash(self):
        """Should match the node even if caller omits trailing slash."""
        auth = get_auth_for_base("https://team-green.herokuapp.com")
        self.assertEqual(auth, ("service_user", "secret_pass"))

    def test_get_auth_for_base_returns_none_for_unknown_node(self):
        """Unknown base URL → cannot authenticate → returns None."""
        auth = get_auth_for_base("https://unknown-node.example.com")
        self.assertIsNone(auth)

    def test_get_auth_for_base_ignores_disabled_node(self):
        """If node.enabled=False → treat as nonexistent."""
        self.node.enabled = False
        self.node.save()

        auth = get_auth_for_base("https://team-green.herokuapp.com")
        self.assertIsNone(auth)

    # ---------------------------
    # remote_post tests
    # ---------------------------

    @patch("authors.utils.nodes.requests.post")
    def test_remote_post_success(self, mock_post):
        """Correct credentials + success response → returns True."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        inbox_url = "https://team-green.herokuapp.com/api/authors/123/inbox"
        payload = {"type": "test"}

        ok = remote_post(
            url=inbox_url,
            payload=payload,
            base_url="https://team-green.herokuapp.com/",
        )

        self.assertTrue(ok)
        mock_post.assert_called_once_with(
            inbox_url,
            json=payload,
            auth=("service_user", "secret_pass"),
            timeout=10,
        )

    @patch("authors.utils.nodes.requests.post")
    def test_remote_post_unknown_base_returns_false_and_does_not_call_requests(self, mock_post):
        """Unknown base URL → no request should be attempted → returns False."""
        inbox_url = "https://unknown-node.example.com/api/authors/999/inbox"
        payload = {"type": "test"}

        ok = remote_post(
            url=inbox_url,
            payload=payload,
            base_url="https://unknown-node.example.com",
        )

        self.assertFalse(ok)
        mock_post.assert_not_called()

    @patch("authors.utils.nodes.requests.post")
    def test_remote_post_handles_network_errors(self, mock_post):
        """requests.post throws exception → remote_post must catch and return False."""
        mock_post.side_effect = Exception("network failure")

        inbox_url = "https://team-green.herokuapp.com/api/authors/123/inbox"
        payload = {"type": "test"}

        ok = remote_post(
            url=inbox_url,
            payload=payload,
            base_url="https://team-green.herokuapp.com",
        )

        self.assertFalse(ok)
        mock_post.assert_called_once()
