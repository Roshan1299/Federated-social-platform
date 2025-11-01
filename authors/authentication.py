"""
Authentication utilities for API endpoints
Provides HTTP Basic Auth for node-to-node communication
"""
import base64
from functools import wraps
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate
from django.conf import settings


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
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is None:
                return HttpResponse(
                    'Invalid credentials',
                    status=401,
                    headers={'WWW-Authenticate': 'Basic realm="API"'}
                )
            
            # Set the authenticated user on the request
            request.user = user
            
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
            
            # Set the authenticated user on the request
            request.user = user
            
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
                    except (ValueError, UnicodeDecodeError):
                        pass
        
        response = self.get_response(request)
        return response
