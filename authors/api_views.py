"""
API Views for Social Distribution Project
Implements REST API endpoints for federation between nodes
"""
import json
import base64
import uuid
from django.http import JsonResponse, HttpResponse, Http404
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Author, Post, Follow, FollowRequest, Like, Comment, CommentLike
from .authentication import http_basic_auth_or_session


# ==================== Helper Functions for FQID Support ====================

def _get_author_by_id_or_fqid(identifier):
    """Get author by UUID or FQID (full URL)"""
    if not identifier:
        return None
    try:
        # Try UUID first
        return Author.objects.get(id=identifier)
    except (Author.DoesNotExist, ValueError):
        # Fall back to FQID (full URL)
        return get_object_or_404(Author, url=identifier)


def _get_post_by_id_or_fqid(entry_id=None, entry_fqid=None, author_id=None):
    """Get post by UUID or FQID (full URL)"""
    if entry_fqid:
        # Try to find by FQID
        try:
            # Try by origin field first
            return Post.objects.get(origin=entry_fqid)
        except Post.DoesNotExist:
            try:
                # Try by source field
                return Post.objects.get(source=entry_fqid)
            except Post.DoesNotExist:
                # Try parsing the FQID to extract UUID
                parts = entry_fqid.split('/')
                if len(parts) >= 2:
                    potential_uuid = parts[-1]
                    try:
                        return Post.objects.get(id=potential_uuid)
                    except (Post.DoesNotExist, ValueError):
                        pass
                raise Http404("Post not found")
    elif entry_id:
        # Use UUID
        if author_id:
            return get_object_or_404(Post, id=entry_id, author_id=author_id)
        else:
            return get_object_or_404(Post, id=entry_id)
    else:
        raise Http404("No entry identifier provided")


def _get_comment_by_fqid(comment_fqid):
    """Get comment by FQID (full URL) or UUID"""
    try:
        # Try UUID first
        return Comment.objects.get(id=comment_fqid)
    except (Comment.DoesNotExist, ValueError, Exception):
        # Try parsing the FQID to extract UUID
        parts = comment_fqid.split('/')
        if len(parts) >= 2:
            potential_uuid = parts[-1]
            try:
                return Comment.objects.get(id=potential_uuid)
            except (Comment.DoesNotExist, ValueError, Exception):
                pass
        raise Http404("Comment not found")


def _get_like_by_fqid(like_fqid):
    """Get like by FQID (full URL) or UUID"""
    try:
        # Try UUID first
        return Like.objects.get(id=like_fqid)
    except (Like.DoesNotExist, ValueError, Exception):
        # Try parsing the FQID to extract UUID
        parts = like_fqid.split('/')
        if len(parts) >= 2:
            potential_uuid = parts[-1]
            try:
                return Like.objects.get(id=potential_uuid)
            except (Like.DoesNotExist, ValueError, Exception):
                pass
        raise Http404("Like not found")


def _get_comment_by_id_or_fqid(comment_id=None, comment_fqid=None):
    """Get comment by UUID or FQID (full URL)"""
    if comment_fqid:
        return _get_comment_by_fqid(comment_fqid)
    elif comment_id:
        return get_object_or_404(Comment, id=comment_id)
    else:
        raise Http404("Comment identifier required")


def _get_like_by_id_or_fqid(like_id=None, like_fqid=None):
    """Get like by UUID or FQID (full URL)"""
    if like_fqid:
        return _get_like_by_fqid(like_fqid)
    elif like_id:
        return get_object_or_404(Like, id=like_id)
    else:
        raise Http404("Like identifier required")


# ==================== JSON Builder Functions ====================

def build_author_dict(author, request):
    """Helper function to build author JSON object"""
    web_url = reverse('authors:author_profile', kwargs={'author_id': author.id})
    return {
        "type": "author",
        "id": author.url or f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/",
        "host": author.host or f"{request.scheme}://{request.get_host()}",
        "displayName": author.displayName,
        "url": author.url or f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/",
        "github": author.github,
        "profileImage": request.build_absolute_uri(author.profileImage.url) if author.profileImage else None,
        "web": f"{request.scheme}://{request.get_host()}{web_url}",
    }


