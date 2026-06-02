from rest_framework import mixins, generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import UserModel
from .serializers import StudentRegisterSerializer, StudentSerializer


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
