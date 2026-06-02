from django.urls import path
from .views import register_student, StudentListRetrieveView

urlpatterns = [
    path("register/", register_student),
    path("students/", StudentListRetrieveView.as_view(), name="student-list"),
    path("students/<int:pk>/", StudentListRetrieveView.as_view(), name="student-detail"),
]