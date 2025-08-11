from rest_framework import permissions

class IsBlogAdmin(permissions.BasePermission):
    """
    Allows access only to users who are blog admins (profile.is_blog_admin True).
    """
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'profile', None) and request.user.profile.is_blog_admin)

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow authors to edit/delete their own posts.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to authenticated users (IsAuthenticated enforced globally)
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user
