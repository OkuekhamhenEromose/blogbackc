from rest_framework import permissions

class IsAdminGroup(permissions.BasePermission):
    """
    Allow access only to users in the ADMIN group.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.groups.filter(name='ADMIN').exists()

class IsAuthorOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow authors of an object or admins to edit/delete it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user (we'll limit listing elsewhere).
        if request.method in permissions.SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.groups.filter(name='ADMIN').exists():
            return True
        return obj.author == request.user
