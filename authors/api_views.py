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
from .models import Author, Post, Follow, FollowRequest, Like, Comment, CommentLike, RemoteNode
from .authentication import http_basic_auth_or_session, http_basic_auth_required
from .inbox_handlers import (
    handle_post as ih_handle_post,
    handle_comment as ih_handle_comment,
    handle_like as ih_handle_like,
    handle_follow_request as ih_handle_follow_request,
    handle_unfollow as ih_handle_unfollow,
    reopen_follow_request as reopen_follow_request,
    get_or_create_author
)
from .utils.federation import (
    notify_remote_new_post,
    notify_remote_edit_post,
    notify_remote_delete_post,
    send_unfollow_to_remote_author,
    notify_remote_author_update,
    send_comment_like_to_post_owner,
)
import requests
import urllib.parse


def json_response(data, status=200):
    """Return a JsonResponse with pretty-printed JSON for readability.
    Uses 2-space indentation so responses are not smashed together.
    """
    return JsonResponse(data, status=status, json_dumps_params={"indent": 2})


# Wrap the imported JsonResponse so existing calls remain valid but default to pretty JSON
_original_JsonResponse = JsonResponse
def JsonResponse(*args, **kwargs):
    # Ensure pretty printing unless explicitly overridden
    if 'json_dumps_params' not in kwargs:
        kwargs['json_dumps_params'] = {'indent': 2}
    return _original_JsonResponse(*args, **kwargs)
# ==================== Helper Functions for FQID Support ====================


def _get_author_by_id_or_fqid(author_id=None, author_fqid=None):
    """Get author by UUID (author_id) or FQID (author_fqid / full URL)."""

    if author_fqid:
        fqid_norm = author_fqid.rstrip('/') if isinstance(author_fqid, str) else author_fqid
        fqid_with_slash = fqid_norm + '/'

        qs = Author.objects.filter(Q(url=fqid_norm) | Q(url=fqid_with_slash))

        if not qs.exists():
            raise Http404("Author not found")

        # If multiple somehow exist, pick a stable one instead of exploding
        return qs.order_by("id").first()

    if author_id:
        try:
            return Author.objects.get(id=author_id)
        except (Author.DoesNotExist, ValueError):
            raise Http404("Author not found")

    raise Http404("Author identifier required")


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
            return Post.objects.get(Q(origin=entry_fqid_normalized) | Q(origin=entry_fqid_with_slash))
        except Post.DoesNotExist:
            try:
                return Post.objects.get(Q(source=entry_fqid_normalized) | Q(source=entry_fqid_with_slash))
            except Post.DoesNotExist:
                raise Http404("Post not found - FQID does not match any post in database")
    
    elif entry_id:
        # UUID/Serial lookup - match by id field
        if author_id:
            return get_object_or_404(Post, id=entry_id, author_id=author_id)
        else:
            return get_object_or_404(Post, id=entry_id)
    
    else:
        raise Http404("No entry identifier provided")


def _get_comment_by_fqid(comment_fqid, author_id=None, entry_id=None):
    """
    Get comment by FQID (full URL)
    """
    if not comment_fqid:
        raise Http404("Comment identifier required")

    # Normalize and try origin lookup first
    fqid_norm = comment_fqid.rstrip('/') if isinstance(comment_fqid, str) else comment_fqid
    fqid_with_slash = fqid_norm + '/'
    try:
        comment = Comment.objects.get(Q(origin=fqid_norm) | Q(origin=fqid_with_slash))
    except Comment.DoesNotExist:
        # No UUID fallback: caller asked for FQID, so fail if origin doesn't match.
        raise Http404("Comment not found")

    # Validate parent relationships
    if entry_id is not None:
        # author refers to owner of  post. Enforce both entry and post author.
        if str(comment.post.id) != str(entry_id):
            raise Http404("Comment not found for this entry")
        if author_id is not None and str(comment.post.author.id) != str(author_id):
            raise Http404("Comment not found for this author")
    else:
        #"commented" endpoint - author_id refers to commenter.
        if author_id is not None and str(comment.author.id) != str(author_id):
            raise Http404("Comment not found for this author")

    return comment


