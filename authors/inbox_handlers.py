import uuid
from django.http import JsonResponse
from django.utils import timezone
from .models import Author, Post, Comment, Like, CommentLike, FollowRequest, Follow
from authors.utils.image_sync import fetch_and_store_remote_image
import typing
import base64

def get_or_create_author(author_data):
    """Normalize incoming author payload and return an Author instance."""

    author_data = author_data or {}
    raw_id = author_data.get("id") or author_data.get("url")
    if not raw_id:
        return None

    print("👤 get_or_create_author raw_id:", raw_id)
    print("   incoming profileImage:", author_data.get("profileImage"))

    # Extract username part safely
    try:
        username_part = raw_id.rstrip("/").split("/")[-1]
    except Exception:
        username_part = "remote"

    display_name = (
        author_data.get("displayName")
        or author_data.get("username")
        or username_part
    )

    host = author_data.get("host") or raw_id.split("/api/authors/")[0]

    author, created = Author.objects.get_or_create(
        url=raw_id,
        defaults={
            "username": f"remote_{username_part}_{uuid.uuid4().hex[:6]}",
            "displayName": display_name,
            "host": host,
            "github": author_data.get("github", ""),
            "description": author_data.get("description", "") or "",
        },
    )

    # Do NOT update local author profiles with remote data to prevent circular profile updates
    # Only update local fields for remote authors (not local ones)
    from django.conf import settings
    current_host = getattr(settings, 'BASE_URL', '').rstrip('/')

    # Only update author fields if the author is from a remote host (not local)
    if author.host != current_host:
        changed_fields = []

        # --- keep displayName fresh ---
        if display_name and author.displayName != display_name:
            author.displayName = display_name
            changed_fields.append("displayName")

        # --- sync github ---
        incoming_github = author_data.get("github")
        if incoming_github is not None and incoming_github != author.github:
            author.github = incoming_github
            changed_fields.append("github")

        # --- sync description ---
        incoming_desc = author_data.get("description", "")
        if incoming_desc is not None and incoming_desc != author.description:
            author.description = incoming_desc
            changed_fields.append("description")

        # --- sync profileImage from remote, if provided ---
        profile_image_url = author_data.get("profileImage")
        if profile_image_url and isinstance(profile_image_url, str):
            try:
                img = fetch_and_store_remote_image(profile_image_url)
            except Exception as e:
                img = None
                print("Failed to sync remote profile image:", e)

            if img and (not author.profileImage_id or author.profileImage_id != img.id):
                author.profileImage = img
                changed_fields.append("profileImage")

        if changed_fields:
            author.save(update_fields=changed_fields)

    return author


def reopen_follow_request(follow_request):
    """Ensure a FollowRequest is in 'PENDING' state.

    If the provided FollowRequest has a status other than 'PENDING', set
    it to 'PENDING' and persist the change. Returns True if an update
    was performed, False otherwise.
    """
    if follow_request.status != 'PENDING':
        follow_request.status = 'PENDING'
        follow_request.save(update_fields=['status'])
        return True
    return False


def handle_follow_request(self, recipient, data, request):
    """Handle incoming follow request (incoming ActivityPub-like Follow).

    Creates a stub Author for the actor if necessary and creates a
    FollowRequest record (or returns existing one).
    """
    try:
        actor_data = data.get('actor', {})
        actor = get_or_create_author(actor_data)

        follow_request, created = FollowRequest.objects.get_or_create(
            sender=actor,
            receiver=recipient,
            defaults={'status': 'PENDING'}
        )

        if created:
            return JsonResponse({'message': 'Follow request created'}, status=201)
        else:
            # If an existing request is present but not pending, reset it to PENDING
            if reopen_follow_request(follow_request):
                return JsonResponse({'message': 'Follow request re-opened'}, status=200)
            return JsonResponse({'message': 'Follow request already exists'}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Failed to process follow request: {str(e)}'}, status=400)


def handle_unfollow(self, recipient, data, request):
    """
    Handle an incoming unfollow from another node.

    Expected payload shape (we only really need 'actor'):
    {
        "type": "unfollow",
        "actor": { ... remote author ... },
        "object": { ... our recipient author ... }   # optional
    }
    """
    try:
        actor_data = data.get("actor", {}) or {}
        if not actor_data:
            return JsonResponse({"error": "Unfollow must include actor"}, status=400)

        # Ensure we have a stub Author for the remote actor
        actor = get_or_create_author(actor_data)

        # Remove any follow relationship actor -> recipient
        Follow.objects.filter(follower=actor, following=recipient).delete()

        # Also clear any pending follow requests from this actor to this recipient
        FollowRequest.objects.filter(sender=actor, receiver=recipient, status="PENDING").delete()

        return JsonResponse({"message": "Unfollow processed"}, status=200)
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to process unfollow: {str(e)}"},
            status=400,
        )


