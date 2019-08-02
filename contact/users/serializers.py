from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


def validate_password(value):
    regex_validate = RegexValidator(
        regex=r"^(?=.*\d).{8,}",
        message=_("Invalid password: it should have numeric symbols"),
    )
    return regex_validate(value)


class SignInSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        required=True, min_length=8, validators=[validate_password]
    )
