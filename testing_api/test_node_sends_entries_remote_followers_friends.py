"""
Test suite for [Posting] Node Sends Entries to Remote Followers and Friends

This test suite validates that when a local author creates a post, 
the node correctly sends it to remote followers and friends.

Edge cases covered:
1. Post with PUBLIC visibility should be sent to all remote followers/friends
2. Post with FRIENDS visibility should be sent only to remote friends (mutual follows)
3. Post with PUBLIC_UNLISTED visibility should NOT be sent to remote nodes
4. Remote node failure should not break the local posting functionality
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from authors.models import Author, Post, Follow, RemoteNode
from authors.utils.federation import notify_remote_new_post
import uuid


User = get_user_model()


@override_settings()
class NodeSendsEntriesToRemoteFollowersFriendsTest(TestCase):
    """
    Test suite for validating that posts are correctly sent to remote followers and friends
    """

    def setUp(self):
        """Set up test data for the tests"""
        # Create local author (the post creator)
        # Using the same fallback as in the actual model code
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
        
        # Create remote nodes for both remote authors - make sure base_url matches author host exactly
        # The host field in Author does not have a trailing slash, but RemoteNode.base_url does
        self.remote_node_1 = RemoteNode.objects.create(
            name='Remote Node 1',
            base_url='http://remote-node.com/',  # Note: has trailing slash like in forms.py
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
        
        # Create a post to test with
        self.post = Post.objects.create(
            title='Test Post',
            content='This is a test post',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )

    @patch('authors.utils.federation.remote_post')
    def test_public_post_sent_to_remote_followers_and_friends(self, mock_remote_post):
        """
        EDGE CASE 1: A PUBLIC post should be sent to all remote followers and friends.
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Create the post 
        public_post = Post.objects.create(
            title='Public Post',
            content='This is a public post',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )
        
        # Call the function directly to trigger sending
        notify_remote_new_post(public_post)
        
        # Verify that remote_post was called for both remote follower and friend
        # There are 2 remote followers/friends, so should be called twice
        self.assertEqual(mock_remote_post.call_count, 2,
                        f"Expected 2 calls to remote_post, but got {mock_remote_post.call_count}. "
                        f"Check that remote followers/friends are correctly identified.")
        
        # Check that calls were made with appropriate parameters
        calls_made = mock_remote_post.call_args_list
        called_urls = [call[1]['url'] for call in calls_made]
        
        # Should have sent to both remote follower and friend's inbox
        expected_inboxes = [
            'http://remote-node.com/api/authors/87654321-4321-8765-2109-210987654321/inbox',
            'http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/inbox'
        ]
        
        for expected_inbox in expected_inboxes:
            self.assertIn(expected_inbox, called_urls,
                         f"Expected inbox URL {expected_inbox} was not found in calls: {called_urls}")

    @patch('authors.utils.federation.remote_post')
    def test_friends_post_sent_only_to_remote_friends(self, mock_remote_post):
        """
        EDGE CASE 2: A FRIENDS post should only be sent to remote friends (mutual followers).
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Create a friends-only post
        friends_post = Post.objects.create(
            title='Friends Only Post',
            content='This is only for friends',
            contentType='text/plain',
            visibility='FRIENDS',
            author=self.local_author
        )
        
        # Call the function directly to trigger sending
        notify_remote_new_post(friends_post)
        
        # Verify that remote_post was called only for the friend, not the follower
        # (remote_friend is mutual follow = friend, remote_follower is one-way = follower only)
        self.assertEqual(mock_remote_post.call_count, 1)
        
        # Check that it was sent only to the remote friend's inbox
        call_args = mock_remote_post.call_args
        self.assertEqual(call_args[1]['url'], 
                        'http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/inbox')

    @patch('authors.utils.federation.remote_post')
    def test_public_unlisted_post_sent_to_remote_followers_and_friends(self, mock_remote_post):
        """
        EDGE CASE 3: A PUBLIC_UNLISTED post should be sent to remote followers and friends, similar to PUBLIC posts.
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Create a public unlisted post
        unlisted_post = Post.objects.create(
            title='Public Unlisted Post',
            content='This unlisted post should be sent to remote followers and friends',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            author=self.local_author
        )
        
        # Call the function directly to trigger sending
        notify_remote_new_post(unlisted_post)
        
        # Verify that remote_post was called for both remote follower and friend (like PUBLIC posts)
        self.assertEqual(mock_remote_post.call_count, 2,
                        f"Expected 2 calls to remote_post, but got {mock_remote_post.call_count}. "
                        f"PUBLIC_UNLISTED posts should be sent to all remote followers and friends.")
        
        # Check that calls were made with appropriate parameters
        calls_made = mock_remote_post.call_args_list
        called_urls = [call[1]['url'] for call in calls_made]
        
        # Should have sent to both remote follower and friend's inbox
        expected_inboxes = [
            'http://remote-node.com/api/authors/87654321-4321-8765-2109-210987654321/inbox',
            'http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/inbox'
        ]
        
        for expected_inbox in expected_inboxes:
            self.assertIn(expected_inbox, called_urls,
                         f"Expected inbox URL {expected_inbox} was not found in calls: {called_urls}")

    @patch('authors.utils.federation.remote_post')
    def test_remote_node_failure_does_not_break_local_posting(self, mock_remote_post):
        """
        EDGE CASE 4: If remote nodes fail during post distribution, local posting should still succeed.
        """
        # Mock remote_post to return False (delivery failure)
        mock_remote_post.return_value = False
        
        # Create a public post
        failed_post = Post.objects.create(
            title='Post with Remote Failure',
            content='This post should still be created locally even if remote delivery fails',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )
        
        # Call the function directly to trigger sending
        notify_remote_new_post(failed_post)
        
        # Verify that remote_post was called but failure didn't break the process
        self.assertGreater(mock_remote_post.call_count, 0)
        
        # Verify that the post still exists locally
        self.assertTrue(Post.objects.filter(id=failed_post.id).exists())
        self.assertEqual(failed_post.title, 'Post with Remote Failure')
        
        # Verify that function didn't raise an exception
        # (if we got here without exception, the test passes)
        self.assertEqual(failed_post.content, 'This post should still be created locally even if remote delivery fails')


