import re
from django import forms
from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from .models import Author, Post, Comment, Image, RemoteNode

class AuthorCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Author
        fields = UserCreationForm.Meta.fields + ('displayName', 'github',)

class AuthorProfileForm(ModelForm):
    profileImage = forms.ModelChoiceField(
        queryset=Image.objects.all().order_by('-id'),
        required=False,
        empty_label="(No profile image)",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Author
        fields = ('displayName', 'github', 'profileImage', 'description')

class PostForm(ModelForm):
    image = forms.ModelChoiceField(
        queryset=Image.objects.all().order_by('-id'),
        required=False,
        empty_label="(No image)",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = Post
        fields = ('title', 'content', 'contentType', 'visibility', 'image')
        labels = {
            'title': 'Post Title',
            'content': 'Content',
            'contentType': 'Content Type',
            'visibility': 'Visibility',
            'image': 'Image (Optional)'
        }

class CommentForm(ModelForm):
    content = forms.CharField(
        label="",
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Write a comment...",
            "required": "required",
        })
    )
    class Meta:
        model = Comment
        fields = ["content"]

class RemoteNodeForm(forms.ModelForm):
    class Meta:
        model = RemoteNode
        fields = ['name', 'base_url', 'username', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def clean_base_url(self):
        base_url = self.cleaned_data.get('base_url')
        if base_url:
            # Ensure URL ends with a slash
            if not base_url.endswith('/'):
                base_url += '/'
            # Validate URL format
            if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', base_url):
                raise forms.ValidationError('Please enter a valid URL.')
        return base_url

    def clean(self):
        cleaned_data = super().clean()
        base_url = cleaned_data.get('base_url')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        # Test the connection before saving
        if base_url and username and password:
            try:
                # Test basic auth connection
                import requests
                from django.conf import settings
                test_url = f"{base_url.rstrip('/')}/api/authors/"
                response = requests.get(test_url, auth=(username, password), timeout=10)
                if response.status_code != 200:
                    raise forms.ValidationError(
                        f"Could not connect to remote node. Status code: {response.status_code}"
                    )
            except requests.exceptions.RequestException:
                raise forms.ValidationError(
                    "Could not connect to the remote node. Please check the URL and credentials."
                )

        return cleaned_data


class NodeConfigurationForm(forms.Form):
    """
    Form to help users configure their node properly
    """
    base_url = forms.URLField(
        label="Your Node Base URL",
        help_text="Your Heroku app URL (e.g., https://your-app-name.herokuapp.com/)",
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://your-app-name.herokuapp.com/'})
    )
    
    service_username = forms.CharField(
        label="Service Username",
        help_text="Username for node-to-node communication",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'node_service'})
    )
    
    service_password = forms.CharField(
        label="Service Password",
        help_text="Password for node-to-node communication",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def clean_base_url(self):
        base_url = self.cleaned_data.get('base_url')
        if base_url and not base_url.endswith('/'):
            base_url += '/'
        return base_url