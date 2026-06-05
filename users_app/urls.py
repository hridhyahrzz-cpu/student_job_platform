from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    register_student,
    register_page,
    login_page,
    CustomTokenObtainPairView,
    logout_view,
    dashboard_page,
    my_applications_page,
    update_application_status,
    profile_page,
    StudentListRetrieveView,
)

urlpatterns = [
    path("register/", register_student),
    path("register-page/", register_page, name="register-page"),
    path("students/", StudentListRetrieveView.as_view(), name="student-list"),
    path("students/<int:pk>/", StudentListRetrieveView.as_view(), name="student-detail"),
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("login-page/", login_page, name="login-page"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_page, name="dashboard"),
    path("my-applications/", my_applications_page, name="my-applications"),
    path("applications/<int:application_id>/status/", update_application_status, name="update-application-status"),

    path("profile/", profile_page, name="profile"),

    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]