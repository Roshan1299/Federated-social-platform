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
from .authentication import http_basic_auth_or_session, http_basic_auth_required

# ==================== Helper Functions for FQID Support ====================

def _get_author_by_id_or_fqid(identifier):
    """Get author by UUID or FQID (full URL)"""
    if not identifier:
        return None
    
    # Normalize trailing slashes
    identifier_normalized = identifier.rstrip('/') if isinstance(identifier, str) else identifier
    
    # Try UUID first (only if it looks like a UUID)
    try:
        # Check if it could be a UUID (doesn't contain :// which indicates a URL)
        if '://' not in str(identifier):
            return Author.objects.get(id=identifier)
    except (Author.DoesNotExist, ValueError):
        pass
    
    # Fall back to FQID (full URL) - try both with and without trailing slash
    try:
        return Author.objects.get(url=identifier_normalized)
    except Author.DoesNotExist:
        try:
            return Author.objects.get(url=identifier_normalized + '/')
        except Author.DoesNotExist:
            raise Http404("Author not found")


def _get_post_by_id_or_fqid(entry_id=None, entry_fqid=None, author_id=None):
    """
    Get post by UUID or FQID (full URL).
    
    IMPORTANT: When entry_fqid is provided, ONLY match against source/origin fields.
    
    """
    if entry_fqid:
        # FQID lookup - ONLY match against source/origin fields
        # Normalize by stripping trailing slashes for comparison
        entry_fqid_normalized = entry_fqid.rstrip('/')
        
        # Also try with trailing slash in case it's stored that way
        entry_fqid_with_slash = entry_fqid_normalized + '/'
        
        try:
            # Try by origin field first (with and without trailing slash)
            return Post.objects.get(Q(origin=entry_fqid_normalized) | Q(origin=entry_fqid_with_slash))
        except Post.DoesNotExist:
            try:
                # Try by source field (with and without trailing slash)
                return Post.objects.get(Q(source=entry_fqid_normalized) | Q(source=entry_fqid_with_slash))
            except Post.DoesNotExist:
                # DO NOT extract UUID as fallback!
                # If FQID doesn't match source/origin, we don't have this post
                raise Http404("Post not found - FQID does not match any post in database")
    
    elif entry_id:
        # UUID/Serial lookup - match by id field
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


# ==================== Access Control Helper ====================

def can_access_post(post, request):
    """
    Check if the requesting user can access a post based on visibility rules.
    
    Returns True if:
    - Post is PUBLIC or PUBLIC_UNLISTED
    - Post is FRIENDS and user is the author
    - Post is FRIENDS and user is a mutual friend (both follow each other)
    - User is authenticated locally (for local requests)
    
    For remote requests (detected by lack of local authentication):
    - Only PUBLIC and PUBLIC_UNLISTED posts are accessible
    """
    # PUBLIC and PUBLIC_UNLISTED are always accessible
    if post.visibility in ['PUBLIC', 'PUBLIC_UNLISTED']:
        return True
    
    # FRIENDS posts require authentication
    if post.visibility == 'FRIENDS':
        # Not authenticated = remote request, FRIENDS posts not accessible
        if not hasattr(request, 'user') or request.user is None or not request.user.is_authenticated:
            return False
        
        # Author can always see their own posts
        if request.user.pk == post.author.pk:
            return True
        
        # Check if mutual friends
        is_friend = (
            Follow.objects.filter(follower=request.user, following=post.author).exists() and
            Follow.objects.filter(follower=post.author, following=request.user).exists()
        )
        return is_friend
    
    return False


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
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{comment.author.id}/commented/{comment.id}"
    
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
    # Use the correct comment URL format: /api/authors/{comment.author.id}/commented/{comment.id}
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{comment.author.id}/commented/{comment.id}"
    
    return {
        "type": "like",
        "author": build_author_dict(comment_like.author, request),
        "object": comment_url,
        "published": comment_like.created_at.isoformat(),
    }




@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(http_basic_auth_required, name='dispatch')
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
            # If the object refers to a comment (comment likes), handle specially
            # Comment URL format used by this API: /api/authors/{author_id}/commented/{comment_id}
            if '/commented/' in object_url or '/comments/' in object_url:
                # Extract comment id (last path component)
                comment_id_str = object_url.split('/')[-1]
                try:
                    # Try to resolve comment by id or FQID
                    comment = _get_comment_by_id_or_fqid(comment_id=comment_id_str, comment_fqid=object_url)
                    if not comment:
                        return JsonResponse({'error': 'Comment not found for comment-like'}, status=404)

                    # Create or get the comment liker (remote/local)
                    # (liker was created above)
                    comment_like, created = CommentLike.objects.get_or_create(
                        author=liker,
                        comment=comment
                    )
                    return JsonResponse({'message': 'Comment like received'}, status=201 if created else 200)
                except Exception as e:
                    return JsonResponse({'error': f'Failed to process comment like: {str(e)}'}, status=400)

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
            
            # Extract post ID - can be from comment's id field OR entry/post/object field
            comment_id_url = data.get('id', '')
            entry_url = data.get('entry', data.get('post', data.get('object', '')))
            
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


