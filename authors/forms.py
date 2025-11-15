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
    """
    Form for adding/editing remote nodes
    """
    password = forms.CharField(
        widget=forms.PasswordInput(),
        help_text="Password for HTTP Basic Auth when connecting to this remote node",
        required=False  # Allow empty for updates
    )

    class Meta:
        model = RemoteNode
        fields = ['name', 'base_url', 'username', 'password', 'enabled']
        widgets = {
            'base_url': forms.URLInput(attrs={'placeholder': 'e.g., https://example.com'}),
            'username': forms.TextInput(attrs={'placeholder': 'Username for remote node auth'}),
            'name': forms.TextInput(attrs={'placeholder': 'Friendly name for this node'}),
        }

    def __init__(self, *args, **kwargs):
        # Store whether this is an update form
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # For updates, make password optional
            self.fields['password'].help_text = "Leave blank to keep the current password"

    def clean_base_url(self):
        base_url = self.cleaned_data.get('base_url')
        if base_url:
            # Ensure the URL ends with a slash for consistency
            if not base_url.endswith('/'):
                base_url += '/'
        return base_url

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Only update password if it's provided in the form
        password = self.cleaned_data.get('password')
        if password:  # Only update password if it was provided
            instance.password = password

        if commit:
            instance.save()
        return instance