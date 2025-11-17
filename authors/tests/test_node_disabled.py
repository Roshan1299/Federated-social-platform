"""
Django Unit Tests for Node To Node Connections to Ensure Disabled Nodes are Handled Correctly

This test suite validates:
1. Requests from disabled remote nodes are rejected.
2. Requests to disabled remote nodes are not attempted.

Usage:
    python manage.py test authors.tests.test_node_disabled
"""

from django.test import TestCase, Client
from authors.models import Author, RemoteNode, Follow, Post
from authors.utils.federation import get_remote_followers_and_friends
import json
import urllib.parse
import base64

class FromDisabledNodeTests(TestCase):
    def setUp(self):
        # Create a disabled remote node
        self.disabled_node_url = "http://disabled-node.com/"
        self.disabled_node = RemoteNode.objects.create(
            base_url=self.disabled_node_url,
            enabled=False
        )
        
        # Create a local author
        self.local_password = "password123"
        self.local_author = Author.objects.create_user(
            displayName="Local Author",
            host="http://local-node.com/",
            url="http://local-node.com/authors/local-author-id",
            username="localauthor",
            password=self.local_password
        )
        # Create a remote author from the disabled node
        self.remote_password = "password2"
        self.remote_author = Author.objects.create_user(
            displayName="Disabled Author",
            host=self.disabled_node_url,
            url=f"{self.disabled_node_url}authors/disabled-author-id",
            username="remote_author",
            password=self.remote_password
        )
        
        # Create a client to simulate requests
        self.client = Client()
        
    def test_inbox_rejects_disabled_node(self):
        # Simulate a POST request to the inbox from the disabled node
        inbox_url = f"/api/authors/{self.local_author.id}/inbox/"
        payload = {
            "type": "post",
            "id": f"{self.disabled_node_url}posts/123",
            "author": {
                "host": self.disabled_node_url,
                "displayName": self.remote_author.displayName,
                "url": self.remote_author.url,
            },
            "content": "This is a post from a disabled node."
        }
        
        # Basic Auth header for disabled node author
        creds = f"{self.remote_author.username}:{self.remote_password}".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(creds).decode("utf-8")  # Simple encoding for example

        response = self.client.post(
            inbox_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=auth_header, 
            HTTP_HOST=urllib.parse.urlparse(self.disabled_node_url).netloc
        )
        
        # Assert that the response status code indicates rejection (403 Forbidden)
        self.assertEqual(response.status_code, 403)
    
    def test_inbox_accepts_enabled_node(self):
        # Enable the remote node
        self.disabled_node.enabled = True
        self.disabled_node.save()
        
        # Simulate a POST request to the inbox from the now-enabled node
        inbox_url = f"/api/authors/{self.local_author.id}/inbox/"
        payload = {
            "type": "post",
            "id": f"{self.disabled_node_url}posts/123",
            "author": {
                "host": self.disabled_node_url,
                "displayName": self.remote_author.displayName,
                "url": self.remote_author.url,
            },
            "content": "This is a post from an enabled node."
        }
        
        # Basic Auth header for remote author
        creds = f"{self.remote_author.username}:{self.remote_password}".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(creds).decode("utf-8")  # Simple encoding for example

        response = self.client.post(
            inbox_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=auth_header, 
            HTTP_HOST=urllib.parse.urlparse(self.disabled_node_url).netloc
        )
        
        # Assert that the response status code indicates success (201 Created)
        self.assertEqual(response.status_code, 201)

    """ Edge Cases: 
    1. No Auth Header Provided
    2. Invalid Credentials Provided
    3. Missing Node Information
    """
    def test_inbox_no_auth_header(self):
        # Simulate a POST request to the inbox without auth header
        inbox_url = f"/api/authors/{self.local_author.id}/inbox/"
        payload = {
            "type": "post",
            "id": f"{self.disabled_node_url}posts/123",
            "author": {
                "host": self.disabled_node_url,
                "displayName": self.remote_author.displayName,
                "url": self.remote_author.url,
            },
            "content": "This is a post without auth."
        }

        response = self.client.post(
            inbox_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_HOST=urllib.parse.urlparse(self.disabled_node_url).netloc
        )
        
        # Assert that the response status code indicates unauthorized (401 Unauthorized)
        self.assertEqual(response.status_code, 401)
    
    def test_inbox_invalid_credentials(self):
        # Simulate a POST request to the inbox with invalid credentials
        inbox_url = f"/api/authors/{self.local_author.id}/inbox/"
        payload = {
            "type": "post",
            "id": f"{self.disabled_node_url}posts/123",
            "author": {
                "host": self.disabled_node_url,
                "displayName": self.remote_author.displayName,
                "url": self.remote_author.url,
            },
            "content": "This is a post with invalid credentials."
        }
        
        # Basic Auth header with invalid password
        creds = f"{self.remote_author.username}:wrongpassword".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(creds).decode("utf-8")  # Simple encoding for example

        response = self.client.post(
            inbox_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=auth_header, 
            HTTP_HOST=urllib.parse.urlparse(self.disabled_node_url).netloc
        )
        
        # Assert that the response status code indicates unauthorized (401 Unauthorized)
        self.assertEqual(response.status_code, 401)

    def test_inbox_missing_node_info(self):
        # Simulate a POST request to the inbox with missing node info
        inbox_url = f"/api/authors/{self.local_author.id}/inbox/"
        payload = {
            "type": "post",
            "id": f"http://unknown-node.com/posts/123",
            "author": {
                "host": "http://unknown-node.com/",
                "displayName": "Unknown Author",
                "url": "http://unknown-node.com/authors/unknown-author-id",
            },
            "content": "This is a post from an unknown node."
        }
        
        # Basic Auth header for unknown author
        creds = f"unknown_author:somepassword".encode("utf-8")
        auth_header = "Basic " + base64.b64encode(creds).decode("utf-8")  # Simple encoding for example

        response = self.client.post(
            inbox_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=auth_header, 
            HTTP_HOST="unknown-node.com"
        )
        
        # Assert that the response status code indicates unauthorized (401 Unauthorized)
        self.assertEqual(response.status_code, 401)

