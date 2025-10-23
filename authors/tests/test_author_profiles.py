"""
Tests for user stories 5, 6, 7, 20. 
5. As an author, I want a public page with my profile information, so that I can link people to it.
6. As an author, I want to be able to edit my profile: name, description, picture, and GitHub.
7. As an author, I want to be able to use my web browser to manage my profile, so I don't have to use a clunky API.
20. As an author, I want my profile page to show my public entries [most recent first], so they can decide if they want to follow me.
"""
from typing import cast
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from authors.models import Author
from authors.models import Post

User = get_user_model()

class AuthorProfileTests(TestCase):
    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = cast(Author, User.objects.create_user( # use cast to specify type. This avoids type warnings later when accessing Author fields.
            username='testuser',
            password='testpass123',
            displayName='Test User'
        ))
        self.other_user = cast(Author, User.objects.create_user(
            username='otheruser',
            password='otherpass123',
            displayName='Other User'
        ))

    def test_view_own_profile(self):
        """Test that an author can view their own profile."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test User')
        print("✓ Author can view their own profile")

    def test_view_other_profile(self):
        """Test that an author can view another author's profile."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.other_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Other User')
        print("✓ Author can view another author's profile")
    
    def test_edit_own_profile(self):
        """Test that an author can edit their own profile."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('authors:edit_profile', args=[self.user.id]),
            {
                'displayName': 'Updated Test User',
                'github': 'https://github.com/updateduser',
                'description': 'Updated description for test user.'
            }
        )
        self.assertEqual(response.status_code, 302)  # Redirect after successful edit
        self.user.refresh_from_db()
        self.assertEqual(self.user.displayName, 'Updated Test User')
        self.assertEqual(self.user.github, 'https://github.com/updateduser')
        print("✓ Author can edit their own profile")

    def test_edit_profile_image(self):
        """Test that an author can edit their profile image."""
        self.client.login(username='testuser', password='testpass123')
        self.assertEqual(self.user.profileImage, None) # self.user shouldn't have a profile picture yet

        with open('authors/tests/profile_image_tester.webp', 'rb') as img:
            response = self.client.post(
                reverse('authors:edit_profile', args=[self.user.id]),
                {
                    'displayName': 'Test User with Image',
                    'profileImage': img,
                }
            )
        self.assertEqual(response.status_code, 302)  # Redirect after successful edit
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.profileImage)
        print("✓ Author can edit their profile image")

    def test_edit_profile_unauthenticated(self):
        """Test that an unauthenticated user cannot edit a profile."""
        response = self.client.post(
            reverse('authors:edit_profile', args=[self.user.id]),
            {
                'displayName': 'Hacked Name',
                'github': 'https://github.com/hackeduser',
                'description': 'Hacked description for test user.'
            }
        )
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
        # Check that the redirect location is the login page
        self.assertTrue(response.url.startswith(reverse('login')))
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.displayName, 'Hacked Name')
        self.assertNotEqual(self.user.github, 'https://github.com/hackeduser')
        self.assertNotEqual(self.user.description, 'Hacked description for test user.')
        print("✓ Unauthenticated user cannot edit profile")

    def test_edit_other_profile_forbidden(self):
        """Test that an author cannot edit another author's profile."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('authors:edit_profile', args=[self.other_user.id]),
            {
                'displayName': 'Hacked Name',
                'github': 'https://github.com/hackeduser'
            }
        )
        self.assertEqual(response.status_code, 403)  # Forbidden
        self.other_user.refresh_from_db()
        self.assertNotEqual(self.other_user.displayName, 'Hacked Name')
        self.assertNotEqual(self.other_user.github, 'https://github.com/hackeduser')
        print("✓ Author cannot edit another author's profile")

    def test_profile_shows_public_posts(self):
        """Test that an author's profile page shows their public posts."""
        # Create public and private posts for the user
        public_post = Post.objects.create(
            author=self.other_user,
            title='Public Post',
            content='This is a public post.',
            visibility='PUBLIC_UNLISTED',
        )
        private_post = Post.objects.create(
            author=self.other_user,
            title='Private Post',
            content='This is a private post.',
            visibility='FRIENDS',
        )
        unlisted_post = Post.objects.create(
            author=self.other_user,
            title='Unlisted Post',
            content='This is an unlisted post.',
            visibility='PUBLIC_UNLISTED',
            
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.other_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Post')
        self.assertNotContains(response, 'Private Post')
        self.assertNotContains(response, 'Unlisted Post')
        print("✓ Author's profile page shows their public posts only to other authors")
    
    def test_profile_shows_all_posts_to_self(self):
        """Test that an author sees all their posts on their own profile."""
        # Create public, private, and unlisted posts for the user
        public_post = Post.objects.create(
            author=self.user,
            title='Public Post',
            content='This is a public post.',
            visibility='PUBLIC_UNLISTED',
        )
        private_post = Post.objects.create(
            author=self.user,
            title='Private Post',
            content='This is a private post.',
            visibility='FRIENDS',
        )
        unlisted_post = Post.objects.create(
            author=self.user,
            title='Unlisted Post',
            content='This is an unlisted post.',
            visibility='PUBLIC_UNLISTED',
            
        )

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Post')
        self.assertContains(response, 'Private Post')
        self.assertContains(response, 'Unlisted Post')
        print("✓ Author sees all their posts on their own profile")
    
    def test_profile_shows_public_and_unlisted_posts_to_followers(self):
        """Test that an author sees public and unlisted posts of authors they follow."""
        # Create public, private, and unlisted posts for the other user
        public_post = Post.objects.create(
            author=self.other_user,
            title='Public Post',
            content='This is a public post.',
            visibility='PUBLIC_UNLISTED',
        )
        private_post = Post.objects.create(
            author=self.other_user,
            title='Private Post',
            content='This is a private post.',
            visibility='FRIENDS',
        )
        unlisted_post = Post.objects.create(
            author=self.other_user,
            title='Unlisted Post',
            content='This is an unlisted post.',
            visibility='PUBLIC_UNLISTED',
            
        )

        # Make testuser follow otheruser
        from authors.models import Follow
        Follow.objects.create(follower=self.user, following=self.other_user)

        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.other_user.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Public Post')
        self.assertNotContains(response, 'Private Post')
        self.assertContains(response, 'Unlisted Post')
        print("✓ Author sees public and unlisted posts of authors they follow")

    