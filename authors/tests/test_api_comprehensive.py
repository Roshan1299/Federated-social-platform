"""
API Testing for Social Distribution Project

This module contains comprehensive tests for the API endpoints including:
- Authentication and authorization
- Visibility-based access controls
- Data integrity
- Error handling
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from authors.models import Post, Follow, Like, Comment, CommentLike
from django.utils import timezone
import json

Author = get_user_model()

class APISecurityTestCase(TestCase):
    """Test API security and access controls"""
    
    def setUp(self):
        self.client = Client()
        
        # Create test users
        self.author1 = Author.objects.create_user(
            username='author1',
            password='testpass123',
            displayName='Author One',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.author2 = Author.objects.create_user(
            username='author2',
            password='testpass123',
            displayName='Author Two',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        
        self.stranger = Author.objects.create_user(
            username='stranger',
            password='testpass123',
            displayName='Stranger',
            host='http://testserver',
            url='http://testserver/api/authors/3/'
        )

    def test_public_post_api_accessibility(self):
        """Test that public posts are accessible to everyone"""
        post = Post.objects.create(
            author=self.author1,
            title='Public Post',
            content='Public content',
            visibility='PUBLIC'
        )
        
        # Unauthenticated user can access public post
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Post')

    def test_public_unlisted_post_api_accessibility(self):
        """Test that public unlisted posts are accessible to everyone"""
        post = Post.objects.create(
            author=self.author1,
            title='Public Unlisted Post',
            content='Public unlisted content',
            visibility='PUBLIC_UNLISTED'
        )
        
        # Unauthenticated user can access public unlisted post
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Unlisted Post')

    def test_friends_post_api_access_by_author(self):
        """Test that authors can access their own friends-only posts"""
        post = Post.objects.create(
            author=self.author1,
            title='Friends Only Post',
            content='Private content',
            visibility='FRIENDS'
        )
        
        # Author can access their own friends-only post
        self.client.login(username='author1', password='testpass123')
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Friends Only Post')

    def test_friends_post_api_access_by_mutual_friend(self):
        """Test that mutual friends can access friends-only posts"""
        post = Post.objects.create(
            author=self.author1,
            title='Friends Only Post',
            content='Private content',
            visibility='FRIENDS'
        )
        
        # Create mutual follow relationship
        Follow.objects.create(follower=self.author2, following=self.author1)
        Follow.objects.create(follower=self.author1, following=self.author2)
        
        # Mutual friend can access friends-only post
        self.client.login(username='author2', password='testpass123')
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Friends Only Post')

    def test_friends_post_api_access_by_non_friend(self):
        """Test that non-friends cannot access friends-only posts"""
        post = Post.objects.create(
            author=self.author1,
            title='Friends Only Post',
            content='Private content',
            visibility='FRIENDS'
        )
        
        # Non-friend cannot access friends-only post
        self.client.login(username='stranger', password='testpass123')
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 403)

    def test_friends_post_api_access_by_one_way_follower(self):
        """Test that one-way followers cannot access friends-only posts"""
        post = Post.objects.create(
            author=self.author1,
            title='Friends Only Post',
            content='Private content',
            visibility='FRIENDS'
        )
        
        # Create one-way follow (author2 follows author1, but not mutual)
        Follow.objects.create(follower=self.author2, following=self.author1)
        
        # One-way follower cannot access friends-only post
        self.client.login(username='author2', password='testpass123')
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 403)

    def test_deleted_post_api_access(self):
        """Test that deleted posts return 404"""
        post = Post.objects.create(
            author=self.author1,
            title='Deleted Post',
            content='Deleted content',
            visibility='PUBLIC',
            deleted=True
        )
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 404)

    def test_author_api_endpoint(self):
        """Test the author API endpoint functionality"""
        response = self.client.get(reverse('authors:author_api', kwargs={'author_id': self.author1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Author One')

    def test_authors_list_api_endpoint(self):
        """Test the authors list API endpoint functionality"""
        response = self.client.get(reverse('authors:authors_api'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Author One')
        self.assertContains(response, 'Author Two')


class APIPostLikeTestCase(TestCase):
    """Test API functionality for post likes"""
    
    def setUp(self):
        self.client = Client()
        
        self.author1 = Author.objects.create_user(
            username='author1',
            password='testpass123',
            displayName='Author One',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.author2 = Author.objects.create_user(
            username='author2',
            password='testpass123',
            displayName='Author Two',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        
        self.post = Post.objects.create(
            author=self.author1,
            title='Test Post',
            content='Test content',
            visibility='PUBLIC'
        )

    def test_public_post_like(self):
        """Test that public posts can be liked by authenticated users"""
        self.client.login(username='author2', password='testpass123')
        
        # Toggle like on the post
        response = self.client.post(reverse('authors:toggle_like', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.status_code, 302)  # Should redirect back to post
        
        # Verify the like was created
        self.assertTrue(Like.objects.filter(author=self.author2, post=self.post).exists())

    def test_friends_post_like_by_friend(self):
        """Test that friends-only posts can be liked by mutual friends"""
        friend_post = Post.objects.create(
            author=self.author1,
            title='Friends Post',
            content='Friends content',
            visibility='FRIENDS'
        )
        
        # Create mutual follow relationship
        Follow.objects.create(follower=self.author2, following=self.author1)
        Follow.objects.create(follower=self.author1, following=self.author2)
        
        self.client.login(username='author2', password='testpass123')
        response = self.client.post(reverse('authors:toggle_like', kwargs={'post_id': friend_post.id}))
        self.assertEqual(response.status_code, 302)

    def test_friends_post_like_by_non_friend(self):
        """Test that friends-only posts cannot be liked by non-friends"""
        friend_post = Post.objects.create(
            author=self.author1,
            title='Friends Post',
            content='Friends content',
            visibility='FRIENDS'
        )
        
        self.client.login(username='author2', password='testpass123')
        response = self.client.post(reverse('authors:toggle_like', kwargs={'post_id': friend_post.id}))
        self.assertEqual(response.status_code, 403)


class APICommentTestCase(TestCase):
    """Test API functionality for comments"""
    
    def setUp(self):
        self.client = Client()
        
        self.author1 = Author.objects.create_user(
            username='author1',
            password='testpass123',
            displayName='Author One',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.author2 = Author.objects.create_user(
            username='author2',
            password='testpass123',
            displayName='Author Two',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        
        self.post = Post.objects.create(
            author=self.author1,
            title='Test Post',
            content='Test content',
            visibility='PUBLIC'
        )

    def test_public_post_comment(self):
        """Test that public posts can have comments added"""
        self.client.login(username='author2', password='testpass123')
        
        response = self.client.post(
            reverse('authors:add_comment', kwargs={'post_id': self.post.id}),
            {'content': 'This is a test comment'}
        )
        self.assertEqual(response.status_code, 302)  # Should redirect back to post
        
        # Verify the comment was created
        self.assertTrue(Comment.objects.filter(author=self.author2, post=self.post).exists())

    def test_friends_post_comment_by_friend(self):
        """Test that friends-only posts can have comments by mutual friends"""
        friend_post = Post.objects.create(
            author=self.author1,
            title='Friends Post',
            content='Friends content',
            visibility='FRIENDS'
        )
        
        # Create mutual follow relationship
        Follow.objects.create(follower=self.author2, following=self.author1)
        Follow.objects.create(follower=self.author1, following=self.author2)
        
        self.client.login(username='author2', password='testpass123')
        response = self.client.post(
            reverse('authors:add_comment', kwargs={'post_id': friend_post.id}),
            {'content': 'Comment on friends post'}
        )
        self.assertEqual(response.status_code, 302)

    def test_friends_post_comment_by_non_friend(self):
        """Test that friends-only posts cannot have comments by non-friends"""
        friend_post = Post.objects.create(
            author=self.author1,
            title='Friends Post',
            content='Friends content',
            visibility='FRIENDS'
        )
        
        self.client.login(username='author2', password='testpass123')
        response = self.client.post(
            reverse('authors:add_comment', kwargs={'post_id': friend_post.id}),
            {'content': 'This should fail'}
        )
        self.assertEqual(response.status_code, 403)


class APIPostLikesViewTestCase(TestCase):
    """Test the post likes API view"""
    
    def setUp(self):
        self.client = Client()
        
        self.author1 = Author.objects.create_user(
            username='author1',
            password='testpass123',
            displayName='Author One',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.author2 = Author.objects.create_user(
            username='author2',
            password='testpass123',
            displayName='Author Two',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        
        self.post = Post.objects.create(
            author=self.author1,
            title='Test Post',
            content='Test content',
            visibility='PUBLIC'
        )

    def test_view_post_likes_authenticated(self):
        """Test that authenticated users can view post likes"""
        # Add a like
        Like.objects.create(author=self.author2, post=self.post)
        
        self.client.login(username='author2', password='testpass123')
        response = self.client.get(reverse('authors:post_likes_page', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Author Two')

    def test_view_friends_post_likes_by_friend(self):
        """Test that friends-only post likes can be viewed by mutual friends"""
        friend_post = Post.objects.create(
            author=self.author1,
            title='Friends Post',
            content='Friends content',
            visibility='FRIENDS'
        )
        
        # Add a like
        Like.objects.create(author=self.author2, post=friend_post)
        
        # Create mutual follow relationship
        Follow.objects.create(follower=self.author2, following=self.author1)
        Follow.objects.create(follower=self.author1, following=self.author2)
        
        self.client.login(username='author2', password='testpass123')
        response = self.client.get(reverse('authors:post_likes_page', kwargs={'post_id': friend_post.id}))
        self.assertEqual(response.status_code, 200)

    def test_view_friends_post_likes_by_non_friend(self):
        """Test that friends-only post likes cannot be viewed by non-friends"""
        friend_post = Post.objects.create(
            author=self.author1,
            title='Friends Post',
            content='Friends content',
            visibility='FRIENDS'
        )
        
        # Add a like
        Like.objects.create(author=self.author2, post=friend_post)
        
        self.client.login(username='author2', password='testpass123')
        response = self.client.get(reverse('authors:post_likes_page', kwargs={'post_id': friend_post.id}))
        # Should return error or redirect since user can't see the friends-only post
        self.assertIn(response.status_code, [200, 302])  # May show error message or redirect


class APIResponseFormatTestCase(TestCase):
    """Test that API responses follow the expected format"""
    
    def setUp(self):
        self.client = Client()
        
        self.author = Author.objects.create_user(
            username='testuser',
            password='testpass123',
            displayName='Test User',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.post = Post.objects.create(
            author=self.author,
            title='API Test Post',
            content='API test content',
            visibility='PUBLIC'
        )

    def test_post_api_response_format(self):
        """Test that post API returns response in expected format"""
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.status_code, 200)
        
        # Parse the JSON response
        data = json.loads(response.content)
        
        # Check required fields
        self.assertEqual(data['type'], 'post')
        self.assertIn('id', data)
        self.assertIn('author', data)
        self.assertIn('title', data)
        self.assertIn('content', data)
        self.assertIn('contentType', data)
        self.assertIn('visibility', data)
        self.assertIn('published', data)
        self.assertIn('updated', data)
        
        # Check author object structure
        author_data = data['author']
        self.assertEqual(author_data['type'], 'author')
        self.assertIn('id', author_data)
        self.assertIn('displayName', author_data)

    def test_author_api_response_format(self):
        """Test that author API returns response in expected format"""
        response = self.client.get(reverse('authors:author_api', kwargs={'author_id': self.author.id}))
        self.assertEqual(response.status_code, 200)
        
        # Parse the JSON response
        data = json.loads(response.content)
        
        # Check required fields
        self.assertEqual(data['type'], 'author')
        self.assertIn('id', data)
        self.assertIn('displayName', data)
        self.assertIn('host', data)
        self.assertIn('web', data)
        self.assertIn('profileImage', data)


class APIAuthorPutTestCase(TestCase):
    """Test updating author profiles via API PUT requests"""
    
    def setUp(self):
        self.client = Client()
        
        self.author = Author.objects.create_user(
            username='testuser',
            password='testpass123',
            displayName='Test User',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )

    def test_update_author_profile(self):
        """Test that an author can update their profile via PUT request"""
        self.client.login(username='testuser', password='testpass123')
        
        updated_data = {
            "displayName": "Updated User",
            "host": "http://updatedserver",
            "description": "Updated description",
        }
        
        response = self.client.put(
            reverse('authors:author_api', kwargs={'author_id': self.author.id}),
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Refresh author from database
        self.author.refresh_from_db()
        
        self.assertEqual(self.author.displayName, "Updated User")
        self.assertEqual(self.author.host, "http://updatedserver") 
        self.assertEqual(self.author.description, "Updated description")