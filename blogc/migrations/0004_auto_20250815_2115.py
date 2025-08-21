from django.db import migrations
from django.utils.text import slugify

def create_default_categories(apps, schema_editor):
    # ✅ Correct app label is "blogc"
    BlogCategory = apps.get_model('blogc', 'BlogCategory')

    default_categories = [
        "Travel",
        "Socials",
        "Politics",
        "Sport",
        "Entertainment",
    ]

    for name in default_categories:
        BlogCategory.objects.get_or_create(
            name=name,
            defaults={"slug": slugify(name)}
        )

class Migration(migrations.Migration):

    dependencies = [
        ('blogc', '0003_alter_userprofile_role'),
    ]

    operations = [
        migrations.RunPython(create_default_categories),
    ]
