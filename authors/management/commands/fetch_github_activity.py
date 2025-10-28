import requests
import json
from django.core.management.base import BaseCommand
from authors.models import Author, Post
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches public GitHub activity for authors and creates posts'

    def handle(self, *args, **options):
        # Get all authors who have a GitHub profile URL set
        authors_with_github = Author.objects.filter(github__isnull=False).exclude(github='')

        for author in authors_with_github:
            self.stdout.write(f"Processing GitHub activity for author: {author.displayName}")
            
            # Extract GitHub username from the GitHub URL
            github_username = self.extract_username_from_url(author.github)
            if not github_username:
                self.stdout.write(f"Could not extract GitHub username from URL: {author.github}")
                continue

            try:
                # Fetch public events from GitHub API, considering the last event ID
                events = self.fetch_github_events(github_username, author.last_github_event_id)
                
                if events:
                    # Process events and create posts
                    created_count = self.process_events(author, events)
                    self.stdout.write(f"Created {created_count} new posts for {author.displayName}")
                else:
                    self.stdout.write(f"No new events found for {author.displayName}")
                    
            except Exception as e:
                logger.error(f"Error processing GitHub activity for {author.displayName}: {str(e)}")
        
        self.stdout.write(
            self.style.SUCCESS('Successfully processed GitHub activity for all authors')
        )

    def extract_username_from_url(self, github_url):
        """Extract GitHub username from the GitHub profile URL"""
        try:
            # Handle various GitHub URL formats:
            # https://github.com/username
            # http://github.com/username
            # https://www.github.com/username
            # etc.
            github_url = github_url.strip().rstrip('/')
            if github_url.startswith('http'):
                # Parse the URL and extract the last part
                parts = github_url.split('/')
                if len(parts) >= 3 and 'github.com' in parts[2]:
                    # Find the username part after 'github.com'
                    for i, part in enumerate(parts):
                        if 'github.com' in part and i + 1 < len(parts):
                            return parts[i + 1]
            return None
        except Exception:
            return None

    def fetch_github_events(self, username, last_event_id=None):
        """Fetch public events for a GitHub user"""
        url = f"https://api.github.com/users/{username}/events/public"
        
        try:
            # Set a reasonable timeout
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            events = response.json()
            
            # Filter to only include events that haven't been processed yet
            if last_event_id:
                # Only return events that are newer than the last processed event
                filtered_events = []
                for event in events:
                    if event['id'] == last_event_id:
                        break
                    filtered_events.append(event)
                return filtered_events
            else:
                # Return the first 10 events (to avoid processing too much at once)
                return events[:10]
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"GitHub user {username} not found")
            elif e.response.status_code == 403:
                logger.warning(f"GitHub API rate limit exceeded for {username}")
            else:
                logger.error(f"HTTP error fetching events for {username}: {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching events for {username}: {e}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response when fetching events for {username}")
            return []

    def process_events(self, author, events):
        """Process GitHub events and create posts"""
        created_count = 0
        
        for event in events:
            try:
                # Check if we've already processed this event
                if author.last_github_event_id and event['id'] == author.last_github_event_id:
                    continue

                # Convert the event to a post
                post = self.create_post_from_event(author, event)
                
                if post:
                    created_count += 1
                    
                    # Update the last event ID for this author
                    author.last_github_event_id = event['id']
                    author.save(update_fields=['last_github_event_id'])
                    
            except Exception as e:
                logger.error(f"Error processing event {event.get('id', 'unknown')} for {author.displayName}: {e}")
                continue
        
        return created_count

    def create_post_from_event(self, author, event):
        """Convert a GitHub event to a Post object"""
        event_type = event.get('type')
        repo_name = event.get('repo', {}).get('name', 'unknown-repo')
        
        if event_type == 'PushEvent':
            return self.create_push_event_post(author, event)
        elif event_type == 'PullRequestEvent':
            return self.create_pull_request_event_post(author, event)
        elif event_type == 'IssuesEvent':
            return self.create_issues_event_post(author, event)
        elif event_type == 'WatchEvent':
            return self.create_watch_event_post(author, event)
        elif event_type == 'ForkEvent':
            return self.create_fork_event_post(author, event)
        elif event_type == 'CreateEvent':
            return self.create_create_event_post(author, event)
        elif event_type == 'DeleteEvent':
            return self.create_delete_event_post(author, event)
        else:
            # For other event types, create a generic post
            return self.create_generic_event_post(author, event)
    
    def create_push_event_post(self, author, event):
        """Create a post from a PushEvent"""
        try:
            repo_name = event['repo']['name']
            payload = event.get('payload', {})
            branch = payload.get('ref', '').replace('refs/heads/', '') if payload.get('ref') else 'main'
            commit_count = payload.get('size', 0)  # GitHub API includes 'size' field with number of commits
            
            # Create title and content
            if commit_count > 0:
                title = f"Pushed {commit_count} commit{'s' if commit_count > 1 else ''} to {repo_name}"
                content = f"Pushed {commit_count} commit{'s' if commit_count > 1 else ''} to branch '{branch}' in {repo_name}"
            else:
                # If no size is provided, just indicate a push occurred
                title = f"Pushed to {repo_name}"
                content = f"Pushed changes to branch '{branch}' in {repo_name}"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating PushEvent post: {e}")
            return None

    def create_pull_request_event_post(self, author, event):
        """Create a post from a PullRequestEvent"""
        try:
            repo_name = event['repo']['name']
            action = event['payload']['action']
            pr = event['payload']['pull_request']
            pr_title = pr['title']
            pr_number = pr['number']
            
            # Create title and content
            title = f"{action.title()} pull request in {repo_name}"
            content = f"{action.title()} pull request #{pr_number}: {pr_title}\n\n{pr.get('body', 'No description provided')}"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating PullRequestEvent post: {e}")
            return None

    def create_issues_event_post(self, author, event):
        """Create a post from an IssuesEvent"""
        try:
            repo_name = event['repo']['name']
            action = event['payload']['action']
            issue = event['payload']['issue']
            issue_title = issue['title']
            issue_number = issue['number']
            
            # Create title and content
            title = f"{action.title()} issue in {repo_name}"
            content = f"{action.title()} issue #{issue_number}: {issue_title}\n\n{issue.get('body', 'No description provided')}"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating IssuesEvent post: {e}")
            return None

    def create_watch_event_post(self, author, event):
        """Create a post from a WatchEvent (starring a repo)"""
        try:
            repo_name = event['repo']['name']
            
            # Create title and content
            title = f"Starred repository {repo_name}"
            content = f"Starred the repository {repo_name} on GitHub"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating WatchEvent post: {e}")
            return None

    def create_fork_event_post(self, author, event):
        """Create a post from a ForkEvent"""
        try:
            repo_name = event['repo']['name']
            
            # Create title and content
            title = f"Forked repository {repo_name}"
            content = f"Forked the repository {repo_name} on GitHub"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating ForkEvent post: {e}")
            return None

    def create_create_event_post(self, author, event):
        """Create a post from a CreateEvent"""
        try:
            repo_name = event['repo']['name']
            ref_type = event.get('payload', {}).get('ref_type', 'unknown')
            
            # Create title and content
            title = f"Created {ref_type} in {repo_name}"
            content = f"Created a new {ref_type} in the repository {repo_name}"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating CreateEvent post: {e}")
            return None

    def create_delete_event_post(self, author, event):
        """Create a post from a DeleteEvent"""
        try:
            repo_name = event['repo']['name']
            ref_type = event.get('payload', {}).get('ref_type', 'unknown')
            
            # Create title and content
            title = f"Deleted {ref_type} in {repo_name}"
            content = f"Deleted a {ref_type} in the repository {repo_name}"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating DeleteEvent post: {e}")
            return None

    def create_generic_event_post(self, author, event):
        """Create a post from other types of events"""
        try:
            event_type = event.get('type', 'Unknown').replace('Event', '')
            repo_name = event.get('repo', {}).get('name', 'unknown')
            
            # Create title and content
            title = f"{event_type} activity in {repo_name}"
            content = f"Performed {event_type} activity in repository {repo_name}"
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=title,
                content=content,
                contentType='text/plain',
                visibility='PUBLIC'
            )
            
            return post
        except Exception as e:
            logger.error(f"Error creating generic event post: {e}")
            return None