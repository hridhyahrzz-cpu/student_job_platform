from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from rest_framework import mixins, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .forms import ProfileForm
from .models import UserModel, Profile
from .serializers import StudentRegisterSerializer, StudentSerializer


def login_page(request):
    return render(request, "users_app/login.html")


def register_page(request):
    return render(request, "users_app/register.html")


def dashboard_page(request):
    return render(request, "users_app/dashboard.html")


@login_required(login_url='/login-page/')
def profile_page(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            success_message = 'Profile updated successfully.'
            return render(request, 'users_app/profile.html', {
                'form': form,
                'profile': profile,
                'success_message': success_message,
            })
        error_message = 'Please fix the errors below.'
        return render(request, 'users_app/profile.html', {
            'form': form,
            'profile': profile,
            'error_message': error_message,
        })

    form = ProfileForm(instance=profile)
    return render(request, 'users_app/profile.html', {
        'form': form,
        'profile': profile,
    })


@api_view(["POST"])
def register_student(request):

    serializer = StudentRegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()

        return Response(
            {"message": "Student registered successfully"},
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


class StudentListRetrieveView(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    generics.GenericAPIView
):
    """
    List all students or retrieve a single student by id.
    """
    queryset = UserModel.objects.filter(user_type="student")
    serializer_class = StudentSerializer
    lookup_field = "pk"

    def get(self, request, pk=None, *args, **kwargs):
        if pk is not None:
            return self.retrieve(request, pk=pk, *args, **kwargs)
        return self.list(request, *args, **kwargs)
