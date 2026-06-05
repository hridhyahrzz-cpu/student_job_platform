from rest_framework import serializers
from .models import UserModel

class StudentRegisterSerializer(serializers.ModelSerializer):
    user_type = serializers.ChoiceField(choices=UserModel.USER_TYPES, default="student")

    class Meta:
        model = UserModel
        fields = ["username", "password", "user_type"]

    def create(self, validated_data):
        user = UserModel.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            user_type=validated_data.get("user_type", "student")
        )
        return user


class StudentSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserModel
        fields = ["id", "username", "user_type"]
        read_only_fields = ["id", "user_type"]