def build_post_dict(post, request):
    """Helper function to build post/entry JSON object"""
    author = post.author
    entry_url = f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}"
    
    data = {
        "type": "post",
        "id": entry_url,
        "author": build_author_dict(author, request),
        "title": post.title,
        "source": post.source or entry_url,
        "origin": post.origin or entry_url,
        "description": post.content[:200] if post.content else "",  # First 200 chars
        "contentType": post.contentType,
        "content": post.content,
        "visibility": post.visibility,
        "published": post.published.isoformat(),
        "count": post.comments.count(),
        "comments": f"{entry_url}/comments",
        "commentsSrc": {
            "type": "comments",
            "page": 1,
            "size": 5,
            "post": entry_url,
            "id": f"{entry_url}/comments",
            "comments": []  # Can be populated if needed
        }
    }
    
    # Add image if present
    if post.image:
        data["image"] = request.build_absolute_uri(post.image.url)
    
    return data


def build_comment_dict(comment, request):
    """Helper function to build comment JSON object"""
    post = comment.post
    author = post.author
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}/comments/{comment.id}"
    
    return {
        "type": "comment",
        "id": comment_url,
        "author": build_author_dict(comment.author, request),
        "comment": comment.content,
        "contentType": "text/plain",
        "published": comment.created_at.isoformat(),
    }


def build_like_dict(like, request):
    """Helper function to build like JSON object"""
    post = like.post
    author = post.author
    like_id_url = f"{request.scheme}://{request.get_host()}/api/authors/{like.author.id}/liked/{like.id}"
    
    return {
        "type": "like",
        "id": like_id_url,
        "author": build_author_dict(like.author, request),
        "object": f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}",
        "published": like.created_at.isoformat(),
    }


def build_comment_like_dict(comment_like, request):
    """Helper function to build comment like JSON object"""
    comment = comment_like.comment
    post = comment.post
    author = post.author
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}/comments/{comment.id}"
    
    return {
        "type": "like",
        "author": build_author_dict(comment_like.author, request),
        "object": comment_url,
        "published": comment_like.created_at.isoformat(),
    }




