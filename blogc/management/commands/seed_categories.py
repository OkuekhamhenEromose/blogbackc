from django.core.management.base import BaseCommand
from blogc.models import BlogCategory
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seed default blog categories'

    def handle(self, *args, **kwargs):
        categories = ["Travel", "Socials", "Politics", "Sport", "Entertainment"]
        for name in categories:
            obj, created = BlogCategory.objects.get_or_create(
                name=name,
                defaults={"slug": slugify(name)}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {name}'))
            else:
                self.stdout.write(f'Category already exists: {name}')
