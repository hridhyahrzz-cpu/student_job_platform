import logging

from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework import status, viewsets, mixins, generics

from users_app.permissions import IsStudentOrRecruiter

from .models import JobModel, ApplicationModel
from .serializers import ApplicationSerializer, JobSerializer
from .permission import IsOwnerOrReadOnly, IsRecruiter
from users_app.authentication import CustomAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class ApplyJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
        user = request.user
        auth_user_model = get_user_model()
        logger.debug(
            "ApplyJobView request.user type=%s is_authenticated=%s user_repr=%r",
            type(user),
            getattr(user, 'is_authenticated', None),
            user,
        )
        if not isinstance(user, auth_user_model):
            logger.error(
                "ApplyJobView request.user is not an instance of AUTH_USER_MODEL (%s): %s",
                auth_user_model,
                type(user),
            )

        try:
            job = JobModel.objects.get(id=job_id)
        except JobModel.DoesNotExist:
            return Response(
                {"error": "Job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # prevent duplicate applications
        if ApplicationModel.objects.filter(job=job, applicant=request.user).exists():
            return Response(
                {"error": "You have already applied for this job"},
                status=status.HTTP_400_BAD_REQUEST
            )

        application = ApplicationModel.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=request.data.get("cover_letter", "")
        )

        serializer = ApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def home_page(request):
    jobs = JobModel.objects.all()
    return render(request, 'home.html', {'jobs': jobs})


def job_list(request):
    jobs = JobModel.objects.all()
    return render(request, 'jobs_app/jobs.html', {'jobs': jobs})


def job_detail(request, job_id):
    job = get_object_or_404(JobModel, id=job_id)
    return render(request, 'job_detail.html', {'job': job})


def apply_job_page(request, job_id):
    job = get_object_or_404(JobModel, id=job_id)
    return render(request, 'apply_job.html', {'job': job})


class JobModelViewSet(viewsets.ModelViewSet):
    queryset = JobModel.objects.all()
    serializer_class = JobSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsRecruiter]
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsStudentOrRecruiter]
        return super().get_permissions()

class ApplicationCreateReadView(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    generics.GenericAPIView
):
    queryset = ApplicationModel.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    lookup_field = "pk"

    def get(self, request, pk=None, *args, **kwargs):
        if pk is not None:
            return self.retrieve(request, pk=pk, *args, **kwargs)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        auth_user_model = get_user_model()
        logger.debug(
            "ApplicationCreateReadView perform_create request.user type=%s is_authenticated=%s user_repr=%r",
            type(user),
            getattr(user, 'is_authenticated', None),
            user,
        )
        if not isinstance(user, auth_user_model):
            logger.error(
                "ApplicationCreateReadView request.user is not an instance of AUTH_USER_MODEL (%s): %s",
                auth_user_model,
                type(user),
            )

        serializer.save(applicant=user)



