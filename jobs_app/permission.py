from rest_framework.permissions import BasePermission

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type == 'student'
        )


class IsRecruiter(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type == 'recruiter'
        )


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission to check if user is the owner of the object or allow read-only access.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        from rest_framework.permissions import SAFE_METHODS
        if request.method in SAFE_METHODS:
            return True
        # Write permissions are only allowed to the owner of the object
        return obj.created_by == request.user