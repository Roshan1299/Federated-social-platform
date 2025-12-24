from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created successfully!")
except Exception as e:
    print(f"Error creating superuser: {e}")