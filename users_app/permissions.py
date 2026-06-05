from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """
    Allows access only to users with user_type = student
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.usermodel.user_type == "student"
        except AttributeError:
            return getattr(request.user, "user_type", None) == "student"
        except Exception:
            return False


class IsRecruiter(BasePermission):
    """
    Allows access only to users with user_type = recruiter
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.usermodel.user_type == "recruiter"
        except AttributeError:
            return getattr(request.user, "user_type", None) == "recruiter"
        except Exception:
            return False


class IsStudentOrRecruiter(BasePermission):
    """
    Allows access to both student and recruiter
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.usermodel.user_type in ["student", "recruiter"]
        except AttributeError:
            return getattr(request.user, "user_type", None) in ["student", "recruiter"]
        except Exception:
            return False