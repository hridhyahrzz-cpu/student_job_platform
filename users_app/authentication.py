from rest_framework.authentication import BaseAuthentication

class CustomAuthentication(BaseAuthentication):

    def authenticate(self, request):

        user = request.user

        if user.is_authenticated:
            return (user, None)

        return None