def _get_like_by_fqid(like_fqid, author_id=None, entry_id=None, comment_id=None):
    """Get like by FQID (full URL).

    Helper to resolve the FQID against both post-likes
    (Like model) and comment-likes (CommentLike model). Validates
    parent relationships (author/entry/comment) if identifiers are
    provided in the URL.
    """
    if not like_fqid:
        raise Http404("Like identifier required")

    fqid_norm = like_fqid.rstrip('/') if isinstance(like_fqid, str) else like_fqid
    fqid_with_slash = fqid_norm + '/'

    # Try resolving as a post-like first
    try:
        like = Like.objects.get(Q(origin=fqid_norm) | Q(origin=fqid_with_slash))
        # If the caller asked to scope to a comment, a post-like does not match
        if comment_id is not None:
            raise Http404("Like not found for this comment")
        if entry_id is not None and str(like.post.id) != str(entry_id):
            raise Http404("Like not found for this entry")
        # Currently, author is always author of like (not post author)
        if author_id is not None and str(like.author.id) != str(author_id):
            raise Http404("Like not found for this author")
        return like
    except Like.DoesNotExist:
        # Not a post-like; try comment-like
        try:
            clike = CommentLike.objects.get(Q(origin=fqid_norm) | Q(origin=fqid_with_slash))
            if comment_id is not None and str(clike.comment.id) != str(comment_id):
                raise Http404("Like not found for this comment")
            if entry_id is not None and str(clike.comment.post.id) != str(entry_id):
                raise Http404("Like not found for this entry")
            # Currently, author is always author of like (not comment author)
            if author_id is not None and str(clike.author.id) != str(author_id):
                raise Http404("Like not found for this author")
            return clike
        except CommentLike.DoesNotExist:
            raise Http404("Like not found")


def _get_comment_by_id_or_fqid(comment_id=None, comment_fqid=None, author_id=None, entry_id=None):
    """Get comment by UUID or FQID (full URL)"""
    if comment_fqid:
        return _get_comment_by_fqid(comment_fqid, author_id=author_id, entry_id=entry_id)
    elif comment_id:
        comment = get_object_or_404(Comment, id=comment_id)
        # validation for UUID lookups
        if entry_id is not None:
            # When entry_id is present, author_id refers to the post owner
            if str(comment.post.id) != str(entry_id):
                raise Http404("Comment not found for this entry")
            if author_id is not None and str(comment.post.author.id) != str(author_id):
                raise Http404("Comment not found for this author")
        else:
            # No entry_id: the endpoint is for comments by an author (commenter)
            if author_id is not None and str(comment.author.id) != str(author_id):
                raise Http404("Comment not found for this author")
        return comment
    else:
        raise Http404("Comment identifier required")


def _get_like_by_id_or_fqid(like_id=None, like_fqid=None, author_id=None, entry_id=None, comment_id=None):
    """Get like by UUID or FQID (full URL)"""
    if like_fqid:
        return _get_like_by_fqid(like_fqid, author_id=author_id, entry_id=entry_id, comment_id=comment_id)
    elif like_id:
        # Try resolving as a post-like first
        try:
            like = Like.objects.get(id=like_id)
            if comment_id is not None:
                raise Http404("Like not found for this comment")
            if entry_id is not None and str(like.post.id) != str(entry_id):
                raise Http404("Like not found for this entry")
            # The author in the URL should match the actor who created the like
            if author_id is not None and str(like.author.id) != str(author_id):
                raise Http404("Like not found for this author")
            return like
        except Like.DoesNotExist:
            # Try comment-like
            try:
                clike = CommentLike.objects.get(id=like_id)
                if comment_id is not None and str(clike.comment.id) != str(comment_id):
                    raise Http404("Like not found for this comment")
                if entry_id is not None and str(clike.comment.post.id) != str(entry_id):
                    raise Http404("Like not found for this entry")
                # For comment-likes, ensure the liker (clike.author) matches
                if author_id is not None and str(clike.author.id) != str(author_id):
                    raise Http404("Like not found for this author")
                return clike
            except CommentLike.DoesNotExist:
                raise Http404("Like not found")
    else:
        raise Http404("Like identifier required")
    

