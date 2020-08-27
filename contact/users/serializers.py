from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()


def validate_password(value):
    regex_validate = RegexValidator(
        regex=r"^(?=.*\d).{8,}",
        message=_("Should have at least 8 symbols \nNumeric values are required"),
    )
    return regex_validate(value)


class SignUpSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True,
        min_length=8,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    email = serializers.EmailField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("username", "password", "email")

    def create(self, validated_data):
        try:
            return User.objects.create_user(**validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"username": "Username is already in used"}
            )


class SignInSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, style={"input_type": "password"})


class TokenAuthSerialized(serializers.Serializer):
    token = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username",)
