from rest_framework import permissions
from .models import UserProfile

class IsBlogAdmin(permissions.BasePermission):
    """
    Allows access only to users who are blog admins (profile.is_blog_admin True).
    """
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get profile using the correct related name
        try:
            profile = request.user.profile
            return bool(profile and profile.is_blog_admin)
        except UserProfile.DoesNotExist:
            # If profile doesn't exist, try to create it
            UserProfile.objects.get_or_create(
                user=request.user, 
                defaults={'role': 'user', 'is_blog_admin': False}
            )
            return False
        except AttributeError:
            return False


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow authors to edit/delete their own posts.
    Admins can always edit.
    """
    def has_object_permission(self, request, view, obj):
        # Read-only methods are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Admins can edit any post
        prof = getattr(request.user, 'profile', None) or getattr(request.user, 'userprofile', None)
        if prof and getattr(prof, 'is_blog_admin', False):
            return True
        
        # Otherwise, only the author can edit/delete
        return obj.author == request.user
