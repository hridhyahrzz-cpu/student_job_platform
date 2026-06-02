from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework import status, viewsets
from rest_framework.decorators import action

from .models import JobModel, ApplicationModel
from .serializers import ApplicationSerializer, JobSerializer
from .permission import IsOwnerOrReadOnly


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
   