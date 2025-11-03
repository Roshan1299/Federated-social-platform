"""
Test authentication for Followers API endpoints
Tests that DELETE and PUT operations are properly authorized according to spec:
- DELETE: Only AUTHOR_SERIAL (the one being followed) can remove followers
- PUT: Only FOREIGN_AUTHOR_ID (the follower) can add themselves
"""
from django.test import TestCase, Client
from django.urls import reverse
from authors.models import Author, Follow
import json
import base64


class FollowersAPIAuthTest(TestCase):
    """Test authentication rules for Followers API"""
    
    def setUp(self):
        """Create test authors and basic setup"""
        # Create authors
        self.alice = Author.objects.create_user(
            username='alice',
            password='alicepass',
            displayName='Alice',
        )
        self.alice.host = 'http://localhost:8000'
        self.alice.url = f'http://localhost:8000/api/authors/{self.alice.id}/'
        self.alice.save()
        
        self.bob = Author.objects.create_user(
            username='bob',
            password='bobpass',
            displayName='Bob',
        )
        self.bob.host = 'http://localhost:8000'
        self.bob.url = f'http://localhost:8000/api/authors/{self.bob.id}/'
        self.bob.save()
        
        self.charlie = Author.objects.create_user(
            username='charlie',
            password='charliepass',
            displayName='Charlie',
        )
        self.charlie.host = 'http://localhost:8000'
        self.charlie.url = f'http://localhost:8000/api/authors/{self.charlie.id}/'
        self.charlie.save()
        
        self.client = Client()
    
    def get_basic_auth_header(self, username, password):
        """Helper to generate HTTP Basic Auth header"""
        credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        return f'Basic {credentials}'
    
    def test_get_follower_success(self):
        """GET should work for anyone authenticated"""
        # Bob follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Authenticated as Alice
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('alice', 'alicepass')
        )
        self.assertEqual(response.status_code, 200)
        
        # Authenticated as Bob
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('bob', 'bobpass')
        )
        self.assertEqual(response.status_code, 200)
        
        # Authenticated as Charlie (unrelated)
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('charlie', 'charliepass')
        )
        self.assertEqual(response.status_code, 200)
    
    def test_get_follower_with_fqid(self):
        """GET should work with FQID instead of UUID"""
        # Bob follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        
        # Use percent-encoded FQID
        import urllib.parse
        bob_fqid = urllib.parse.quote(self.bob.url, safe='')
        url = f'/api/authors/{self.alice.id}/followers/{bob_fqid}'
        
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('alice', 'alicepass')
        )
        self.assertEqual(response.status_code, 200)
    
    def test_delete_follower_by_author_success(self):
        """DELETE: AUTHOR_SERIAL (Alice) can remove her follower"""
        # Bob follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Alice removes Bob as follower - should succeed
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('alice', 'alicepass')
        )
        self.assertEqual(response.status_code, 204)
        
        # Verify follow relationship is deleted
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_delete_follower_by_follower_forbidden(self):
        """DELETE: FOREIGN_AUTHOR_ID (Bob) cannot remove himself as follower"""
        # Bob follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Bob tries to remove himself - should fail with 403
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('bob', 'bobpass')
        )
        self.assertEqual(response.status_code, 403)
        
        # Verify follow relationship still exists
        self.assertTrue(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_delete_follower_by_unrelated_user_forbidden(self):
        """DELETE: Unrelated user (Charlie) cannot remove Bob as follower of Alice"""
        # Bob follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Charlie tries to remove Bob - should fail with 403
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('charlie', 'charliepass')
        )
        self.assertEqual(response.status_code, 403)
        
        # Verify follow relationship still exists
        self.assertTrue(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_delete_follower_with_fqid(self):
        """DELETE: Should work with FQID when authenticated as AUTHOR_SERIAL"""
        # Bob follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        
        # Use percent-encoded FQID
        import urllib.parse
        bob_fqid = urllib.parse.quote(self.bob.url, safe='')
        url = f'/api/authors/{self.alice.id}/followers/{bob_fqid}'
        
        # Alice removes Bob as follower using FQID - should succeed
        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('alice', 'alicepass')
        )
        self.assertEqual(response.status_code, 204)
        
        # Verify follow relationship is deleted
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_put_follower_by_follower_success(self):
        """PUT: FOREIGN_AUTHOR_ID (Bob) can add himself as follower"""
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Bob adds himself as follower - should succeed
        response = self.client.put(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('bob', 'bobpass')
        )
        self.assertIn(response.status_code, [200, 201])
        
        # Verify follow relationship is created
        self.assertTrue(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_put_follower_by_author_forbidden(self):
        """PUT: AUTHOR_SERIAL (Alice) cannot add Bob as her follower"""
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Alice tries to add Bob as follower - should fail with 403
        response = self.client.put(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('alice', 'alicepass')
        )
        self.assertEqual(response.status_code, 403)
        
        # Verify follow relationship is NOT created
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_put_follower_by_unrelated_user_forbidden(self):
        """PUT: Unrelated user (Charlie) cannot add Bob as follower of Alice"""
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Charlie tries to add Bob as follower of Alice - should fail with 403
        response = self.client.put(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('charlie', 'charliepass')
        )
        self.assertEqual(response.status_code, 403)
        
        # Verify follow relationship is NOT created
        self.assertFalse(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_put_follower_with_fqid(self):
        """PUT: Should work with FQID when authenticated as FOREIGN_AUTHOR_ID"""
        # Use percent-encoded FQID
        import urllib.parse
        bob_fqid = urllib.parse.quote(self.bob.url, safe='')
        url = f'/api/authors/{self.alice.id}/followers/{bob_fqid}'
        
        # Bob adds himself as follower using FQID - should succeed
        response = self.client.put(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('bob', 'bobpass')
        )
        self.assertIn(response.status_code, [200, 201])
        
        # Verify follow relationship is created
        self.assertTrue(
            Follow.objects.filter(follower=self.bob, following=self.alice).exists()
        )
    
    def test_put_follower_idempotent(self):
        """PUT: Should be idempotent - adding existing follower returns 200"""
        # Bob already follows Alice
        Follow.objects.create(follower=self.bob, following=self.alice)
        
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # Bob adds himself again - should succeed with 200 (not 201)
        response = self.client.put(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('bob', 'bobpass')
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify only one follow relationship exists
        self.assertEqual(
            Follow.objects.filter(follower=self.bob, following=self.alice).count(),
            1
        )
    
    def test_unauthenticated_requests_forbidden(self):
        """All operations should require authentication"""
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        # GET without auth
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
        
        # DELETE without auth
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 401)
        
        # PUT without auth
        response = self.client.put(url)
        self.assertEqual(response.status_code, 401)
    
    def test_invalid_credentials_forbidden(self):
        """Invalid credentials should return 401"""
        url = f'/api/authors/{self.alice.id}/followers/{self.bob.id}'
        
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=self.get_basic_auth_header('alice', 'wrongpassword')
        )
        self.assertEqual(response.status_code, 401)
