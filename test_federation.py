#!/usr/bin/env python
"""
Test script to verify the federation functionality works properly
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_distribution.settings')
django.setup()

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from django.conf import settings
        from authors.views import NodeConfigurationView, ConfigureRemoteNodeView, FederationGuideView
        from authors.forms import NodeConfigurationForm
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_models():
    """Test that models can be accessed"""
    try:
        from authors.models import Author, RemoteNode
        print("✓ Models accessible")
        return True
    except Exception as e:
        print(f"✗ Model access error: {e}")
        return False

def test_urls():
    """Test that URLs are properly configured"""
    try:
        from django.urls import reverse
        urls_to_test = [
            'authors:node_config',
            'authors:configure_remote_node', 
            'authors:federation_guide',
            'authors:remote_nodes_list'
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"✓ URL {url_name} -> {url}")
            except:
                print(f"✗ URL {url_name} failed")
                return False
        return True
    except Exception as e:
        print(f"✗ URL test error: {e}")
        return False

def main():
    print("Testing Social Distribution Federation Functionality")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Models", test_models),
        ("URLs", test_urls),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        if test_func():
            print(f"✓ {test_name} test passed")
        else:
            print(f"✗ {test_name} test failed")
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed! Federation functionality should work.")
        print("\nTo test manually:")
        print("1. Run: python manage.py runserver")
        print("2. Go to http://127.0.0.1:8000/node_config/ as a superuser")
        print("3. Verify the page loads without errors")
    else:
        print("✗ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()