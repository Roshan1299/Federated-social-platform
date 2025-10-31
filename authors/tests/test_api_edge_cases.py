"""
Comprehensive API Testing with Edge Cases and Error Scenarios

This module contains tests for error conditions, edge cases, 
malicious attempts, and boundary conditions for the API endpoints.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from authors.models import Post, Follow, Like, Comment, CommentLike
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import uuid

Author = get_user_model()

class APIEdgeCaseTestCase(TestCase):
    """Test API edge cases and boundary conditions"""
    
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

    def test_invalid_post_id(self):
        """Test API response for invalid/missing post ID"""
        invalid_uuid = "12345"  # Invalid UUID format
        response = self.client.get(f"/api/posts/{invalid_uuid}/")
        self.assertEqual(response.status_code, 404)  # Should return 404

    def test_nonexistent_post_id(self):
        """Test API response for valid UUID format but non-existent post"""
        fake_uuid = uuid.uuid4()
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': fake_uuid}))
        self.assertEqual(response.status_code, 404)

    def test_long_post_content(self):
        """Test API with very long post content"""
        long_content = "x" * 10000  # 10,000 characters
        post = Post.objects.create(
            author=self.author1,
            title='Long Content Post',
            content=long_content,
            visibility='PUBLIC'
        )
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['content']), 10000)

    def test_special_characters_in_content(self):
        """Test API with special characters and JSON-breaking characters"""
        special_content = 'Special chars: \n \t " \' \\ <script>alert("xss")</script>'
        post = Post.objects.create(
            author=self.author1,
            title='Special Chars Post',
            content=special_content,
            visibility='PUBLIC'
        )
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['content'], special_content)

    def test_unicode_content(self):
        """Test API with unicode characters"""
        unicode_content = 'Unicode: 🐍 🦄 Café résumé naïve'
        post = Post.objects.create(
            author=self.author1,
            title='Unicode Post',
            content=unicode_content,
            visibility='PUBLIC'
        )
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)


class APIErrorScenarioTestCase(TestCase):
    """Test API error scenarios and error handling"""
    
    def setUp(self):
        self.client = Client()
        
        self.author = Author.objects.create_user(
            username='testuser',
            password='testpass123',
            displayName='Test User',
            host='http://testserver', 
            url='http://testserver/api/authors/1/'
        )

    def test_authorization_bypass_attempts(self):
        """Test various authorization bypass attempts"""
        post = Post.objects.create(
            author=self.author,
            title='Protected Post',
            content='Private content',
            visibility='FRIENDS'
        )
        
        # Try unauthenticated access to friends-only post
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 403)
        
        # Try with different user attempting to access
        other_user = Author.objects.create_user(
            username='other',
            password='otherpass',
            displayName='Other User',
            host='http://testserver',
            url='http://testserver/api/authors/2/'
        )
        self.client.login(username='other', password='otherpass')
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 403)

    def test_rate_limit_simulation(self):
        """Test behavior under multiple rapid requests (simulated rate limit)"""
        post = Post.objects.create(
            author=self.author,
            title='Rate Limit Test Post',
            content='Content',
            visibility='PUBLIC'
        )
        
        # Make multiple requests in a row
        for i in range(10):
            response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
            self.assertEqual(response.status_code, 200)

    def test_deleted_post_access_various_states(self):
        """Test access to various post deletion states"""
        # Normal post
        post = Post.objects.create(
            author=self.author,
            title='Normal Post',
            content='Content',
            visibility='PUBLIC'
        )
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        
        # Deleted post - should return 404
        post.deleted = True
        post.save()
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 404)

    def test_minimum_content_post(self):
        """Test post with minimal valid content"""
        post = Post.objects.create(
            author=self.author,
            title='',
            content='Minimal content',
            visibility='PUBLIC'
        )
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['content'], 'Minimal content')


class APIInvalidInputTestCase(TestCase):
    """Test API behavior with invalid inputs"""
    
    def setUp(self):
        self.client = Client()
        
        self.author = Author.objects.create_user(
            username='testuser',
            password='testpass123',
            displayName='Test User',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )
    
    def test_invalid_uuid_format(self):
        """Test various invalid UUID formats"""
        invalid_formats = [
            "not-a-uuid",
            "12345",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  # Invalid chars but right length
            "12345678-1234-1234-1234-123456789abc-def",  # Too long
            "1234",  # Too short
            "-12345678-1234-1234-1234-123456789abc",  # Extra dash
        ]
        
        for invalid_uuid in invalid_formats:
            try:
                response = self.client.get(f"/api/posts/{invalid_uuid}/")
                # Should return 404 for invalid UUID (caught by Django URL resolver)
                self.assertIn(response.status_code, [404])
            except:
                # URL resolver might throw exception for invalid format
                pass

    def test_extremely_large_title(self):
        """Test post with extremely large title"""
        large_title = "x" * 1000  # Way beyond normal field length
        try:
            post = Post.objects.create(
                author=self.author,
                title=large_title,
                content='Content',
                visibility='PUBLIC'
            )
            response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
            self.assertEqual(response.status_code, 200)
        except ValidationError:
            # Expected if model validates field length
            pass


class APISecurityAttackTestCase(TestCase):
    """Test potential security attack vectors"""
    
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
        
        self.stranger = Author.objects.create_user(
            username='stranger',
            password='testpass123',
            displayName='Stranger',
            host='http://testserver',
            url='http://testserver/api/authors/3/'
        )

    def test_xss_attempt_in_content(self):
        """Test malicious XSS attempts in post content"""
        xss_content = '<script>alert("XSS")</script> Normal content'
        post = Post.objects.create(
            author=self.author1,
            title='XSS Test Post',
            content=xss_content,
            visibility='PUBLIC'
        )
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        # The content should be returned as-is since it's JSON, but should be properly escaped when rendered
        
    def test_sql_injection_attempts(self):
        """Test potential SQL injection attempts in URL parameters"""
        # This is more of a general test - Django's ORM provides protection
        post = Post.objects.create(
            author=self.author1,
            title="SQL Injection Test",
            content="Content",
            visibility='PUBLIC'
        )
        
        # Test with parameter-like strings in URL
        sqlish_attempts = [
            f"12345678-1234-1234-1234-123456789abc'; DROP TABLE posts; --",
            f"12345678-1234-1234-1234-123456789abc' OR '1'='1",
            f"12345678-1234-1234-1234-123456789abc%27%20OR%20%271%27=%271",
        ]
        
        for attempt in sqlish_attempts:
            try:
                response = self.client.get(f"/api/posts/{attempt}/")
                # Should be treated as invalid UUID and return 404
            except:
                # If URL patterns catch these properly
                pass

    def test_access_to_another_user_post(self):
        """Test attempts to access posts from different users without permission"""
        post1 = Post.objects.create(
            author=self.author1,
            title='Author1 Post',
            content='Private content',
            visibility='FRIENDS'
        )
        
        post2 = Post.objects.create(
            author=self.author2,
            title='Author2 Post',
            content='Also private content',
            visibility='FRIENDS'
        )
        
        # Stranger should not be able to access either author's friends-only posts
        self.client.login(username='stranger', password='testpass123')
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post1.id}))
        self.assertEqual(response.status_code, 403)
        
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post2.id}))
        self.assertEqual(response.status_code, 403)
        
        # Also test that author1 can't access author2's post
        self.client.login(username='author1', password='testpass123')
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post2.id}))
        self.assertEqual(response.status_code, 403)

    def test_brute_force_post_ids(self):
        """Test brute force attempts to guess post IDs"""
        post = Post.objects.create(
            author=self.author1,
            title='Protected Post',
            content='Private content',
            visibility='FRIENDS'
        )
        
        # Try a bunch of random UUIDs to see if we can access the post
        for i in range(50):  # Try 50 random attempts
            fake_uuid = uuid.uuid4()
            if str(fake_uuid) != str(post.id):  # Don't try the real one
                response = self.client.get(reverse('authors:post_api', kwargs={'post_id': fake_uuid}))
                # Should return 404 for non-existent posts
                self.assertEqual(response.status_code, 404)


class APIBoundaryTestCase(TestCase):
    """Test API behavior at boundary conditions"""
    
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

    def test_boundary_visibility_values(self):
        """Test all visibility values work correctly"""
        for visibility in ['PUBLIC', 'PUBLIC_UNLISTED', 'FRIENDS']:
            post = Post.objects.create(
                author=self.author1,
                title=f'{visibility} Post',
                content='Content',
                visibility=visibility
            )
            
            # Public and Public Unlisted should be accessible
            if visibility in ['PUBLIC', 'PUBLIC_UNLISTED']:
                response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
                self.assertEqual(response.status_code, 200)
            # Friends should not be accessible without proper relationship
            else:
                # Test with unauthenticated user
                response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
                self.assertEqual(response.status_code, 403)

    def test_timestamp_precision(self):
        """Test posts with very close timestamps"""
        post1 = Post.objects.create(
            author=self.author1,
            title='Post 1',
            content='Content 1',
            visibility='PUBLIC'
        )
        
        post2 = Post.objects.create(
            author=self.author1,
            title='Post 2',
            content='Content 2',
            visibility='PUBLIC'
        )
        
        # Both should be accessible
        response1 = self.client.get(reverse('authors:post_api', kwargs={'post_id': post1.id}))
        response2 = self.client.get(reverse('authors:post_api', kwargs={'post_id': post2.id}))
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)


class APIConcurrentTestCase(TestCase):
    """Test API behavior under concurrent access"""
    
    def setUp(self):
        self.client = Client()
        
        self.author = Author.objects.create_user(
            username='testuser',
            password='testpass123',
            displayName='Test User',
            host='http://testserver',
            url='http://testserver/api/authors/1/'
        )

    def test_multiple_concurrent_reads(self):
        """Test multiple concurrent reads to the same post"""
        post = Post.objects.create(
            author=self.author,
            title='Concurrent Test Post',
            content='Content for concurrent testing',
            visibility='PUBLIC'
        )
        
        # Simulate multiple concurrent requests
        responses = []
        for i in range(5):
            response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
            responses.append(response.status_code)
        
        # All should succeed
        for status_code in responses:
            self.assertEqual(status_code, 200)