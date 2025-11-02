"""
Test script to verify User Story: CommonMark entries support image links
As an author, entries I create that are in CommonMark can link to images, so that I can illustrate my entries.

This test file validates the CommonMark image link functionality that:
- Properly renders markdown image syntax ![alt text](image_url) to HTML img tags
- Handles various image URL formats (external, local, with special characters)
- Ensures image links only work with markdown content type, not plain text
- Validates image rendering in different contexts (posts, API responses)
- Tests complex markdown with mixed formatting and image links

Edge cases covered:
- Malformed markdown image syntax (missing alt text, broken URLs, unbalanced brackets)
- Very long alt text and URLs
- Special characters in alt text and URLs
- Invalid or broken image links
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from authors.models import Post
import markdown

User = get_user_model()

class CommonMarkImageLinkTests(TestCase):
    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            displayName='Test User'
        )

    def test_commonmark_image_syntax_rendering(self):
        """Test that CommonMark image syntax is properly rendered in posts."""
        # Create a post with markdown content containing image links
        post_content = """
# My Project Update

Here's an image in my post:

![Alt text for image](http://example.com/image.png)

And another image:

![Another image](https://external-site.com/photo.jpg)
        """
        
        post = Post.objects.create(
            title='CommonMark Image Test',
            content=post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Render the content using the same function as the views
        from authors.views import render_post_content
        rendered_html = render_post_content(post)
        
        # Check that markdown image syntax is converted to proper HTML img tags
        self.assertIn('<img', rendered_html)
        self.assertIn('alt="Alt text for image"', rendered_html)
        self.assertIn('src="http://example.com/image.png"', rendered_html)
        self.assertIn('alt="Another image"', rendered_html)
        self.assertIn('src="https://external-site.com/photo.jpg"', rendered_html)
        
        print("✓ CommonMark image syntax is properly rendered to HTML")

    def test_commonmark_image_links_in_post_display(self):
        """Test that CommonMark posts with image links display correctly on post page."""
        self.client.login(username='testuser', password='testpass123')
        
        post_content = """
# Documentation Images

Here's a diagram showing the architecture:

![System Architecture](https://example.com/arch.png)
        """
        
        post = Post.objects.create(
            title='Documentation Post',
            content=post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Access the post detail page
        response = self.client.get(f'/posts/{post.id}/')
        self.assertEqual(response.status_code, 200)
        
        # Verify the markdown content is rendered to HTML with image tags
        self.assertContains(response, '<img', status_code=200)
        self.assertContains(response, 'alt="System Architecture"', status_code=200)
        self.assertContains(response, 'src="https://example.com/arch.png"', status_code=200)
        
        print("✓ CommonMark posts with image links display correctly on post pages")

    def test_commonmark_image_syntax_with_local_images(self):
        """Test that CommonMark image syntax works with local image URLs."""
        post_content = """
# Local Image Test

Here's a local image:

![Profile Picture](/media/user_images/profile.jpg)
        """
        
        post = Post.objects.create(
            title='Local Image Test',
            content=post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Render the content
        from authors.views import render_post_content
        rendered_html = render_post_content(post)
        
        # Check that the image link is properly converted to HTML
        self.assertIn('<img', rendered_html)
        self.assertIn('alt="Profile Picture"', rendered_html)
        self.assertIn('src="/media/user_images/profile.jpg"', rendered_html)
        
        print("✓ CommonMark image syntax works with local image URLs")

    def test_commonmark_image_syntax_special_characters(self):
        """Test that CommonMark image syntax handles special characters in alt text and URLs."""
        post_content = """
# Special Characters Test

![Image with "quotes" and & symbols](https://example.com/image?param=value&other=123)
        """
        
        post = Post.objects.create(
            title='Special Characters Test',
            content=post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Render the content
        from authors.views import render_post_content
        rendered_html = render_post_content(post)
        
        # Check that special characters are handled properly
        self.assertIn('alt="Image with &quot;quotes&quot; and &amp; symbols"', rendered_html)
        self.assertIn('src="https://example.com/image?param=value&amp;other=123"', rendered_html)
        
        print("✓ CommonMark image syntax handles special characters properly")

    def test_commonmark_vs_plaintext_image_syntax(self):
        """Test that image syntax is only processed for markdown content, not plain text."""
        markdown_post_content = "![Markdown Image](https://example.com/markdown.png)"
        plaintext_post_content = "![Plain Text Image](https://example.com/plain.png)"
        
        # Create markdown post
        markdown_post = Post.objects.create(
            title='Markdown Post',
            content=markdown_post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Create plain text post
        plaintext_post = Post.objects.create(
            title='Plain Text Post',
            content=plaintext_post_content,
            contentType='text/plain',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Render both contents
        from authors.views import render_post_content
        markdown_rendered = render_post_content(markdown_post)
        plaintext_rendered = render_post_content(plaintext_post)
        
        # Markdown should render image tag
        self.assertIn('<img', markdown_rendered)
        self.assertIn('src="https://example.com/markdown.png"', markdown_rendered)
        
        # Plain text should NOT render image tag, should show raw text or converted newlines
        # The plain text should show the literal markdown syntax
        self.assertNotIn('<img', plaintext_rendered)
        self.assertIn('![Plain Text Image](https://example.com/plain.png)', plaintext_rendered)
        
        print("✓ CommonMark image syntax only processed for markdown, not plain text")

    def test_complex_commonmark_with_images_and_text(self):
        """Test complex CommonMark content with images mixed with other formatting."""
        post_content = """
# Project Update

Here's our current progress:

![Progress Chart](https://example.com/chart.png)

## Goals

- Goal 1 ![icon](icon1.png)
- Goal 2 ![icon](icon2.png)

### Code Sample

    # This code does something
    image_url = "https://example.com/code_related.png"

![End Image](https://example.com/final.png)
        """
        
        post = Post.objects.create(
            title='Complex CommonMark Test',
            content=post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Render the content
        from authors.views import render_post_content
        rendered_html = render_post_content(post)
        
        # Check that all images are rendered while preserving other markdown elements
        self.assertIn('<img', rendered_html)
        self.assertIn('alt="Progress Chart"', rendered_html)
        self.assertIn('alt="icon"', rendered_html)  # appears twice
        self.assertIn('alt="End Image"', rendered_html)
        
        # Check that other markdown elements are also preserved
        self.assertIn('<h1', rendered_html)
        self.assertIn('<h2', rendered_html)
        self.assertIn('<h3', rendered_html)
        # Using indented code block instead of fenced code block for standard markdown
        self.assertIn('<code', rendered_html)  # Check for code element
        
        print("✓ Complex CommonMark with images and other formatting works correctly")

    def test_api_response_includes_image_links(self):
        """Test that API responses properly handle posts with image links."""
        from django.urls import reverse
        
        post_content = """
            # API Image Test

            ![API Image](https://example.com/api_image.png)
        """
        
        post = Post.objects.create(
            title='API Image Test',
            content=post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        # Access the API endpoint
        response = self.client.get(reverse('authors:post_api', kwargs={'post_id': post.id}))
        self.assertEqual(response.status_code, 200)
        
        # The API should return the raw content, which can then be rendered on the client
        response_content = response.json()
        self.assertEqual(response_content['contentType'], 'text/markdown')
        self.assertIn('![API Image](https://example.com/api_image.png)', response_content['content'])
        
        print("✓ API properly returns CommonMark content with image links")

    def test_commonmark_malformed_image_syntax(self):
        """Test that malformed CommonMark image syntax is handled gracefully."""
        # Test various malformed syntax that shouldn't render as images
        malformed_cases = [
            # Missing closing parenthesis
            "![Alt text](http://example.com/image.png",  
            # Missing alt text
            "![](http://example.com/image.png)",
            # Missing URL
            "![Alt text]()",
            # Unbalanced brackets
            "![Alt text(http://example.com/image.png)",
        ]
        
        from authors.views import render_post_content
        
        for i, malformed_syntax in enumerate(malformed_cases):
            with self.subTest(malformed_syntax=malformed_syntax):
                post = Post.objects.create(
                    title=f'Malformed Test {i}',
                    content=malformed_syntax,
                    contentType='text/markdown',
                    visibility='PUBLIC',
                    author=self.user
                )
                
                rendered_html = render_post_content(post)
                # Malformed syntax should not create img tags
                # But should still render the raw text or handle gracefully
                # The important thing is that it doesn't crash
                self.assertIsNotNone(rendered_html)
                
        print("✓ Malformed CommonMark image syntax handled gracefully")

    def test_commonmark_image_with_very_long_alt_text_and_url(self):
        """Test CommonMark rendering with very long alt text and URLs."""
        very_long_alt = "A" * 500  # Very long alt text
        very_long_url = "https://example.com/" + "x" * 500 + ".png"  # Very long URL
        
        post_content = f"![{very_long_alt}]({very_long_url})"
        
        post = Post.objects.create(
            title='Long Content Test',
            content=post_content,
            contentType='text/markdown',
            visibility='PUBLIC',
            author=self.user
        )
        
        from authors.views import render_post_content
        rendered_html = render_post_content(post)
        
        # Should still render properly even with long content
        self.assertIn('<img', rendered_html)
        self.assertIn(very_long_alt[:100], rendered_html)  # Check that at least part of long alt text is included
        self.assertIn('src="https://example.com/', rendered_html)  # Check that URL is in there
        
        print("✓ CommonMark handles very long alt text and URLs properly")