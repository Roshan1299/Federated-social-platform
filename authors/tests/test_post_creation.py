"""
Tests for User Stories 8, 9, 10, 11, 14, 16:
8. As an author, I want to make entries, so I can share my thoughts and pictures with other local authors.
9. As an author, I want to be able to make my entries 'public', so that everyone can see them.
10. As an author, entries I make can be in simple plain text, because I don't always want all the formatting features of CommonMark.
11. As an author, entries I make can be in CommonMark, so I can give my entries some basic formatting.
14. As an author, I want to be able to use my web-browser to manage/author my entries, so I don't have to use a clunky API.
16. As a reader, I can get a link to a public or unlisted entry, so I can send it to my friends over email, discord, slack, etc.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from authors.models import Post
import uuid

User = get_user_model()

class PostCreationTests(TestCase):
    """Test cases for user stories related to creating posts"""
    
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

    def test_create_plain_text_post(self):
        """Test US 10: Create plain text post"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test creating a plain text post via UI
        response = self.client.post(reverse('authors:create_post'), {
            'title': 'Test Plain Text Post',
            'content': 'Hello world! This is plain text content.',
            'contentType': 'text/plain',
            'visibility': 'PUBLIC'
        })
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Verify post was created
        post = Post.objects.get(title='Test Plain Text Post')
        self.assertEqual(post.content, 'Hello world! This is plain text content.')
        self.assertEqual(post.contentType, 'text/plain')
        self.assertEqual(post.visibility, 'PUBLIC')
        self.assertEqual(post.author, self.user)

    def test_create_commonmark_post(self):
        """Test US 11: Create CommonMark (markdown) post"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test creating a markdown post via UI
        response = self.client.post(reverse('authors:create_post'), {
            'title': 'Test Markdown Post',
            'content': '# Hello World\n\nThis is **markdown** content.',
            'contentType': 'text/markdown',
            'visibility': 'PUBLIC'
        })
        
        # Should redirect after successful creation
        self.assertEqual(response.status_code, 302)
        
        # Verify markdown post was created
        post = Post.objects.get(title='Test Markdown Post')
        self.assertEqual(post.content, '# Hello World\n\nThis is **markdown** content.')
        self.assertEqual(post.contentType, 'text/markdown')
        self.assertEqual(post.visibility, 'PUBLIC')
        self.assertEqual(post.author, self.user)

    def test_create_public_post(self):
        """Test US 9: Create public post that everyone can see"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create a public post
        response = self.client.post(reverse('authors:create_post'), {
            'title': 'Public Post',
            'content': 'This is a public post visible to everyone',
            'contentType': 'text/plain',
            'visibility': 'PUBLIC'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Log out and check if public post is visible to anonymous users
        self.client.logout()
        
        post = Post.objects.get(title='Public Post')
        response = self.client.get(reverse('authors:post_detail', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This is a public post visible to everyone')

    def test_create_image_post(self):
        """Test US 8: Create post with images"""
        self.client.login(username='testuser', password='testpass123')
        
        # Mock image file creation
        from io import BytesIO
        from PIL import Image as PILImage
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a simple 1x1 pixel image for testing
        image = PILImage.new('RGB', (1, 1), color='red')
        image_io = BytesIO()
        image.save(image_io, format='PNG')
        image_io.seek(0)
        
        # Create image file
        image_file = SimpleUploadedFile(
            name='test_image.png',
            content=image_io.read(),
            content_type='image/png'
        )
        
        # Create post with image
        response = self.client.post(reverse('authors:create_post'), {
            'title': 'Image Post',
            'content': 'Check out this image!',
            'contentType': 'image/png',
            'visibility': 'PUBLIC',
            'image': image_file
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify post was created with image
        post = Post.objects.get(title='Image Post')
        self.assertTrue(post.image)

    def test_post_creation_ui_access(self):
        """Test US 14: Web UI for managing/authoring entries"""
        # Test that users can access the create post form
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('authors:create_post'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Title')
        self.assertContains(response, 'Content')
        self.assertContains(response, 'Visibility')

    def test_post_editing_ui(self):
        """Test US 14: Web UI for editing entries"""
        # Create a post first
        post = Post.objects.create(
            title='Original Title',
            content='Original content',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            author=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test editing the post
        response = self.client.get(reverse('authors:edit_post', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        
        # Submit updated data
        response = self.client.post(reverse('authors:edit_post', kwargs={'post_id': post.id}), {
            'title': 'Updated Title',
            'content': 'Updated content',
            'contentType': 'text/plain',
            'visibility': 'PUBLIC'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify changes were saved
        post.refresh_from_db()
        self.assertEqual(post.title, 'Updated Title')
        self.assertEqual(post.content, 'Updated content')

    def test_post_deletion_ui(self):
        """Test US 14: Web UI for deleting entries"""
        # Create a post
        post = Post.objects.create(
            title='Post to Delete',
            content='Content to delete',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            author=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # Test that user can access delete page
        response = self.client.get(reverse('authors:delete_post', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Post to Delete')
        
        # Test deletion
        response = self.client.post(reverse('authors:delete_post', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 302)
        
        # Verify post was soft deleted
        post.refresh_from_db()
        self.assertTrue(post.deleted)

    def test_content_type_choices(self):
        """Test that all required content types are available (US 10, 11)"""
        # Check that text/plain and text/markdown are available
        content_type_field = Post._meta.get_field('contentType')
        choices = dict(content_type_field.choices)
        
        # Verify plain text is available
        self.assertIn('text/plain', choices)
        
        # Verify markdown is available
        self.assertIn('text/markdown', choices)
        
        # Verify image types are available (US 8)
        image_types = ['image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/webp']
        for img_type in image_types:
            self.assertIn(img_type, choices)

    def test_multiple_content_types(self):
        """Test that posts can be created with different content types"""
        self.client.login(username='testuser', password='testpass123')
        
        # Test various content types
        content_types = [
            ('text/plain', 'Plain text content'),
            ('text/markdown', '# Markdown content'),
        ]
        
        for content_type, content in content_types:
            with self.subTest(content_type=content_type):
                response = self.client.post(reverse('authors:create_post'), {
                    'title': f'Test {content_type}',
                    'content': content,
                    'contentType': content_type,
                    'visibility': 'PUBLIC'
                })
                
                self.assertEqual(response.status_code, 302)
                
                # Verify post was created with correct content type
                post = Post.objects.get(title=f'Test {content_type}')
                self.assertEqual(post.contentType, content_type)
                self.assertEqual(post.content, content)
                self.assertEqual(post.visibility, 'PUBLIC')

    """
    User story 16: As a reader, I can get a link to a public or unlisted entry, so I can send it to my friends over email, discord, slack, etc.
    """
    def test_access_post_via_link(self):
        """Test that a user can access a public post via a direct link."""
        post = Post.objects.create(
            title='Public Post',
            content='This is a public post.',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            author=self.user
        )

        response = self.client.get(reverse('authors:post_detail', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Post')
    
    def test_access_unlisted_post_via_link(self):
        """Test that a user can access an unlisted post via a direct link."""
        post = Post.objects.create(
            title='Unlisted Post',
            content='This is an unlisted post.',
            contentType='text/plain',
            visibility='PUBLIC_UNLISTED',
            author=self.user
        )

        response = self.client.get(reverse('authors:post_detail', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unlisted Post')
    
    def test_cannot_access_private_post_via_link(self):
        """Test that a user cannot access a private post via a direct link."""
        post = Post.objects.create(
            title='Private Post',
            content='This is a private post.',
            contentType='text/plain',
            visibility='FRIENDS',
            author=self.user
        )

        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('authors:post_detail', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 403)  # Forbidden

    
    def test_create_post_requires_login(self):
        """Anonymous users should not be able to create posts."""
        response = self.client.post(reverse('authors:create_post'), {
            'title': 'Anon Post',
            'content': 'Should not be created',
            'contentType': 'text/plain',
            'visibility': 'PUBLIC',
        })

        # Expect redirect to login or 403 depending on how you enforce it
        self.assertIn(response.status_code, [302, 403])
        self.assertFalse(Post.objects.filter(title='Anon Post').exists())

def test_cannot_create_post_with_empty_title(self):
    """Post must have a non-empty title."""
    self.client.login(username='testuser', password='testpass123')

    response = self.client.post(reverse('authors:create_post'), {
        'title': '',
        'content': 'Some content',
        'contentType': 'text/plain',
        'visibility': 'PUBLIC',
    })

    self.assertEqual(response.status_code, 200)  # form re-rendered
    self.assertFalse(Post.objects.filter(content='Some content').exists())


def test_cannot_create_post_with_empty_content(self):
    """Post must have non-empty content for text types."""
    self.client.login(username='testuser', password='testpass123')

    response = self.client.post(reverse('authors:create_post'), {
        'title': 'Empty content',
        'content': '',
        'contentType': 'text/plain',
        'visibility': 'PUBLIC',
    })

    self.assertEqual(response.status_code, 200)
    self.assertFalse(Post.objects.filter(title='Empty content').exists())


def test_invalid_content_type_rejected(self):
    """Form should reject contentType that is not one of the choices."""
    self.client.login(username='testuser', password='testpass123')

    response = self.client.post(reverse('authors:create_post'), {
        'title': 'Bad type',
        'content': 'Some content',
        'contentType': 'application/json',  # not in choices
        'visibility': 'PUBLIC',
    })

    self.assertEqual(response.status_code, 200)
    self.assertFalse(Post.objects.filter(title='Bad type').exists())


def test_image_content_type_requires_image_file(self):
    """If contentType is image/* but no image is uploaded, form should fail."""
    self.client.login(username='testuser', password='testpass123')

    response = self.client.post(reverse('authors:create_post'), {
        'title': 'Image without file',
        'content': 'This should fail',
        'contentType': 'image/png',
        'visibility': 'PUBLIC',
        # no 'image' in POST
    })

    self.assertEqual(response.status_code, 200)
    self.assertFalse(Post.objects.filter(title='Image without file').exists())


def test_cannot_spoof_author_on_post_creation(self):
    """Author field in POST data should be ignored; request.user must be the author."""
    self.client.login(username='testuser', password='testpass123')

    response = self.client.post(reverse('authors:create_post'), {
        'title': 'Spoofed Author',
        'content': 'Trying to spoof author',
        'contentType': 'text/plain',
        'visibility': 'PUBLIC',
        'author': str(self.other_user.id),  # attempt to spoof
    })

    self.assertEqual(response.status_code, 302)

    post = Post.objects.get(title='Spoofed Author')
    self.assertEqual(post.author, self.user)          # still current user
    self.assertNotEqual(post.author, self.other_user)


def test_create_friends_only_post(self):
    """Authors can create FRIENDS-only posts via the UI."""
    self.client.login(username='testuser', password='testpass123')

    response = self.client.post(reverse('authors:create_post'), {
        'title': 'Friends Only Post',
        'content': 'Only friends should see this',
        'contentType': 'text/plain',
        'visibility': 'FRIENDS',
    })

    self.assertEqual(response.status_code, 302)
    post = Post.objects.get(title='Friends Only Post')
    self.assertEqual(post.visibility, 'FRIENDS')
    self.assertEqual(post.author, self.user)


def test_create_unlisted_post(self):
    """Authors can create PUBLIC_UNLISTED posts via the UI."""
    self.client.login(username='testuser', password='testpass123')

    response = self.client.post(reverse('authors:create_post'), {
        'title': 'Unlisted Post',
        'content': 'Unlisted but shareable by link',
        'contentType': 'text/plain',
        'visibility': 'PUBLIC_UNLISTED',
    })

    self.assertEqual(response.status_code, 302)
    post = Post.objects.get(title='Unlisted Post')
    self.assertEqual(post.visibility, 'PUBLIC_UNLISTED')


def test_title_too_long_rejected(self):
    """Title exceeding max_length should be rejected."""
    self.client.login(username='testuser', password='testpass123')
    long_title = 'a' * 300  # adjust based on your model's max_length

    response = self.client.post(reverse('authors:create_post'), {
        'title': long_title,
        'content': 'Content with long title',
        'contentType': 'text/plain',
        'visibility': 'PUBLIC',
    })

    self.assertEqual(response.status_code, 200)
    self.assertFalse(Post.objects.filter(content='Content with long title').exists())
