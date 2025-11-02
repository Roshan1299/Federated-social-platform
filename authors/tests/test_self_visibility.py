"""
Test script for self-visibility functionality
User Story: As an author, I want all my entries visible to me until deleted.

This test file validates that authors can see all their entries regardless of visibility settings,
with comprehensive tests covering:
- All visibility types (PUBLIC, FRIENDS, PUBLIC_UNLISTED)
- Different user relationships (self, other users, followers, mutual followers)
- Edge cases (no posts, many posts of different types)

Main functionality tested:
- Self-visibility: Authors see all their own posts regardless of visibility
- Other users: Can only see PUBLIC posts
- Followers: Can see PUBLIC and PUBLIC_UNLISTED posts
- Mutual followers: Can see PUBLIC, PUBLIC_UNLISTED, and FRIENDS posts

Edge cases tested:
- User with no posts
- User with many posts of different visibility types
- Interaction between different user relationship types and visibility settings
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from authors.models import Post, Follow

User = get_user_model()

class SelfVisibilityTests(TestCase):
    def setUp(self):
        """Set up test users and client for self-visibility tests."""
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

    def test_self_visibility_on_own_profile_all_visibilities(self):
        """Test that authors see all their posts on their own profile regardless of visibility."""
        # Create posts with different visibility settings
        public_post = Post.objects.create(
            author=self.user,
            title='Public Post',
            content='This is a public post.',
            visibility='PUBLIC',
        )
        friends_post = Post.objects.create(
            author=self.user,
            title='Friends Post',
            content='This is a friends-only post.',
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
        
        # Author should see ALL their posts regardless of visibility
        self.assertContains(response, 'Public Post')
        self.assertContains(response, 'Friends Post')
        self.assertContains(response, 'Unlisted Post')
        
        print("✓ Self-visibility works for all visibility types on own profile")



    def test_self_visibility_edge_case_no_posts(self):
        """Test self-visibility when user has no posts."""
        # Create a user with no posts
        no_post_user = User.objects.create_user(
            username='nopostuser',
            password='testpass123',
            displayName='No Posts User'
        )
        
        self.client.login(username='nopostuser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[no_post_user.id]))
        self.assertEqual(response.status_code, 200)
        
        # Should show the profile but with no posts
        self.assertContains(response, 'No Posts User')
        # The posts container should exist but be empty
        
        print("✓ Self-visibility works when user has no posts")

    def test_self_visibility_edge_case_many_posts(self):
        """Test self-visibility when user has many posts of different types."""
        # Create multiple posts of different visibility types
        for i in range(3):
            Post.objects.create(
                author=self.user,
                title=f'Public Post {i}',
                content=f'This is public post {i}',
                visibility='PUBLIC',
            )
            Post.objects.create(
                author=self.user,
                title=f'Friends Post {i}',
                content=f'This is friends-only post {i}',
                visibility='FRIENDS',
            )
            Post.objects.create(
                author=self.user,
                title=f'Unlisted Post {i}',
                content=f'This is unlisted post {i}',
                visibility='PUBLIC_UNLISTED',
            )
        
        # Verify posts were actually created in the database
        total_posts = Post.objects.filter(author=self.user).count()
        self.assertEqual(total_posts, 9)  # 3 * 3 types
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        
        # User should see their posts regardless of visibility (within the display limit)
        content = response.content.decode('utf-8')
        
        # At least one post of each type should be visible on the page
        found_public = any(f'Public Post {i}' in content for i in range(3))
        found_friends = any(f'Friends Post {i}' in content for i in range(3))
        found_unlisted = any(f'Unlisted Post {i}' in content for i in range(3))
        
        self.assertTrue(found_public, "At least one public post should be visible to the author")
        self.assertTrue(found_friends, "At least one friends-only post should be visible to the author")
        self.assertTrue(found_unlisted, "At least one unlisted post should be visible to the author")
        
        print("✓ Self-visibility works with posts of different visibility types")

    def test_others_dont_see_private_posts(self):
        """Test that other users only see public posts on another user's profile."""
        # Create posts with different visibility settings
        Post.objects.create(
            author=self.user,
            title='Public Post',
            content='This is a public post.',
            visibility='PUBLIC',
        )
        Post.objects.create(
            author=self.user,
            title='Friends Post',
            content='This is a friends-only post.',
            visibility='FRIENDS',
        )
        Post.objects.create(
            author=self.user,
            title='Unlisted Post',
            content='This is an unlisted post.',
            visibility='PUBLIC_UNLISTED',
        )

        # Log in as different user
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        
        # Other users should only see PUBLIC posts (not FRIENDS or PUBLIC_UNLISTED posts)
        self.assertContains(response, 'Public Post')
        self.assertNotContains(response, 'Friends Post')  # Others shouldn't see friends-only
        self.assertNotContains(response, 'Unlisted Post')  # Others shouldn't see unlisted without direct link
        
        print("✓ Other users only see public posts on another profile")

    def test_followers_see_public_and_unlisted(self):
        """Test that followers can see public and unlisted posts but not friends-only."""
        # Create posts with different visibility settings
        Post.objects.create(
            author=self.user,
            title='Public Post',
            content='This is a public post.',
            visibility='PUBLIC',
        )
        Post.objects.create(
            author=self.user,
            title='Friends Post',
            content='This is a friends-only post.',
            visibility='FRIENDS',
        )
        Post.objects.create(
            author=self.user,
            title='Unlisted Post',
            content='This is an unlisted post.',
            visibility='PUBLIC_UNLISTED',
        )

        # Make other user follow the main user
        Follow.objects.create(follower=self.other_user, following=self.user)

        # Log in as follower
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        
        # Followers should see PUBLIC and PUBLIC_UNLISTED but not FRIENDS
        self.assertContains(response, 'Public Post')
        self.assertContains(response, 'Unlisted Post')  # Followers can see unlisted
        self.assertNotContains(response, 'Friends Post')  # Only mutual friends see friends-only
        
        print("✓ Followers see public and unlisted posts, but not friends-only")

    def test_mutual_followers_see_all_except_private(self):
        """Test that mutual followers can see public, unlisted, and friends-only posts."""
        # Create posts with different visibility settings
        Post.objects.create(
            author=self.user,
            title='Public Post',
            content='This is a public post.',
            visibility='PUBLIC',
        )
        Post.objects.create(
            author=self.user,
            title='Friends Post',
            content='This is a friends-only post.',
            visibility='FRIENDS',
        )
        Post.objects.create(
            author=self.user,
            title='Unlisted Post',
            content='This is an unlisted post.',
            visibility='PUBLIC_UNLISTED',
        )

        # Create mutual follow relationship
        Follow.objects.create(follower=self.other_user, following=self.user)
        Follow.objects.create(follower=self.user, following=self.other_user)

        # Log in as mutual follower
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(reverse('authors:author_profile', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)
        
        # Mutual followers should see PUBLIC, PUBLIC_UNLISTED, and FRIENDS posts
        self.assertContains(response, 'Public Post')
        self.assertContains(response, 'Unlisted Post')
        self.assertContains(response, 'Friends Post')  # Mutual friends can see friends-only
        
        print("✓ Mutual followers see all post types except private")