from django.forms import BaseModelForm
from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic import DetailView
from django.views import View
from django.http import HttpResponse, JsonResponse
from .models import Author

from .forms import AuthorCreationForm, AuthorProfileForm

class SignUpView(CreateView):
    form_class = AuthorCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False

        host = self.request.scheme + "://" + self.request.get_host()
        user.host = host
        user.save()

        api_url = reverse('authors:author_api', kwargs={'author_id': user.id})
        user.url = host + api_url
        user.save(update_fields=['url'])

        return redirect(self.success_url)

class AuthorProfileView(DetailView):
    form_class = AuthorProfileForm
    model = Author
    template_name = "authors/profile.html"
    pk_url_kwarg = "author_id"

    # Both AuthorProfileView and AuthorEditView extend profile_base.html. To distinguish between them, set 'editable' context.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editable'] = False
        return context

class AuthorEditView(UpdateView):
    form_class = AuthorProfileForm
    model = Author
    template_name = "authors/edit_profile.html"
    pk_url_kwarg = "author_id"

    # Both AuthorProfileView and AuthorEditView extend profile_base.html. To distinguish between them, set 'editable' context.
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['editable'] = True
        return context
    
    def form_valid(self, form) -> HttpResponse:
        user = form.save(commit=False)
        user.is_active = False

        user.save()

        success_url = reverse('authors:author_profile', kwargs={'author_id': user.id})
        return redirect(success_url)
    
class AuthorAPIView(View):
    def get(self, request, author_id):
        author = Author.objects.get(id=author_id)
        web_url = reverse('authors:author_profile', kwargs={'author_id': author.id})
        data = {
            "type": "author",
            "id": author.url, 
            "host": author.host,
            "displayName": author.displayName,
            "github": author.github,
            "profileImage": author.profileImage,
            "web": request.scheme + "://" + request.get_host() + web_url,
        }
        return JsonResponse(data)