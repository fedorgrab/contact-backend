from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.sessions.models import Session
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contact.users import serializers


class SignInAPIView(GenericAPIView):
    serializer_class = serializers.SignInSerializer

    @staticmethod
    def login(request, username, password):
        user = authenticate(request=request, username=username, password=password)

        if not user:
            raise ValidationError({"username": ["Invalid credentials"]})

        login(request=request, user=user)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.login(request=request, **serializer.validated_data)
        return Response({"token": request.session.session_key})


class SingInWithCookiesAPIView(GenericAPIView):
    serializer_class = serializers.TokenAuthSerialized

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            session = Session.objects.get(
                session_key=serializer.validated_data["token"]
            )
        except Session.DoesNotExist:
            raise ValidationError({"token": "Session not found"})
        response = Response({"message": "success"})
        response.set_cookie(key=settings.SESSION_COOKIE_NAME, value=session.session_key)
        return response


class SignUpAPIView(GenericAPIView):
    serializer_class = serializers.SignUpSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request=request, user=user)
        return Response({"token": request.session.session_key})


class UserProfileAPIView(RetrieveAPIView):
    serializer_class = serializers.UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