def handle_post(self, recipient, data, request):
    """
    Handle incoming post from a remote node.
    Includes:
    - creating/updating post
    - fetching & attaching remote images (URL or base64)
    - inbox receipts
    """
    try:
        from .models import InboxReceipt, Image

        # ---------------------------------------------------------
        # EXTRACT ORIGIN
        # ---------------------------------------------------------
        origin = data.get("origin") or data.get("id")
        if not origin:
            return JsonResponse({"error": "Post must have origin/id"}, status=400)

        # ---------------------------------------------------------
        # NORMALIZE VISIBILITY
        # ---------------------------------------------------------
        visibility = (data.get("visibility") or "PUBLIC").upper()
        if data.get("unlisted", False):
            visibility = "PUBLIC_UNLISTED"

        # ---------------------------------------------------------
        # IMAGE HANDLING
        # ---------------------------------------------------------
        remote_image_url = (
            data.get("image")
            or data.get("image_url")
            or data.get("imageUrl")
        )

        content_type = (data.get("contentType") or "").strip()
        content = data.get("content", "") or ""

        local_image = None

        # 1) If we got an explicit image URL, try to download that
        if remote_image_url:
            print("REMOTE IMAGE URL:", remote_image_url)
            local_image = fetch_and_store_remote_image(remote_image_url)
            print("LOCAL IMAGE:", local_image)

        # 2) If no URL image, but content is base64, decode and store
        if (not local_image) and ("base64" in content_type.lower()) and content:
            try:
                clean_type = content_type.split(";")[0]
                img_bytes = base64.b64decode(content)

                ext = "png"
                if "jpeg" in clean_type or "jpg" in clean_type:
                    ext = "jpg"
                elif "gif" in clean_type:
                    ext = "gif"

                local_image = Image.objects.create(
                    file_name=f"remote_post_{uuid.uuid4()}.{ext}",
                    content_type=clean_type,
                    data=img_bytes,
                )
            except Exception as e:
                print("Failed to decode inline base64 image:", e)

        # ---------------------------------------------------------
        # CHECK IF POST ALREADY EXISTS
        # ---------------------------------------------------------
        existing_post = Post.objects.filter(origin=origin).first()

        if existing_post:
            existing_post.title = data.get("title", existing_post.title)
            existing_post.content = data.get("content", existing_post.content)
            existing_post.contentType = data.get(
                "contentType", existing_post.contentType
            )
            existing_post.visibility = visibility
            existing_post.source = data.get("source", existing_post.source)
            existing_post.updated = timezone.now()

            if data.get("deleted", False):
                existing_post.deleted = True

            if local_image:
                existing_post.image = local_image

            existing_post.save()

            InboxReceipt.objects.get_or_create(
                recipient=recipient,
                post=existing_post,
            )

            return JsonResponse({"message": "Post updated"}, status=200)

        # ---------------------------------------------------------
        # NEW POST
        # ---------------------------------------------------------
        author_data = data.get("author", {})
        if not author_data:
            return JsonResponse({"error": "Post must include author"}, status=400)

        author = get_or_create_author(author_data)

        post = Post.objects.create(
            author=author,
            title=data.get("title", "Untitled"),
            content=content,
            contentType=content_type or "text/plain",
            visibility=visibility,
            source=data.get("source", origin),
            origin=origin,
            image=local_image,  # may be None
        )

        InboxReceipt.objects.create(
            recipient=recipient,
            post=post,
        )

        return JsonResponse({"message": "Post received"}, status=201)

    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to process post: {str(e)}"},
            status=400,
        )




