#!/usr/bin/env python
"""
Setup script for Social Distribution federation
This script provides a guided user experience for setting up federation
between nodes, replacing the need for complex shell commands.
"""

import os
import sys
import django
from django.conf import settings
from django.contrib.auth import get_user_model

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_distribution.settings')
django.setup()

from authors.models import Author, RemoteNode


def main():
    print("=" * 60)
    print("Social Distribution Federation Setup Guide")
    print("=" * 60)
    print()
    
    print("This script will guide you through setting up federation with other nodes.")
    print("You'll need to coordinate with the other party to exchange information.")
    print()
    
    # Get user's current information
    user = get_current_user()
    if not user:
        print("Error: No superuser found. Please create a superuser first.")
        print("Run: python manage.py createsuperuser")
        return
    
    print(f"Current user: {user.username}")
    print(f"Current host: {user.host}")
    print(f"Current URL: {user.url}")
    print()
    
    # Step 1: Configure base URL
    print("Step 1: Update your node's base URL")
    print("This should be your full Heroku URL (e.g., https://your-app.herokuapp.com/)")
    base_url = input("Enter your node's base URL: ").strip()
    
    if not base_url.endswith('/'):
        base_url += '/'
    
    # Update user's host and URL
    user.host = base_url.rstrip('/')
    user.url = f"{base_url.rstrip('/')}/api/authors/{user.id}/"
    user.save(update_fields=["host", "url"])
    
    print(f"✓ Updated user host to: {user.host}")
    print(f"✓ Updated user URL to: {user.url}")
    print()
    
    # Step 2: Set up service account
    print("Step 2: Create a service account for node-to-node communication")
    svc_username = input("Enter service username (e.g., node_service): ").strip()
    svc_password = input("Enter service password: ").strip()
    
    # Create or update service user
    service_user, created = Author.objects.get_or_create(username=svc_username)
    service_user.set_password(svc_password)
    service_user.displayName = f"Node Service User ({svc_username})"
    service_user.save()
    
    if created:
        print(f"✓ Created new service user: {svc_username}")
    else:
        print(f"✓ Updated existing service user: {svc_username}")
    print()
    
    # Step 3: Add remote node
    print("Step 3: Add a remote node to connect with")
    print("You'll need the other party's information:")
    print("- Their base URL (e.g., https://their-app.herokuapp.com/)")
    print("- Their service username")
    print("- Their service password")
    print()
    
    add_remote = input("Do you want to add a remote node now? (y/n): ").lower().strip()
    
    if add_remote == 'y':
        remote_name = input("Enter a name for this remote node (e.g., 'Partner Node'): ").strip()
        remote_base_url = input("Enter remote base URL: ").strip()
        remote_username = input("Enter remote service username: ").strip()
        remote_password = input("Enter remote service password: ").strip()
        
        if not remote_base_url.endswith('/'):
            remote_base_url += '/'
        
        # Create remote node entry
        remote_node, created = RemoteNode.objects.get_or_create(
            name=remote_name,
            base_url=remote_base_url,
            defaults={
                'username': remote_username,
                'password': remote_password,
                'enabled': True
            }
        )
        
        if not created:
            # Update existing
            remote_node.username = remote_username
            remote_node.password = remote_password
            remote_node.enabled = True
            remote_node.save()
            print(f"✓ Updated remote node: {remote_name}")
        else:
            print(f"✓ Added new remote node: {remote_name}")
    
    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print("Your node is now configured for federation.")
    print()
    print("To connect with the other party:")
    print(f"- Share your base URL: {base_url}")
    print(f"- Share your service username: {svc_username}")
    print(f"- Share your service password: [the password you entered]")
    print()
    print("They will need to add your node as a remote node on their end too.")
    print()
    print("To test the connection:")
    print("1. Go to your Explore page")
    print("2. Use 'Follow Remote Author' to follow someone on their node")
    print("3. Have them approve the follow request")
    print("4. Create a public post to test if it appears on their stream")
    print()
    print("Visit your node configuration page for easier management:")
    print(f"- URL: {base_url}node_config/")
    print("- You'll need admin privileges to access this page")
    print("=" * 60)


def get_current_user():
    """Get the first superuser in the database"""
    User = get_user_model()
    try:
        user = User.objects.filter(is_superuser=True).first()
        return user
    except:
        return None


if __name__ == "__main__":
    main()