from rest_framework import serializers
from .models import UserModel

class StudentRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserModel
        fields = ["username", "password"]

    def create(self, validated_data):
        user = UserModel.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            user_type="student"
        )
        return user