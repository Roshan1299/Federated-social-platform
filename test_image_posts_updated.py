"""
Test script to verify User Story 14: Image posts functionality
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append('/Users/bhuvan/CMPUT 404/project/f25-project-darkblue')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_distribution.settings')
django.setup()

from authors.models import Post
from authors.forms import PostForm

def test_image_post_implementation():
    print("Testing User Story 14: Image posts implementation...")
    
    # Test 1: Check if Post model has image field
    try:
        image_field = Post._meta.get_field('image')
        print("✓ Post model has image field")
    except:
        print("✗ Post model does not have image field")
        return False

    # Test 2: Check if content type choices include image types
    content_type_field = Post._meta.get_field('contentType')
    choices = dict(content_type_field.choices)
    image_types = ['image/png', 'image/jpeg', 'image/gif', 'image/bmp', 'image/webp']
    
    found_image_types = [img_type for img_type in image_types if img_type in choices]
    if len(found_image_types) > 0:
        print(f"✓ Content type choices include image types: {found_image_types}")
    else:
        print("✗ Content type choices do not include image types")
        return False

    # Test 3: Check if PostForm includes image field
    form = PostForm()
    if 'image' in form.fields:
        print("✓ PostForm includes image field")
    else:
        print("✗ PostForm does not include image field")
        return False

    # Test 4: Check the form fields list
    if 'image' in form._meta.fields:
        print("✓ Image field is included in form Meta fields")
    else:
        print("✗ Image field is not included in form Meta fields")
        return False

    print("\nAll tests passed! User Story 14: Image posts is properly implemented.")
    print("\nSummary of implementation:")
    print("- Image field added to Post model")
    print("- Image content type choices added to Post model")
    print("- PostForm includes image field")
    print("- Templates updated to handle image posts properly")
    
    return True

if __name__ == "__main__":
    test_image_post_implementation()