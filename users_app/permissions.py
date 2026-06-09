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


from functools import wraps
from django.http import HttpResponseForbidden

def recruiter_required(view_func):
    """
    Decorator for views that checks that the user is logged in and is a recruiter,
    redirecting to the log-in page or returning 403 Forbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user or not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('login-page')
            
        user = request.user
        user_type = None
        if hasattr(user, 'usermodel'):
            user_type = user.usermodel.user_type
        elif hasattr(user, 'user_type'):
            user_type = user.user_type
            
        if user_type != 'recruiter':
            return HttpResponseForbidden("Only recruiters can access this page.")
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view