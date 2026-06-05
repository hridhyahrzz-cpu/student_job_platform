from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as django_login, logout as django_logout, authenticate
from rest_framework import mixins, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .forms import ProfileForm
from .models import UserModel, Profile
from .serializers import StudentRegisterSerializer, StudentSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            username = request.data.get("username")
            password = request.data.get("password")
            user = authenticate(request, username=username, password=password)
            if user is not None:
                django_login(request, user)
                user_type = "student"
                if hasattr(user, 'usermodel'):
                    user_type = user.usermodel.user_type
                elif hasattr(user, 'user_type'):
                    user_type = user.user_type
                response.data["user_type"] = user_type
        return response


def logout_view(request):
    django_logout(request)
    return redirect("login-page")



def login_page(request):
    return render(request, "users_app/login.html")


def register_page(request):
    return render(request, "users_app/register.html")


@login_required(login_url='/login-page/')
def dashboard_page(request):
    user = request.user
    user_type = "student"
    if hasattr(user, 'usermodel'):
        user_type = user.usermodel.user_type
    elif hasattr(user, 'user_type'):
        user_type = user.user_type

    if user_type == "recruiter":
        from jobs_app.models import JobModel, ApplicationModel
        jobs = JobModel.objects.filter(created_by_id=user.id)
        from django.db.models import Window, F, Value
        from django.db.models.functions import RowNumber, Coalesce
        applications = ApplicationModel.objects.filter(job__in=jobs).select_related('job', 'applicant').annotate(
            score_val=Coalesce(F('applicant__profile__score'), Value(0))
        ).annotate(
            rank=Window(
                expression=RowNumber(),
                partition_by=[F('job')],
                order_by=[F('score_val').desc(), F('applied_at').asc()]
            )
        ).order_by('job', '-score_val', 'applied_at')
        return render(request, "users_app/dashboard_recruiter.html", {
            "jobs": jobs,
            "applications": applications
        })
    else:
        from jobs_app.models import ApplicationModel
        applications = ApplicationModel.objects.filter(applicant=user).select_related('job')
        return render(request, "users_app/dashboard_student.html", {
            "applications": applications
        })


@login_required(login_url='/login-page/')
def my_applications_page(request):
    from jobs_app.models import ApplicationModel
    applications = ApplicationModel.objects.filter(applicant=request.user).select_related('job')
    return render(request, "users_app/my_applications.html", {"applications": applications})


@login_required(login_url='/login-page/')
def update_application_status(request, application_id):
    user = request.user
    user_type = "student"
    if hasattr(user, 'usermodel'):
        user_type = user.usermodel.user_type
    elif hasattr(user, 'user_type'):
        user_type = user.user_type

    if user_type != "recruiter":
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Only recruiters can update application status.")

    from jobs_app.models import ApplicationModel
    application = get_object_or_404(ApplicationModel, id=application_id)
    
    if application.job.created_by_id != user.id:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You do not have permission to update this application.")

    if request.method == "POST":
        if request.content_type == "application/json":
            try:
                import json
                data = json.loads(request.body)
                new_status = data.get("status")
            except Exception:
                new_status = None
        else:
            new_status = request.POST.get("status")
            
        if new_status in ["accepted", "rejected", "pending"]:
            application.status = new_status
            application.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == "application/json":
                from django.http import JsonResponse
                return JsonResponse({"success": True, "status": application.status})
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == "application/json":
                from django.http import JsonResponse
                return JsonResponse({"success": False, "error": "Invalid status value"}, status=400)
                
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == "application/json":
        from django.http import JsonResponse
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
        
    return redirect("dashboard")



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
