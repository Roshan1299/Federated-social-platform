"""
Tests for the AuthorStreamView
- Stream should show public, non-unlisted posts
- Posts should be ordered by most recent 'updated' timestamp
- Stream should be paginated (PAGE_SIZE posts per page by default)
- Stream should show posts from followed authors
- Stream is accessible to authenticated users
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from authors.models import Post, Follow
from datetime import datetime, timedelta
from django.utils import timezone


Author = get_user_model()
PAGE_SIZE = 20

class AuthorStreamViewTestCase(TestCase):
    """Test suite for AuthorStreamView - Core functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create test authors
        self.author1 = Author.objects.create_user(
            username='testauthor1',
            email='author1@test.com',
            password='testpass123',
            displayName='Test Author 1'
        )
        
        self.author2 = Author.objects.create_user(
            username='testauthor2',
            email='author2@test.com',
            password='testpass123',
            displayName='Test Author 2'
        )
        
        self.author3 = Author.objects.create_user(
            username='testauthor3',
            email='author3@test.com',
            password='testpass123',
            displayName='Test Author 3'
        )
        
        # Set up host and URL for authors
        for author in [self.author1, self.author2, self.author3]:
            author.host = "http://testserver"
            author.url = f"http://testserver/api/authors/{author.id}/"
            author.save()

    def test_stream_requires_authentication(self):
        """Test that unauthenticated users are redirected to login"""
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        
        self.assertIn(response.status_code, [302])

    def test_authenticated_user_can_access_stream(self):
        """Test that authenticated users can access the stream"""
        self.client.login(username='testauthor1', password='testpass123')
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'authors/author_stream.html')

    def test_stream_shows_only_public_posts(self):
        """Test that stream only displays PUBLIC visibility posts"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Create public post
        public_post = Post.objects.create(
            author=self.author2,
            title='Public Post',
            content='This is public',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        # Create private post
        private_post = Post.objects.create(
            author=self.author2,
            title='Private Post',
            content='This is private',
            contentType='text/plain',
            visibility='FRIENDS',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Check that only public post appears
        self.assertContains(response, 'Public Post')
        self.assertNotContains(response, 'Private Post')

    def test_stream_excludes_unlisted_posts(self):
        """Test that unlisted posts do not appear in stream"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Create listed post
        listed_post = Post.objects.create(
            author=self.author2,
            title='Listed Post',
            content='This is listed',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        # Create unlisted post
        unlisted_post = Post.objects.create(
            author=self.author2,
            title='Unlisted Post',
            content='This is unlisted',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Only listed post should appear
        self.assertContains(response, 'Listed Post')
        self.assertNotContains(response, 'Unlisted Post')

    def test_stream_ordered_by_most_recent_updated(self):
        """Test that posts are ordered by most recent 'updated' timestamp (descending)"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Create posts with different timestamps
        now = timezone.now()
        
        post1 = Post.objects.create(
            author=self.author2,
            title='Oldest Post',
            content='Created first',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        post1.updated = now - timedelta(days=3)
        post1.save()
        
        post2 = Post.objects.create(
            author=self.author2,
            title='Middle Post',
            content='Created second',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        post2.updated = now - timedelta(days=1)
        post2.save()
        
        post3 = Post.objects.create(
            author=self.author2,
            title='Newest Post',
            content='Created third',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        post3.updated = now
        post3.save()
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Get posts from context
        posts = list(response.context['posts'])
        
        # Verify order (most recent first)
        self.assertEqual(posts[0].title, 'Newest Post')
        self.assertEqual(posts[1].title, 'Middle Post')
        self.assertEqual(posts[2].title, 'Oldest Post')

    def test_stream_pagination(self):
        """Test that stream is paginated with PAGE_SIZE posts per page"""
        self.client.login(username='testauthor1', password='testpass123')
        
        for i in range(25):
            Post.objects.create(
                author=self.author2,
                title=f'Post {i}',
                content=f'Content {i}',
                contentType='text/plain',
                visibility='PUBLIC',
            )
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # First page should have PAGE_SIZE posts
        self.assertEqual(len(response.context['posts']), PAGE_SIZE)
        
        # Check pagination context
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(response.context['paginator'].num_pages, 2)

    def test_stream_pagination_second_page(self):
        """Test that second page of pagination works correctly"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Create 25 public posts
        for i in range(25):
            Post.objects.create(
                author=self.author2,
                title=f'Post {i}',
                content=f'Content {i}',
                contentType='text/plain',
                visibility='PUBLIC',
            )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url + '?page=2')
        
        # Second page should have 5 posts
        self.assertEqual(len(response.context['posts']), 5)

    def test_stream_shows_followed_authors_posts(self):
        """Test that stream highlights posts from authors the user follows"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Author1 follows Author2
        Follow.objects.create(follower=self.author1, following=self.author2)
        
        # Create posts from followed author
        followed_post = Post.objects.create(
            author=self.author2,
            title='Post from followed author',
            content='Should appear in followed section',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Check that followed_data context exists
        self.assertIn('followed_data', response.context)
        
        # Verify the post from followed author appears
        self.assertContains(response, 'Post from followed author')

    def test_stream_context_contains_followed_data(self):
        """Test that stream context includes followed_data for authenticated users"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Author1 follows Author2
        Follow.objects.create(follower=self.author1, following=self.author2)
        
        # Create post from followed author
        Post.objects.create(
            author=self.author2,
            title='Followed Post',
            content='Content',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Check followed_data in context
        self.assertIn('followed_data', response.context)
        followed_data = response.context['followed_data']
        
        # Should have data for one followed author
        self.assertEqual(len(followed_data), 1)
        self.assertEqual(followed_data[0]['author'].id, self.author2.id)

    def test_stream_context_contains_author_id(self):
        """Test that stream context includes the authenticated user's author_id"""
        self.client.login(username='testauthor1', password='testpass123')
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        self.assertIn('author_id', response.context)
        # Should be the authenticated user's ID
        self.assertEqual(response.context['author_id'], self.author1.id)

    def test_stream_with_markdown_posts(self):
        """Test that stream can display markdown posts"""
        self.client.login(username='testauthor1', password='testpass123')
        
        markdown_post = Post.objects.create(
            author=self.author2,
            title='Markdown Post',
            content='# Heading\n\n**Bold text**',
            contentType='text/markdown',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        self.assertContains(response, 'Markdown Post')

    def test_stream_with_image_posts(self):
        """Test that stream can display posts with images"""
        self.client.login(username='testauthor1', password='testpass123')
        
        image_post = Post.objects.create(
            author=self.author2,
            title='Image Post',
            content='Check out this image',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        self.assertContains(response, 'Image Post')

    def test_empty_stream(self):
        """Test stream when there are no posts"""
        self.client.login(username='testauthor1', password='testpass123')
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['posts']), 0)

    def test_stream_context_object_name(self):
        """Test that posts are available under correct context name"""
        self.client.login(username='testauthor1', password='testpass123')
        
        Post.objects.create(
            author=self.author2,
            title='Test Post',
            content='Content',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Verify context_object_name is 'posts'
        self.assertIn('posts', response.context)
        self.assertTrue(hasattr(response.context['posts'], '__iter__'))

    def test_stream_excludes_deleted_posts(self):
        """Test that deleted posts don't appear in stream"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Create and then delete a post
        deleted_post = Post.objects.create(
            author=self.author2,
            title='To be deleted',
            content='This will be deleted',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED'
        )
        
        post_id = deleted_post.id
        deleted_post.deleted = True
        deleted_post.save()
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Deleted post should not appear
        self.assertNotContains(response, 'To be deleted')

    def test_stream_with_multiple_content_types(self):
        """Test stream displays posts with various content types"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Create posts with different content types
        plain_post = Post.objects.create(
            author=self.author2,
            title='Plain Text',
            content='Plain text content',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        markdown_post = Post.objects.create(
            author=self.author2,
            title='Markdown',
            content='# Markdown content',
            contentType='text/markdown',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Both posts should appear
        self.assertContains(response, 'Plain Text')
        self.assertContains(response, 'Markdown')

    def test_stream_url_pattern(self):
        """Test that the stream URL is correctly formed"""
        self.client.login(username='testauthor1', password='testpass123')
        
        expected_url = f'/authors/{self.author1.id}/stream'
        actual_url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        
        self.assertEqual(expected_url, actual_url)

    def test_stream_model_attribute(self):
        """Test that ListView uses correct model"""
        self.client.login(username='testauthor1', password='testpass123')
        
        # Create a post
        Post.objects.create(
            author=self.author2,
            title='Test Post',
            content='Content',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author1.id})
        response = self.client.get(url)
        
        # Posts should be Post model instances
        if len(response.context['posts']) > 0:
            self.assertIsInstance(response.context['posts'][0], Post)


class StreamViewFollowIntegrationTestCase(TestCase):
    """Integration tests for stream functionality with follows
        1. Posts from followed authors appear in stream
        2. Test that only the 5 most recent posts from each followed author appear
        3. Test that posts from non-followed authors do not appear in the followed_data
        4. Test that followed_data contains multiple followed authors when applicable
    """
    
    '''
    TODO: Update tests when friend functionality is fully implemented
    
    '''
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create a network of authors
        self.user = Author.objects.create_user(
            username='mainuser',
            email='user@test.com',
            password='testpass123',
            displayName='Main User',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.friend1 = Author.objects.create_user(
            username='friend1',
            email='friend1@test.com',
            password='testpass123',
            displayName='Friend One',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        
        self.friend2 = Author.objects.create_user(
            username='friend2',
            email='friend2@test.com',
            password='testpass123',
            displayName='Friend Two',
            host='http://testserver',
            url='http://testserver/api/authors/3/'
        )

    def test_complex_stream_scenario(self):
        """Test a complex scenario with follows"""
        self.client.login(username='mainuser', password='testpass123')
        
        # User follows friend1
        Follow.objects.create(follower=self.user, following=self.friend1)
        
        # Create various posts
        friend_post = Post.objects.create(
            author=self.friend1,
            title='Friend Post',
            content='Friend content',
            contentType='text/markdown',
            visibility='PUBLIC',
        )
        
        # Friend2's public post (user doesn't follow friend2)
        stranger_post = Post.objects.create(
            author=self.friend2,
            title='Stranger Post',
            content='Stranger content',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        # Private post shouldn't appear
        private_post = Post.objects.create(
            author=self.friend1,
            title='Private Post',
            content='Private content',
            contentType='text/plain',
            visibility='FRIENDS',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.user.id})
        response = self.client.get(url)
        
        # Verify expected posts appear
        self.assertContains(response, 'Friend Post')
        self.assertContains(response, 'Stranger Post')  # All public posts appear in main stream
        self.assertNotContains(response, 'Private Post')
        
        # Verify response is successful
        self.assertEqual(response.status_code, 200)

    def test_followed_data_limited_to_5_posts_per_author(self):
        """Test that followed_data shows maximum 5 recent posts per followed author"""
        self.client.login(username='mainuser', password='testpass123')
        
        # User follows friend1
        Follow.objects.create(follower=self.user, following=self.friend1)
        
        # Create 7 posts from followed author
        for i in range(7):
            Post.objects.create(
                author=self.friend1,
                title=f'Friend Post {i}',
                content=f'Content {i}',
                contentType='text/plain',
                visibility='PUBLIC',
            )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.user.id})
        response = self.client.get(url)
        
        followed_data = response.context['followed_data']
        
        # Should have data for friend1
        self.assertEqual(len(followed_data), 1)
        
        # Should have max 5 posts
        self.assertLessEqual(len(followed_data[0]['posts']), 5)

    def test_multiple_followed_authors_in_stream(self):
        """Test stream with multiple followed authors"""
        self.client.login(username='mainuser', password='testpass123')
        
        # User follows both friends
        Follow.objects.create(follower=self.user, following=self.friend1)
        Follow.objects.create(follower=self.user, following=self.friend2)
        
        # Create posts from both
        Post.objects.create(
            author=self.friend1,
            title='Friend1 Post',
            content='Content from friend 1',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        Post.objects.create(
            author=self.friend2,
            title='Friend2 Post',
            content='Content from friend 2',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.user.id})
        response = self.client.get(url)
        
        followed_data = response.context['followed_data']
        
        # Should have data for both followed authors
        self.assertEqual(len(followed_data), 2)
        
        # Both posts should appear
        self.assertContains(response, 'Friend1 Post')
        self.assertContains(response, 'Friend2 Post')

    def test_stream_empty_followed_data_when_no_follows(self):
        """Test that followed_data is empty when user doesn't follow anyone"""
        self.client.login(username='mainuser', password='testpass123')
        
        # Create some posts but don't follow anyone
        Post.objects.create(
            author=self.friend1,
            title='Some Post',
            content='Content',
            contentType='text/plain',
            visibility='PUBLIC',
        )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.user.id})
        response = self.client.get(url)
        
        followed_data = response.context['followed_data']
        
        # Should be empty list
        self.assertEqual(len(followed_data), 0)


class StreamViewPaginationTestCase(TestCase):
    """Detailed pagination tests for stream view"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        self.author = Author.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            displayName='Test User',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
        
        self.client.login(username='testuser', password='testpass123')

    def test_pagination_with_exactly_PAGE_SIZE_posts(self):
        """Test pagination with exactly PAGE_SIZE posts (one full page)"""
        for i in range(PAGE_SIZE):
            Post.objects.create(
                author=self.author,
                title=f'Post {i}',
                content=f'Content {i}',
                contentType='text/plain',
                visibility='PUBLIC',
            )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author.id})
        response = self.client.get(url)
        
        # Should have exactly PAGE_SIZE posts on one page
        self.assertEqual(len(response.context['posts']), PAGE_SIZE)
        
        # Should be paginated but only 1 page
        self.assertFalse(response.context['is_paginated'])
        self.assertEqual(response.context['paginator'].num_pages, 1)

    def test_pagination_exceeds_limit(self):
        """Test pagination with more posts (requires 2 pages)"""
        for i in range(PAGE_SIZE + 1):
            Post.objects.create(
                author=self.author,
                title=f'Post {i}',
                content=f'Content {i}',
                contentType='text/plain',
                visibility='PUBLIC',
            )        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author.id})
        response = self.client.get(url)
        
        # First page should have PAGE_SIZE posts
        self.assertEqual(len(response.context['posts']), PAGE_SIZE)
        
        # Should have 2 pages
        self.assertEqual(response.context['paginator'].num_pages, 2)
        
        # Check second page has 1 post
        response = self.client.get(url + '?page=2')
        self.assertEqual(len(response.context['posts']), 1)

    def test_pagination_page_out_of_range(self):
        """Test pagination with invalid page number"""
        # Create 10 posts
        for i in range(10):
            Post.objects.create(
                author=self.author,
                title=f'Post {i}',
                content=f'Content {i}',
                contentType='text/plain',
                visibility='PUBLIC',
            )
        
        url = reverse('authors:author_stream', kwargs={'author_id': self.author.id})
        
        # Try to access page 99
        response = self.client.get(url + '?page=99')
        
        # Should handle gracefully (typically shows last page or returns 404)
        self.assertIn(response.status_code, [200, 404])