def resolve_target_host(target, request):
    """Resolve a target host (scheme://netloc) from an Author-like object.

    Returns: normalized `scheme://netloc` string (no trailing slash).
    """
    raw_host = None
    if getattr(target, 'host', None):
        raw_host = target.host
    elif getattr(target, 'url', None):
        raw_host = target.url

    if not raw_host:
        return None

    # Ensure the string has a scheme so parsing behaves predictably
    if not raw_host.startswith('http://') and not raw_host.startswith('https://'):
        raw_host = f"{request.scheme}://{raw_host.lstrip('/')}"

    parsed = urllib.parse.urlparse(raw_host)
    if not parsed.scheme or not parsed.netloc:
        return None

    return f"{parsed.scheme}://{parsed.netloc}".rstrip('/')


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
    # Always deny access if the post is marked as deleted
    if post.deleted or post.visibility == "DELETED":
        return False
        
    # PUBLIC and PUBLIC_UNLISTED are always accessible
    if post.visibility in ['PUBLIC', 'PUBLIC_UNLISTED']:
        return True

    # If the request has been authenticated via HTTP Basic Auth (node-to-node),
    # treat it as a trusted remote and allow access to posts regardless of the
    # visibility flag. This enables remote nodes that present valid basic-auth
    # credentials to read friends-only content when authorized by credentials.
    if getattr(request, 'is_basic_auth', False):
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
    
    # Build profileImage URL using API endpoint /api/authors/{author_id}/image
    profile_image_url = None
    if author.profileImage:
        # Use the proper API endpoint for profile images
        image_path = reverse('authors:author_image_api', args=[author.id])
        profile_image_url = request.build_absolute_uri(image_path)
    
    return {
        "type": "author",
        "id": author.url or f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/",
        "host": author.host or f"{request.scheme}://{request.get_host()}",
        "displayName": author.displayName,
        "url": author.url or f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/",
        "github": author.github,
        "description": author.description,
        "profileImage": profile_image_url,
        "web": f"{request.scheme}://{request.get_host()}{web_url}",
    }


def build_post_dict(post, request):
    """Helper function to build post/entry JSON object"""
    author = post.author
    entry_url = f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}"
    
    data = {
        "type": "entry",
        # Use canonical origin as the id when available
        "id": post.origin or entry_url,
        "author": build_author_dict(author, request),
        "title": post.title,
        "source": post.source or entry_url,
        "origin": post.origin or entry_url,
        "description": post.description if post.description else "", 
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
            "entry": entry_url,
            "id": f"{entry_url}/comments",
            "comments": []  # Can be populated if needed
        }
    }
    
    # Add image if present - use proper API endpoint /api/authors/{author_id}/entries/{entry_id}/image
    if post.image:
        image_path = reverse('authors:image_entry_api', args=[author.id, post.id])
        data["image"] = request.build_absolute_uri(image_path)

    # Add likes metadata for this entry
    likes_url = f"{entry_url}/likes"
    # Derive a human web URL by removing '/api' if present
    web_url = entry_url.replace('/api', '')
    data["likes"] = likes_url
    data["likesSrc"] = {
        "type": "likes",
        "page": 1,
        "size": 5,
        "entry": entry_url,
        "id": likes_url,
        "web": web_url,
        "src": []  # can be populated with like objects
    }
    
    return data


def build_comment_dict(comment, request):
    """Helper function to build comment JSON object"""
    post = comment.post
    author = post.author
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{comment.author.id}/commented/{comment.id}"

    return {
        "type": "comment",
        # Use canonical origin as the id when available
        "id": comment.origin or comment_url,
        "author": build_author_dict(comment.author, request),
        "comment": comment.content,
        "contentType": "text/plain",
        "published": comment.created_at.isoformat(),
        # Add likes metadata for this comment
        "likes": f"{request.scheme}://{request.get_host()}/api/authors/{comment.post.author.id}/entries/{comment.post.id}/comments/{comment.id}/likes",
        "likesSrc": {
            "type": "likes",
            "page": 1,
            "size": 5,
            "entry": f"{request.scheme}://{request.get_host()}/api/authors/{comment.post.author.id}/entries/{comment.post.id}",
            "id": f"{request.scheme}://{request.get_host()}/api/authors/{comment.post.author.id}/entries/{comment.post.id}/comments/{comment.id}/likes",
            "web": f"{request.scheme}://{request.get_host()}/authors/{comment.post.author.id}/entries/{comment.post.id}/",
            "src": []
        }
    }


def build_like_dict(like, request):
    """Helper function to build like JSON object"""
    post = like.post
    author = post.author
    like_id_url = f"{request.scheme}://{request.get_host()}/api/authors/{like.author.id}/liked/{like.id}"

    return {
        "type": "like",
        # Use canonical origin as the id when available
        "id": like.origin or like_id_url,
        "author": build_author_dict(like.author, request),
        "object": like.post.origin or f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/entries/{post.id}",
        "published": like.created_at.isoformat(),
    }


