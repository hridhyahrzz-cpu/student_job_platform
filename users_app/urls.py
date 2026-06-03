from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import register_student, StudentListRetrieveView

urlpatterns = [
    path("register/", register_student),
    path("students/", StudentListRetrieveView.as_view(), name="student-list"),
    path("students/<int:pk>/", StudentListRetrieveView.as_view(), name="student-detail"),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]