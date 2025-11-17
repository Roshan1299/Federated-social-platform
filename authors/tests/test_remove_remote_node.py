"""
Unit Tests for Remote Node Removal

Tests:
1. Node admin can delete a remote node
2. After deletion, content is no longer shared with that node
3. Followers from deleted node are no longer considered for content distribution
4. Non-admin users cannot delete remote nodes
5. Deleting a node doesn't break existing follow relationships (they remain in DB)

Usage:
    python manage.py test authors.tests.test_remove_remote_node
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from authors.models import Author, RemoteNode, Follow, Post
from authors.utils.federation import get_remote_followers_and_friends
from django.urls import reverse
import json

Author = get_user_model()


class RemoveRemoteNodeTests(TestCase):
    """Test suite for removing remote nodes"""

    def setUp(self):
        """Set up test data"""
        # Create a superuser (node admin)
        self.admin = Author.objects.create_superuser(
            username='admin',
            password='adminpass123',
            displayName='Node Admin',
            host='http://localhost:8000/',
            url='http://localhost:8000/api/authors/admin-id'
        )

        # Create a regular user (not admin)
        self.regular_user = Author.objects.create_user(
            username='regularuser',
            password='userpass123',
            displayName='Regular User',
            host='http://localhost:8000/',
            url='http://localhost:8000/api/authors/regular-id'
        )

        # Create remote nodes
        self.remote_node1 = RemoteNode.objects.create(
            name='Team Blue',
            base_url='https://team-blue.herokuapp.com/',
            username='node_user',
            password='node_pass',
            enabled=True
        )

        self.remote_node2 = RemoteNode.objects.create(
            name='Team Green',
            base_url='https://team-green.herokuapp.com/',
            username='node_user2',
            password='node_pass2',
            enabled=True
        )

        # Create remote authors on these nodes
        self.remote_author1 = Author.objects.create_user(
            username='blueauthor',
            password='pass123',
            displayName='Blue Author',
            host='https://team-blue.herokuapp.com/',
            url='https://team-blue.herokuapp.com/api/authors/blue-id'
        )

        self.remote_author2 = Author.objects.create_user(
            username='greenauthor',
            password='pass456',
            displayName='Green Author',
            host='https://team-green.herokuapp.com/',
            url='https://team-green.herokuapp.com/api/authors/green-id'
        )

        # Create follow relationships
        # Remote author 1 follows admin
        Follow.objects.create(follower=self.remote_author1, following=self.admin)
        # Remote author 2 follows admin
        Follow.objects.create(follower=self.remote_author2, following=self.admin)

        # Create test client
        self.client = Client()

    def test_admin_can_access_remote_nodes_list(self):
        """Test that admin can view the remote nodes list"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('authors:remote_nodes_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team Blue')
        self.assertContains(response, 'Team Green')

    def test_admin_can_delete_remote_node(self):
        """Test that node admin can delete a remote node"""
        self.client.login(username='admin', password='adminpass123')

        # Get initial count
        initial_count = RemoteNode.objects.count()
        self.assertEqual(initial_count, 2)

        # Delete remote node 1
        response = self.client.post(
            reverse('authors:delete_remote_node', kwargs={'node_id': self.remote_node1.id})
        )

        # Should redirect to list view
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('authors:remote_nodes_list'))

        # Verify node is deleted
        self.assertEqual(RemoteNode.objects.count(), 1)
        self.assertFalse(RemoteNode.objects.filter(id=self.remote_node1.id).exists())
        self.assertTrue(RemoteNode.objects.filter(id=self.remote_node2.id).exists())

    def test_non_admin_cannot_delete_remote_node(self):
        """Test that regular users cannot delete remote nodes"""
        self.client.login(username='regularuser', password='userpass123')

        initial_count = RemoteNode.objects.count()

        # Attempt to delete remote node
        response = self.client.post(
            reverse('authors:delete_remote_node', kwargs={'node_id': self.remote_node1.id})
        )

        # Should redirect (not allowed)
        self.assertEqual(response.status_code, 302)

        # Node should still exist
        self.assertEqual(RemoteNode.objects.count(), initial_count)
        self.assertTrue(RemoteNode.objects.filter(id=self.remote_node1.id).exists())

    def test_deleted_node_not_included_in_federation(self):
        """Test that after deletion, the node is not included in content distribution"""
        # Before deletion - both remote followers should be included
        followers_and_friends = get_remote_followers_and_friends(self.admin)
        self.assertEqual(len(followers_and_friends), 2)

        # Delete remote node 1
        self.remote_node1.delete()

        # After deletion - only remote author from node 2 should be included
        followers_and_friends = get_remote_followers_and_friends(self.admin)
        self.assertEqual(len(followers_and_friends), 1)

        # Verify the remaining follower is from node 2
        node, author = followers_and_friends[0]
        self.assertEqual(node.id, self.remote_node2.id)
        self.assertEqual(author.id, self.remote_author2.id)

    def test_follow_relationships_persist_after_node_deletion(self):
        """Test that follow relationships remain in DB after node deletion"""
        # Initial follow count
        initial_follow_count = Follow.objects.count()
        self.assertEqual(initial_follow_count, 2)

        # Delete remote node 1
        self.remote_node1.delete()

        # Follow relationships should still exist
        self.assertEqual(Follow.objects.count(), initial_follow_count)
        self.assertTrue(
            Follow.objects.filter(
                follower=self.remote_author1,
                following=self.admin
            ).exists()
        )

    def test_disabled_then_deleted_node_workflow(self):
        """Test the workflow of disabling then deleting a node"""
        self.client.login(username='admin', password='adminpass123')

        # First, disable the node
        self.remote_node1.enabled = False
        self.remote_node1.save()

        # Verify it's not included in federation when disabled
        followers_and_friends = get_remote_followers_and_friends(self.admin)
        self.assertEqual(len(followers_and_friends), 1)  # Only node 2

        # Then delete it
        response = self.client.post(
            reverse('authors:delete_remote_node', kwargs={'node_id': self.remote_node1.id})
        )
        self.assertEqual(response.status_code, 302)

        # Verify it's gone
        self.assertFalse(RemoteNode.objects.filter(id=self.remote_node1.id).exists())

    def test_delete_nonexistent_node_shows_error(self):
        """Test that deleting a non-existent node shows an error message"""
        self.client.login(username='admin', password='adminpass123')

        # Try to delete a node with an ID that doesn't exist
        response = self.client.post(
            reverse('authors:delete_remote_node', kwargs={'node_id': 99999}),
            follow=True
        )

        # Should redirect and show error message
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('not found' in str(m).lower() for m in messages))

    def test_remote_nodes_list_shows_remove_button(self):
        """Test that the remote nodes list displays remove buttons"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('authors:remote_nodes_list'))

        # Check for remove button/form
        self.assertContains(response, 'Remove')
        self.assertContains(response, reverse('authors:delete_remote_node', kwargs={'node_id': self.remote_node1.id}))

    def test_remove_node_confirmation_dialog(self):
        """Test that the template includes confirmation for node removal"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('authors:remote_nodes_list'))

        # Check for confirmation dialog
        self.assertContains(response, 'Are you sure')
        self.assertContains(response, 'onsubmit')


