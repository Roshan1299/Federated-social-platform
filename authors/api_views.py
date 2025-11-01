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
