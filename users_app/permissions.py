from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """
    Allows access only to users with user_type = student
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type == "student"
        )


class IsRecruiter(BasePermission):
    """
    Allows access only to users with user_type = recruiter
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type == "recruiter"
        )


class IsStudentOrRecruiter(BasePermission):
    """
    Allows access to both student and recruiter (if needed)
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.user_type in ["student", "recruiter"]
        )