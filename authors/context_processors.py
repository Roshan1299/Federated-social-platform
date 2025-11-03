from .models import FollowRequest

def pending_follow_requests_count(request):
    """
    Adds the count of pending follow requests to all templates.
    """
    if request.user.is_authenticated:
        count = FollowRequest.objects.filter(receiver=request.user, status='PENDING').count()
        return {'pending_follow_requests_count': count}
    return {'pending_follow_requests_count': 0}
