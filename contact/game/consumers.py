import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from contact.game.constants import GameEvent
from contact.game.game_manager import GameManager, GameManagerDelegate


class ContactGameWSConsumer(GameManagerDelegate, AsyncWebsocketConsumer):
    game_manager: GameManager = None

    @property
    def room_id(self):
        return str(getattr(self, "_room_id"))

    async def connect(self):
        self.game_manager = GameManager(user=self.scope["user"], delegate=self)
        room = self.game_manager.append_user_to_game()
        setattr(self, "_room_id", room.id)

        await self.channel_layer.group_add(
            group=self.room_id, channel=self.channel_name
        )
        await self.accept()

        await self.send_room_initial_information(start_game_data_info=room.serialize())

    async def receive(self, text_data=None, bytes_data=None):
        data_json = json.loads(text_data)
        response_data = self.handle_game_action(event_data=data_json)
        await self.group_send(response_data)

    def handle_game_action(self, event_data):
        game_object_data = event_data["data"]
        event = GameEvent(event_data["event"])

        response_game_data = self.game_manager.perform_game_action(
            event, data=game_object_data
        )
        return {"data": response_game_data, "event": event.value}

    async def group_send(self, data):
        await self.channel_layer.group_send(
            group=self.room_id, message={"type": "send_game_message", "data": data}
        )

    async def send_game_message(self, message):
        await self.send(text_data=json.dumps(message["data"]))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_id, self.channel_name)
        sync_to_async(self.game_manager.remove_user_from_game())

    # Game Manager Interface implementation #
    async def contact_closure(self, contact_data):
        pass

    async def send_room_initial_information(self, start_game_data_info):
        if self.game_manager.game_is_started:
            await self.group_send(
                {"data": start_game_data_info, "event": GameEvent.START.value}
            )
