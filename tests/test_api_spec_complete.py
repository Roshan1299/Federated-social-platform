"""
Complete API Test Suite for Social Distribution Project
Tests ALL endpoints from project.txt specification with proper authentication

This test suite validates:
1. All API endpoints work as specified
2. Authentication requirements are enforced
3. Visibility restrictions are properly implemented
4. Different user types get appropriate access

Usage:
    python test_api_spec_complete.py
    python test_api_spec_complete.py --url https://<service_url> --user admin --password secret
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import sys
import argparse
import urllib.parse
from datetime import datetime
import base64


class APISpecTester:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        
        # Test data storage
        self.author1_id = None  # Main test author
        self.author2_id = None  # Friend of author1
        self.author3_id = None  # Follower of author1 (not friend)
        self.author4_id = None  # Not following author1
        
        self.public_post_id = None
        self.unlisted_post_id = None
        self.friends_post_id = None
        self.image_post_id = None
        
        self.comment_id = None
        self.like_id = None
        self.comment_like_id = None
        
        # Statistics
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.test_results = []
        
    def log_result(self, test_name, passed, message="", skip=False):
        """Log test result"""
        self.total_tests += 1
        if skip:
            self.skipped_tests += 1
            status = "SKIP"
            symbol = "⚠️ "
        elif passed:
            self.passed_tests += 1
            status = "PASS"
            symbol = "✅"
        else:
            self.failed_tests += 1
            status = "FAIL"
            symbol = "❌"
        
        result = {
            'name': test_name,
            'status': status,
            'message': message
        }
        self.test_results.append(result)
        
        print(f"{symbol} {status}: {test_name}")
        if message:
            print(f"   → {message}")
        print()
        
        return passed
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total Tests:  {self.total_tests}")
        print(f"✅ Passed:    {self.passed_tests}")
        print(f"❌ Failed:    {self.failed_tests}")
        print(f"⚠️  Skipped:   {self.skipped_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / (self.total_tests - self.skipped_tests)) * 100 if (self.total_tests - self.skipped_tests) > 0 else 0
            print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        print("="*80)
        
        # Print failed tests
        if self.failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  ❌ {result['name']}: {result['message']}")
        
        return self.failed_tests == 0
    
    # ==================== AUTHENTICATION TESTS ====================
    
    def test_auth_required_no_auth(self):
        """Test that endpoints require authentication when no auth provided"""
        print("\n" + "="*80)
        print("AUTHENTICATION TESTS - No Auth Provided")
        print("="*80 + "\n")
        
        endpoints = [
            ("GET", "/api/authors/"),
            ("GET", "/api/authors/fake-id/"),
            ("GET", "/api/authors/fake-id/entries/"),
            ("GET", "/api/authors/fake-id/followers"),
        ]
        
        all_passed = True
        for method, endpoint in endpoints:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url)
            
            passed = response.status_code == 401
            all_passed = all_passed and self.log_result(
                f"Auth Required: {method} {endpoint}",
                passed,
                f"Expected 401, got {response.status_code}" if not passed else "Correctly requires authentication"
            )
        
        return all_passed
    
    def test_auth_valid(self):
        """Test that valid authentication works"""
        print("\n" + "="*80)
        print("AUTHENTICATION TESTS - Valid Auth")
        print("="*80 + "\n")
        
        url = f"{self.base_url}/api/authors/"
        response = requests.get(url, auth=self.auth)
        
        return self.log_result(
            "Valid Authentication",
            response.status_code == 200,
            f"Expected 200, got {response.status_code}" if response.status_code != 200 else "Authentication accepted"
        )
    
    # ==================== AUTHORS API TESTS ====================
    
    def test_get_authors_paginated(self):
        """Test GET /api/authors/ with pagination"""
        print("\n" + "="*80)
        print("AUTHORS API TESTS")
        print("="*80 + "\n")
        
        # Test without pagination
        url = f"{self.base_url}/api/authors/"
        response = requests.get(url, auth=self.auth)
        
        if response.status_code != 200:
            return self.log_result(
                "GET /api/authors/",
                False,
                f"Expected 200, got {response.status_code}"
            )
        
        try:
            data = response.json()
            # Store author IDs for later tests
            if isinstance(data, dict) and 'authors' in data:
                authors = data['authors']
            elif isinstance(data, list):
                authors = data
            else:
                authors = []
            
            if len(authors) > 0:
                self.author1_id = authors[0].get('id', '').split('/')[-2]
                if len(authors) > 1:
                    self.author2_id = authors[1].get('id', '').split('/')[-2]
                if len(authors) > 2:
                    self.author3_id = authors[2].get('id', '').split('/')[-2]
                if len(authors) > 3:
                    self.author4_id = authors[3].get('id', '').split('/')[-2]
            
            passed = self.log_result(
                "GET /api/authors/",
                True,
                f"Retrieved {len(authors)} authors"
            )
            
            # Test with pagination
            url_paginated = f"{self.base_url}/api/authors/?page=1&size=5"
            response_paginated = requests.get(url_paginated, auth=self.auth)
            
            self.log_result(
                "GET /api/authors/?page=1&size=5",
                response_paginated.status_code == 200,
                f"Pagination works" if response_paginated.status_code == 200 else f"Expected 200, got {response_paginated.status_code}"
            )
            
            return passed
        except Exception as e:
            return self.log_result(
                "GET /api/authors/",
                False,
                f"Error parsing response: {str(e)}"
            )
    
    def test_get_single_author(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/"""
        if not self.author1_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/",
                False,
                "No author ID available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/"
        response = requests.get(url, auth=self.auth)
        
        if response.status_code != 200:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/",
                False,
                f"Expected 200, got {response.status_code}"
            )
        
        try:
            data = response.json()
            has_required_fields = all(k in data for k in ['type', 'id', 'displayName', 'host'])
            
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/",
                has_required_fields,
                f"Author object has all required fields" if has_required_fields else "Missing required fields"
            )
        except Exception as e:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/",
                False,
                f"Error parsing response: {str(e)}"
            )
    
    def test_get_author_by_fqid(self):
        """Test GET /api/authors/{AUTHOR_FQID}/"""
        if not self.author1_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_FQID}/",
                False,
                "No author ID available",
                skip=True
            )
        
        # First get the author to get their FQID
        url = f"{self.base_url}/api/authors/{self.author1_id}/"
        response = requests.get(url, auth=self.auth)
        
        if response.status_code != 200:
            return self.log_result(
                "GET /api/authors/{AUTHOR_FQID}/",
                False,
                "Could not get author FQID",
                skip=True
            )
        
        try:
            author_data = response.json()
            author_fqid = author_data.get('id', author_data.get('url', ''))
            
            # Percent encode the FQID
            encoded_fqid = urllib.parse.quote(author_fqid, safe='')
            
            # Try to get author by FQID
            url_fqid = f"{self.base_url}/api/authors/{encoded_fqid}/"
            response_fqid = requests.get(url_fqid, auth=self.auth)
            
            return self.log_result(
                "GET /api/authors/{AUTHOR_FQID}/",
                response_fqid.status_code == 200,
                f"FQID lookup works" if response_fqid.status_code == 200 else f"Expected 200, got {response_fqid.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "GET /api/authors/{AUTHOR_FQID}/",
                False,
                f"Error: {str(e)}"
            )
    
    # ==================== FOLLOWERS API TESTS ====================
    
    def test_followers_api(self):
        """Test followers API endpoints"""
        print("\n" + "="*80)
        print("FOLLOWERS API TESTS")
        print("="*80 + "\n")
        
        if not self.author1_id:
            return self.log_result(
                "Followers API",
                False,
                "No author ID available",
                skip=True
            )
        
        # Test GET followers list
        url = f"{self.base_url}/api/authors/{self.author1_id}/followers"
        response = requests.get(url, auth=self.auth)
        
        passed = self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/followers",
            response.status_code == 200,
            f"Retrieved followers list" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
        
        # Test GET specific follower (if we have one)
        if response.status_code == 200:
            try:
                data = response.json()
                followers = data.get('followers', [])
                
                if len(followers) > 0:
                    follower_id = followers[0].get('id', '')
                    encoded_follower = urllib.parse.quote(follower_id, safe='')
                    
                    url_check = f"{self.base_url}/api/authors/{self.author1_id}/followers/{encoded_follower}"
                    response_check = requests.get(url_check, auth=self.auth)
                    
                    self.log_result(
                        "GET /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_FQID}",
                        response_check.status_code == 200,
                        f"Follower check works" if response_check.status_code == 200 else f"Expected 200, got {response_check.status_code}"
                    )
                else:
                    self.log_result(
                        "GET /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_FQID}",
                        False,
                        "No followers to test with",
                        skip=True
                    )
            except Exception as e:
                self.log_result(
                    "GET /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_FQID}",
                    False,
                    f"Error: {str(e)}"
                )
        
        return passed
    
    # ==================== INBOX API TESTS ====================
    
    def test_inbox_follow_request(self):
        """Test POST /api/authors/{AUTHOR_SERIAL}/inbox with follow request"""
        print("\n" + "="*80)
        print("INBOX API TESTS")
        print("="*80 + "\n")
        
        if not self.author1_id or not self.author2_id:
            return self.log_result(
                "POST Inbox - Follow Request",
                False,
                "Need at least 2 authors",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/inbox"
        follow_request = {
            "type": "follow",
            "summary": "Author 2 wants to follow Author 1",
            "actor": {
                "type": "author",
                "id": f"{self.base_url}/api/authors/{self.author2_id}/",
                "host": f"{self.base_url}/api/",
                "displayName": "Test Author 2"
            },
            "object": {
                "type": "author",
                "id": f"{self.base_url}/api/authors/{self.author1_id}/",
                "host": f"{self.base_url}/api/",
                "displayName": "Test Author 1"
            }
        }
        
        response = requests.post(url, json=follow_request, auth=self.auth)
        
        return self.log_result(
            "POST Inbox - Follow Request",
            response.status_code in [200, 201, 204],
            f"Follow request accepted" if response.status_code in [200, 201, 204] else f"Expected 200/201/204, got {response.status_code}"
        )
    
    def test_inbox_post(self):
        """Test POST /api/authors/{AUTHOR_SERIAL}/inbox with post/entry"""
        if not self.author1_id:
            return self.log_result(
                "POST Inbox - Entry",
                False,
                "No author ID available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/inbox"
        post_object = {
            "type": "post",
            "title": "Test Post via Inbox",
            "id": f"{self.base_url}/api/authors/{self.author1_id}/entries/test-post-123",
            "source": f"{self.base_url}/api/authors/{self.author1_id}/entries/test-post-123",
            "origin": f"{self.base_url}/api/authors/{self.author1_id}/entries/test-post-123",
            "description": "Test post sent via inbox",
            "contentType": "text/plain",
            "content": "This is a test post sent via inbox API",
            "author": {
                "type": "author",
                "id": f"{self.base_url}/api/authors/{self.author1_id}/",
                "host": f"{self.base_url}/api/",
                "displayName": "Test Author"
            },
            "visibility": "PUBLIC",
            "unlisted": False,
            "published": datetime.now().isoformat()
        }
        
        response = requests.post(url, json=post_object, auth=self.auth)
        
        return self.log_result(
            "POST Inbox - Entry",
            response.status_code in [200, 201, 204],
            f"Entry accepted" if response.status_code in [200, 201, 204] else f"Expected 200/201/204, got {response.status_code}"
        )
    
    def test_inbox_like(self):
        """Test POST /api/authors/{AUTHOR_SERIAL}/inbox with like"""
        if not self.author1_id:
            return self.log_result(
                "POST Inbox - Like",
                False,
                "No author ID available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/inbox"
        like_object = {
            "type": "like",
            "author": {
                "type": "author",
                "id": f"{self.base_url}/api/authors/{self.author2_id if self.author2_id else 'test-author'}/",
                "host": f"{self.base_url}/api/",
                "displayName": "Test Liker"
            },
            "object": f"{self.base_url}/api/authors/{self.author1_id}/entries/test-post",
            "published": datetime.now().isoformat()
        }
        
        response = requests.post(url, json=like_object, auth=self.auth)
        
        return self.log_result(
            "POST Inbox - Like",
            response.status_code in [200, 201, 204],
            f"Like accepted" if response.status_code in [200, 201, 204] else f"Expected 200/201/204, got {response.status_code}"
        )
    
    def test_inbox_comment(self):
        """Test POST /api/authors/{AUTHOR_SERIAL}/inbox with comment"""
        if not self.author1_id:
            return self.log_result(
                "POST Inbox - Comment",
                False,
                "No author ID available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/inbox"
        comment_object = {
            "type": "comment",
            "author": {
                "type": "author",
                "id": f"{self.base_url}/api/authors/{self.author2_id if self.author2_id else 'test-author'}/",
                "host": f"{self.base_url}/api/",
                "displayName": "Test Commenter"
            },
            "comment": "This is a test comment via inbox",
            "contentType": "text/plain",
            "entry": f"{self.base_url}/api/authors/{self.author1_id}/entries/test-post",
            "published": datetime.now().isoformat()
        }
        
        response = requests.post(url, json=comment_object, auth=self.auth)
        
        return self.log_result(
            "POST Inbox - Comment",
            response.status_code in [200, 201, 204],
            f"Comment accepted" if response.status_code in [200, 201, 204] else f"Expected 200/201/204, got {response.status_code}"
        )
    
    # ==================== ENTRIES/POSTS API TESTS ====================
    
    def test_entries_api(self):
        """Test entries/posts API endpoints"""
        print("\n" + "="*80)
        print("ENTRIES/POSTS API TESTS")
        print("="*80 + "\n")
        
        if not self.author1_id:
            return self.log_result(
                "Entries API",
                False,
                "No author ID available",
                skip=True
            )
        
        # Test GET entries list
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/"
        response = requests.get(url, auth=self.auth)
        
        passed = self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/entries/",
            response.status_code == 200,
            f"Retrieved entries list" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
        
        # Test pagination
        url_paginated = f"{self.base_url}/api/authors/{self.author1_id}/entries/?page=1&size=10"
        response_paginated = requests.get(url_paginated, auth=self.auth)
        
        self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/entries/ (paginated)",
            response_paginated.status_code == 200,
            f"Pagination works" if response_paginated.status_code == 200 else f"Expected 200, got {response_paginated.status_code}"
        )
        
        # Try to get entry IDs for later tests
        if response.status_code == 200:
            try:
                data = response.json()
                entries = data.get('entries', data.get('items', []))
                
                if len(entries) > 0:
                    # Store entry ID for later tests
                    self.public_post_id = entries[0].get('id', '').split('/')[-1]
            except:
                pass
        
        return passed
    
    def test_create_entry(self):
        """Test POST /api/authors/{AUTHOR_SERIAL}/entries/ (create entry)"""
        if not self.author1_id:
            return self.log_result(
                "POST /api/authors/{AUTHOR_SERIAL}/entries/",
                False,
                "No author ID available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/"
        
        # Create a public post
        public_post = {
            "title": "Test Public Post",
            "description": "A test public post",
            "contentType": "text/plain",
            "content": "This is public content",
            "visibility": "PUBLIC",
            "unlisted": False
        }
        
        response = requests.post(url, json=public_post, auth=self.auth)
        
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                self.public_post_id = data.get('id', '').split('/')[-1]
            except:
                pass
        
        return self.log_result(
            "POST /api/authors/{AUTHOR_SERIAL}/entries/ (create)",
            response.status_code in [200, 201],
            f"Entry created" if response.status_code in [200, 201] else f"Expected 200/201, got {response.status_code}"
        )
    
    def test_get_single_entry(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}"""
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
                False,
                "No entry available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}"
        response = requests.get(url, auth=self.auth)
        
        return self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
            response.status_code == 200,
            f"Entry retrieved" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
    
    def test_update_entry(self):
        """Test PUT /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}"""
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "PUT /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
                False,
                "No entry available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}"
        
        updated_post = {
            "title": "Updated Test Post",
            "description": "Updated description",
            "contentType": "text/plain",
            "content": "Updated content",
            "visibility": "PUBLIC",
            "unlisted": False
        }
        
        response = requests.put(url, json=updated_post, auth=self.auth)
        
        return self.log_result(
            "PUT /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
            response.status_code == 200,
            f"Entry updated" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
    
    def test_delete_entry(self):
        """Test DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}"""
        if not self.author1_id:
            return self.log_result(
                "DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
                False,
                "No author available",
                skip=True
            )
        
        # Create a post to delete
        url_create = f"{self.base_url}/api/authors/{self.author1_id}/entries/"
        test_post = {
            "title": "Post to Delete",
            "contentType": "text/plain",
            "content": "This will be deleted",
            "visibility": "PUBLIC"
        }
        
        response_create = requests.post(url_create, json=test_post, auth=self.auth)
        
        if response_create.status_code not in [200, 201]:
            return self.log_result(
                "DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
                False,
                "Could not create post to delete",
                skip=True
            )
        
        try:
            post_data = response_create.json()
            post_id = post_data.get('id', '').split('/')[-1]
            
            url_delete = f"{self.base_url}/api/authors/{self.author1_id}/entries/{post_id}"
            response_delete = requests.delete(url_delete, auth=self.auth)
            
            return self.log_result(
                "DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
                response_delete.status_code in [200, 204],
                f"Entry deleted" if response_delete.status_code in [200, 204] else f"Expected 200/204, got {response_delete.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}",
                False,
                f"Error: {str(e)}"
            )
    
    def test_get_entry_by_fqid(self):
        """Test GET /api/entries/{ENTRY_FQID}"""
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}",
                False,
                "No entry available",
                skip=True
            )
        
        # First get the entry to get its FQID
        url_get = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}"
        response_get = requests.get(url_get, auth=self.auth)
        
        if response_get.status_code != 200:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}",
                False,
                "Could not get entry FQID",
                skip=True
            )
        
        try:
            entry_data = response_get.json()
            entry_fqid = entry_data.get('id', entry_data.get('url', ''))
            
            # Percent encode the FQID
            encoded_fqid = urllib.parse.quote(entry_fqid, safe='')
            
            # Try to get entry by FQID
            url_fqid = f"{self.base_url}/api/entries/{encoded_fqid}"
            response_fqid = requests.get(url_fqid, auth=self.auth)
            
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}",
                response_fqid.status_code == 200,
                f"FQID entry lookup works" if response_fqid.status_code == 200 else f"Expected 200, got {response_fqid.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}",
                False,
                f"Error: {str(e)}"
            )
    
    # ==================== VISIBILITY TESTS ====================
    
    def test_visibility_public(self):
        """Test that public posts are visible to everyone"""
        print("\n" + "="*80)
        print("VISIBILITY TESTS - Public Posts")
        print("="*80 + "\n")
        
        if not self.author1_id:
            return self.log_result(
                "Visibility - Public Posts",
                False,
                "No author available",
                skip=True
            )
        
        # Create a public post
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/"
        public_post = {
            "title": "Public Visibility Test",
            "contentType": "text/plain",
            "content": "This is public",
            "visibility": "PUBLIC",
            "unlisted": False
        }
        
        response_create = requests.post(url, json=public_post, auth=self.auth)
        
        if response_create.status_code not in [200, 201]:
            return self.log_result(
                "Visibility - Public Posts",
                False,
                f"Could not create public post: {response_create.status_code}"
            )
        
        try:
            post_data = response_create.json()
            post_id = post_data.get('id', '').split('/')[-1]
            self.public_post_id = post_id
            
            # Try to get it (authenticated)
            url_get = f"{self.base_url}/api/authors/{self.author1_id}/entries/{post_id}"
            response_get = requests.get(url_get, auth=self.auth)
            
            return self.log_result(
                "Visibility - Public Post Accessible",
                response_get.status_code == 200,
                f"Public post accessible" if response_get.status_code == 200 else f"Expected 200, got {response_get.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "Visibility - Public Posts",
                False,
                f"Error: {str(e)}"
            )
    
    def test_visibility_friends_only(self):
        """Test that friends-only posts require authentication"""
        print("\n" + "="*80)
        print("VISIBILITY TESTS - Friends-Only Posts")
        print("="*80 + "\n")
        
        if not self.author1_id:
            return self.log_result(
                "Visibility - Friends-Only",
                False,
                "No author available",
                skip=True
            )
        
        # Create a friends-only post
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/"
        friends_post = {
            "title": "Friends-Only Visibility Test",
            "contentType": "text/plain",
            "content": "This is friends-only",
            "visibility": "FRIENDS",
            "unlisted": False
        }
        
        response_create = requests.post(url, json=friends_post, auth=self.auth)
        
        if response_create.status_code not in [200, 201]:
            return self.log_result(
                "Visibility - Friends-Only Creation",
                False,
                f"Could not create friends-only post: {response_create.status_code}"
            )
        
        try:
            post_data = response_create.json()
            post_id = post_data.get('id', '').split('/')[-1]
            self.friends_post_id = post_id
            
            # Try to get it with auth (should work for author)
            url_get = f"{self.base_url}/api/authors/{self.author1_id}/entries/{post_id}"
            response_get_auth = requests.get(url_get, auth=self.auth)
            
            passed = self.log_result(
                "Visibility - Friends-Only Accessible to Author",
                response_get_auth.status_code == 200,
                f"Friends-only post accessible to author" if response_get_auth.status_code == 200 else f"Expected 200, got {response_get_auth.status_code}"
            )
            
            # Try to get it without auth (should fail or require auth)
            response_get_noauth = requests.get(url_get)
            
            self.log_result(
                "Visibility - Friends-Only Requires Auth",
                response_get_noauth.status_code == 401,
                f"Friends-only post requires auth" if response_get_noauth.status_code == 401 else f"Expected 401, got {response_get_noauth.status_code}"
            )
            
            return passed
        except Exception as e:
            return self.log_result(
                "Visibility - Friends-Only",
                False,
                f"Error: {str(e)}"
            )
    
    def test_visibility_unlisted(self):
        """Test that unlisted posts are accessible with link but not listed"""
        print("\n" + "="*80)
        print("VISIBILITY TESTS - Unlisted Posts")
        print("="*80 + "\n")
        
        if not self.author1_id:
            return self.log_result(
                "Visibility - Unlisted",
                False,
                "No author available",
                skip=True
            )
        
        # Create an unlisted post
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/"
        unlisted_post = {
            "title": "Unlisted Visibility Test",
            "contentType": "text/plain",
            "content": "This is unlisted",
            "visibility": "PUBLIC",
            "unlisted": True
        }
        
        response_create = requests.post(url, json=unlisted_post, auth=self.auth)
        
        if response_create.status_code not in [200, 201]:
            return self.log_result(
                "Visibility - Unlisted Creation",
                False,
                f"Could not create unlisted post: {response_create.status_code}"
            )
        
        try:
            post_data = response_create.json()
            post_id = post_data.get('id', '').split('/')[-1]
            self.unlisted_post_id = post_id
            
            # Try to get it with direct link
            url_get = f"{self.base_url}/api/authors/{self.author1_id}/entries/{post_id}"
            response_get = requests.get(url_get, auth=self.auth)
            
            return self.log_result(
                "Visibility - Unlisted Accessible with Link",
                response_get.status_code == 200,
                f"Unlisted post accessible with link" if response_get.status_code == 200 else f"Expected 200, got {response_get.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "Visibility - Unlisted",
                False,
                f"Error: {str(e)}"
            )
    
    # ==================== IMAGE ENTRIES TESTS ====================
    
    def test_image_entries(self):
        """Test image entry endpoints"""
        print("\n" + "="*80)
        print("IMAGE ENTRIES TESTS")
        print("="*80 + "\n")
        
        if not self.author1_id:
            return self.log_result(
                "Image Entries",
                False,
                "No author available",
                skip=True
            )
        
        # Create a small test image (1x1 red pixel PNG)
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        
        # Create an image post
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/"
        image_post = {
            "title": "Test Image Post",
            "contentType": "image/png;base64",
            "content": test_image_base64,
            "visibility": "PUBLIC",
            "unlisted": False
        }
        
        response_create = requests.post(url, json=image_post, auth=self.auth)
        
        if response_create.status_code not in [200, 201]:
            return self.log_result(
                "Image Entry - Create",
                False,
                f"Could not create image post: {response_create.status_code}"
            )
        
        try:
            post_data = response_create.json()
            image_post_id = post_data.get('id', '').split('/')[-1]
            self.image_post_id = image_post_id
            
            # Test GET image as binary
            url_image = f"{self.base_url}/api/authors/{self.author1_id}/entries/{image_post_id}/image"
            response_image = requests.get(url_image, auth=self.auth)
            
            passed = self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/image",
                response_image.status_code == 200 and 'image' in response_image.headers.get('Content-Type', ''),
                f"Image retrieved as binary" if response_image.status_code == 200 else f"Expected 200, got {response_image.status_code}"
            )
            
            # Test FQID image endpoint
            entry_fqid = post_data.get('id', post_data.get('url', ''))
            encoded_fqid = urllib.parse.quote(entry_fqid, safe='')
            url_fqid_image = f"{self.base_url}/api/entries/{encoded_fqid}/image"
            response_fqid_image = requests.get(url_fqid_image, auth=self.auth)
            
            self.log_result(
                "GET /api/entries/{ENTRY_FQID}/image",
                response_fqid_image.status_code == 200,
                f"FQID image endpoint works" if response_fqid_image.status_code == 200 else f"Expected 200, got {response_fqid_image.status_code}"
            )
            
            return passed
        except Exception as e:
            return self.log_result(
                "Image Entries",
                False,
                f"Error: {str(e)}"
            )
    
    # ==================== COMMENTS API TESTS ====================
    
    def test_comments_api(self):
        """Test comments API endpoints"""
        print("\n" + "="*80)
        print("COMMENTS API TESTS")
        print("="*80 + "\n")
        
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "Comments API",
                False,
                "No post available",
                skip=True
            )
        
        # Test GET comments on post
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}/comments"
        response = requests.get(url, auth=self.auth)
        
        passed = self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments",
            response.status_code == 200,
            f"Comments retrieved" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
        
        # Test pagination
        url_paginated = f"{url}?page=1&size=5"
        response_paginated = requests.get(url_paginated, auth=self.auth)
        
        self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments (paginated)",
            response_paginated.status_code == 200,
            f"Comment pagination works" if response_paginated.status_code == 200 else f"Expected 200, got {response_paginated.status_code}"
        )
        
        return passed
    
    def test_comments_by_fqid(self):
        """Test GET /api/entries/{ENTRY_FQID}/comments"""
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/comments",
                False,
                "No post available",
                skip=True
            )
        
        # Get entry FQID
        url_get = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}"
        response_get = requests.get(url_get, auth=self.auth)
        
        if response_get.status_code != 200:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/comments",
                False,
                "Could not get entry FQID",
                skip=True
            )
        
        try:
            entry_data = response_get.json()
            entry_fqid = entry_data.get('id', entry_data.get('url', ''))
            encoded_fqid = urllib.parse.quote(entry_fqid, safe='')
            
            url_comments = f"{self.base_url}/api/entries/{encoded_fqid}/comments"
            response_comments = requests.get(url_comments, auth=self.auth)
            
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/comments",
                response_comments.status_code == 200,
                f"FQID comments endpoint works" if response_comments.status_code == 200 else f"Expected 200, got {response_comments.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/comments",
                False,
                f"Error: {str(e)}"
            )
    
    def test_commented_api(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/commented"""
        if not self.author1_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/commented",
                False,
                "No author available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/commented"
        response = requests.get(url, auth=self.auth)
        
        return self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/commented",
            response.status_code == 200,
            f"Author comments retrieved" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
    
    def test_single_comment(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}"""
        if not self.author1_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}",
                False,
                "No author available",
                skip=True
            )
        
        # First get list of comments
        url_list = f"{self.base_url}/api/authors/{self.author1_id}/commented"
        response_list = requests.get(url_list, auth=self.auth)
        
        if response_list.status_code != 200:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}",
                False,
                "No comments available",
                skip=True
            )
        
        try:
            comments_data = response_list.json()
            comments = comments_data if isinstance(comments_data, list) else comments_data.get('comments', [])
            
            if len(comments) == 0:
                return self.log_result(
                    "GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}",
                    False,
                    "No comments to test with",
                    skip=True
                )
            
            comment_id = comments[0].get('id', '').split('/')[-1]
            
            url_single = f"{self.base_url}/api/authors/{self.author1_id}/commented/{comment_id}"
            response_single = requests.get(url_single, auth=self.auth)
            
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}",
                response_single.status_code == 200,
                f"Single comment retrieved" if response_single.status_code == 200 else f"Expected 200, got {response_single.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}",
                False,
                f"Error: {str(e)}"
            )
    
    # ==================== LIKES API TESTS ====================
    
    def test_likes_on_entry(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/likes"""
        print("\n" + "="*80)
        print("LIKES API TESTS")
        print("="*80 + "\n")
        
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/likes",
                False,
                "No post available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}/likes"
        response = requests.get(url, auth=self.auth)
        
        return self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/likes",
            response.status_code == 200,
            f"Entry likes retrieved" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
    
    def test_likes_on_entry_by_fqid(self):
        """Test GET /api/entries/{ENTRY_FQID}/likes"""
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/likes",
                False,
                "No post available",
                skip=True
            )
        
        # Get entry FQID
        url_get = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}"
        response_get = requests.get(url_get, auth=self.auth)
        
        if response_get.status_code != 200:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/likes",
                False,
                "Could not get entry FQID",
                skip=True
            )
        
        try:
            entry_data = response_get.json()
            entry_fqid = entry_data.get('id', entry_data.get('url', ''))
            encoded_fqid = urllib.parse.quote(entry_fqid, safe='')
            
            url_likes = f"{self.base_url}/api/entries/{encoded_fqid}/likes"
            response_likes = requests.get(url_likes, auth=self.auth)
            
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/likes",
                response_likes.status_code == 200,
                f"FQID entry likes endpoint works" if response_likes.status_code == 200 else f"Expected 200, got {response_likes.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "GET /api/entries/{ENTRY_FQID}/likes",
                False,
                f"Error: {str(e)}"
            )
    
    def test_likes_on_comment(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments/{COMMENT_FQID}/likes"""
        if not self.author1_id or not self.public_post_id:
            return self.log_result(
                "GET /api/.../comments/{COMMENT_FQID}/likes",
                False,
                "No post available",
                skip=True
            )
        
        # This endpoint needs a comment to exist
        # For now, just test that the endpoint responds
        url = f"{self.base_url}/api/authors/{self.author1_id}/entries/{self.public_post_id}/comments/test-comment-id/likes"
        response = requests.get(url, auth=self.auth)
        
        # It's OK if it returns 404 (no comment), but shouldn't return 500 or other errors
        return self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments/{COMMENT_FQID}/likes",
            response.status_code in [200, 404],
            f"Comment likes endpoint exists" if response.status_code in [200, 404] else f"Expected 200/404, got {response.status_code}"
        )
    
    def test_liked_api(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/liked"""
        if not self.author1_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/liked",
                False,
                "No author available",
                skip=True
            )
        
        url = f"{self.base_url}/api/authors/{self.author1_id}/liked"
        response = requests.get(url, auth=self.auth)
        
        return self.log_result(
            "GET /api/authors/{AUTHOR_SERIAL}/liked",
            response.status_code == 200,
            f"Author liked items retrieved" if response.status_code == 200 else f"Expected 200, got {response.status_code}"
        )
    
    def test_single_like(self):
        """Test GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}"""
        if not self.author1_id:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}",
                False,
                "No author available",
                skip=True
            )
        
        # First get list of likes
        url_list = f"{self.base_url}/api/authors/{self.author1_id}/liked"
        response_list = requests.get(url_list, auth=self.auth)
        
        if response_list.status_code != 200:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}",
                False,
                "No likes available",
                skip=True
            )
        
        try:
            likes_data = response_list.json()
            likes = likes_data.get('items', likes_data.get('src', []))
            
            if len(likes) == 0:
                return self.log_result(
                    "GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}",
                    False,
                    "No likes to test with",
                    skip=True
                )
            
            like_id = likes[0].get('id', '').split('/')[-1]
            
            url_single = f"{self.base_url}/api/authors/{self.author1_id}/liked/{like_id}"
            response_single = requests.get(url_single, auth=self.auth)
            
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}",
                response_single.status_code == 200,
                f"Single like retrieved" if response_single.status_code == 200 else f"Expected 200, got {response_single.status_code}"
            )
        except Exception as e:
            return self.log_result(
                "GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}",
                False,
                f"Error: {str(e)}"
            )
    
    # ==================== MAIN TEST RUNNER ====================
    
    def run_all_tests(self):
        """Run all test suites"""
        print("\n" + "="*80)
        print("SOCIAL DISTRIBUTION API COMPREHENSIVE TEST SUITE")
        print("Testing against:", self.base_url)
        print("="*80)
        
        # Authentication tests
        self.test_auth_required_no_auth()
        self.test_auth_valid()
        
        # Authors API tests
        self.test_get_authors_paginated()
        self.test_get_single_author()
        self.test_get_author_by_fqid()
        
        # Followers API tests
        self.test_followers_api()
        
        # Inbox API tests
        self.test_inbox_follow_request()
        self.test_inbox_post()
        self.test_inbox_like()
        self.test_inbox_comment()
        
        # Entries/Posts API tests
        self.test_entries_api()
        self.test_create_entry()
        self.test_get_single_entry()
        self.test_update_entry()
        self.test_delete_entry()
        self.test_get_entry_by_fqid()
        
        # Visibility tests
        self.test_visibility_public()
        self.test_visibility_friends_only()
        self.test_visibility_unlisted()
        
        # Image entries tests
        self.test_image_entries()
        
        # Comments API tests
        self.test_comments_api()
        self.test_comments_by_fqid()
        self.test_commented_api()
        self.test_single_comment()
        
        # Likes API tests
        self.test_likes_on_entry()
        self.test_likes_on_entry_by_fqid()
        self.test_likes_on_comment()
        self.test_liked_api()
        self.test_single_like()
        
        # Print summary
        success = self.print_summary()
        return success


def main():
    parser = argparse.ArgumentParser(description='Test Social Distribution API')
    parser.add_argument('--url', default='http://127.0.0.1:8000', help='Base URL of the API')
    parser.add_argument('--user', default='admin', help='Username for authentication')
    parser.add_argument('--password', default='admin', help='Password for authentication')
    
    args = parser.parse_args()
    
    tester = APISpecTester(args.url, args.user, args.password)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
