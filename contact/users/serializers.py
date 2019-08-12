from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()


def validate_password(value):
    regex_validate = RegexValidator(
        regex=r"^(?=.*\d).{8,}",
        message=_("Invalid password: it should have numeric symbols"),
    )
    return regex_validate(value)


class AuthSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    password = serializers.CharField(
        required=True,
        min_length=8,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ("username", "password")

    def create(self, validated_data):
        return User.objects.create(**validated_data)
