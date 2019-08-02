from django.contrib.auth import authenticate, login
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .serializers import SignInSerializer


class SignInAPIView(GenericAPIView):
    serializer_class = SignInSerializer

    @staticmethod
    def login(request, username, password):
        user = authenticate(username=username, password=password)
        login(request=request, user=user)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.login(request=request, **serializer.validated_data)
        return Response(serializer.validated_data)
