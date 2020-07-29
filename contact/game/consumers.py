import asyncio
import time
from typing import Any, Callable, Dict, Optional

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from contact.game.constants import GameEvent
from contact.game.exceptions import GameException
from contact.game.game_manager import GameManager, GameManagerDelegate

JSON = Dict[str, Any]


class ContactGameWSConsumer(GameManagerDelegate, AsyncJsonWebsocketConsumer):
    game_manager: GameManager

    @property
    def room_id(self):
        return getattr(self, "_room_id")

    # Connection life cycle #
    async def connect(self):
        self.game_manager = GameManager(user=self.scope["user"], delegate=self)
        room = self.game_manager.append_user_to_game()
        setattr(self, "_room_id", room.id_key)

        await self.channel_layer.group_add(
            group=self.room_id, channel=self.channel_name
        )
        await self.accept()

        initial_content = self.compose_game_message(
            data=self.game_manager.initial_information,
            event=self.game_manager.initial_event,
        )

        if self.game_manager.restored:
            await self.send_json(content=initial_content)
        else:
            await self.group_send(initial_content)

    async def disconnect(self, close_code):
        print(close_code)

    # Communication #
    # Send:
    async def send_json_type(self, content: JSON, close=False):
        await self.send_json(content["data"], close=close)

    async def group_send(self, data: JSON):
        await self.channel_layer.group_send(
            group=self.room_id, message={"type": "send_json_type", "data": data}
        )

    async def group_send_delayed(
        self, after: int, callback: Callable, callback_kwargs: Dict
    ):
        """
        :param after: Time after which message should be sent
        :param callback: Function returning data which should be sent
        :param callback_kwargs: Callback keyword arguments
        :return: none
        """
        print(f"Delayed message is executing. Will be done in {after} seconds")
        now = time.time()

        await asyncio.sleep(after)
        response_data = await callback(**callback_kwargs)

        after_t = time.time()
        print(f"Delay is done. It consumed {after_t - now}")

        if response_data:
            await self.group_send(response_data)

    # process:
    @staticmethod
    def compose_game_message(data: JSON, event: GameEvent) -> JSON:
        return {"data": data, "event": event.value}

    @staticmethod
    def compose_error_message(data: JSON, event: GameEvent) -> JSON:
        return {"error": True, "data": data, "event": event.value}

    async def handle_game_action(
        self, event: str, game_data: Optional[JSON] = None
    ) -> Optional[Dict]:
        if game_data is None:
            game_data = {}
        game_event = GameEvent(event)

        try:
            response_data = self.game_manager.perform_game_action(game_event, game_data)
        except GameException as game_error:
            await self.send_json(
                content=self.compose_error_message(game_error.data, game_event)
            )
        else:
            return self.compose_game_message(data=response_data, event=game_event)

    # receive:
    async def receive_json(self, content: JSON, **kwargs):
        event, game_data = content["event"], content["data"]
        response_data = await self.handle_game_action(event, game_data)

        if response_data:
            await self.group_send(response_data)

    # Game Manager Delegate #
    def order_delayed_action(self, after: int, event: GameEvent, action_kwargs=None):
        action_kwargs = action_kwargs or {}
        asyncio.create_task(
            self.group_send_delayed(
                after=after,
                callback=self.handle_game_action,
                callback_kwargs={"event": event, **action_kwargs},
            )
        )
