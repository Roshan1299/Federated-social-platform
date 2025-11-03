"""
Tests for entry visibility and unlisted combinations in the stream view

Frontend/API Visibility Table:
                Admin       Friend          Follower        Everyone
Public          control     link + stream   link + stream   link + stream
Unlisted        control     link + stream   link + stream   link (no stream)
Friends Only    control     authenticated   (no access)     (no access)
Deleted         control     (no access)     (no access)     (no access)

"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from authors.models import Post, Follow
from django.utils import timezone
from datetime import timedelta


Author = get_user_model()

'''
#######################################################
TODO: UPDATE AFTER CHANGING VISIBILITY LOGIC IN VIEWS
#######################################################
'''
class VisibilityCombinationsTestCase(TestCase):
    """Test visibility and unlisted attribute combinations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create test authors
        self.author = Author.objects.create_user(
            username='author',
            email='author@test.com',
            password='testpass123',
            displayName='Main Author',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.follower = Author.objects.create_user(
            username='follower',
            email='follower@test.com',
            password='testpass123',
            displayName='Follower',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        
        self.friend = Author.objects.create_user(
            username='friend',
            email='friend@test.com',
            password='testpass123',
            displayName='Friend',
            host='http://testserver',
            url='http://testserver/api/authors/3/'
        )
        
        self.stranger = Author.objects.create_user(
            username='stranger',
            email='stranger@test.com',
            password='testpass123',
            displayName='Stranger',
            host='http://testserver',
            url='http://testserver/api/authors/4/'
        )
        
        # Set up relationships
        # Follower follows author (one-way)
        Follow.objects.create(follower=self.follower, following=self.author)
        
        # Friend relationship (mutual follows)
        Follow.objects.create(follower=self.friend, following=self.author)
        Follow.objects.create(follower=self.author, following=self.friend)

    def test_public_not_unlisted_visible_to_everyone(self):
        """Public + : Should appear in everyone's stream"""
        post = Post.objects.create(
            author=self.author,
            title='Public Listed Post',
            content='Everyone should see this',
            contentType='text/plain',
            visibility='PUBLIC',
            
        )
        
        # Test stranger's stream (doesn't follow author)
        self.client.login(username='stranger', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.stranger.id})
        response = self.client.get(url)
        self.assertContains(response, 'Public Listed Post')
        
        # Test follower's stream
        self.client.login(username='follower', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.follower.id})
        response = self.client.get(url)
        self.assertContains(response, 'Public Listed Post')
        
        # Test friend's stream
        self.client.login(username='friend', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.friend.id})
        response = self.client.get(url)
        self.assertContains(response, 'Public Listed Post')

    def test_public_unlisted_not_in_non_follower_stream(self):
        """Public + : Should NOT appear in non-followers' streams"""
        post = Post.objects.create(
            author=self.author,
            title='Public Unlisted Post',
            content='Only followers see this in stream',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        # Stranger (doesn't follow) should NOT see it in stream
        self.client.login(username='stranger', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.stranger.id})
        response = self.client.get(url)
        self.assertNotContains(response, 'Public Unlisted Post')

    def test_public_unlisted_visible_to_followers(self):
        """Public + : Should appear in followers' streams"""
        post = Post.objects.create(
            author=self.author,
            title='Public Unlisted Post',
            content='Followers see this',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        # Follower should see it
        self.client.login(username='follower', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.follower.id})
        response = self.client.get(url)
        self.assertContains(response, 'Public Unlisted Post')
        
        # Friend should also see it (friends are also followers)
        self.client.login(username='friend', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.friend.id})
        response = self.client.get(url)
        self.assertContains(response, 'Public Unlisted Post')

    def test_public_unlisted_accessible_by_link_to_everyone(self):
        """Public + : Anyone with link can access it"""
        post = Post.objects.create(
            author=self.author,
            title='Public Unlisted Post',
            content='Link accessible to all',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        # Stranger can access via direct link
        self.client.login(username='stranger', password='testpass123')
        url = reverse('authors:post_detail', kwargs={'post_id': post.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Unlisted Post')

    # def test_friends_only_not_unlisted_visible_to_friends_only(self):
    #     """Friends-only + : Only friends see in stream"""
    #     post = Post.objects.create(
    #         author=self.author,
    #         title='Friends Only Post',
    #         content='Only friends',
    #         contentType='text/plain',
    #         visibility='FRIENDS',
    #         
    #     )
        
    #     # Friend should see it
    #     self.client.login(username='friend', password='testpass123')
    #     url = reverse('authors:author_stream', kwargs={'author_id': self.friend.id})
    #     response = self.client.get(url)
    #     self.assertContains(response, 'Friends Only Post')
        
    #     # Follower should NOT see it (not a friend)
    #     self.client.login(username='follower', password='testpass123')
    #     url = reverse('authors:author_stream', kwargs={'author_id': self.follower.id})
    #     response = self.client.get(url)
    #     self.assertNotContains(response, 'Friends Only Post')
        
    #     # Stranger should NOT see it
    #     self.client.login(username='stranger', password='testpass123')
    #     url = reverse('authors:author_stream', kwargs={'author_id': self.stranger.id})
    #     response = self.client.get(url)
    #     self.assertNotContains(response, 'Friends Only Post')

    # def test_friends_only_unlisted_still_friends_only(self):
    #     """Friends-only + : Still only friends (unlisted doesn't matter)"""
    #     post = Post.objects.create(
    #         author=self.author,
    #         title='Friends Only Unlisted',
    #         content='Still friends only',
    #         contentType='text/plain',
    #         visibility='FRIENDS',
    #         
    #     )
        
    #     # Friend should see it
    #     self.client.login(username='friend', password='testpass123')
    #     url = reverse('authors:author_stream', kwargs={'author_id': self.friend.id})
    #     response = self.client.get(url)
    #     self.assertContains(response, 'Friends Only Unlisted')
        
    #     # Follower should NOT see it
    #     self.client.login(username='follower', password='testpass123')
    #     url = reverse('authors:author_stream', kwargs={'author_id': self.follower.id})
    #     response = self.client.get(url)
    #     self.assertNotContains(response, 'Friends Only Unlisted')

    # def test_friends_only_not_accessible_by_link_to_non_friends(self):
    #     """Friends-only: Non-friends cannot access via direct link"""
    #     post = Post.objects.create(
    #         author=self.author,
    #         title='Friends Only Secret',
    #         content='Secret content',
    #         contentType='text/plain',
    #         visibility='FRIENDS',
    #         
    #     )
        
    #     # Friend can access
    #     self.client.login(username='friend', password='testpass123')
    #     url = reverse('authors:post_detail', kwargs={'post_id': post.id})
    #     response = self.client.get(url)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, 'Friends Only Secret')
        
    #     # Follower cannot access (should be forbidden or redirected)
    #     self.client.login(username='follower', password='testpass123')
    #     url = reverse('authors:post_detail', kwargs={'post_id': post.id})
    #     response = self.client.get(url)
    #     # Should be 403 Forbidden or 404 Not Found
    #     self.assertIn(response.status_code, [403, 404])

    def test_author_always_sees_own_posts(self):
        """Author should always see their own posts regardless of visibility"""
        # Create posts with different visibilities
        public_post = Post.objects.create(
            author=self.author,
            title='My Public Post',
            content='Public',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        unlisted_post = Post.objects.create(
            author=self.author,
            title='My Unlisted Post',
            content='Unlisted',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        # friends_post = Post.objects.create(
        #     author=self.author,
        #     title='My Friends Post',
        #     content='Friends',
        #     contentType='text/plain',
        #     visibility='FRIENDS',
        #     
        # )
        
        private_post = Post.objects.create(
            author=self.author,
            title='My Private Post',
            content='Private',
            contentType='text/plain',
            visibility='FRIENDS',
            
        )
        
        # Author should see all their posts
        self.client.login(username='author', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.author.id})
        response = self.client.get(url)
        
        self.assertContains(response, 'My Public Post')
        self.assertContains(response, 'My Unlisted Post')
        # self.assertContains(response, 'My Friends Post')
        self.assertContains(response, 'My Private Post')

    def test_private_posts_not_visible_to_non_friends(self):
        """Friends-only posts should not be visible to followers or strangers, only to mutual friends and author"""
        post = Post.objects.create(
            author=self.author,
            title='Private Post',
            content='Totally private',
            contentType='text/plain',
            visibility='FRIENDS',
            
        )
        
        # Friend CAN see it since they are mutual friends
        self.client.login(username='friend', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.friend.id})
        response = self.client.get(url)
        self.assertContains(response, 'Private Post')
        
        # Follower cannot see it (not a mutual friend)
        self.client.login(username='follower', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.follower.id})
        response = self.client.get(url)
        self.assertNotContains(response, 'Private Post')


class StreamVisibilityMatrixTestCase(TestCase):
    """Test the complete visibility matrix from requirements"""
    
    def setUp(self):
        """Set up test fixtures matching the visibility matrix"""
        self.client = Client()
        
        self.author = Author.objects.create_user(
            username='author',
            password='testpass123',
            displayName='Author',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.friend = Author.objects.create_user(
            username='friend',
            password='testpass123',
            displayName='Friend',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        
        self.follower = Author.objects.create_user(
            username='follower',
            password='testpass123',
            displayName='Follower',
            host='http://testserver',
            url='http://testserver/api/authors/3/'
        )
        
        self.everyone = Author.objects.create_user(
            username='everyone',
            password='testpass123',
            displayName='Everyone',
            host='http://testserver',
            url='http://testserver/api/authors/4/'
        )
        
        # Set up relationships
        # Friend (mutual)
        Follow.objects.create(follower=self.friend, following=self.author)
        Follow.objects.create(follower=self.author, following=self.friend)
        
        # Follower (one-way)
        Follow.objects.create(follower=self.follower, following=self.author)

    def test_visibility_matrix_unlisted(self):
        """Test: Unlisted posts -> Friend: link+stream, Follower: link+stream, Everyone: link only (no stream)"""
        post = Post.objects.create(
            author=self.author,
            title='Unlisted Post',
            content='Unlisted content',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        # Friend sees in stream
        self.client.login(username='friend', password='testpass123')
        response = self.client.get(reverse('authors:author_stream', 
                                           kwargs={'author_id': self.friend.id}))
        self.assertContains(response, 'Unlisted Post')
        
        # Follower sees in stream
        self.client.login(username='follower', password='testpass123')
        response = self.client.get(reverse('authors:author_stream', 
                                           kwargs={'author_id': self.follower.id}))
        self.assertContains(response, 'Unlisted Post')
        
        # Everyone does NOT see in stream (only via direct link)
        self.client.login(username='everyone', password='testpass123')
        response = self.client.get(reverse('authors:author_stream', 
                                           kwargs={'author_id': self.everyone.id}))
        self.assertNotContains(response, 'Unlisted Post')

    def test_visibility_matrix_unlisted(self):
        """Test: Unlisted posts -> Friend: link+stream, Follower: link+stream, Everyone: link only"""
        post = Post.objects.create(
            author=self.author,
            title='Unlisted Post',
            content='Unlisted content',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        # Friend sees in stream
        self.client.login(username='friend', password='testpass123')
        response = self.client.get(reverse('authors:author_stream', 
                                           kwargs={'author_id': self.friend.id}))
        self.assertContains(response, 'Unlisted Post')
        
        # Follower sees in stream
        self.client.login(username='follower', password='testpass123')
        response = self.client.get(reverse('authors:author_stream', 
                                           kwargs={'author_id': self.follower.id}))
        self.assertContains(response, 'Unlisted Post')
        
        # Everyone does NOT see in stream
        self.client.login(username='everyone', password='testpass123')
        response = self.client.get(reverse('authors:author_stream', 
                                           kwargs={'author_id': self.everyone.id}))
        self.assertNotContains(response, 'Unlisted Post')
        
        # But everyone CAN access via link
        response = self.client.get(reverse('authors:post_detail', 
                                           kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)

    # def test_visibility_matrix_friends_only(self):
    #     """Test: Friends-only -> Friend: authenticated, Follower: no access, Everyone: no access"""
    #     post = Post.objects.create(
    #         author=self.author,
    #         title='Friends Only Post',
    #         content='Friends content',
    #         visibility='FRIENDS',
    #         
    #     )
        
    #     # Friend sees it
    #     self.client.login(username='friend', password='testpass123')
    #     response = self.client.get(reverse('authors:author_stream', 
    #                                        kwargs={'author_id': self.friend.id}))
    #     self.assertContains(response, 'Friends Only Post')
        
    #     # Follower does NOT see it
    #     self.client.login(username='follower', password='testpass123')
    #     response = self.client.get(reverse('authors:author_stream', 
    #                                        kwargs={'author_id': self.follower.id}))
    #     self.assertNotContains(response, 'Friends Only Post')
        
    #     # Everyone does NOT see it
    #     self.client.login(username='everyone', password='testpass123')
    #     response = self.client.get(reverse('authors:author_stream', 
    #                                        kwargs={'author_id': self.everyone.id}))
    #     self.assertNotContains(response, 'Friends Only Post')

    # def test_multiple_visibility_combinations_in_stream(self):
    #     """Test that stream correctly handles multiple posts with different visibilities"""
    #     # Create posts with all visibility types
    #     public = Post.objects.create(
    #         author=self.author,
    #         title='Public',
    #         content='Public',
    #         visibility='PUBLIC_UNLISTED',
    #         
    #     )
        
    #     unlisted = Post.objects.create(
    #         author=self.author,
    #         title='Unlisted',
    #         content='Unlisted',
    #         visibility='PUBLIC_UNLISTED',
    #         
    #     )
        
    #     friends = Post.objects.create(
    #         author=self.author,
    #         title='Friends',
    #         content='Friends',
    #         visibility='FRIENDS',
    #         
    #     )
        
    #     # Friend should see all three
    #     self.client.login(username='friend', password='testpass123')
    #     response = self.client.get(reverse('authors:author_stream', 
    #                                        kwargs={'author_id': self.friend.id}))
    #     self.assertContains(response, 'Public')
    #     self.assertContains(response, 'Unlisted')
    #     self.assertContains(response, 'Friends')
        
    #     # Follower should see public and unlisted only
    #     self.client.login(username='follower', password='testpass123')
    #     response = self.client.get(reverse('authors:author_stream', 
    #                                        kwargs={'author_id': self.follower.id}))
    #     self.assertContains(response, 'Public')
    #     self.assertContains(response, 'Unlisted')
    #     self.assertNotContains(response, 'Friends')
        
    #     # Everyone should see only public
    #     self.client.login(username='everyone', password='testpass123')
    #     response = self.client.get(reverse('authors:author_stream', 
    #                                        kwargs={'author_id': self.everyone.id}))
    #     self.assertContains(response, 'Public')
    #     self.assertNotContains(response, 'Unlisted')
    #     self.assertNotContains(response, 'Friends')
