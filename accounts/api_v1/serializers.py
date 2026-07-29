from rest_framework import serializers
from accounts.models import Administrator
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError


class AdministratorSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()

    def get_photo(self, administrator):
        request = self.context.get("request")
        if  administrator.photo:
            url = administrator.photo.url
            return request.build_absolute_uri(url)

    class Meta:
        model = Administrator
        exclude = [
            "created_at",
            "password",
            "is_staff",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administrator
        fields = [
            "id",
            "fullname",
            "title",
            "password",
            "photo",
            "email_address",
            "is_active",
        ]
        extra_kwargs = {
            "password": {
                "write_only": True,
            },
            "id": {
                "read_only": True,
            },
            "title": {
                "required": False,
                "allow_blank": True,
            },
            "is_active": {
                "required": False,
            },
        }

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Administrator.objects.create_user(
            password=password,
            is_staff=True,
            **validated_data,
        )


class LoginSerializer(serializers.Serializer):
    email_address = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active and user.is_staff:
            return user
        raise serializers.ValidationError("Incorrect Credentials")


class ChangeAdministratorPasswordSerializer(serializers.Serializer):
    email_address = serializers.EmailField()
    old_password = serializers.CharField(
        required=False,
        allow_blank=True,
        trim_whitespace=False,
        write_only=True,
    )
    new_password = serializers.CharField(
        trim_whitespace=False,
        write_only=True,
    )

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return value
