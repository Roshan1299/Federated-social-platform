from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm
from .models import Author

class AuthorCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Author
        fields = UserCreationForm.Meta.fields + ('displayName', 'github',)

class AuthorProfileForm(ModelForm):
    class Meta:
        model = Author
        fields = ('displayName', 'github', 'profileImage', 'description')