class NodeSendsEntriesEdgeCasesTest(TestCase):
    """
    Additional edge cases for node sending entries to remote followers and friends
    """

    def setUp(self):
        """Set up test data"""
        self.local_author = Author.objects.create(
            username='test_author',
            displayName='Test Author',
            host='http://localhost:8000',
            url='http://localhost:8000/api/authors/12345678-1234-5678-9012-123456789012/'
        )

    @patch('authors.utils.federation.remote_post')
    def test_no_followers_no_remote_calls(self, mock_remote_post):
        """
        Additional edge case: If there are no remote followers or friends, 
        no remote calls should be made.
        """
        mock_remote_post.return_value = True
        
        # Create a post when author has no followers/friends
        post = Post.objects.create(
            title='No Followers Post',
            content='No one should receive this',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )
        
        # Call the notification function
        notify_remote_new_post(post)
        
        # Should not make any remote calls since there are no followers/friends
        mock_remote_post.assert_not_called()

    @patch('authors.utils.federation.remote_post')
    def test_only_local_followers_no_remote_calls(self, mock_remote_post):
        """
        Additional edge case: If author only has local followers/friends,
        no remote calls should be made.
        """
        mock_remote_post.return_value = True
        
        # Create a local follower (same host)
        local_follower = Author.objects.create(
            username='local_follower',
            displayName='Local Follower',
            host='http://localhost:8000',
            url='http://localhost:8000/api/authors/87654321-4321-8765-2109-210987654321/'
        )
        
        # Create follow relationship
        Follow.objects.create(follower=local_follower, following=self.local_author)
        
        # Create a post
        post = Post.objects.create(
            title='Local Only Post',
            content='Only local followers should receive this (not pushed)',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )
        
        # Call the notification function
        notify_remote_new_post(post)
        
        # Should not make any remote calls since all followers are local
        mock_remote_post.assert_not_called()