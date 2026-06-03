from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import UserModel


class CustomAuthentication(JWTAuthentication):
    def authenticate(self, request):

        user = request.user

        if user.is_authenticated:
            return (user, None)

        return None