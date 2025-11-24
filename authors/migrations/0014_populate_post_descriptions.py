from django.db import migrations


def populate_post_descriptions(apps, schema_editor):
    Post = apps.get_model('authors', 'Post')
    # Set a sensible default for posts that lack a description
    Post.objects.filter(description__isnull=True).update(description='(No description provided)')
    Post.objects.filter(description='').update(description='(No description provided)')


class Migration(migrations.Migration):

    dependencies = [
        ('authors', '0013_add_post_description_field'),
    ]

    operations = [
        migrations.RunPython(populate_post_descriptions, reverse_code=migrations.RunPython.noop),
    ]
