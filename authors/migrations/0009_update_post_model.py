# Generated migration for adding deleted field to Post model and updating visibility choices
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authors', '0008_comment_commentlike'),
    ]

    operations = [
        # Remove the unlisted field that was previously in the model
        migrations.RemoveField(
            model_name='post',
            name='unlisted',
        ),
        # Add the new deleted field
        migrations.AddField(
            model_name='post',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
        # Update the visibility choices to include PUBLIC_UNLISTED and exclude PRIVATE
        migrations.AlterField(
            model_name='post',
            name='visibility',
            field=models.CharField(
                choices=[
                    ('PUBLIC', 'Public'),
                    ('PUBLIC_UNLISTED', 'Public Unlisted'),
                    ('FRIENDS', 'Friends Only'),
                ],
                default='PUBLIC',
                max_length=20
            ),
        ),
    ]