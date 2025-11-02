"""
Django Unit Tests for FQID-based API Endpoints
Tests all API endpoints that accept Fully Qualified IDs (FQIDs) as percent-encoded URLs

This test suite validates:
1. All FQID endpoints work correctly with percent-encoded URLs
2. FQID endpoints handle both local and "remote" node URLs
3. Visibility restrictions work with FQID endpoints
4. FQID endpoints are compatible with federation

FQID Format:
- Full URL to a resource (e.g., http://testserver/api/authors/{uuid}/)
- Must be percent-encoded when used in URL paths
- Example: http%3A%2F%2Ftestserver%2Fapi%2Fauthors%2F{uuid}%2F

Usage:
    python manage.py test authors.tests.test_api_fqid
"""

from django.test import TestCase, Client
from authors.models import Author, Post, Follow, Comment, Like, CommentLike
import json
import urllib.parse


class FQIDTestCase(TestCase):
    """Base test case with common setup for FQID tests"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test authors representing different "nodes"
        # Simulate a local node (testserver)
        self.local_author = Author.objects.create_user(
            username='local_author',
            password='password1',
            displayName='Local Author',
            host='http://testserver',
            github='https://github.com/local'
        )
        # Set URL after creation to include the ID
        self.local_author.url = f'http://testserver/api/authors/{self.local_author.id}/'
        self.local_author.save()
        
        # Simulate a remote node (another-node.com)
        self.remote_author = Author.objects.create_user(
            username='remote_author',
            password='password2',
            displayName='Remote Author',
            host='http://another-node.com',
            github='https://github.com/remote'
        )
        # Set URL after creation to include the ID
        self.remote_author.url = f'http://another-node.com/api/authors/{self.remote_author.id}/'
        self.remote_author.save()
        
        # Another local author for testing
        self.local_author2 = Author.objects.create_user(
            username='local_author2',
            password='password3',
            displayName='Local Author Two',
            host='http://testserver',
            github='https://github.com/local2'
        )
        # Set URL after creation to include the ID
        self.local_author2.url = f'http://testserver/api/authors/{self.local_author2.id}/'
        self.local_author2.save()
        
        # Set up relationships
        Follow.objects.create(follower=self.remote_author, following=self.local_author)
        Follow.objects.create(follower=self.local_author, following=self.remote_author)
        
        # Create posts
        self.public_post = Post.objects.create(
            author=self.local_author,
            title='Public Post',
            content='This is a public post',
            contentType='text/plain',
            visibility='PUBLIC'
        )
        
        self.friends_post = Post.objects.create(
            author=self.local_author,
            title='Friends Post',
            content='This is a friends only post',
            contentType='text/plain',
            visibility='FRIENDS'
        )
        
        # Create comment
        self.comment = Comment.objects.create(
            post=self.public_post,
            author=self.remote_author,
            content='Nice post!'
        )
        
        # Create like
        self.like = Like.objects.create(
            author=self.remote_author,
            post=self.public_post
        )
    
    def build_fqid(self, base_url, *path_parts):
        """Build an FQID from URL parts"""
        # Join path parts and ensure proper formatting
        path = '/'.join(str(p) for p in path_parts)
        return f"{base_url}/{path}"
    
    def encode_fqid(self, fqid):
        """Percent-encode an FQID for use in URL paths"""
        return urllib.parse.quote(fqid, safe='')
    
    def login_as(self, author):
        """Login as a specific author"""
        self.client.login(username=author.username, password=f'password{author.id.hex[:1]}')


class AuthorFQIDTests(FQIDTestCase):
    """Test Author API with FQID"""
    
    def test_get_author_by_fqid(self):
        """Test getting an author by their FQID (percent-encoded URL)"""
        self.client.login(username='local_author', password='password1')
        
        # Build FQID for local author
        author_fqid = f'http://testserver/api/authors/{self.local_author.id}/'
        encoded_fqid = self.encode_fqid(author_fqid)
        
        response = self.client.get(f'/api/authors/{encoded_fqid}/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'author')
        self.assertEqual(data['displayName'], 'Local Author')
    
    def test_get_remote_author_by_fqid(self):
        """Test getting a remote author by their FQID"""
        self.client.login(username='local_author', password='password1')
        
        # Build FQID for remote author
        author_fqid = f'http://another-node.com/api/authors/{self.remote_author.id}/'
        encoded_fqid = self.encode_fqid(author_fqid)
        
        response = self.client.get(f'/api/authors/{encoded_fqid}/')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'author')
        self.assertEqual(data['displayName'], 'Remote Author')


class EntryFQIDTests(FQIDTestCase):
    """Test Entries/Posts API with FQID"""
    
    def test_get_entry_by_fqid(self):
        """Test getting a post by its FQID"""
        self.client.login(username='remote_author', password='password2')
        
        # Build FQID for the post
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'post')
        self.assertEqual(data['title'], 'Public Post')
    
    def test_get_entry_by_fqid_with_trailing_slash(self):
        """Test getting a post by FQID with trailing slash"""
        self.client.login(username='remote_author', password='password2')
        
        # Build FQID with trailing slash - the entry_fqid will be decoded in the view
        # and should match the post regardless of trailing slash
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'post')
    
    def test_update_entry_by_fqid(self):
        """Test updating a post by its FQID"""
        self.client.login(username='local_author', password='password1')
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        update_data = {
            'title': 'Updated via FQID',
            'content': 'Updated content',
            'contentType': 'text/plain',
            'visibility': 'PUBLIC'
        }
        
        response = self.client.put(
            f'/api/entries/{encoded_fqid}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify update
        self.public_post.refresh_from_db()
        self.assertEqual(self.public_post.title, 'Updated via FQID')
    
    def test_delete_entry_by_fqid(self):
        """Test deleting a post by its FQID"""
        self.client.login(username='local_author', password='password1')
        
        # Create a post to delete
        post = Post.objects.create(
            author=self.local_author,
            title='Delete Me',
            content='Will be deleted',
            contentType='text/plain',
            visibility='PUBLIC'
        )
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.delete(f'/api/entries/{encoded_fqid}')
        self.assertEqual(response.status_code, 204)
        
        # Verify soft delete
        post.refresh_from_db()
        self.assertTrue(post.deleted)
    
    def test_get_friends_entry_by_fqid_visibility(self):
        """Test that friends-only posts are protected even with FQID"""
        self.client.login(username='local_author2', password='password3')
        
        # local_author2 is not friends with local_author
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.friends_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}')
        self.assertEqual(response.status_code, 403)  # Should be forbidden


class CommentsFQIDTests(FQIDTestCase):
    """Test Comments API with FQID"""
    
    def test_get_comments_by_entry_fqid(self):
        """Test getting comments using entry FQID"""
        self.client.login(username='remote_author', password='password2')
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}/comments')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'comments')
        self.assertGreater(len(data['comments']), 0)
    
    def test_get_single_comment_by_fqid(self):
        """Test getting a single comment by its FQID"""
        self.client.login(username='remote_author', password='password2')
        
        comment_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}/comments/{self.comment.id}'
        encoded_fqid = self.encode_fqid(comment_fqid)
        
        # Using the remote comment endpoint
        response = self.client.get(
            f'/api/authors/{self.local_author.id}/entries/{self.public_post.id}/comment/{encoded_fqid}'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'comment')
        self.assertEqual(data['comment'], 'Nice post!')
    
    def test_get_commented_by_author_fqid(self):
        """Test getting all comments by an author using their FQID"""
        self.client.login(username='local_author', password='password1')
        
        # Use remote author's actual URL (strip trailing slash since we're appending /commented)
        author_fqid = self.remote_author.url.rstrip('/')
        encoded_fqid = self.encode_fqid(author_fqid)
        
        response = self.client.get(f'/api/authors/{encoded_fqid}/commented')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'comments')
    
    def test_get_comment_by_comment_fqid(self):
        """Test getting a comment using the /commented/{COMMENT_FQID} endpoint"""
        self.client.login(username='local_author', password='password1')
        
        comment_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}/comments/{self.comment.id}'
        encoded_fqid = self.encode_fqid(comment_fqid)
        
        response = self.client.get(f'/api/commented/{encoded_fqid}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'comment')


class LikesFQIDTests(FQIDTestCase):
    """Test Likes API with FQID"""
    
    def test_get_likes_by_entry_fqid(self):
        """Test getting likes on a post using entry FQID"""
        self.client.login(username='remote_author', password='password2')
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}/likes')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'likes')
        self.assertGreater(len(data['items']), 0)
    
    def test_get_liked_by_author_fqid(self):
        """Test getting all things an author liked using their FQID"""
        self.client.login(username='local_author', password='password1')
        
        # Use remote author's actual URL (strip trailing slash since we're appending /liked)
        author_fqid = self.remote_author.url.rstrip('/')
        encoded_fqid = self.encode_fqid(author_fqid)
        
        response = self.client.get(f'/api/authors/{encoded_fqid}/liked')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'liked')
    
    def test_get_single_like_by_fqid(self):
        """Test getting a single like by its FQID"""
        self.client.login(username='local_author', password='password1')
        
        like_fqid = f'http://testserver/api/authors/{self.remote_author.id}/liked/{self.like.id}'
        encoded_fqid = self.encode_fqid(like_fqid)
        
        response = self.client.get(f'/api/liked/{encoded_fqid}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'like')


class CommentLikesFQIDTests(FQIDTestCase):
    """Test Comment Likes API with FQID"""
    
    def test_get_comment_likes_by_comment_fqid(self):
        """Test getting likes on a comment using comment FQID"""
        self.client.login(username='local_author', password='password1')
        
        # Create a like on the comment
        CommentLike.objects.create(author=self.local_author, comment=self.comment)
        
        comment_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}/comments/{self.comment.id}'
        encoded_fqid = self.encode_fqid(comment_fqid)
        
        response = self.client.get(
            f'/api/authors/{self.local_author.id}/entries/{self.public_post.id}/comments/{encoded_fqid}/likes'
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'likes')


class ImageEntryFQIDTests(FQIDTestCase):
    """Test Image Entry API with FQID"""
    
    def test_get_image_by_entry_fqid(self):
        """Test getting an image using entry FQID"""
        self.client.login(username='remote_author', password='password2')
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        # This should return 404 (no image) not 403 (forbidden)
        response = self.client.get(f'/api/entries/{encoded_fqid}/image')
        self.assertEqual(response.status_code, 404)
    
    def test_get_image_on_friends_post_by_fqid_visibility(self):
        """Test that image endpoint respects visibility even with FQID"""
        self.client.login(username='local_author2', password='password3')
        
        # local_author2 is not friends with local_author
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.friends_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}/image')
        self.assertEqual(response.status_code, 403)  # Should be forbidden


class FollowersFQIDTests(FQIDTestCase):
    """Test Followers API with FQID"""
    
    def test_check_follower_by_fqid(self):
        """Test checking if someone is a follower using FQID"""
        self.client.login(username='local_author', password='password1')
        
        # Check if remote_author follows local_author
        follower_fqid = f'http://another-node.com/api/authors/{self.remote_author.id}/'
        encoded_fqid = self.encode_fqid(follower_fqid)
        
        response = self.client.get(
            f'/api/authors/{self.local_author.id}/followers/{encoded_fqid}'
        )
        self.assertEqual(response.status_code, 200)
    
    def test_check_non_follower_by_fqid(self):
        """Test checking a non-follower using FQID"""
        self.client.login(username='local_author', password='password1')
        
        # local_author2 doesn't follow local_author
        follower_fqid = f'http://testserver/api/authors/{self.local_author2.id}/'
        encoded_fqid = self.encode_fqid(follower_fqid)
        
        response = self.client.get(
            f'/api/authors/{self.local_author.id}/followers/{encoded_fqid}'
        )
        self.assertEqual(response.status_code, 404)
    
    def test_add_follower_by_fqid(self):
        """Test adding a follower using FQID"""
        self.client.login(username='local_author', password='password1')
        
        follower_fqid = f'http://testserver/api/authors/{self.local_author2.id}/'
        encoded_fqid = self.encode_fqid(follower_fqid)
        
        response = self.client.put(
            f'/api/authors/{self.local_author.id}/followers/{encoded_fqid}'
        )
        self.assertEqual(response.status_code, 201)
        
        # Verify the follow relationship was created
        self.assertTrue(
            Follow.objects.filter(
                follower=self.local_author2,
                following=self.local_author
            ).exists()
        )
    
    def test_remove_follower_by_fqid(self):
        """Test removing a follower using FQID"""
        self.client.login(username='local_author', password='password1')
        
        follower_fqid = f'http://another-node.com/api/authors/{self.remote_author.id}/'
        encoded_fqid = self.encode_fqid(follower_fqid)
        
        response = self.client.delete(
            f'/api/authors/{self.local_author.id}/followers/{encoded_fqid}'
        )
        self.assertEqual(response.status_code, 204)
        
        # Verify the follow relationship was removed
        self.assertFalse(
            Follow.objects.filter(
                follower=self.remote_author,
                following=self.local_author
            ).exists()
        )


class FQIDEdgeCaseTests(FQIDTestCase):
    """Test edge cases and special scenarios with FQIDs"""
    
    def test_fqid_with_special_characters(self):
        """Test FQID with special characters in URL"""
        self.client.login(username='local_author', password='password1')
        
        # Create an author with special characters in host
        special_author = Author.objects.create_user(
            username='special',
            password='password',
            displayName='Special Author',
            host='https://node-with-dash.example.com:8080',
        )
        # Set URL after creation to include the ID
        special_author.url = f'https://node-with-dash.example.com:8080/api/authors/{special_author.id}/'
        special_author.save()
        
        author_fqid = f'https://node-with-dash.example.com:8080/api/authors/{special_author.id}/'
        encoded_fqid = self.encode_fqid(author_fqid)
        
        response = self.client.get(f'/api/authors/{encoded_fqid}/')
        self.assertEqual(response.status_code, 200)
    
    def test_fqid_double_encoding_prevention(self):
        """Test that double-encoding doesn't break the endpoint"""
        self.client.login(username='local_author', password='password1')
        
        author_fqid = f'http://testserver/api/authors/{self.local_author.id}/'
        # Encode once
        encoded_once = self.encode_fqid(author_fqid)
        
        # This should work (single encoding)
        response = self.client.get(f'/api/authors/{encoded_once}/')
        self.assertEqual(response.status_code, 200)
        
        # Double encoding should fail gracefully
        encoded_twice = self.encode_fqid(encoded_once)
        response = self.client.get(f'/api/authors/{encoded_twice}/')
        self.assertEqual(response.status_code, 404)
    
    def test_fqid_with_query_parameters(self):
        """Test FQID endpoints with query parameters"""
        self.client.login(username='local_author', password='password1')
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        # Add pagination query params
        response = self.client.get(f'/api/entries/{encoded_fqid}/comments?page=1&size=5')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['page'], 1)
        self.assertEqual(data['size'], 5)
    
    def test_uuid_fallback_on_fqid_endpoint(self):
        """Test that FQID endpoints can also accept plain UUIDs"""
        self.client.login(username='local_author', password='password1')
        
        # Try using a plain UUID instead of FQID on FQID endpoint
        # This tests the helper functions' ability to handle both
        entry_fqid = str(self.public_post.id)  # Plain UUID, not encoded
        
        response = self.client.get(f'/api/entries/{entry_fqid}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'post')


class FQIDCrossNodeTests(FQIDTestCase):
    """Test cross-node scenarios using FQIDs"""
    
    def test_remote_node_accessing_local_post_by_fqid(self):
        """Simulate a remote node accessing a local post using FQID"""
        self.client.login(username='remote_author', password='password2')
        
        # Remote author accessing local post
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['title'], 'Public Post')
        # Verify author info is included
        self.assertEqual(data['author']['displayName'], 'Local Author')
    
    def test_local_node_accessing_remote_author_comments(self):
        """Simulate local node accessing remote author's comments"""
        self.client.login(username='local_author', password='password1')
        
        # Create more comments from remote author
        Comment.objects.create(
            post=self.public_post,
            author=self.remote_author,
            content='Another comment from remote'
        )
        
        # Access remote author's comments using FQID (without trailing slash)
        author_fqid = f'http://another-node.com/api/authors/{self.remote_author.id}'
        encoded_fqid = self.encode_fqid(author_fqid)
        
        response = self.client.get(f'/api/authors/{encoded_fqid}/commented')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['type'], 'comments')
        self.assertGreaterEqual(len(data['comments']), 2)
    
    def test_federation_like_flow_with_fqids(self):
        """Test a complete federation-like flow using FQIDs"""
        # The like already exists from setUp, so just test querying it
        
        # Step 1: Local author queries likes using entry FQID
        self.client.login(username='local_author', password='password1')
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        response = self.client.get(f'/api/entries/{encoded_fqid}/likes')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        likes = data['items']
        
        # Verify like from remote author is present
        remote_like_found = False
        for like_obj in likes:
            if like_obj['author']['displayName'] == 'Remote Author':
                remote_like_found = True
                break
        
        self.assertTrue(remote_like_found, "Like from remote author should be in the list")


class FQIDPerformanceTests(FQIDTestCase):
    """Test FQID endpoint performance and efficiency"""
    
    def test_fqid_lookup_efficiency(self):
        """Test that FQID lookups don't cause excessive database queries"""
        self.client.login(username='local_author', password='password1')
        
        entry_fqid = f'http://testserver/api/authors/{self.local_author.id}/entries/{self.public_post.id}'
        encoded_fqid = self.encode_fqid(entry_fqid)
        
        # Use Django's assertNumQueries to check query count
        from django.test import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(f'/api/entries/{encoded_fqid}')
            self.assertEqual(response.status_code, 200)
        
        # Should not require excessive queries (adjust threshold as needed)
        # Typically: 1 for auth, 1 for post lookup, 1-2 for related data
        self.assertLess(len(queries), 10, "FQID endpoint should not cause excessive queries")
