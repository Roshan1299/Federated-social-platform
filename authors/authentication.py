"""
Authentication utilities for API endpoints
Provides HTTP Basic Auth for node-to-node communication
"""
import base64
from functools import wraps
import json
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate
from django.conf import settings
from django.shortcuts import get_object_or_404
from authors.models import Author, RemoteNode
from urllib.parse import urlparse


def normalize_host(url: str) -> str:
    """
    Normalize a host/base_url so we can reliably match RemoteNode entries.

    - strips spaces
    - removes trailing slash
    - lowercases
    - keeps just scheme://netloc if it's a full URL
    """
    if not url:
        return ""

    url = url.strip()

    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".lower()

    # Fallback for weird stored values
    return url.rstrip("/").lower()


def http_basic_auth_required(view_func):
    """
    Decorator for views that require HTTP Basic Authentication
    Used for remote API access (node-to-node communication)
    
    Usage:
        @http_basic_auth_required
        def my_api_view(request):
            ...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if Authorization header is present
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return HttpResponse(
                'Authentication required',
                status=401,
                headers={'WWW-Authenticate': 'Basic realm="API"'}
            )
        
        try:
            # Parse Basic Auth header
            auth_type, auth_string = auth_header.split(' ', 1)
            
            if auth_type.lower() != 'basic':
                return HttpResponse('Invalid authentication method', status=401)
            
            # Decode base64 credentials
            auth_decoded = base64.b64decode(auth_string).decode('utf-8')
            username, password = auth_decoded.split(':', 1)
            
            # Authenticate user (should be an Author in our system)
            user = authenticate(request, username=username, password=password)
            
            if user is None:
                return HttpResponse(
                    'Invalid credentials',
                    status=401,
                    headers={'WWW-Authenticate': 'Basic realm="API"'}
                )
            if not isinstance(user, Author):
                user = Author.objects.get(id=user.pk)

            if user.is_remote(): # This doesn't actually check if request is coming from remote since all go through a service user
                # Log somehow so the frontend can see we got here
                incoming_host = normalize_host(user.host)

                remote_user_node = None
                for node in RemoteNode.objects.all():
                    if normalize_host(node.base_url) == normalize_host(incoming_host):
                        remote_user_node = node
                        break

                if remote_user_node is None:
                    return HttpResponse(
                        'Remote node is not configured',
                        status=404,
                        headers={'WWW-Authenticate': 'Basic realm="API"'}
                    )

                if not remote_user_node.enabled:
                    return HttpResponse(
                        'Remote node is disabled',
                        status=403,  # 403 Forbidden for disabled nodes
                        headers={'WWW-Authenticate': 'Basic realm="API"'}
                    )
                
            if not _is_request_from_valid_node(request):
                return HttpResponse(
                    'Request is from an invalid or unrecognized remote node',
                    status=403,
                    headers={'WWW-Authenticate': 'Basic realm="API"'}
                )


            # Set the authenticated user on the request and mark that this
            # request was authenticated via HTTP Basic Auth. Views can use
            # `getattr(request, 'is_basic_auth', False)` to detect node-to-node
            # authentication and relax visibility rules if desired.
            request.user = user
            try:
                request.is_basic_auth = True
            except Exception:
                # In case request object is immutable for any reason, ignore
                pass
            
            # Call the actual view
            return view_func(request, *args, **kwargs)
            
        except (ValueError, UnicodeDecodeError):
            return HttpResponse(
                'Invalid authorization header',
                status=401,
                headers={'WWW-Authenticate': 'Basic realm="API"'}
            )
    
    return _wrapped_view


def http_basic_auth_or_session(view_func):
    """
    Decorator that accepts EITHER HTTP Basic Auth OR Django session authentication
    Useful for APIs that can be accessed both from the web UI and from other nodes
    
    Usage:
        @http_basic_auth_or_session
        def my_api_view(request):
            ...
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # If user is already authenticated via session, allow access
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        
        # Otherwise, try HTTP Basic Auth
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return HttpResponse(
                'Authentication required',
                status=401,
                headers={'WWW-Authenticate': 'Basic realm="API"'}
            )
        
        try:
            # Parse Basic Auth header
            auth_type, auth_string = auth_header.split(' ', 1)
            
            if auth_type.lower() != 'basic':
                return HttpResponse('Invalid authentication method', status=401)
            
            # Decode base64 credentials
            auth_decoded = base64.b64decode(auth_string).decode('utf-8')
            username, password = auth_decoded.split(':', 1)
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)

            if user is None:
                return HttpResponse(
                    'Invalid credentials',
                    status=401,
                    headers={'WWW-Authenticate': 'Basic realm="API"'}
                )
            if not isinstance(user, Author):
                user = Author.objects.get(id=user.pk)
        
            if not _is_request_from_valid_node(request):
                return HttpResponse(
                    'Request is from an invalid or unrecognized remote node',
                    status=403,
                    headers={'WWW-Authenticate': 'Basic realm="API"'}
                )

            if user.is_remote():
                incoming_host = normalize_host(user.host)

                remote_user_node = None
                for node in RemoteNode.objects.all():
                    if normalize_host(node.base_url) == incoming_host:
                        remote_user_node = node
                        break

                if remote_user_node is None:
                    return HttpResponse(
                        'Remote node is not configured',
                        status=404,
                        headers={'WWW-Authenticate': 'Basic realm="API"'}
                    )

                if not remote_user_node.enabled:
                    return HttpResponse(
                        'Remote node is disabled',
                        status=403,
                        headers={'WWW-Authenticate': 'Basic realm="API"'}
                    )


            # Set the authenticated user on the request
            request.user = user
            try:
                request.is_basic_auth = True
            except Exception:
                pass
            
            # Call the actual view
            return view_func(request, *args, **kwargs)
            
        except (ValueError, UnicodeDecodeError):
            return HttpResponse(
                'Invalid authorization header',
                status=401,
                headers={'WWW-Authenticate': 'Basic realm="API"'}
            )
    
    return _wrapped_view


