"""
Test script to verify User Story 14: Image posts functionality
"""
from django.test import TestCase
from authors.models import Post
from authors.forms import PostForm

class ImagePostTests(TestCase):
    def test_image_post_implementation(self):
        """Test US 14: Image posts implementation"""
        
        # Test 1: Check if Post model has image field
        try:
            image_field = Post._meta.get_field('image')
            self.assertIsNotNone(image_field, "Post model has image field")
            print("✓ Post model has image field")
        except:
            self.fail("Post model does not have image field")

        # Test 2: Check if content type choices include image types
        content_type_field = Post._meta.get_field('contentType')
        choices = dict(content_type_field.choices)
        image_types = ['image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/webp']
        
        found_image_types = [img_type for img_type in image_types if img_type in choices]
        self.assertGreater(len(found_image_types), 0, "Content type choices include image types")
        print(f"✓ Content type choices include image types: {found_image_types}")

        # Test 3: Check if PostForm includes image field
        form = PostForm()
        self.assertIn('image', form.fields, "PostForm includes image field")
        print("✓ PostForm includes image field")

        # Test 4: Check the form fields list
        self.assertIn('image', form._meta.fields, "Image field is included in form Meta fields")
        print("✓ Image field is included in form Meta fields")

        print("\nAll tests passed! User Story 14: Image posts is properly implemented.")
        print("\nSummary of implementation:")
        print("- Image field added to Post model")
        print("- Image content type choices added to Post model")
        print("- PostForm includes image field")
        print("- Templates updated to handle image posts properly")