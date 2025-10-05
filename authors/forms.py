from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm
from .models import Author, Post

class AuthorCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Author
        fields = UserCreationForm.Meta.fields + ('displayName', 'github',)

class AuthorProfileForm(ModelForm):
    class Meta:
        model = Author
        fields = ('displayName', 'github', 'profileImage', 'description')

class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'description', 'content', 'contentType', 'visibility', 'unlisted')
        labels = {
            'title': 'Post Title',
            'description': 'Description (Optional)',
            'content': 'Content',
            'contentType': 'Content Type',
            'visibility': 'Visibility',
            'unlisted': 'Unlisted (Public but not in feeds)'
        }