@method_decorator(csrf_exempt, name='dispatch')
class InboxAPIView(View):
    """
    POST /api/authors/{AUTHOR_SERIAL}/inbox
    The inbox is how other nodes send objects to an author
    Accepts: follow requests, posts, likes, comments
    """
    
    def post(self, request, author_id):
        """Receive an object in the author's inbox"""
        try:
            # Get the recipient author
            recipient = get_object_or_404(Author, id=author_id)
            
            # Parse the incoming JSON
            data = json.loads(request.body)
            object_type = data.get('type', '').lower()
            
            if object_type == 'follow':
                return self.handle_follow_request(recipient, data, request)
            elif object_type == 'post':
                return self.handle_post(recipient, data, request)
            elif object_type == 'like':
                return self.handle_like(recipient, data, request)
            elif object_type == 'comment':
                return self.handle_comment(recipient, data, request)
            else:
                return JsonResponse({'error': f'Unknown object type: {object_type}'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def handle_follow_request(self, recipient, data, request):
        """Handle incoming follow request"""
        try:
            # Extract actor (sender) information
            actor_data = data.get('actor', {})
            actor_id = actor_data.get('id')
            
            # Try to find existing author or create a stub
            # For remote authors, generate username from URL
            actor_username = actor_id.split('/')[-2] if actor_id else 'remote_actor'
            actor, created = Author.objects.get_or_create(
                url=actor_id,
                defaults={
                    'username': f"remote_{actor_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': actor_data.get('displayName', 'Unknown'),
                    'host': actor_data.get('host', ''),
                    'github': actor_data.get('github'),
                }
            )
            
            # Create or get follow request
            follow_request, created = FollowRequest.objects.get_or_create(
                sender=actor,
                receiver=recipient,
                defaults={'status': 'PENDING'}
            )
            
            if created:
                return JsonResponse({'message': 'Follow request created'}, status=201)
            else:
                return JsonResponse({'message': 'Follow request already exists'}, status=200)
                
        except Exception as e:
            return JsonResponse({'error': f'Failed to process follow request: {str(e)}'}, status=400)
    
    def handle_post(self, recipient, data, request):
        """Handle incoming post/entry"""
        try:
            # Extract author information
            author_data = data.get('author', {})
            author_id = author_data.get('id')
            
            # Get or create the author
            # For remote authors, generate username from URL
            author_username = author_id.split('/')[-2] if author_id else 'remote_author'
            author, created = Author.objects.get_or_create(
                url=author_id,
                defaults={
                    'username': f"remote_{author_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': author_data.get('displayName', 'Unknown'),
                    'host': author_data.get('host', ''),
                    'github': author_data.get('github'),
                }
            )
            
            # Extract post ID from the post's id field
            post_id_str = data.get('id', '').split('/')[-1]
            # Try to use the ID if it's a valid UUID, otherwise let Django generate one
            try:
                post_id = uuid.UUID(post_id_str) if post_id_str else None
            except (ValueError, AttributeError):
                post_id = None
            
            # Create or update the post
            if post_id:
                post, created = Post.objects.update_or_create(
                    id=post_id,
                    defaults={
                        'author': author,
                        'title': data.get('title', 'Untitled'),
                        'content': data.get('content', ''),
                        'contentType': data.get('contentType', 'text/plain'),
                        'visibility': data.get('visibility', 'PUBLIC'),
                        'source': data.get('source'),
                        'origin': data.get('origin'),
                    }
                )
            else:
                # If no valid UUID, create a new post
                post = Post.objects.create(
                    author=author,
                    title=data.get('title', 'Untitled'),
                    content=data.get('content', ''),
                    contentType=data.get('contentType', 'text/plain'),
                    visibility=data.get('visibility', 'PUBLIC'),
                    source=data.get('source'),
                    origin=data.get('origin'),
                )
                created = True
            
            return JsonResponse({'message': 'Post received'}, status=201 if created else 200)
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to process post: {str(e)}'}, status=400)
    
    def handle_like(self, recipient, data, request):
        """Handle incoming like"""
        try:
            # Extract author information
            author_data = data.get('author', {})
            author_id = author_data.get('id')
            
            # Get or create the liker
            # For remote authors, generate username from URL
            author_username = author_id.split('/')[-2] if author_id else 'remote_author'
            liker, created = Author.objects.get_or_create(
                url=author_id,
                defaults={
                    'username': f"remote_{author_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': author_data.get('displayName', 'Unknown'),
                    'host': author_data.get('host', ''),
                    'github': author_data.get('github'),
                }
            )
            
            # Extract the object being liked (post ID)
            object_url = data.get('object', '')
            post_id_str = object_url.split('/')[-1]
            
            # Try to parse as UUID
            try:
                post_id = uuid.UUID(post_id_str)
                # Try to find the post
                post = Post.objects.filter(id=post_id).first()
                if not post:
                    # Post doesn't exist locally - create a stub for federated content
                    # Extract author ID from object URL (/authors/{id}/entries/{post_id})
                    url_parts = object_url.split('/')
                    if 'authors' in url_parts and 'entries' in url_parts:
                        author_idx = url_parts.index('authors') + 1
                        post_author_id = url_parts[author_idx]
                        # Create or get the author stub
                        post_author, _ = Author.objects.get_or_create(
                            id=post_author_id,
                            defaults={
                                'username': f"federated_{post_author_id[:8]}",
                                'displayName': 'Federated Author'
                            }
                        )
                        # Create stub post
                        post = Post.objects.create(
                            id=post_id,
                            author=post_author,
                            title='Federated Post',
                            content='',
                            source=object_url,
                            origin=object_url
                        )
                    else:
                        return JsonResponse({'error': 'Invalid object URL format'}, status=400)
            except (ValueError, AttributeError):
                # If not a valid UUID, we can't process this like
                return JsonResponse({'message': 'Like recorded for external content'}, status=201)
            
            # Create the like (if it doesn't exist)
            like, created = Like.objects.get_or_create(
                author=liker,
                post=post
            )
            
            return JsonResponse({'message': 'Like received'}, status=201 if created else 200)
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to process like: {str(e)}'}, status=400)
    
    def handle_comment(self, recipient, data, request):
        """Handle incoming comment"""
        try:
            # Extract author information
            author_data = data.get('author', {})
            author_id = author_data.get('id')
            
            # Get or create the commenter
            # For remote authors, generate username from URL
            author_username = author_id.split('/')[-2] if author_id else 'remote_author'
            commenter, created = Author.objects.get_or_create(
                url=author_id,
                defaults={
                    'username': f"remote_{author_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': author_data.get('displayName', 'Unknown'),
                    'host': author_data.get('host', ''),
                    'github': author_data.get('github'),
                }
            )
            
            # Extract post ID - can be from comment's id field OR entry field
            comment_id_url = data.get('id', '')
            entry_url = data.get('entry', data.get('object', ''))
            
            # Try to extract from id field first (format: .../authors/{id}/entries/{post_id}/comments/{comment_id})
            if comment_id_url:
                parts = comment_id_url.split('/')
                if 'entries' in parts:
                    entries_idx = parts.index('entries')
                    post_id_str = parts[entries_idx + 1] if entries_idx + 1 < len(parts) else None
                else:
                    post_id_str = None
            else:
                # Fall back to entry/object field (format: .../authors/{id}/entries/{post_id})
                post_id_str = entry_url.split('/')[-1] if entry_url else None
            
            # Try to parse as UUID
            try:
                post_id = uuid.UUID(post_id_str) if post_id_str else None
                # Try to find the post
                post = Post.objects.filter(id=post_id).first() if post_id else None
                if not post:
                    # Post doesn't exist locally - create a stub for federated content
                    # Use entry_url to extract author and post IDs
                    url_parts = (entry_url or comment_id_url).split('/')
                    if 'authors' in url_parts and 'entries' in url_parts:
                        author_idx = url_parts.index('authors') + 1
                        entries_idx = url_parts.index('entries')
                        post_author_id_str = url_parts[author_idx]
                        post_id_str = url_parts[entries_idx + 1]
                        
                        # Try to parse author and post IDs as UUIDs
                        try:
                            post_author_id = uuid.UUID(post_author_id_str)
                            post_id = uuid.UUID(post_id_str)
                        except (ValueError, AttributeError):
                            return JsonResponse({'message': 'Comment recorded for external content'}, status=201)
                        
                        # Create or get the author stub
                        post_author, _ = Author.objects.get_or_create(
                            id=post_author_id,
                            defaults={
                                'username': f"federated_{str(post_author_id)[:8]}",
                                'displayName': 'Federated Author'
                            }
                        )
                        # Create stub post
                        post = Post.objects.create(
                            id=post_id,
                            author=post_author,
                            title='Federated Post',
                            content='',
                        )
                    else:
                        return JsonResponse({'error': 'Invalid comment/entry URL format'}, status=400)
            except (ValueError, AttributeError, TypeError):
                return JsonResponse({'message': 'Comment recorded for external content'}, status=201)
            
            # Create the comment
            comment = Comment.objects.create(
                post=post,
                author=commenter,
                content=data.get('comment', '')
            )
            
            return JsonResponse({'message': 'Comment received'}, status=201)
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to process comment: {str(e)}'}, status=400)



# ==================== JSON Builder Functions ====================

def build_author_dict(author, request):
    """Helper function to build author JSON object"""
    web_url = reverse('authors:author_profile', kwargs={'author_id': author.id})
    return {
        "type": "author",
        "id": author.url or f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/",
        "host": author.host or f"{request.scheme}://{request.get_host()}",
        "displayName": author.displayName,
        "url": author.url or f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/",
        "github": author.github,
        "profileImage": request.build_absolute_uri(author.profileImage.url) if author.profileImage else None,
        "web": f"{request.scheme}://{request.get_host()}{web_url}",
    }


def build_post_dict(post, request):
    """Helper function to build post/entry JSON object"""
    author = post.author
    entry_url = f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}"
    
    data = {
        "type": "post",
        "id": entry_url,
        "author": build_author_dict(author, request),
        "title": post.title,
        "source": post.source or entry_url,
        "origin": post.origin or entry_url,
        "description": post.content[:200] if post.content else "",  # First 200 chars
        "contentType": post.contentType,
        "content": post.content,
        "visibility": post.visibility,
        "published": post.published.isoformat(),
        "count": post.comments.count(),
        "comments": f"{entry_url}/comments",
        "commentsSrc": {
            "type": "comments",
            "page": 1,
            "size": 5,
            "post": entry_url,
            "id": f"{entry_url}/comments",
            "comments": []  # Can be populated if needed
        }
    }
    
    # Add image if present
    if post.image:
        data["image"] = request.build_absolute_uri(post.image.url)
    
    return data


def build_comment_dict(comment, request):
    """Helper function to build comment JSON object"""
    post = comment.post
    author = post.author
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}/comments/{comment.id}"
    
    return {
        "type": "comment",
        "id": comment_url,
        "author": build_author_dict(comment.author, request),
        "comment": comment.content,
        "contentType": "text/plain",
        "published": comment.created_at.isoformat(),
    }


