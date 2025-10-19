"""
Tests for user stories 5, 6, 7. 
5. As an author, I want a public page with my profile information, so that I can link people to it.
6. As an author, I want to be able to edit my profile: name, description, picture, and GitHub.
7. As an author, I want to be able to use my web browser to manage my profile, so I don't have to use a clunky API.
"""
from typing import cast
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from authors.models import Author

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

        with open('authors/tests/TEST_IMAGE.webp', 'rb') as img:
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

    