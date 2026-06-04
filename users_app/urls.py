from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    register_student,
    register_page,
    login_page,
    dashboard_page,
    profile_page,
    StudentListRetrieveView,
)

urlpatterns = [
    path("register/", register_student),
    path("register-page/", register_page, name="register-page"),
    path("students/", StudentListRetrieveView.as_view(), name="student-list"),
    path("students/<int:pk>/", StudentListRetrieveView.as_view(), name="student-detail"),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login-page/', login_page, name='login-page'),
    path('dashboard/', dashboard_page, name='dashboard'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]