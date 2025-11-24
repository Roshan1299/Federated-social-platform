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
    # Custom content type field with Image option
    contentType = forms.ChoiceField(
        choices=[
            ('text/plain', 'Plain Text'),
            ('text/markdown', 'Markdown'),
            ('image', 'Image'),
        ],
        widget=forms.Select(attrs={"class": "form-select", "id": "id_contentType"})
    )
    
    visibility = forms.ChoiceField(
        choices=Post.VISIBILITY_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    image = forms.ModelChoiceField(
        queryset=Image.objects.all().order_by('-id'),
        required=False,
        empty_label="(No image)",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_image"})
    )
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Brief description..."}),
        label="Description"
    )
    
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 10, "placeholder": "Write your content here...", "id": "id_content"}),
        label="Content"
    )

    class Meta:
        model = Post
        fields = ('title', 'description', 'content', 'contentType', 'visibility', 'image')
        labels = {
            'title': 'Post Title',
            'description': 'Description',
            'content': 'Content',
            'contentType': 'Content Type',
            'visibility': 'Visibility',
            'image': 'Image',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('contentType')
        image = cleaned_data.get('image')
        content = cleaned_data.get('content')
        
        # If image content type is selected, image is required
        if content_type == 'image':
            if not image:
                raise forms.ValidationError("You must select an image when 'Image' content type is chosen.")
        
        return cleaned_data


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
        fields = ['name', 'base_url', 'username', 'password', 'enabled']
        widgets = {
            'password': forms.PasswordInput(),
            'enabled': forms.CheckboxInput(),
        }

    def clean_base_url(self):
        base_url = self.cleaned_data.get('base_url')
        if base_url:
            if not base_url.endswith('/'):
                base_url += '/'
            if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', base_url):
                raise forms.ValidationError('Please enter a valid URL.')
        return base_url

    def clean(self):
        cleaned_data = super().clean()
        base_url = cleaned_data.get('base_url')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if base_url and username and password:
            try:
                import requests
                test_url = f"{base_url.rstrip('/')}/api/authors/"

                response = requests.get(
                    test_url,
                    auth=(username, password),
                    timeout=15,
                    headers={'User-Agent': 'SocialDistribution/1.0'}
                )

                if response.status_code not in [200, 401, 403, 404]:
                    raise forms.ValidationError(
                        f"Connection failed: status {response.status_code}"
                    )

            except requests.exceptions.Timeout:
                raise forms.ValidationError("Connection timed out.")
            except requests.exceptions.ConnectionError:
                raise forms.ValidationError("Could not connect. Check URL.")
            except requests.exceptions.RequestException as e:
                raise forms.ValidationError(str(e))

        return cleaned_data


class NodeConfigurationForm(forms.Form):
    base_url = forms.URLField(
        label="Your Node Base URL",
        help_text="Example: https://your-app-name.herokuapp.com/",
        widget=forms.URLInput(attrs={'class': 'form-control'})
    )

    service_username = forms.CharField(
        label="Service Username",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    service_password = forms.CharField(
        label="Service Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean_base_url(self):
        base_url = self.cleaned_data.get('base_url')
        if base_url and not base_url.endswith('/'):
            base_url += '/'
        return base_url


class ImageUploadForm(forms.ModelForm):
    """
    Used ONLY for /authors/upload_image/.
    Accepts a file upload and the view manually creates Image(data=...).
    """
    image = forms.ImageField(required=True, label="Select an image")

    class Meta:
        model = Image
        fields = []  # DO NOT include data / content_type (non-editable)