def build_like_dict(like, request):
    """Helper function to build like JSON object"""
    post = like.post
    author = post.author
    like_id_url = f"{request.scheme}://{request.get_host()}/api/authors/{like.author.id}/liked/{like.id}"
    
    return {
        "type": "like",
        "id": like_id_url,
        "author": build_author_dict(like.author, request),
        "object": f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}",
        "published": like.created_at.isoformat(),
    }


def build_comment_like_dict(comment_like, request):
    """Helper function to build comment like JSON object"""
    comment = comment_like.comment
    post = comment.post
    author = post.author
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}/comments/{comment.id}"
    
    return {
        "type": "like",
        "author": build_author_dict(comment_like.author, request),
        "object": comment_url,
        "published": comment_like.created_at.isoformat(),
    }




@method_decorator(csrf_exempt, name='dispatch')
class InboxAPIView(View):
    """
    POST /api/authors/{AUTHOR_SERIAL}/inbox
    The inbox is how other nodes send objects to an author
    Accepts: follow requests, posts, likes, comments
    """
    
    def post(self, request, author_id):
        """Receive an object in the author's inbox"""
        try:
            # Get the recipient author
            recipient = get_object_or_404(Author, id=author_id)
            
            # Parse the incoming JSON
            data = json.loads(request.body)
            object_type = data.get('type', '').lower()
            
            if object_type == 'follow':
                return self.handle_follow_request(recipient, data, request)
            elif object_type == 'post':
                return self.handle_post(recipient, data, request)
            elif object_type == 'like':
                return self.handle_like(recipient, data, request)
            elif object_type == 'comment':
                return self.handle_comment(recipient, data, request)
            else:
                return JsonResponse({'error': f'Unknown object type: {object_type}'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def handle_follow_request(self, recipient, data, request):
        """Handle incoming follow request"""
        try:
            # Extract actor (sender) information
            actor_data = data.get('actor', {})
            actor_id = actor_data.get('id')
            
            # Try to find existing author or create a stub
            # For remote authors, generate username from URL
            actor_username = actor_id.split('/')[-2] if actor_id else 'remote_actor'
            actor, created = Author.objects.get_or_create(
                url=actor_id,
                defaults={
                    'username': f"remote_{actor_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': actor_data.get('displayName', 'Unknown'),
                    'host': actor_data.get('host', ''),
                    'github': actor_data.get('github'),
                }
            )
            
            # Create or get follow request
            follow_request, created = FollowRequest.objects.get_or_create(
                sender=actor,
                receiver=recipient,
                defaults={'status': 'PENDING'}
            )
            
            if created:
                return JsonResponse({'message': 'Follow request created'}, status=201)
            else:
                return JsonResponse({'message': 'Follow request already exists'}, status=200)
                
        except Exception as e:
            return JsonResponse({'error': f'Failed to process follow request: {str(e)}'}, status=400)
    
    def handle_post(self, recipient, data, request):
        """Handle incoming post/entry"""
        try:
            # Extract author information
            author_data = data.get('author', {})
            author_id = author_data.get('id')
            
            # Get or create the author
            # For remote authors, generate username from URL
            author_username = author_id.split('/')[-2] if author_id else 'remote_author'
            author, created = Author.objects.get_or_create(
                url=author_id,
                defaults={
                    'username': f"remote_{author_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': author_data.get('displayName', 'Unknown'),
                    'host': author_data.get('host', ''),
                    'github': author_data.get('github'),
                }
            )
            
            # Extract post ID from the post's id field
            post_id_str = data.get('id', '').split('/')[-1]
            # Try to use the ID if it's a valid UUID, otherwise let Django generate one
            try:
                post_id = uuid.UUID(post_id_str) if post_id_str else None
            except (ValueError, AttributeError):
                post_id = None
            
            # Create or update the post
            if post_id:
                post, created = Post.objects.update_or_create(
                    id=post_id,
                    defaults={
                        'author': author,
                        'title': data.get('title', 'Untitled'),
                        'content': data.get('content', ''),
                        'contentType': data.get('contentType', 'text/plain'),
                        'visibility': data.get('visibility', 'PUBLIC'),
                        'source': data.get('source'),
                        'origin': data.get('origin'),
                    }
                )
            else:
                # If no valid UUID, create a new post
                post = Post.objects.create(
                    author=author,
                    title=data.get('title', 'Untitled'),
                    content=data.get('content', ''),
                    contentType=data.get('contentType', 'text/plain'),
                    visibility=data.get('visibility', 'PUBLIC'),
                    source=data.get('source'),
                    origin=data.get('origin'),
                )
                created = True
            
            return JsonResponse({'message': 'Post received'}, status=201 if created else 200)
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to process post: {str(e)}'}, status=400)
    
    def handle_like(self, recipient, data, request):
        """Handle incoming like"""
        try:
            # Extract author information
            author_data = data.get('author', {})
            author_id = author_data.get('id')
            
            # Get or create the liker
            # For remote authors, generate username from URL
            author_username = author_id.split('/')[-2] if author_id else 'remote_author'
            liker, created = Author.objects.get_or_create(
                url=author_id,
                defaults={
                    'username': f"remote_{author_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': author_data.get('displayName', 'Unknown'),
                    'host': author_data.get('host', ''),
                    'github': author_data.get('github'),
                }
            )
            
            # Extract the object being liked (post ID)
            object_url = data.get('object', '')
            post_id_str = object_url.split('/')[-1]
            
            # Try to parse as UUID
            try:
                post_id = uuid.UUID(post_id_str)
                # Try to find the post
                post = Post.objects.filter(id=post_id).first()
                if not post:
                    # Post doesn't exist locally - create a stub for federated content
                    # Extract author ID from object URL (/authors/{id}/entries/{post_id})
                    url_parts = object_url.split('/')
                    if 'authors' in url_parts and 'entries' in url_parts:
                        author_idx = url_parts.index('authors') + 1
                        post_author_id = url_parts[author_idx]
                        # Create or get the author stub
                        post_author, _ = Author.objects.get_or_create(
                            id=post_author_id,
                            defaults={
                                'username': f"federated_{post_author_id[:8]}",
                                'displayName': 'Federated Author'
                            }
                        )
                        # Create stub post
                        post = Post.objects.create(
                            id=post_id,
                            author=post_author,
                            title='Federated Post',
                            content='',
                            source=object_url,
                            origin=object_url
                        )
                    else:
                        return JsonResponse({'error': 'Invalid object URL format'}, status=400)
            except (ValueError, AttributeError):
                # If not a valid UUID, we can't process this like
                return JsonResponse({'message': 'Like recorded for external content'}, status=201)
            
            # Create the like (if it doesn't exist)
            like, created = Like.objects.get_or_create(
                author=liker,
                post=post
            )
            
            return JsonResponse({'message': 'Like received'}, status=201 if created else 200)
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to process like: {str(e)}'}, status=400)
    
    def handle_comment(self, recipient, data, request):
        """Handle incoming comment"""
        try:
            # Extract author information
            author_data = data.get('author', {})
            author_id = author_data.get('id')
            
            # Get or create the commenter
            # For remote authors, generate username from URL
            author_username = author_id.split('/')[-2] if author_id else 'remote_author'
            commenter, created = Author.objects.get_or_create(
                url=author_id,
                defaults={
                    'username': f"remote_{author_username}_{uuid.uuid4().hex[:8]}",
                    'displayName': author_data.get('displayName', 'Unknown'),
                    'host': author_data.get('host', ''),
                    'github': author_data.get('github'),
                }
            )
            
            # Extract post ID - can be from comment's id field OR entry field
            comment_id_url = data.get('id', '')
            entry_url = data.get('entry', data.get('object', ''))
            
            # Try to extract from id field first (format: .../authors/{id}/entries/{post_id}/comments/{comment_id})
            if comment_id_url:
                parts = comment_id_url.split('/')
                if 'entries' in parts:
                    entries_idx = parts.index('entries')
                    post_id_str = parts[entries_idx + 1] if entries_idx + 1 < len(parts) else None
                else:
                    post_id_str = None
            else:
                # Fall back to entry/object field (format: .../authors/{id}/entries/{post_id})
                post_id_str = entry_url.split('/')[-1] if entry_url else None
            
            # Try to parse as UUID
            try:
                post_id = uuid.UUID(post_id_str) if post_id_str else None
                # Try to find the post
                post = Post.objects.filter(id=post_id).first() if post_id else None
                if not post:
                    # Post doesn't exist locally - create a stub for federated content
                    # Use entry_url to extract author and post IDs
                    url_parts = (entry_url or comment_id_url).split('/')
                    if 'authors' in url_parts and 'entries' in url_parts:
                        author_idx = url_parts.index('authors') + 1
                        entries_idx = url_parts.index('entries')
                        post_author_id_str = url_parts[author_idx]
                        post_id_str = url_parts[entries_idx + 1]
                        
                        # Try to parse author and post IDs as UUIDs
                        try:
                            post_author_id = uuid.UUID(post_author_id_str)
                            post_id = uuid.UUID(post_id_str)
                        except (ValueError, AttributeError):
                            return JsonResponse({'message': 'Comment recorded for external content'}, status=201)
                        
                        # Create or get the author stub
                        post_author, _ = Author.objects.get_or_create(
                            id=post_author_id,
                            defaults={
                                'username': f"federated_{str(post_author_id)[:8]}",
                                'displayName': 'Federated Author'
                            }
                        )
                        # Create stub post
                        post = Post.objects.create(
                            id=post_id,
                            author=post_author,
                            title='Federated Post',
                            content='',
                        )
                    else:
                        return JsonResponse({'error': 'Invalid comment/entry URL format'}, status=400)
            except (ValueError, AttributeError, TypeError):
                return JsonResponse({'message': 'Comment recorded for external content'}, status=201)
            
            # Create the comment
            comment = Comment.objects.create(
                post=post,
                author=commenter,
                content=data.get('comment', '')
            )
            
            return JsonResponse({'message': 'Comment received'}, status=201)
            
        except Exception as e:
            return JsonResponse({'error': f'Failed to process comment: {str(e)}'}, status=400)