@method_decorator(http_basic_auth_or_session, name='dispatch')
class FollowersAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/followers
    Returns a list of authors who follow the specified author
    """
    
    def get(self, request, author_id):
        """Get list of followers"""
        author = get_object_or_404(Author, id=author_id)
        
        # Get all follower relationships
        follower_relations = Follow.objects.filter(following=author)
        
        # Build items list
        items = []
        for follow in follower_relations:
            items.append(build_author_dict(follow.follower, request))
        
        response_data = {
            "type": "followers",
            "items": items
        }
        
        return JsonResponse(response_data)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class SingleFollowerAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_ID}
    Check if FOREIGN_AUTHOR is a follower of AUTHOR
    Returns 404 if not a follower, 200 if they are
    """
    
    def get(self, request, author_id, follower_id):
        """Check if follower_id follows author_id"""
        author = get_object_or_404(Author, id=author_id)

        # The follower_id could be a UUID or a full URL
        import re
        follower = None
        uuid_regex = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        if uuid_regex.match(follower_id):
            try:
                follower = Author.objects.get(id=follower_id)
            except Author.DoesNotExist:
                follower = None

        if not follower:
            follower_id_norm = follower_id.rstrip('/')
            follower = Author.objects.filter(url__in=[follower_id_norm, follower_id_norm + '/']).first()
        
        # Check if follow relationship exists
        is_follower = Follow.objects.filter(follower=follower, following=author).exists()
        
        if is_follower:
            return JsonResponse(build_author_dict(follower, request))
        else:
            return HttpResponse("Not Found", status=404)
    
    def delete(self, request, author_id, follower_id):
        """Remove a follower - only AUTHOR_SERIAL can remove their followers"""
        author = get_object_or_404(Author, id=author_id)
        
        # Authorization: Only the author being followed can remove followers
        if str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: Only the author can remove their followers', status=403)
        
        # Parse follower_id (UUID or FQID)
        import re
        follower = None
        uuid_regex = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        if uuid_regex.match(follower_id):
            try:
                follower = Author.objects.get(id=follower_id)
            except Author.DoesNotExist:
                follower = None
        
        if not follower:
            follower_id_norm = follower_id.rstrip('/')
            follower = Author.objects.filter(url__in=[follower_id_norm, follower_id_norm + '/']).first()
        
        if not follower:
            return HttpResponse("Follower not found", status=404)
        
        # Delete the follow relationship
        Follow.objects.filter(follower=follower, following=author).delete()
        
        return JsonResponse({'message': 'Follower removed'}, status=204)
    
    @method_decorator(csrf_exempt)
    def put(self, request, author_id, follower_id):
        """Add a follower - only FOREIGN_AUTHOR_ID (the follower) can add themselves"""
        author = get_object_or_404(Author, id=author_id)
        
        # Parse follower_id (UUID or FQID)
        import re
        follower = None
        uuid_regex = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
        if uuid_regex.match(follower_id):
            try:
                follower = Author.objects.get(id=follower_id)
            except Author.DoesNotExist:
                follower = None
        
        if not follower:
            follower_id_norm = follower_id.rstrip('/')
            follower = Author.objects.filter(url__in=[follower_id_norm, follower_id_norm + '/']).first()
        
        if not follower:
            return HttpResponse("Follower not found", status=404)
        
        # Authorization: Only the follower themselves can add the follow relationship
        # Compare authenticated user with the follower
        if str(request.user.id) != str(follower.id):
            return HttpResponse('Forbidden: Only the follower can add themselves', status=403)
        
        # Create follow relationship
        follow, created = Follow.objects.get_or_create(
            follower=follower,
            following=author
        )
        
        return JsonResponse({'message': 'Follower added'}, status=201 if created else 200)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(http_basic_auth_or_session, name='dispatch')
class EntriesAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/entries/
    Returns recent posts by the author (paginated)
    
    POST /api/authors/{AUTHOR_SERIAL}/entries/
    Create a new post for the author
    """
    
    def get(self, request, author_id):
        """Get paginated list of author's posts"""
        author = get_object_or_404(Author, id=author_id)
        
        # Get page and size parameters
        page_num = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('size', 10))
        
        # Determine what posts the user can see based on authentication and relationship
        if request.user.is_authenticated and request.user.id == author.id:
            # Authenticated as author: all entries
            posts = Post.objects.filter(author=author, deleted=False).order_by('-published')
        elif request.user.is_authenticated:
            # Check if authenticated user is a friend (mutual follow)
            is_friend = (
                Follow.objects.filter(follower=request.user, following=author).exists() and
                Follow.objects.filter(follower=author, following=request.user).exists()
            )
            
            if is_friend:
                # Authenticated as friend: all entries
                posts = Post.objects.filter(author=author, deleted=False).order_by('-published')
            elif Follow.objects.filter(follower=request.user, following=author).exists():
                # Authenticated as follower: public + unlisted
                posts = Post.objects.filter(
                    author=author, 
                    deleted=False,
                    visibility__in=['PUBLIC', 'PUBLIC_UNLISTED']
                ).order_by('-published')
            else:
                # Authenticated but not following: only public
                posts = Post.objects.filter(author=author, visibility='PUBLIC', deleted=False).order_by('-published')
        else:
            # Not authenticated: only public entries
            posts = Post.objects.filter(author=author, visibility='PUBLIC', deleted=False).order_by('-published')
        
        # Paginate
        paginator = Paginator(posts, page_size)
        page_obj = paginator.get_page(page_num)
        
        # Build items list
        items = [build_post_dict(post, request) for post in page_obj]
        
        response_data = {
            "type": "posts",
            "items": items,
            "page": page_num,
            "size": page_size,
            "count": paginator.count
        }
        
        return JsonResponse(response_data)
    
    @method_decorator(csrf_exempt)
    def post(self, request, author_id):
        """Create a new post"""
        author = get_object_or_404(Author, id=author_id)
        
        # Check that authenticated user is the author
        if not request.user.is_authenticated or request.user.id != author.id:
            return HttpResponse("Forbidden", status=403)
        
        try:
            data = json.loads(request.body)
            content_type = data.get('contentType', 'text/plain')
            content = data.get('content', '')
            
            # Create the post
            post = Post.objects.create(
                author=author,
                title=data.get('title', 'Untitled'),
                content=content,
                contentType=content_type,
                visibility=data.get('visibility', 'PUBLIC'),
                source=data.get('source'),
                origin=data.get('origin'),
            )
            
            # Handle base64 image data
            if ';base64' in content_type and content:
                try:
                    # Decode the base64 image
                    image_data = base64.b64decode(content)
                    
                    # Determine file extension
                    ext = 'png'
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        ext = 'jpg'
                    elif 'gif' in content_type:
                        ext = 'gif'
                    
                    # Save to image field
                    from django.core.files.base import ContentFile
                    filename = f"post_{post.id}.{ext}"
                    post.image.save(filename, ContentFile(image_data), save=True)
                except Exception as e:
                    # If image decoding fails, continue without image
                    pass
            
            return JsonResponse(build_post_dict(post, request), status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(http_basic_auth_or_session, name='dispatch')
class SingleEntryAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}
    GET /api/entries/{ENTRY_FQID}
    Get a single post/entry
    
    PUT /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}
    Update a post/entry
    
    DELETE /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}
    Delete a post/entry
    """
    
    def get(self, request, author_id=None, entry_id=None, entry_fqid=None):
        """Get a single post - handles both UUID and FQID"""
        post = _get_post_by_id_or_fqid(entry_id=entry_id, entry_fqid=entry_fqid, author_id=author_id)
        
        # Check if deleted
        if post.deleted:
            return HttpResponse("Not Found", status=404)
        
        # Check visibility permissions
        if post.visibility == "FRIENDS":
            # Require authentication for friends-only posts
            if not request.user.is_authenticated:
                return HttpResponse("Forbidden", status=403)
            
            # Author can always see their own posts
            # Use Django ORM comparison to ensure proper UUID handling
            if request.user.pk != post.author.pk:
                # Check if they are friends (mutual follows)
                is_friend = (
                    Follow.objects.filter(follower=request.user, following=post.author).exists() and
                    Follow.objects.filter(follower=post.author, following=request.user).exists()
                )
                if not is_friend:
                    return HttpResponse("Forbidden", status=403)
        
        return JsonResponse(build_post_dict(post, request))
    
    @method_decorator(csrf_exempt)
    def put(self, request, author_id=None, entry_id=None, entry_fqid=None):
        """Update a post"""
        post = _get_post_by_id_or_fqid(entry_id=entry_id, entry_fqid=entry_fqid, author_id=author_id)
        
        # Check that authenticated user is the author
        if not request.user.is_authenticated or request.user.pk != post.author.pk:
            return HttpResponse("Forbidden", status=403)
        
        try:
            data = json.loads(request.body)
            
            # Update fields
            post.title = data.get('title', post.title)
            post.content = data.get('content', post.content)
            post.contentType = data.get('contentType', post.contentType)
            post.visibility = data.get('visibility', post.visibility)
            post.save()
            
            return JsonResponse(build_post_dict(post, request))
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    @method_decorator(csrf_exempt)
    def delete(self, request, author_id=None, entry_id=None, entry_fqid=None):
        """Delete a post (soft delete)"""
        post = _get_post_by_id_or_fqid(entry_id=entry_id, entry_fqid=entry_fqid, author_id=author_id)
        
        # Check that authenticated user is the author
        if not request.user.is_authenticated or request.user.pk != post.author.pk:
            return HttpResponse("Forbidden", status=403)
        
        post.deleted = True
        post.save()
        
        return JsonResponse({'message': 'Post deleted'}, status=204)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class CommentsAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments
    GET /api/entries/{ENTRY_FQID}/comments
    GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comment/{COMMENT_FQID}
    GET /api/authors/{AUTHOR_SERIAL}/commented
    GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}
    GET /api/authors/{AUTHOR_FQID}/commented
    GET /api/commented/{COMMENT_FQID}
    Get comments on a post (paginated) or single comment
    """
    
    def get(self, request, author_id=None, entry_id=None, entry_fqid=None, 
            comment_id=None, comment_fqid=None, author_fqid=None):
        """Get paginated list of comments or single comment - handles UUID and FQID"""
        
        # Handle different route patterns
        if comment_fqid or comment_id:
            # GET /api/commented/{COMMENT_FQID}
            # GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comment/{COMMENT_FQID}
            # GET /api/authors/{AUTHOR_SERIAL}/commented/{COMMENT_SERIAL}
            comment = _get_comment_by_id_or_fqid(comment_id=comment_id, comment_fqid=comment_fqid)
            
            # Check if user can access the post this comment is on
            if not can_access_post(comment.post, request):
                return HttpResponse("Forbidden", status=403)
            
            return JsonResponse(build_comment_dict(comment, request))
        
        elif author_fqid or (author_id and not entry_id):
            # GET /api/authors/{AUTHOR_FQID}/commented
            # GET /api/authors/{AUTHOR_ID}/commented
            author = _get_author_by_id_or_fqid(author_fqid or author_id)
            all_comments = Comment.objects.filter(author=author).order_by('-created_at')
            
            # Filter comments based on post visibility
            # Local authenticated users can see comments on all posts (including FRIENDS)
            # Remote users can only see comments on PUBLIC and PUBLIC_UNLISTED posts
            filtered_comments = []
            for comment in all_comments:
                if can_access_post(comment.post, request):
                    filtered_comments.append(comment)
            
            # Paginate the filtered comments
            page_num = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('size', 10))
            paginator = Paginator(filtered_comments, page_size)
            page_obj = paginator.get_page(page_num)
            
            items = [build_comment_dict(comment, request) for comment in page_obj]
            
            response_data = {
                "type": "comments",
                "page": page_num,
                "size": page_size,
                "comments": items
            }
            return JsonResponse(response_data)
        
        else:
            # GET /api/authors/{AUTHOR_ID}/entries/{ENTRY_ID}/comments
            # GET /api/entries/{ENTRY_FQID}/comments
            post = _get_post_by_id_or_fqid(entry_id=entry_id, entry_fqid=entry_fqid, author_id=author_id)
            
            # Check if user can access this post
            if not can_access_post(post, request):
                return HttpResponse("Forbidden", status=403)
            
            # Get page and size parameters
            page_num = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('size', 5))
            
            # Get comments
            comments = Comment.objects.filter(post=post).order_by('created_at')
            
            # Paginate
            paginator = Paginator(comments, page_size)
            page_obj = paginator.get_page(page_num)
            
            # Build items list
            items = [build_comment_dict(comment, request) for comment in page_obj]
            
            # Build post URL
            if entry_fqid:
                post_url = entry_fqid
            else:
                post_url = f"{request.scheme}://{request.get_host()}/api/authors/{author_id}/entries/{entry_id}"
            
            response_data = {
                "type": "comments",
                "page": page_num,
                "size": page_size,
                "post": post_url,
                "id": f"{post_url}/comments",
                "comments": items
            }
            
            return JsonResponse(response_data)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class LikesAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/likes
    GET /api/entries/{ENTRY_FQID}/likes
    Get likes on a post
    """
    
    def get(self, request, author_id=None, entry_id=None, entry_fqid=None):
        """Get list of likes on a post - handles both UUID and FQID"""
        post = _get_post_by_id_or_fqid(entry_id=entry_id, entry_fqid=entry_fqid, author_id=author_id)
        
        # Check if user can access this post
        if not can_access_post(post, request):
            return HttpResponse("Forbidden", status=403)
        
        # Get all likes
        likes = Like.objects.filter(post=post).order_by('-created_at')
        
        # Build items list
        items = [build_like_dict(like, request) for like in likes]
        
        response_data = {
            "type": "likes",
            "items": items
        }
        
        return JsonResponse(response_data)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class CommentLikesAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/comments/{COMMENT_FQID}/likes
    Get likes on a specific comment
    """
    
    def get(self, request, author_id=None, entry_id=None, comment_id=None, comment_fqid=None):
        """Get list of likes on a comment - handles both UUID and FQID"""
        # Get the comment
        comment = _get_comment_by_id_or_fqid(comment_id=comment_id, comment_fqid=comment_fqid)
        
        # Check if user can access the post this comment is on
        if not can_access_post(comment.post, request):
            return HttpResponse("Forbidden", status=403)
        
        # Get all comment likes
        comment_likes = CommentLike.objects.filter(comment=comment).order_by('-created_at')
        
        # Build items list
        items = [build_comment_like_dict(comment_like, request) for comment_like in comment_likes]
        
        response_data = {
            "type": "likes",
            "items": items
        }
        
        return JsonResponse(response_data)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class LikedAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/liked
    GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}
    GET /api/authors/{AUTHOR_FQID}/liked
    GET /api/liked/{LIKE_FQID}
    Get list of things the author has liked or a single like
    """
    
    def get(self, request, author_id=None, author_fqid=None, like_id=None, like_fqid=None):
        """Get list of posts liked by author or single like - handles UUID and FQID"""
        
        if like_fqid or like_id:
            # GET /api/liked/{LIKE_FQID}
            # GET /api/authors/{AUTHOR_SERIAL}/liked/{LIKE_SERIAL}
            like = _get_like_by_id_or_fqid(like_id=like_id, like_fqid=like_fqid)
            
            # Check if user can access the post that was liked
            if not can_access_post(like.post, request):
                return HttpResponse("Forbidden", status=403)
            
            return JsonResponse(build_like_dict(like, request))
        
        else:
            # GET /api/authors/{AUTHOR_ID or FQID}/liked
            identifier = author_fqid or author_id
            author = _get_author_by_id_or_fqid(identifier)
            
            # Get all post likes by this author
            post_likes = Like.objects.filter(author=author).order_by('-created_at')
            
            # Get all comment likes by this author
            comment_likes = CommentLike.objects.filter(author=author).order_by('-created_at')
            
            # Build items list - combine both types of likes, filtering by post visibility
            items = []
            
            # Add post likes (only for posts the requester can access)
            for like in post_likes:
                if can_access_post(like.post, request):
                    items.append(build_like_dict(like, request))
            
            # Add comment likes (only for comments on posts the requester can access)
            for comment_like in comment_likes:
                if can_access_post(comment_like.comment.post, request):
                    items.append(build_comment_like_dict(comment_like, request))
            
            # Sort by published timestamp (most recent first)
            items.sort(key=lambda x: x.get('published', ''), reverse=True)
            
            response_data = {
                "type": "liked",
                "items": items
            }
            
            return JsonResponse(response_data)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class ImageEntryAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/entries/{ENTRY_SERIAL}/image
    GET /api/entries/{ENTRY_FQID}/image
    Get the image from an image post as binary data
    """
    
    def get(self, request, author_id=None, entry_id=None, entry_fqid=None):
        """Get image from post - handles both UUID and FQID"""
        post = _get_post_by_id_or_fqid(entry_id=entry_id, entry_fqid=entry_fqid, author_id=author_id)
        
        # Check if user can access this post
        if not can_access_post(post, request):
            return HttpResponse("Forbidden", status=403)
        
        if not post.image:
            return HttpResponse("No image found", status=404)
        
        # Return the image file
        with open(post.image.path, 'rb') as f:
            image_data = f.read()
        
        # Determine content type
        content_type = 'image/jpeg'
        if post.image.name.endswith('.png'):
            content_type = 'image/png'
        elif post.image.name.endswith('.gif'):
            content_type = 'image/gif'
        
        return HttpResponse(image_data, content_type=content_type)
