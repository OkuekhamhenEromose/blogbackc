from rest_framework import permissions

class IsBlogAdmin(permissions.BasePermission):
    """
    Allows access only to users who are blog admins (profile.is_blog_admin True).
    """
    def has_permission(self, request, view):
        # Support both 'profile' and 'userprofile' in case of naming differences
        prof = getattr(request.user, 'profile', None) or getattr(request.user, 'userprofile', None)
        return bool(
            request.user 
            and request.user.is_authenticated 
            and prof 
            and getattr(prof, 'is_blog_admin', False)
        )


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
