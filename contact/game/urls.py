from django.urls import path

from .views import GetRoomAPIView

urlpatterns = [path("room", GetRoomAPIView.as_view(), name="room")]
