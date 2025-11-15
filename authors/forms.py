from django import forms
from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from .models import Author, Post, Comment, Image

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
