#!/usr/bin/env python3
"""
Test script to demonstrate the inbox receipt solution for stale Follow relationships.

This script simulates TWO scenarios:

SCENARIO 1: Friends-Only Posts
1. Two local authors follow a remote author
2. Remote author follows both back (mutual friends)
3. Remote author unfollows one local author (our node doesn't know)
4. Remote author creates friends-only post and sends to only one inbox

SCENARIO 2: Unlisted Posts
1. Two local authors follow a remote author
2. Remote author creates unlisted post, sends to both inboxes
3. Remote author removes one as a follower (our node doesn't know)
4. Remote author creates another unlisted post, sends to only one inbox

With the old system: Both local authors would see the posts (wrong)
With inbox receipts: Only the author who received it in their inbox sees it (correct)
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'social_distribution.settings')
django.setup()

from authors.models import Author, Post, Follow, InboxReceipt
from django.conf import settings

def run_test():
    print("\n" + "="*70)
    print("TESTING INBOX RECEIPT SOLUTION FOR STALE FOLLOW RELATIONSHIPS")
    print("="*70 + "\n")
    
    # Setup: Get/create test authors
    local_host = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    
    # Create two local authors
    local_a, _ = Author.objects.get_or_create(
        username='local_author_a',
        defaults={'displayName': 'Local Author A', 'host': local_host, 'url': f'{local_host}/api/authors/local_a/'}
    )
    local_b, _ = Author.objects.get_or_create(
        username='local_author_b',
        defaults={'displayName': 'Local Author B', 'host': local_host, 'url': f'{local_host}/api/authors/local_b/'}
    )
    
    # Create a "remote" author (simulated)
    remote_host = 'https://remote-node.example.com'
    remote_author, _ = Author.objects.get_or_create(
        username='remote_author_r',
        defaults={
            'displayName': 'Remote Author R',
            'host': remote_host,
            'url': f'{remote_host}/api/authors/remote_r/'
        }
    )
    
    print(f"✓ Created test authors:")
    print(f"  - {local_a.displayName} (local)")
    print(f"  - {local_b.displayName} (local)")
    print(f"  - {remote_author.displayName} (remote at {remote_host})")
    print()
    
    # Step 1: Both local authors follow remote author
    Follow.objects.get_or_create(follower=local_a, following=remote_author)
    Follow.objects.get_or_create(follower=local_b, following=remote_author)
    print("Step 1: Both local authors follow remote author")
    print()
    
    # Step 2: Remote author follows both back (mutual friends)
    Follow.objects.get_or_create(follower=remote_author, following=local_a)
    Follow.objects.get_or_create(follower=remote_author, following=local_b)
    print("Step 2: Remote author follows both back (all are mutual friends)")
    print()
    
    # Step 3: Remote author "unfollows" local_a (but our node doesn't know!)
    # In reality, the remote node would delete this Follow, but we keep it
    # to simulate stale data
    print("Step 3: Remote author unfollows Local Author A")
    print("        (but our node still has the Follow record - STALE DATA)")
    print()
    
    # Step 4: Remote author creates friends-only post
    friends_post, _ = Post.objects.get_or_create(
        author=remote_author,
        title='Remote Friends-Only Post',
        defaults={
            'content': 'This is a friends-only post from remote author',
            'visibility': 'FRIENDS',
            'origin': f'{remote_host}/api/authors/remote_r/entries/test_friends_123'
        }
    )
    
    # Remote node sends it ONLY to local_b's inbox (correctly, since local_a is no longer a friend)
    InboxReceipt.objects.get_or_create(recipient=local_b, post=friends_post)
    
    print("Step 4: Remote author creates friends-only post")
    print("        Remote node sends it to Local Author B's inbox ONLY")
    print()
    
    # Step 5: Remote author creates unlisted post (different scenario)
    unlisted_post, _ = Post.objects.get_or_create(
        author=remote_author,
        title='Remote Unlisted Post',
        defaults={
            'content': 'This is an unlisted post from remote author',
            'visibility': 'PUBLIC_UNLISTED',
            'origin': f'{remote_host}/api/authors/remote_r/entries/test_unlisted_456'
        }
    )
    
    # Remote node sends it ONLY to local_b's inbox (local_a was removed as follower)
    InboxReceipt.objects.get_or_create(recipient=local_b, post=unlisted_post)
    
    print("Step 5: Remote author creates unlisted post")
    print("        Remote node sends it to Local Author B's inbox ONLY")
    print("        (Local Author A was removed as follower)")
    print()
    
    # Now test the visibility logic
    print("="*70)
    print("TESTING VISIBILITY WITH INBOX RECEIPTS")
    print("="*70 + "\n")
    
    # Check if local_a can see the post (they shouldn't!)
    from django.test import RequestFactory
    from authors.views import AuthorStreamView
    
    # Simulate local_a's stream
    factory = RequestFactory()
    request_a = factory.get('/stream')
    request_a.user = local_a
    
    view = AuthorStreamView()
    view.request = request_a
    queryset_a = view.get_queryset()
    
    can_see_friends_a = friends_post in queryset_a
    can_see_unlisted_a = unlisted_post in queryset_a
    
    print(f"Local Author A can see friends-only post: {can_see_friends_a}")
    if not can_see_friends_a:
        print("  ✓ CORRECT - Local Author A was not in the inbox receipt")
    else:
        print("  ✗ WRONG - Local Author A should not see this post!")
    
    print(f"Local Author A can see unlisted post: {can_see_unlisted_a}")
    if not can_see_unlisted_a:
        print("  ✓ CORRECT - Local Author A was removed as follower")
    else:
        print("  ✗ WRONG - Local Author A should not see this post!")
    print()
    
    # Simulate local_b's stream
    request_b = factory.get('/stream')
    request_b.user = local_b
    
    view_b = AuthorStreamView()
    view_b.request = request_b
    queryset_b = view_b.get_queryset()
    
    can_see_friends_b = friends_post in queryset_b
    can_see_unlisted_b = unlisted_post in queryset_b
    
    print(f"Local Author B can see friends-only post: {can_see_friends_b}")
    if can_see_friends_b:
        print("  ✓ CORRECT - Local Author B received it in their inbox")
    else:
        print("  ✗ WRONG - Local Author B should see this post!")
    
    print(f"Local Author B can see unlisted post: {can_see_unlisted_b}")
    if can_see_unlisted_b:
        print("  ✓ CORRECT - Local Author B received it in their inbox")
    else:
        print("  ✗ WRONG - Local Author B should see this post!")
    print()
    
    # Show the stale Follow data
    print("="*70)
    print("FOLLOW RELATIONSHIP STATUS (potentially stale)")
    print("="*70 + "\n")
    
    print(f"Local Author A follows Remote Author R: {Follow.objects.filter(follower=local_a, following=remote_author).exists()}")
    print(f"Remote Author R follows Local Author A: {Follow.objects.filter(follower=remote_author, following=local_a).exists()}")
    print(f"  → Appears as mutual friends in our database (STALE)")
    print()
    
    print(f"Local Author B follows Remote Author R: {Follow.objects.filter(follower=local_b, following=remote_author).exists()}")
    print(f"Remote Author R follows Local Author B: {Follow.objects.filter(follower=remote_author, following=local_b).exists()}")
    print(f"  → Mutual friends (CORRECT)")
    print()
    
    # Show inbox receipts
    print("="*70)
    print("INBOX RECEIPTS (source of truth for remote posts)")
    print("="*70 + "\n")
    
    receipt_friends_a = InboxReceipt.objects.filter(recipient=local_a, post=friends_post).exists()
    receipt_friends_b = InboxReceipt.objects.filter(recipient=local_b, post=friends_post).exists()
    receipt_unlisted_a = InboxReceipt.objects.filter(recipient=local_a, post=unlisted_post).exists()
    receipt_unlisted_b = InboxReceipt.objects.filter(recipient=local_b, post=unlisted_post).exists()
    
    print(f"Local Author A has inbox receipt for friends-only post: {receipt_friends_a}")
    print(f"Local Author B has inbox receipt for friends-only post: {receipt_friends_b}")
    print(f"Local Author A has inbox receipt for unlisted post: {receipt_unlisted_a}")
    print(f"Local Author B has inbox receipt for unlisted post: {receipt_unlisted_b}")
    print()
    
    print("="*70)
    print("CONCLUSION")
    print("="*70 + "\n")
    
    all_correct = (
        not can_see_friends_a and can_see_friends_b and
        not can_see_unlisted_a and can_see_unlisted_b
    )
    
    if all_correct:
        print("✓ SUCCESS: Inbox receipts correctly handle stale Follow relationships!")
        print()
        print("The system correctly shows BOTH friends-only AND unlisted posts")
        print("ONLY to the author who received them in their inbox, regardless")
        print("of stale Follow data.")
        print()
        print("This prevents:")
        print("  • Unfollowed users seeing friends-only posts")
        print("  • Removed followers seeing unlisted posts")
        print("  • 'Proxy viewing' through other local users with access")
    else:
        print("✗ ISSUE: The visibility logic may not be working correctly.")
        print()
        if can_see_friends_a:
            print("  ✗ Local Author A can see friends-only post (should not)")
        if can_see_unlisted_a:
            print("  ✗ Local Author A can see unlisted post (should not)")
        if not can_see_friends_b:
            print("  ✗ Local Author B cannot see friends-only post (should see it)")
        if not can_see_unlisted_b:
            print("  ✗ Local Author B cannot see unlisted post (should see it)")
    
    print()
    print("="*70 + "\n")

if __name__ == '__main__':
    run_test()