class ToDisabledNodeTests(TestCase):
    def setUp(self):
        # Create a disabled remote node
        self.disabled_node_url = "http://disabled-node.com/"
        self.disabled_node = RemoteNode.objects.create(
            base_url=self.disabled_node_url,
            enabled=False
        )
        
        # Create a local author
        self.local_password = "password123"
        self.local_author = Author.objects.create_user(
            displayName="Local Author",
            host="http://local-node.com/",
            url="http://local-node.com/authors/local-author-id",
            username="localauthor",
            password=self.local_password
        )

        # Create a remote author from the disabled node
        self.remote_password = "password2"
        self.remote_author = Author.objects.create_user(
            displayName="Disabled Author",
            host=self.disabled_node_url,
            url=f"{self.disabled_node_url}authors/disabled-author-id",
            username="remote_author",
            password=self.remote_password
        )
        # Create a Friend relationship between local and remote author
        Follow.objects.create(
            follower=self.local_author,
            following=self.remote_author
        )
        Follow.objects.create(
            follower=self.remote_author,
            following=self.local_author
        )
        """
        # Create posts by the local author
        self.local_public_post = Post.objects.create(
            author=self.local_author,
            title="Public Post",
            content="This is a public post.",
            contentType="text/plain",
            visibility="PUBLIC"
        )

        self.local_unlisted_post = Post.objects.create(
            author=self.local_author,
            title="Unlisted Post",
            content="This is an unlisted post.",
            contentType="text/plain",
            visibility="PUBLIC_UNLISTED"
        )

        self.local_friends_post = Post.objects.create(
            author=self.local_author,
            title="Test Post",
            content="This is a test post.",
            contentType="text/plain",
            visibility="FRIENDS"
        )
        """
        # Create a client to simulate requests
        self.client = Client()
        
    def test_no_request_to_disabled_node(self):
        # We can't locally test that no request is made to the disabled node
        # but we can test that the disabled node is not included in the remote followers/friends list
        remote_nodes_and_authors = get_remote_followers_and_friends(self.local_author) # returns a list of (node, follower) tuples
        for node, follower in remote_nodes_and_authors:
            self.assertNotEqual(node, self.disabled_node)

    def test_request_to_enabled_node(self):
        # Enable the remote node
        self.disabled_node.enabled = True
        self.disabled_node.save()
        
        # Now the disabled node should appear in the remote followers/friends list
        remote_nodes_and_authors = get_remote_followers_and_friends(self.local_author) # returns a list of (node, follower) tuples
        found = False
        for node, follower in remote_nodes_and_authors:
            if node == self.disabled_node and follower == self.remote_author:
                found = True
                break
        self.assertTrue(found)
