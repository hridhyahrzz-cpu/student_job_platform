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


class ApplyJobView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, job_id):
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
    lookup_field = "pk"

    def get(self, request, pk=None, *args, **kwargs):
        if pk is not None:
            return self.retrieve(request, pk=pk, *args, **kwargs)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)