class StopSharingAfterRemovalTests(TestCase):
    """Test that content sharing stops after node removal"""

    def setUp(self):
        """Set up test data"""
        # Create local author
        self.local_author = Author.objects.create_user(
            username='localauthor',
            password='pass123',
            displayName='Local Author',
            host='http://localhost:8000/',
            url='http://localhost:8000/api/authors/local-id'
        )

        # Create remote node
        self.remote_node = RemoteNode.objects.create(
            name='Remote Node',
            base_url='https://remote.example.com/',
            username='remote_user',
            password='remote_pass',
            enabled=True
        )

        # Create remote author
        self.remote_author = Author.objects.create_user(
            username='remoteauthor',
            password='pass456',
            displayName='Remote Author',
            host='https://remote.example.com/',
            url='https://remote.example.com/api/authors/remote-id'
        )

        # Remote author follows local author
        Follow.objects.create(follower=self.remote_author, following=self.local_author)

    def test_get_remote_followers_excludes_deleted_node(self):
        """Test that get_remote_followers_and_friends excludes authors from deleted nodes"""
        # Before deletion
        followers = get_remote_followers_and_friends(self.local_author)
        self.assertEqual(len(followers), 1)

        # Delete the remote node
        self.remote_node.delete()

        # After deletion - should be empty
        followers = get_remote_followers_and_friends(self.local_author)
        self.assertEqual(len(followers), 0)

    def test_new_posts_not_shared_after_node_removal(self):
        """Test that new posts are not shared with removed nodes"""
        # Create a post
        post = Post.objects.create(
            author=self.local_author,
            title='Test Post',
            content='This is a test post',
            visibility='PUBLIC'
        )

        # Before deletion - remote follower should be included
        followers = get_remote_followers_and_friends(self.local_author)
        self.assertEqual(len(followers), 1)

        # Delete the node
        self.remote_node.delete()

        # After deletion - no remote followers
        followers = get_remote_followers_and_friends(self.local_author)
        self.assertEqual(len(followers), 0)

        # This ensures that when notify_remote_new_post is called,
        # it won't send to the deleted node


class RemoteNodeDeletionEdgeCasesTests(TestCase):
    """Test edge cases for remote node deletion"""

    def setUp(self):
        """Set up test data"""
        self.admin = Author.objects.create_superuser(
            username='admin',
            password='adminpass123',
            displayName='Admin',
            host='http://localhost:8000/',
            url='http://localhost:8000/api/authors/admin-id'
        )
        self.client = Client()

    def test_delete_node_with_no_followers(self):
        """Test deleting a node that has no associated followers"""
        node = RemoteNode.objects.create(
            name='Empty Node',
            base_url='https://empty.example.com/',
            username='user',
            password='pass',
            enabled=True
        )

        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('authors:delete_remote_node', kwargs={'node_id': node.id})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(RemoteNode.objects.filter(id=node.id).exists())

    def test_delete_already_disabled_node(self):
        """Test deleting a node that is already disabled"""
        node = RemoteNode.objects.create(
            name='Disabled Node',
            base_url='https://disabled.example.com/',
            username='user',
            password='pass',
            enabled=False
        )

        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(
            reverse('authors:delete_remote_node', kwargs={'node_id': node.id})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(RemoteNode.objects.filter(id=node.id).exists())
