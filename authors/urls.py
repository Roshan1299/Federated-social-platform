from django.urls import path
from .views import SignUpView, AuthorProfileView, AuthorAPIView

urlpatterns = [
    path("accounts/signup/", SignUpView.as_view(), name="signup"),
    path("authors/<uuid:author_id>/", AuthorProfileView.as_view(), name="author_profile"),
    path("api/authors/<uuid:author_id>/", AuthorAPIView.as_view(), name="author_api"),
]
