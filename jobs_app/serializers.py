from rest_framework import serializers
from .models import JobModel, ApplicationModel
from users_app.serializers import StudentSerializer


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobModel
        fields = '__all__'

    def to_internal_value(self, data):
        user=self.context.get("request").user
        data["created_by"] = user.id
        return super().to_internal_value(data)


class ApplicationSerializer(serializers.ModelSerializer):
    applicant = StudentSerializer(read_only=True)
    rank = serializers.IntegerField(read_only=True)

    class Meta:
        model = ApplicationModel
        fields = ['id', 'job', 'cover_letter', 'applicant', 'rank']
        read_only_fields = ['applicant', 'rank']
