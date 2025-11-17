"""
Test suite for [Posting] Node Re-sends Deleted Entries

This test suite validates that when a local author deletes a post, 
the node correctly sends a delete notification to all destinations 
where the post was originally sent (remote followers and friends).

Edge cases covered:
1. Deleted PUBLIC post should trigger delete notification to all remote followers/friends
2. Deleted FRIENDS post should trigger delete notification only to remote friends (mutual follows)
3. Deleted PUBLIC_UNLISTED post should NOT trigger delete notification to remote nodes
4. Remote node failure during delete notification should not break the local deletion functionality
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from authors.models import Author, Post, Follow, RemoteNode
from authors.utils.federation import notify_remote_delete_post
import uuid


User = get_user_model()


@override_settings()
class NodeReSendsDeletedEntriesTest(TestCase):
    """
    Test suite for validating that deleted posts trigger notifications to remote followers and friends
    """

    def setUp(self):
        """Set up test data for the tests"""
        # Create local author (the post creator)
        self.local_author = Author.objects.create(
            username='local_user',
            displayName='Local User',
            host='http://localhost:8000',  # Use the same default as model.save() method
            url='http://localhost:8000/api/authors/12345678-1234-5678-9012-123456789012/'
        )
        
        # Create a remote author who follows local_author
        self.remote_follower = Author.objects.create(
            username='remote_follower',
            displayName='Remote Follower',
            host='http://remote-node.com',
            url='http://remote-node.com/api/authors/87654321-4321-8765-2109-210987654321/'
        )
        
        # Create a remote author who is a friend (mutual follow) with local_author
        self.remote_friend = Author.objects.create(
            username='remote_friend',
            displayName='Remote Friend',
            host='http://another-remote.com',
            url='http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/'
        )
        
        # Create remote nodes for both remote authors
        self.remote_node_1 = RemoteNode.objects.create(
            name='Remote Node 1',
            base_url='http://remote-node.com/',
            username='test_user',
            password='test_pass',
            enabled=True
        )
        
        self.remote_node_2 = RemoteNode.objects.create(
            name='Remote Node 2', 
            base_url='http://another-remote.com/',
            username='test_user2',
            password='test_pass2',
            enabled=True
        )
        
        # Set up the relationships
        # remote_follower follows local_author (one-way follow)
        Follow.objects.create(follower=self.remote_follower, following=self.local_author)
        
        # local_author and remote_friend have mutual follow relationship (friends)
        Follow.objects.create(follower=self.local_author, following=self.remote_friend)
        Follow.objects.create(follower=self.remote_friend, following=self.local_author)
        
        # Create an initial post to delete
        self.post = Post.objects.create(
            title='Original Title',
            content='Original content',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )

    @patch('authors.utils.federation.remote_post')
    def test_deleted_public_post_sends_delete_notification_to_remote_followers_and_friends(self, mock_remote_post):
        """
        EDGE CASE 1: A deleted PUBLIC post should trigger delete notification to all remote followers and friends.
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Mark the post as deleted
        self.post.deleted = True
        self.post.save()
        
        # Call the function directly to trigger sending delete notification
        notify_remote_delete_post(self.post)
        
        # Verify that remote_post was called for both remote follower and friend
        self.assertEqual(mock_remote_post.call_count, 2)
        
        # Check that calls were made with appropriate parameters for delete notification
        calls_made = mock_remote_post.call_args_list
        called_urls = [call[1]['url'] for call in calls_made]
        
        # Should have sent to both remote follower and friend's inbox
        expected_inboxes = [
            'http://remote-node.com/api/authors/87654321-4321-8765-2109-210987654321/inbox',
            'http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/inbox'
        ]
        
        for expected_inbox in expected_inboxes:
            self.assertIn(expected_inbox, called_urls)
        
        # Verify that the payload type is 'delete'
        for call in calls_made:
            payload = call[1]['payload']
            self.assertEqual(payload['type'], 'delete')
            self.assertEqual(payload['id'], self.post.origin)
            self.assertEqual(payload['author'], self.post.author.url)

    @patch('authors.utils.federation.remote_post')
    def test_deleted_friends_post_sends_delete_notification_only_to_remote_friends(self, mock_remote_post):
        """
        EDGE CASE 2: A deleted FRIENDS post should only trigger delete notification to remote friends (mutual followers).
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Create and delete a friends-only post
        friends_post = Post.objects.create(
            title='Friends Only Title',
            content='Friends only content',
            contentType='text/plain',
            visibility='FRIENDS',
            author=self.local_author
        )
        
        # Mark as deleted
        friends_post.deleted = True
        friends_post.save()
        
        # Call the function directly to trigger sending delete notification
        notify_remote_delete_post(friends_post)
        
        # Verify that remote_post was called only for the friend, not the follower
        # (remote_friend is mutual follow = friend, remote_follower is one-way = follower only)
        self.assertEqual(mock_remote_post.call_count, 1)
        
        # Check that it was sent only to the remote friend's inbox
        call_args = mock_remote_post.call_args
        self.assertEqual(call_args[1]['url'], 
                        'http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/inbox')
        
        # Verify payload type
        payload = call_args[1]['payload']
        self.assertEqual(payload['type'], 'delete')

    @patch('authors.utils.federation.remote_post')
    def test_deleted_public_unlisted_post_not_sent_to_remote_nodes(self, mock_remote_post):
        """
        EDGE CASE 3: A deleted PUBLIC_UNLISTED post should NOT trigger delete notification to remote nodes.
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Create and delete a public unlisted post
        unlisted_post = Post.objects.create(
            title='Unlisted Title',
            content='Unlisted content',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            author=self.local_author
        )
        
        # Mark as deleted
        unlisted_post.deleted = True
        unlisted_post.save()
        
        # Call the function directly to trigger sending delete notification
        notify_remote_delete_post(unlisted_post)
        
        # Verify that remote_post was NOT called (unlisted posts should not be pushed even when deleted)
        self.assertEqual(mock_remote_post.call_count, 0)

    @patch('authors.utils.federation.remote_post')
    def test_remote_node_failure_does_not_break_local_deletion(self, mock_remote_post):
        """
        EDGE CASE 4: If remote nodes fail during delete notification, local deletion should still succeed.
        """
        # Mock remote_post to return False (delivery failure)
        mock_remote_post.return_value = False
        
        # Mark the post as deleted
        self.post.deleted = True
        self.post.save()
        
        # Call the function directly to trigger sending delete notification
        notify_remote_delete_post(self.post)
        
        # Verify that remote_post was called but failure didn't break the process
        self.assertGreater(mock_remote_post.call_count, 0)
        
        # Verify that the post is properly marked as deleted locally
        updated_post = Post.objects.get(id=self.post.id)
        self.assertTrue(updated_post.deleted)
        
        # Verify that function didn't raise an exception
        # (if we got here without exception, the test passes)
        self.assertTrue(updated_post.deleted)


class NodeReSendsDeletedEntriesEdgeCasesTest(TestCase):
    """
    Additional edge cases for node sending delete notifications to remote followers and friends
    """

    def setUp(self):
        """Set up test data"""
        self.local_author = Author.objects.create(
            username='test_author',
            displayName='Test Author',
            host='http://localhost:8000',  # Use the same default as model.save() method
            url='http://localhost:8000/api/authors/12345678-1234-5678-9012-123456789012/'
        )

    @patch('authors.utils.federation.remote_post')
    def test_delete_post_with_no_followers_no_remote_calls(self, mock_remote_post):
        """
        Additional edge case: If there are no remote followers or friends, 
        no remote calls should be made when deleting.
        """
        mock_remote_post.return_value = True
        
        # Create a post when author has no followers/friends
        post = Post.objects.create(
            title='Original No Followers Title',
            content='Original no followers content',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )
        
        # Mark as deleted
        post.deleted = True
        post.save()
        
        # Call the notification function
        notify_remote_delete_post(post)
        
        # Should not make any remote calls since there are no followers/friends
        mock_remote_post.assert_not_called()