def handle_comment(self, recipient, data, request):
    """
    Handle incoming comment from another node.
    """
    try:
        # Extract origin/id - the globally unique identifier
        origin = data.get('id') or data.get('origin')
        
        if not origin:
            return JsonResponse({'error': 'Comment must have id or origin field'}, status=400)
        
        # STEP 1: Check if we already have this comment (by origin, NOT by UUID!)
        existing_comment = Comment.objects.filter(origin=origin).first()
        
        if existing_comment:
            # Comment already exists - optionally update content
            existing_comment.content = data.get('comment') or data.get('content', existing_comment.content)
            existing_comment.save()
            return JsonResponse({'message': 'Comment updated'}, status=200)
        
        # STEP 2: Get or create the comment author
        author_data = data.get('author', {})
        if not author_data:
            return JsonResponse({'error': 'Comment must have an author'}, status=400)
        commenter = get_or_create_author(author_data)
        
        # STEP 3: Find the post being commented on
        # The comment's "object" field should reference the post URL
        post_url = data.get('object') or data.get('post') or data.get('entry')
        
        if not post_url:
            return JsonResponse({'error': 'Comment must reference a post (object field)'}, status=400)
        
        # Try to find post by origin
        post = Post.objects.filter(origin=post_url).first()
        
        if not post:
            # Try extracting UUID from post URL
            post_id_str = post_url.split('/')[-1]
            try:
                post_id = uuid.UUID(post_id_str)
                post = Post.objects.filter(id=post_id).first()
            except (ValueError, AttributeError):
                pass
        
        if not post:
            return JsonResponse({'error': 'Post not found'}, status=404)
        
        # STEP 4: Create the comment. Don't attempt to reuse incoming UUIDs;
        # just create a local Comment with the provided origin.
        comment = Comment.objects.create(
            post=post,
            author=commenter,
            content=data.get('comment') or data.get('content', ''),
            origin=origin,
        )
        
        return JsonResponse({'message': 'Comment received'}, status=201)
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to process comment: {str(e)}'}, status=400)


def handle_like(self, recipient, data, request):
    """
    Handle incoming like from another node.
    
    Supports both post likes and comment likes.
    """
    try:
        origin = data.get('id') or data.get('origin')
        
        # Get the object being liked
        object_url = data.get('object', '')
        
        if not object_url:
            return JsonResponse({'error': 'Like must have object field'}, status=400)
        
        # STEP 1: Determine if this is a post like or comment like
        is_comment_like = '/commented/' in object_url or '/comments/' in object_url
        
        if is_comment_like:
            return handle_comment_like(self, recipient, data, request, origin, object_url)
        else:
            return handle_post_like(self, recipient, data, request, origin, object_url)
        
    except Exception as e:
        return JsonResponse({'error': f'Failed to process like: {str(e)}'}, status=400)


def handle_post_like(self, recipient, data, request, origin, object_url):
    """Handle a like on a post"""
    # Check if we already have this like (by origin if provided)
    if origin:
        existing_like = Like.objects.filter(origin=origin).first()
        if existing_like:
            return JsonResponse({'message': 'Like already recorded'}, status=200)
    
    # Get or create the liker
    author_data = data.get('author', {})
    if not author_data:
        return JsonResponse({'error': 'Like must have an author'}, status=400)
    liker = get_or_create_author(author_data)
    
    # Find the post being liked
    post = Post.objects.filter(origin=object_url).first()
    
    if not post:
        # Try UUID lookup
        post_id_str = object_url.split('/')[-1]
        try:
            post_id = uuid.UUID(post_id_str)
            post = Post.objects.filter(id=post_id).first()
        except (ValueError, AttributeError):
            pass
    
    if not post:
        return JsonResponse({'error': 'Post not found'}, status=404)
    
    # Create or get the like
    like, created = Like.objects.get_or_create(
        author=liker,
        post=post,
        defaults={
            'origin': origin,
        }
    )
    
    # If not created and origin was provided, update it
    if not created and origin and not like.origin:
        like.origin = origin
        like.save()
    
    return JsonResponse({'message': 'Like received'}, status=201 if created else 200)


def handle_comment_like(self, recipient, data, request, origin, object_url):
    """Handle a like on a comment"""
    # Check if we already have this like
    if origin:
        existing_like = CommentLike.objects.filter(origin=origin).first()
        if existing_like:
            return JsonResponse({'message': 'Comment like already recorded'}, status=200)
    
    # Get or create the liker
    author_data = data.get('author', {})
    author_id = author_data.get('id') or author_data.get('url')
    
    liker = get_or_create_author(author_data)
    
    # Find the comment being liked
    comment = Comment.objects.filter(origin=object_url).first()
    
    if not comment:
        # Try UUID lookup
        comment_id_str = object_url.split('/')[-1]
        try:
            comment_id = uuid.UUID(comment_id_str)
            comment = Comment.objects.filter(id=comment_id).first()
        except (ValueError, AttributeError):
            pass
    
    if not comment:
        return JsonResponse({'error': 'Comment not found'}, status=404)
    
    # Create or get the comment like
    comment_like, created = CommentLike.objects.get_or_create(
        author=liker,
        comment=comment,
        defaults={
            'origin': origin,
        }
    )
    
    # If not created and origin was provided, update it
    if not created and origin and not comment_like.origin:
        comment_like.origin = origin
        comment_like.save()
    
    return JsonResponse({'message': 'Comment like received'}, status=201 if created else 200)
