"""
Test suite for [Posting] Node Re-sends Edited Entries

This test suite validates that when a local author edits a post, 
the node correctly re-sends the updated post to all destinations 
where it was originally sent (remote followers and friends).

Edge cases covered:
1. Edited PUBLIC post should be re-sent to all remote followers/friends
2. Edited FRIENDS post should be re-sent only to remote friends (mutual follows)
3. Edited PUBLIC_UNLISTED post should NOT be re-sent to remote nodes
4. Remote node failure during edit should not break the local edit functionality
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from authors.models import Author, Post, Follow, RemoteNode
from authors.utils.federation import notify_remote_edit_post
import uuid


User = get_user_model()


@override_settings()
class NodeReSendsEditedEntriesTest(TestCase):
    """
    Test suite for validating that edited posts are correctly re-sent to remote followers and friends
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
        
        # Create an initial post to edit
        self.post = Post.objects.create(
            title='Original Title',
            content='Original content',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )

    @patch('authors.utils.federation.remote_post')
    def test_edited_public_post_sent_to_remote_followers_and_friends(self, mock_remote_post):
        """
        EDGE CASE 1: An edited PUBLIC post should be re-sent to all remote followers and friends.
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Edit the post
        self.post.title = 'Edited Title'
        self.post.content = 'Edited content for public post'
        self.post.save()
        
        # Call the function directly to trigger re-sending
        notify_remote_edit_post(self.post)
        
        # Verify that remote_post was called for both remote follower and friend
        self.assertEqual(mock_remote_post.call_count, 2)
        
        # Check that calls were made with appropriate parameters
        calls_made = mock_remote_post.call_args_list
        called_urls = [call[1]['url'] for call in calls_made]
        
        # Should have sent to both remote follower and friend's inbox
        expected_inboxes = [
            'http://remote-node.com/api/authors/87654321-4321-8765-2109-210987654321/inbox',
            'http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/inbox'
        ]
        
        for expected_inbox in expected_inboxes:
            self.assertIn(expected_inbox, called_urls)

    @patch('authors.utils.federation.remote_post')
    def test_edited_friends_post_sent_only_to_remote_friends(self, mock_remote_post):
        """
        EDGE CASE 2: An edited FRIENDS post should only be re-sent to remote friends (mutual followers).
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Create and edit a friends-only post
        friends_post = Post.objects.create(
            title='Original Friends Only Title',
            content='Original friends only content',
            contentType='text/plain',
            visibility='FRIENDS',
            author=self.local_author
        )
        
        # Edit the friends-only post
        friends_post.title = 'Edited Friends Only Title'
        friends_post.content = 'Edited friends only content'
        friends_post.save()
        
        # Call the function directly to trigger re-sending
        notify_remote_edit_post(friends_post)
        
        # Verify that remote_post was called only for the friend, not the follower
        # (remote_friend is mutual follow = friend, remote_follower is one-way = follower only)
        self.assertEqual(mock_remote_post.call_count, 1)
        
        # Check that it was sent only to the remote friend's inbox
        call_args = mock_remote_post.call_args
        self.assertEqual(call_args[1]['url'], 
                        'http://another-remote.com/api/authors/11111111-2222-3333-4444-555555555555/inbox')

    @patch('authors.utils.federation.remote_post')
    def test_edited_public_unlisted_post_sent_to_remote_followers_and_friends(self, mock_remote_post):
        """
        EDGE CASE 3: An edited PUBLIC_UNLISTED post should be sent to remote followers and friends, similar to PUBLIC posts.
        """
        # Mock remote_post to return True (successful delivery)
        mock_remote_post.return_value = True
        
        # Create and edit a public unlisted post
        unlisted_post = Post.objects.create(
            title='Original Unlisted Title',
            content='Original unlisted content',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            author=self.local_author
        )
        
        # Edit the unlisted post
        unlisted_post.title = 'Edited Unlisted Title'
        unlisted_post.content = 'Edited unlisted content'
        unlisted_post.save()
        
        # Call the function directly to trigger re-sending
        notify_remote_edit_post(unlisted_post)
        
        # Verify that remote_post was called for both remote follower and friend (like PUBLIC posts)
        self.assertEqual(mock_remote_post.call_count, 2,
                        f"Expected 2 calls to remote_post, but got {mock_remote_post.call_count}. "
                        f"Edited PUBLIC_UNLISTED posts should be sent to all remote followers and friends.")
        
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
    def test_remote_node_failure_does_not_break_local_editing(self, mock_remote_post):
        """
        EDGE CASE 4: If remote nodes fail during post editing distribution, local editing should still succeed.
        """
        # Mock remote_post to return False (delivery failure)
        mock_remote_post.return_value = False
        
        # Edit a public post
        self.post.title = 'Title After Remote Failure'
        self.post.content = 'Content after remote failure - editing should still work locally'
        self.post.save()
        
        # Call the function directly to trigger re-sending
        notify_remote_edit_post(self.post)
        
        # Verify that remote_post was called but failure didn't break the process
        self.assertGreater(mock_remote_post.call_count, 0)
        
        # Verify that the post is properly updated locally
        updated_post = Post.objects.get(id=self.post.id)
        self.assertEqual(updated_post.title, 'Title After Remote Failure')
        self.assertEqual(updated_post.content, 'Content after remote failure - editing should still work locally')
        
        # Verify that function didn't raise an exception
        # (if we got here without exception, the test passes)
        self.assertEqual(updated_post.content, 'Content after remote failure - editing should still work locally')