def build_comment_like_dict(comment_like, request):
    """Helper function to build comment like JSON object"""
    comment = comment_like.comment
    # Use the correct comment URL format: /api/authors/{comment.author.id}/commented/{comment.id}
    comment_url = f"{request.scheme}://{request.get_host()}/api/authors/{comment.author.id}/commented/{comment.id}"
    like_id_url = f"{request.scheme}://{request.get_host()}/api/authors/{comment_like.author.id}/liked/{comment_like.id}"

    return {
        "type": "like",
        # Use canonical origin as the id when available
        "id": comment_like.origin or like_id_url,
        "author": build_author_dict(comment_like.author, request),
        "object": comment.origin or comment_url,
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

            # DEBUG:
            print("INBOX PAYLOAD:", data.get("id"), "image:", data.get("image"))
            
            object_type = data.get('type', '').lower()

            if object_type == 'follow':
                return self.handle_follow_request(recipient, data, request)
            elif object_type == 'unfollow':
                return self.handle_unfollow(recipient, data, request)
            elif object_type == 'post' or object_type == 'entry':
                return self.handle_post(recipient, data, request)
            elif object_type == 'like':
                return self.handle_like(recipient, data, request)
            elif object_type == 'comment':
                return self.handle_comment(recipient, data, request)
            
            # Might cause issues when connecting to other groups nodes
            elif object_type == 'author':
                # Author profile update (e.g., new displayName/profileImage)
                # We don't really care which inbox it came through; we just
                # refresh/create our stub for that remote author.
                remote_author = get_or_create_author(data)
                if remote_author is None:
                    return json_response(
                        {'error': 'Author payload missing id/url'},
                        status=400
                    )
                return json_response(
                    {'message': 'Author updated', 'id': remote_author.url},
                    status=200
                )
            
            else:
                return json_response({'error': f'Unknown object type: {object_type}'}, status=400)
                
        except json.JSONDecodeError:
            return json_response({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)
    
    def handle_follow_request(self, recipient, data, request):
        """Delegate follow handling to inbox_handlers_updated.handle_follow_request"""
        return ih_handle_follow_request(self, recipient, data, request)
    
    def handle_unfollow(self, recipient, data, request):
        """Delegate unfollow handling to inbox_handlers.handle_unfollow"""
        return ih_handle_unfollow(self, recipient, data, request)

    def handle_post(self, recipient, data, request):
        """Delegate post handling to inbox_handlers_updated.handle_post"""
        return ih_handle_post(self, recipient, data, request)
    
    def handle_like(self, recipient, data, request):
        """Delegate like handling to inbox_handlers_updated.handle_like"""
        return ih_handle_like(self, recipient, data, request)
    
    def handle_comment(self, recipient, data, request):
        """Delegate comment handling to inbox_handlers_updated.handle_comment"""
        return ih_handle_comment(self, recipient, data, request)


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
        
        return json_response(response_data)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class FollowingAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/following
    Returns list of authors that AUTHOR_SERIAL is following (local author only)
    """

    def get(self, request, author_id):
        # Only the local author may call this endpoint
        author = get_object_or_404(Author, id=author_id)
        if not request.user.is_authenticated or str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: only the author may view their following list', status=403)

        following_rels = Follow.objects.filter(follower=author)
        items = [build_author_dict(rel.following, request) for rel in following_rels]

        return json_response({
            'type': 'following',
            'items': items
        })


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(http_basic_auth_or_session, name='dispatch')
class SingleFollowingAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/following/{FOREIGN_AUTHOR_FQID}
    PUT /api/authors/{AUTHOR_SERIAL}/following/{FOREIGN_AUTHOR_FQID} -> generate follow request
    DELETE /api/authors/{AUTHOR_SERIAL}/following/{FOREIGN_AUTHOR_FQID} -> unfollow

    TODO: Add user/pass for HTTP Basic Auth to remote follow requests
    """

    def get(self, request, author_id, following_fqid):
        # Only the local author may call this endpoint
        author = get_object_or_404(Author, id=author_id)
        if not request.user.is_authenticated or str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: only the author may check following relationships', status=403)

        # Resolve target author by FQID (strict)
        try:
            target = _get_author_by_id_or_fqid(author_fqid=following_fqid)
        except Http404:
            return HttpResponse('Not Found', status=404)

        is_following = Follow.objects.filter(follower=author, following=target).exists()
        if is_following:
            return json_response(build_author_dict(target, request))
        else:
            return HttpResponse('Not Found', status=404)

    @method_decorator(csrf_exempt)
    def put(self, request, author_id, following_fqid):
        """Generate a follow request from AUTHOR_SERIAL -> FOREIGN_AUTHOR_FQID"""
        author = get_object_or_404(Author, id=author_id)
        if not request.user.is_authenticated or str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: only the author may create follow requests', status=403)

        # Resolve or create the target author using shared normalizer
        # This prevents duplicates by canonicalizing the FQID (e.g. /authors/ -> /api/authors/)
        target = get_or_create_author({"id": following_fqid})
        if target is None:
            return HttpResponse("Bad Request: invalid following_fqid", status=400)


        # If the target's host differs from our host, send follow request to the remote inbox
        local_base = f"{request.scheme}://{request.get_host()}".rstrip('/')

        # Resolve target host using helper
        target_host = resolve_target_host(target, request)
        
        if target_host and target_host != local_base:
            # Look up RemoteNode configuration for this host
            # RemoteNode.base_url is stored with a trailing slash (see RemoteNodeForm.clean_base_url)
            remote_node = None
            for node in RemoteNode.objects.filter(enabled=True):
                node_base = node.base_url.rstrip('/')
                if node_base == target_host:
                    remote_node = node
                    break

            if remote_node is None:
                return json_response(
                    {'error': f'No RemoteNode configured for host {target_host}'},
                    status=502
                )

            payload = {
                'type': 'follow',
                'actor': build_author_dict(author, request),
                'object': build_author_dict(target, request),
            }

            # Build inbox URL from target.url
            target_fqid = target.url
            parsed = urllib.parse.urlparse(target_fqid)
            base = f"{parsed.scheme}://{parsed.netloc}"
            path_parts = parsed.path.rstrip('/').split('/')
            remote_author_id = path_parts[-1] if path_parts else ''
            inbox_url = f"{base}/api/authors/{remote_author_id}/inbox/"

            # Use HTTP Basic Auth with the configured RemoteNode credentials
            auth = (remote_node.username, remote_node.password) if remote_node.username and remote_node.password else None

            try:
                resp = requests.post(inbox_url, json=payload, auth=auth, timeout=10)
            except Exception as e:
                return json_response(
                    {'error': f'Failed to send follow request to remote inbox: {str(e)}'},
                    status=502
                )

            # create Follow if remote node accepted the request (prevents invalid fqids)
            if resp.status_code in (200, 201, 202, 204):
                # Create the Follow relationship immediately (idempotent).
                follow, created = Follow.objects.get_or_create(follower=author, following=target)
                return json_response(
                    {'message': 'Following created' if created else 'Already following'},
                    status=201 if created else 200
                )
            else:
                return json_response(
                    {'error': f'Remote inbox responded with {resp.status_code}: {resp.text}'},
                    status=resp.status_code
                )

        # Otherwise target is local to our node: create a FollowRequest locally
        fr, created = FollowRequest.objects.get_or_create(sender=author, receiver=target, defaults={'status': 'PENDING'})
        if not created and reopen_follow_request(fr):
            return json_response({'message': 'Follow request re-sent'}, status=200)
        return json_response({'message': 'Follow request created' if created else 'Follow request already exists'}, status=201 if created else 200)


    def delete(self, request, author_id, following_fqid):
        """Unfollow FOREIGN_AUTHOR_FQID - only author may call"""
        author = get_object_or_404(Author, id=author_id)
        if not request.user.is_authenticated or str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: only the author may unfollow', status=403)

        try:
            target = _get_author_by_id_or_fqid(author_fqid=following_fqid)
        except Http404:
            return HttpResponse('Not Found', status=404)

        if Follow.objects.filter(follower=author, following=target).exists():
            # Remove local relationship
            Follow.objects.filter(follower=author, following=target).delete()

            # If target is remote, notify their node
            try:
                if getattr(target, "is_remote", None) and target.is_remote():
                    send_unfollow_to_remote_author(author, target)
            except Exception:
                pass  # don't fail the API if federation call dies

            return json_response({'message': 'Unfollowed'}, status=204)

        return HttpResponse('Not Found', status=404)



@method_decorator(http_basic_auth_or_session, name='dispatch')
class SingleFollowerAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/followers/{FOREIGN_AUTHOR_ID}
    Check if FOREIGN_AUTHOR is a follower of AUTHOR
    Returns 404 if not a follower, 200 if they are
    """
    
    def get(self, request, author_id, follower_fqid):
        """Check if follower_fqid follows author_id.
        If the follower Author cannot be resolved by FQID, return 404. If resolved but
        not a follower, return 404. Otherwise return the follower author JSON.
        """
        author = get_object_or_404(Author, id=author_id)

        # Resolve follower by FQID only (strict match against Author.url)
        try:
            follower = _get_author_by_id_or_fqid(author_fqid=follower_fqid)
        except Http404:
            return HttpResponse("Not Found", status=404)

        # Check if follow relationship exists
        is_follower = Follow.objects.filter(follower=follower, following=author).exists()

        if is_follower:
            return json_response(build_author_dict(follower, request))
        else:
            return HttpResponse("Not Found", status=404)
    
    def delete(self, request, author_id, follower_fqid):
        """Remove a follower - only AUTHOR_SERIAL can remove their followers"""
        author = get_object_or_404(Author, id=author_id)
        # Authorization: Only the author being followed can remove/deny followers
        if str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: Only the author can remove or deny followers', status=403)

        # Resolve follower by FQID only
        try:
            follower = _get_author_by_id_or_fqid(author_fqid=follower_fqid)
        except Http404:
            return HttpResponse("Not Found", status=404)

        # If there's a pending follow request, treat DELETE as 'deny' and remove it
        fr_qs = FollowRequest.objects.filter(sender=follower, receiver=author, status='PENDING')
        if fr_qs.exists():
            fr_qs.delete()
            return json_response({'message': 'Follow request denied'}, status=204)

        # Otherwise, if follower relationship exists, remove it (revoke)
        if Follow.objects.filter(follower=follower, following=author).exists():
            Follow.objects.filter(follower=follower, following=author).delete()
            return json_response({'message': 'Follower removed'}, status=204)

        # Nothing to deny or remove
        return HttpResponse("Not Found", status=404)
    
    @method_decorator(csrf_exempt)
    def put(self, request, author_id, follower_fqid):
        """Accept a follow request: only the local AUTHOR_SERIAL may accept.

        If a pending follow request from the foreign author does not exist, return 404. Otherwise
        mark the request approved and create the Follow relationship.
        """
        author = get_object_or_404(Author, id=author_id)

        # Authorization: only the receiver (author) can accept follow requests
        if str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: Only the author can accept follow requests', status=403)

        # Resolve follower by FQID only
        try:
            follower = _get_author_by_id_or_fqid(author_fqid=follower_fqid)
        except Http404:
            return HttpResponse("Not Found", status=404)

        # Look for a pending follow request from this follower to this author
        try:
            fr = FollowRequest.objects.get(sender=follower, receiver=author, status='PENDING')
        except FollowRequest.DoesNotExist:
            return HttpResponse("Not Found", status=404)

        # Approve the follow request and create the follower relationship
        fr.status = 'APPROVED'
        fr.save()

        Follow.objects.get_or_create(follower=follower, following=author)

        return json_response({'message': 'Follow request approved'}, status=200)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class FollowRequestsAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/follow_requests
    Returns a list of pending follow requests for the specified local author.

    Only the local author (session-authenticated) may call this endpoint.
    """

    def get(self, request, author_id):
        # Only the local author may call this endpoint
        author = get_object_or_404(Author, id=author_id)
        if not request.user.is_authenticated or str(request.user.id) != str(author_id):
            return HttpResponse('Forbidden: only the author may view their follow requests', status=403)

        # Find pending follow requests targeting this author
        fr_qs = FollowRequest.objects.filter(receiver=author, status='PENDING').order_by('-created_at')

        items = []
        for fr in fr_qs:
            sender = fr.sender
            # Build follow-request object according to the project's follow request shape
            fr_obj = {
                'type': 'follow',
                'id': f"{request.scheme}://{request.get_host()}/api/authors/{author.id}/follow_requests/{fr.id}",
                'actor': build_author_dict(sender, request),
                'object': build_author_dict(author, request),
                'status': fr.status,
            }
            try:
                fr_obj['summary'] = f"{sender.displayName} wants to follow {author.displayName}"
            except Exception:
                pass

            items.append(fr_obj)

        return json_response({'type': 'follow_requests', 'items': items})


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
        # If this request was authenticated via HTTP Basic Auth (node-to-node),
        # treat it as trusted and allow access to all entries for this author.
        if getattr(request, 'is_basic_auth', False):
            posts = Post.objects.filter(author=author, deleted=False).order_by('-published')
        elif request.user.is_authenticated and request.user.id == author.id:
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
        
        return json_response(response_data)
    
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

            # Notify remote followers about the new post
            notify_remote_new_post(post)

            return json_response(build_post_dict(post, request), status=201)
            
        except json.JSONDecodeError:
            return json_response({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return json_response({'error': str(e)}, status=500)


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
        # If  request was authenticated via HTTP Basic Auth (node-to-node),
        # allow access regardless of visibility.
        if getattr(request, 'is_basic_auth', False):
            return json_response(build_post_dict(post, request))

        # Check visibility permissions for non-basic-auth requests
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
        
        return json_response(build_post_dict(post, request))
    
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

            # Notify remote followers about the edited post
            notify_remote_edit_post(post)

            return json_response(build_post_dict(post, request))
            
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
        post.visibility = 'DELETED'
        post.save()

        # Notify remote followers about the deleted post (User Story 2)
        notify_remote_delete_post(post)

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
            comment = _get_comment_by_id_or_fqid(comment_id=comment_id, comment_fqid=comment_fqid, author_id=self.kwargs.get('author_id'), entry_id=self.kwargs.get('entry_id'))
            
            # Check if user can access the post this comment is on
            if not can_access_post(comment.post, request):
                return HttpResponse("Forbidden", status=403)
            
            return JsonResponse(build_comment_dict(comment, request))
        
        elif author_fqid or (author_id and not entry_id):
            # GET /api/authors/{AUTHOR_FQID}/commented
            # GET /api/authors/{AUTHOR_ID}/commented
            author = _get_author_by_id_or_fqid(author_id=author_id, author_fqid=author_fqid)
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
                "entry": post_url,
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
        
        # Paginate likes
        page_num = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('size', 10))

        likes_qs = Like.objects.filter(post=post).order_by('-created_at')
        paginator = Paginator(likes_qs, page_size)
        page_obj = paginator.get_page(page_num)

        # Build src list
        src = [build_like_dict(like, request) for like in page_obj]

        # Determine post URL (could be FQID)
        if entry_fqid:
            post_url = entry_fqid
        else:
            post_url = f"{request.scheme}://{request.get_host()}/api/authors/{author_id}/entries/{entry_id}"

        web_url = post_url.replace('/api', '')

        response_data = {
            "type": "likes",
            "id": f"{post_url}/likes",
            "web": web_url,
            "page": page_num,
            "size": page_size,
            "count": paginator.count,
            "items": src
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
        comment = _get_comment_by_id_or_fqid(comment_id=comment_id, comment_fqid=comment_fqid, author_id=author_id, entry_id=entry_id)
        
        # Check if user can access the post this comment is on
        if not can_access_post(comment.post, request):
            return HttpResponse("Forbidden", status=403)
        
        # Paginate comment likes
        page_num = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('size', 10))

        comment_likes_qs = CommentLike.objects.filter(comment=comment).order_by('-created_at')
        paginator = Paginator(comment_likes_qs, page_size)
        page_obj = paginator.get_page(page_num)

        src = [build_comment_like_dict(cl, request) for cl in page_obj]

        post_url = f"{request.scheme}://{request.get_host()}/api/authors/{comment.post.author.id}/entries/{comment.post.id}"
        web_url = post_url.replace('/api', '')

        response_data = {
            "type": "likes",
            "id": f"{post_url}/comments/{comment.id}/likes",
            "web": web_url,
            "page": page_num,
            "size": page_size,
            "count": paginator.count,
            "items": src
        }

        return JsonResponse(response_data)
    
    @method_decorator(csrf_exempt)
    def post(self, request, author_id=None, entry_id=None, comment_id=None, comment_fqid=None):
        """
        Create a like on a specific comment (local action).
        Also sends the ActivityPub 'Like' to the remote owner(s)
        of the comment / post.
        """
        # 1) Auth check – only logged-in users can like
        if not request.user.is_authenticated:
            return HttpResponse("Forbidden", status=403)

        liker = request.user

        # 2) Resolve the comment the same way as in GET
        comment = _get_comment_by_id_or_fqid(
            comment_id=comment_id,
            comment_fqid=comment_fqid,
            author_id=author_id,
            entry_id=entry_id,
        )

        # 3) Avoid duplicate likes from the same user on the same comment
        comment_like, created = CommentLike.objects.get_or_create(
            author=liker,
            comment=comment,
        )

        # 4) On first creation, send to remote node(s)
        # CommentLike.save() will auto-fill .origin for local likes
        if created:
            send_comment_like_to_post_owner(comment_like)

        # 5) Return JSON for the like (same shape as your GET)
        return JsonResponse(
            build_comment_like_dict(comment_like, request),
            status=201 if created else 200,
        )


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
            like_obj = _get_like_by_id_or_fqid(like_id=like_id, like_fqid=like_fqid, author_id=author_id)

            # Determine the post the like is associated with (post-like vs comment-like)
            if hasattr(like_obj, 'post'):
                post = like_obj.post
            elif hasattr(like_obj, 'comment'):
                post = like_obj.comment.post
            else:
                return HttpResponse("Not Found", status=404)

            # Check if user can access the post that was liked
            if not can_access_post(post, request):
                return HttpResponse("Forbidden", status=403)

            # Return appropriate JSON depending on like type
            if isinstance(like_obj, CommentLike) or hasattr(like_obj, 'comment'):
                return JsonResponse(build_comment_like_dict(like_obj, request))
            else:
                return JsonResponse(build_like_dict(like_obj, request))
        
        else:
            # GET /api/authors/{AUTHOR_ID or FQID}/liked
            # Determine author by UUID or FQID (pass both so helper can choose)
            author = _get_author_by_id_or_fqid(author_id=author_id, author_fqid=author_fqid)
            
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

            # Paginate combined items
            page_num = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('size', 10))
            paginator = Paginator(items, page_size)
            page_obj = paginator.get_page(page_num)

            author_id_val = author.id
            response_data = {
                "type": "liked",
                "id": f"{request.scheme}://{request.get_host()}/api/authors/{author_id_val}/liked",
                "web": build_author_dict(author, request).get('web'),
                "page": page_num,
                "size": page_size,
                "count": paginator.count,
                "items": list(page_obj)
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
        # If basic-authenticated, allow access to the image regardless of
        # post visibility for remote nodes
        if not getattr(request, 'is_basic_auth', False):
            # For non-basic-auth requests, use the normal visibility rules
            if not can_access_post(post, request):
                return HttpResponse("Forbidden", status=403)
        
        if not post.image:
            return HttpResponse("No image found", status=404)
        
        # Get the image data from the database
        image = post.image
        image_data = bytes(image.data)
        
        # Use the content_type from the Image model
        content_type = image.content_type or 'image/jpeg'
        
        return HttpResponse(image_data, content_type=content_type)


class AuthorImageAPIView(View):
    """
    GET /api/authors/{AUTHOR_SERIAL}/image
    Get the profile image from an author as binary data
    """
    
    def get(self, request, author_id=None, author_fqid=None):
        """Get profile image from author - handles both UUID and FQID"""
        author = _get_author_by_id_or_fqid(author_id=author_id, author_fqid=author_fqid)
        
        if not author.profileImage:
            return HttpResponse("No profile image found", status=404)
        
        # Get the image data from the database
        image = author.profileImage
        image_data = bytes(image.data)
        
        # Use the content_type from the Image model
        content_type = image.content_type or 'image/jpeg'
        
        return HttpResponse(image_data, content_type=content_type)


@method_decorator(http_basic_auth_or_session, name='dispatch')
class AuthorAPIView(View):
    def get(self, request, author_id=None, author_fqid=None):
        """Get author by UUID or FQID"""
        identifier = author_fqid or author_id
        
        # Try UUID first
        try:
            author = Author.objects.get(id=identifier)
        except (Author.DoesNotExist, ValueError, Exception):
            # Fall back to FQID - try with and without trailing slash
            try:
                author = Author.objects.get(url=identifier)
            except Author.DoesNotExist:
                try:
                    # Try with trailing slash added
                    author = Author.objects.get(url=identifier + '/')
                except Author.DoesNotExist:
                    try:
                        # Try with trailing slash removed
                        author = Author.objects.get(url=identifier.rstrip('/'))
                    except Author.DoesNotExist:
                        return JsonResponse({"error": "Author not found"}, status=404)
        
        # Use build_author_dict for consistency
        data = build_author_dict(author, request)
        return JsonResponse(data)
    
    def put(self, request, author_id=None, author_fqid=None):
        """Update author info - only the author themselves may update"""
        identifier = author_fqid or author_id

        author = _get_author_by_id_or_fqid(author_id=author_id, author_fqid=author_fqid)  # to raise 404 if not found

        # Check that authenticated user is the author
        if not request.user.is_authenticated or str(request.user.id) != str(author.id):
            return HttpResponse("Forbidden", status=403)
        
        try:
            data = json.loads(request.body)
            
            # Update fields
            author.displayName = data.get('displayName', author.displayName)
            author.github = data.get('github', author.github)
            author.description = data.get('description', author.description)
            author.host = data.get('host', author.host)
            
            author.save()
            notify_remote_author_update(author)
            
            # Use build_author_dict for consistency
            response_data = build_author_dict(author, request)
            return JsonResponse(response_data)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print("Error updating author:", str(e))
            return JsonResponse({'error': str(e)}, status=500) 
        

'''
AuthorsListAPIView: returns a JSON list of all authors.
Same format as AuthorAPIView but for multiple authors.
GET requests only.
'''
@method_decorator(http_basic_auth_or_session, name='dispatch')
class AuthorsListAPIView(View):
    def get(self, request):
        # Pagination parameters
        try:
            page_num = int(request.GET.get('page', 1))
        except ValueError:
            page_num = 1

        try:
            page_size = int(request.GET.get('size', 10))
        except ValueError:
            page_size = 10

        # Base queryset and ordering
        authors_qs = Author.objects.all().order_by('displayName')

        paginator = Paginator(authors_qs, page_size)
        page_obj = paginator.get_page(page_num)

        items = []
        for author in page_obj:
            # Use build_author_dict for consistency
            items.append(build_author_dict(author, request))

        response_data = {
            "type": "authors",
            "authors": items,
            "page": page_obj.number,
            "size": page_size,
            "count": paginator.count,
            "num_pages": paginator.num_pages,
        }

        return JsonResponse(response_data, safe=False, json_dumps_params={'indent': 2})