class BasicAuthMiddleware:
    """
    Middleware to handle HTTP Basic Authentication for API requests
    Can be added to MIDDLEWARE in settings.py (for global basic auth support)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply to API endpoints
        if request.path.startswith('/api/'):
            # If not authenticated via session, try basic auth
            if not request.user.is_authenticated:
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                
                if auth_header.startswith('Basic '):
                    try:
                        auth_string = auth_header.split(' ', 1)[1]
                        auth_decoded = base64.b64decode(auth_string).decode('utf-8')
                        username, password = auth_decoded.split(':', 1)
                        
                        user = authenticate(request, username=username, password=password)
                        if user:
                            request.user = user
                            try:
                                request.is_basic_auth = True
                            except Exception:
                                pass
                    except (ValueError, UnicodeDecodeError):
                        pass
        
        response = self.get_response(request)
        return response

# Helper function to check JSON payloads. 
def _is_request_from_valid_node(request):
    """
    Return True if the request should be allowed as coming from a valid node.
    - Non-JSON or requests without an author/actor are treated as valid (not a remote node payload).
    - Local node (BASE_URL) is valid.
    - Remote nodes are valid only if they exist in RemoteNode and are enabled.
    - Unknown remote hosts are treated as invalid.
    """
    content_type = request.META.get("CONTENT_TYPE", "")
    if not content_type.startswith("application/json"):
        return True  # not a remote payload; allow

    body = request.body.decode("utf-8") if request.body else ""
    if not body:
        return True  # no body to inspect; allow

    try:
        data = json.loads(body)
    except Exception:
        return True  # malformed JSON -> don't block here

    author = data.get("author") or data.get("actor")
    if not author:
        return False  # no author/actor -> Invalid

    author_host = author.get("host")
    if not author_host:
        return False  # no host -> Invalid

    local_node = (getattr(settings, "BASE_URL", "") or "").rstrip("/")
    # If the author is from our local node, it's valid
    if author == "" or author_host == local_node:
        return True

    # Otherwise, match against configured RemoteNode entries
    for node in RemoteNode.objects.all():
        if normalize_host(node.base_url) == normalize_host(author_host):
            return node.enabled  # valid if enabled, invalid if disabled

    # Unknown remote host -> treat as invalid
    return False