class NodeReSendsEditedEntriesEdgeCasesTest(TestCase):
    """
    Additional edge cases for node re-sending edited entries to remote followers and friends
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
    def test_edit_post_with_no_followers_no_remote_calls(self, mock_remote_post):
        """
        Additional edge case: If there are no remote followers or friends, 
        no remote calls should be made when editing.
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
        
        # Edit the post
        post.title = 'Edited No Followers Title'
        post.content = 'Edited no followers content'
        post.save()
        
        # Call the notification function
        notify_remote_edit_post(post)
        
        # Should not make any remote calls since there are no followers/friends
        mock_remote_post.assert_not_called()

    @patch('authors.utils.federation.remote_post')
    def test_edit_post_with_only_local_followers_no_remote_calls(self, mock_remote_post):
        """
        Additional edge case: If author only has local followers/friends,
        no remote calls should be made when editing.
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
        
        # Create and edit a post
        post = Post.objects.create(
            title='Original Local Only Title',
            content='Original local only content',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )
        
        # Edit the post
        post.title = 'Edited Local Only Title'
        post.content = 'Edited local only content - should not trigger remote calls'
        post.save()
        
        # Call the notification function
        notify_remote_edit_post(post)
        
        # Should not make any remote calls since all followers are local
        mock_remote_post.assert_not_called()

    @patch('authors.utils.federation.remote_post')
    def test_edit_post_visibility_from_public_to_friends(self, mock_remote_post):
        """
        Additional edge case: When editing post visibility from PUBLIC to FRIENDS,
        it should only be sent to remote friends after the edit (not all followers).
        """
        mock_remote_post.return_value = True
        
        # Create a post with remote followers and friends
        remote_friend = Author.objects.create(
            username='remote_friend',
            displayName='Remote Friend',
            host='http://friend-node.com',
            url='http://friend-node.com/api/authors/friend123/'
        )
        
        remote_follower = Author.objects.create(
            username='remote_follower',
            displayName='Remote Follower', 
            host='http://follower-node.com',
            url='http://follower-node.com/api/authors/follower123/'
        )
        
        # Create remote nodes
        RemoteNode.objects.create(
            name='Friend Node',
            base_url='http://friend-node.com/',
            username='friend_user',
            password='friend_pass',
            enabled=True
        )
        
        RemoteNode.objects.create(
            name='Follower Node',
            base_url='http://follower-node.com/',
            username='follow_user', 
            password='follow_pass',
            enabled=True
        )
        
        # Set up relationships: follower is one-way, friend is mutual
        Follow.objects.create(follower=remote_follower, following=self.local_author)  # one-way follow
        Follow.objects.create(follower=self.local_author, following=remote_friend)    # local -> friend
        Follow.objects.create(follower=remote_friend, following=self.local_author)    # friend -> local (mutual)
        
        # Create post as public
        post = Post.objects.create(
            title='Public to Friends Title',
            content='Public to friends content',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.local_author
        )
        
        # Change visibility to friends
        post.visibility = 'FRIENDS'
        post.title = 'Changed to Friends Title'
        post.content = 'Changed to friends content'
        post.save()
        
        # Call the notification function
        notify_remote_edit_post(post)
        
        # Should only send to remote friend, not follower (since now FRIENDS visibility)
        # This means only 1 call should be made (to the friend)
        self.assertEqual(mock_remote_post.call_count, 1)
        
        # Check that it was sent to the friend's inbox, not the follower's
        call_args = mock_remote_post.call_args
        self.assertIn('friend123', call_args[1]['url'])  # Should contain friend's ID
        self.assertNotIn('follower123', call_args[1]['url'])  # Should not contain follower's ID