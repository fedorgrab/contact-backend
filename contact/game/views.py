from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from contact.game import game_manager


class GetRoomAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        room = game_manager.get_free_room()
        return Response({"ws_route": f"/ws/room/{room.id}"})
