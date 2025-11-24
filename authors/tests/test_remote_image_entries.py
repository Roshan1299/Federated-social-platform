import base64

from django.test import TestCase
from django.urls import reverse

from authors.models import Author, Post, Image, RemoteNode, Follow


class RemoteImageEntryTests(TestCase):
    """Ensure entries with images are accessible to connected remote nodes."""

    def setUp(self):
        # Local author who owns the post
        self.local_author = Author.objects.create_user(
            username="local_author",
            password="localpass",
            displayName="Local Author",
        )

        # Remote node service user (represents the remote server connecting to us)
        self.remote_service_user = Author.objects.create_user(
            username="remote_service",
            password="remotepass",
            displayName="Remote Service",
        )
        self.remote_service_user.host = "https://remote-node.example.com"
        self.remote_service_user.url = f"https://remote-node.example.com/api/authors/{self.remote_service_user.id}/"
        self.remote_service_user.save(update_fields=["host", "url"])

        # Remote node configuration (mirrors production setup where credentials are stored)
        self.remote_node = RemoteNode.objects.create(
            name="Remote Node",
            base_url="https://remote-node.example.com",
            username="local_service",
            password="local_service_password",
            enabled=True,
        )

        # Remote author follows the local author to simulate federation awareness
        Follow.objects.create(follower=self.remote_service_user, following=self.local_author)

        # Local author follows back to simulate mutual friendship (optional but realistic)
        Follow.objects.create(follower=self.local_author, following=self.remote_service_user)

        # Create an image and attach it to a post
        self.image_bytes = b"fake-image-bytes"
        image = Image.objects.create(
            file_name="test.png",
            content_type="image/png",
            data=self.image_bytes,
        )

        self.post = Post.objects.create(
            author=self.local_author,
            title="Post with image",
            content="Some content",
            contentType="text/plain",
            visibility="PUBLIC",
            image=image,
        )

    def _basic_auth_header(self, username: str, password: str) -> str:
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {token}"

    def test_remote_node_can_fetch_entry_and_image_binary(self):
        """Remote nodes authenticated via Basic Auth should see entry images."""
        auth_header = self._basic_auth_header("remote_service", "remotepass")

        # Remote node fetches the entry JSON
        entry_url = reverse(
            "authors:single_entry_api",
            kwargs={"author_id": self.local_author.id, "entry_id": self.post.id},
        )
        entry_response = self.client.get(entry_url, HTTP_AUTHORIZATION=auth_header)
        self.assertEqual(entry_response.status_code, 200)

        entry_data = entry_response.json()
        expected_image_url = f"http://testserver{reverse('authors:image_entry_api', kwargs={'author_id': self.local_author.id, 'entry_id': self.post.id})}"
        self.assertEqual(entry_data.get("image"), expected_image_url)

        # Remote node follows the image link to download the binary
        image_url = reverse(
            "authors:image_entry_api",
            kwargs={"author_id": self.local_author.id, "entry_id": self.post.id},
        )
        image_response = self.client.get(image_url, HTTP_AUTHORIZATION=auth_header)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response["Content-Type"], "image/png")
        self.assertEqual(image_response.content, self.image_bytes)
