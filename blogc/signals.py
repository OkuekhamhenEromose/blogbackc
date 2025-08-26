# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    # Create a profile for any user that doesn't have one
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={
            "role": "user",
            "is_blog_admin": False,
        },
        )
    else:
        # If user existed before you added profiles, backfill safely
        if not hasattr(instance, "profile"):
            UserProfile.objects.get_or_create(user=instance, defaults={
                "role": "user",
                "is_blog_admin": False,
            })
