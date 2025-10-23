"""
API Tests for User Stories 8, 9, 10, 11, 14:
8. As an author, I want to make entries, so I can share my thoughts and pictures with other local authors.
9. As an author, I want to be able to make my entries 'public', so that everyone can see them.
10. As an author, entries I make can be in simple plain text, because I don't always want all the formatting features of CommonMark.
11. As an author, entries I make can be in CommonMark, so I can give my entries some basic formatting.
14. As an author, I want to be able to use my web-browser to manage/author my entries, so I don't have to use a clunky API.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from authors.models import Post
import json

User = get_user_model()

class PostAPITests(TestCase):
    """Test API endpoints for posts"""
    
    def setUp(self):
        """Set up test users and client"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            displayName='Test User'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123',
            displayName='Other User'
        )

    def test_post_api_creation(self):
        """Test creating a post via API (US 8, 10, 11)"""
        # Log in to create a session
        self.client.login(username='testuser', password='testpass123')
        
        # Create a plain text post via POST request to create view
        response = self.client.post(reverse('authors:create_post'), {
            'title': 'API Test Post',
            'description': 'Test post created via form',
            'content': 'This is content created via API-like request',
            'contentType': 'text/plain',
            'visibility': 'PUBLIC'
        })
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Verify the post was created
        post = Post.objects.get(title='API Test Post')
        self.assertEqual(post.content, 'This is content created via API-like request')
        self.assertEqual(post.contentType, 'text/plain')
        self.assertEqual(post.visibility, 'PUBLIC')

    def test_post_api_retrieval(self):
        """Test retrieving a post via API"""
        # Create a post
        post = Post.objects.create(
            title='API Retrieve Test',
            content='Content for API retrieval',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Access the post API endpoint
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Parse the JSON response
        data = json.loads(response.content)
        
        # Verify required fields are present
        self.assertEqual(data['type'], 'post')
        self.assertEqual(data['title'], 'API Retrieve Test')
        self.assertEqual(data['content'], 'Content for API retrieval')
        self.assertEqual(data['contentType'], 'text/plain')
        self.assertEqual(data['visibility'], 'PUBLIC')
        self.assertIn('author', data)
        self.assertIn('published', data)
        self.assertIn('updated', data)
        
        # Verify author information is included
        author_data = data['author']
        self.assertEqual(author_data['type'], 'author')
        self.assertEqual(author_data['displayName'], 'Test User')

    def test_public_post_accessibility(self):
        """Test that public posts are accessible (US 9)"""
        # Create a public post
        post = Post.objects.create(
            title='Public API Post',
            content='Public content',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Test that it's accessible without authentication
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'Public API Post')
        self.assertEqual(data['content'], 'Public content')
        self.assertEqual(data['visibility'], 'PUBLIC')

    def test_private_post_accessibility(self):
        """Test that private posts follow access rules"""
        # Create a private post
        post = Post.objects.create(
            title='Private API Post',
            content='Private content',
            contentType='text/plain',
            visibility='FRIENDS',
            author=self.user
        )
        
        # Test that it's accessible by owner (when logged in)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        
        # Verify the content matches
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'Private API Post')
        self.assertEqual(data['content'], 'Private content')
        self.assertEqual(data['visibility'], 'FRIENDS')

    def test_post_content_types_api(self):
        """Test that different content types work through API (US 10, 11)"""
        content_types_test = [
            ('text/plain', 'Plain text content'),
            ('text/markdown', '# Markdown header\n\nParagraph content'),
        ]
        
        for content_type, content in content_types_test:
            with self.subTest(content_type=content_type):
                # Create post
                post = Post.objects.create(
                    title=f'Test {content_type}',
                    content=content,
                    contentType=content_type,
                    visibility='PUBLIC',
                    author=self.user
                )
                
                # Test API retrieval
                response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
                self.assertEqual(response.status_code, 200)
                
                data = json.loads(response.content)
                self.assertEqual(data['contentType'], content_type)
                self.assertEqual(data['content'], content)

    def test_post_api_structure(self):
        """Test that post API response follows the documented structure"""
        # Create a post
        post = Post.objects.create(
            title='Structure Test Post',
            description='Testing API structure',
            content='Test content',
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.user
        )
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        
        # Verify all required fields from documentation are present
        required_fields = ['type', 'id', 'author', 'title', 'description', 
                          'content', 'contentType', 'visibility', 'published', 'updated']
        
        for field in required_fields:
            self.assertIn(field, data, f"Missing field: {field}")
        
        # Verify field types and values
        self.assertEqual(data['type'], 'post')
        self.assertEqual(data['title'], 'Structure Test Post')
        self.assertEqual(data['content'], 'Test content')
        self.assertEqual(data['contentType'], 'text/plain')
        self.assertEqual(data['visibility'], 'PUBLIC')
        
        # Verify author structure
        self.assertIn('displayName', data['author'])
        self.assertIn('id', data['author'])
        self.assertEqual(data['author']['displayName'], 'Test User')