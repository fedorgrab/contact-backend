from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from contact.game.game_manager import GameManager


class GetRoomAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        room = GameManager.get_free_room()
        return Response({"ws_route": f"/ws/contact-game/{room.id}"})
