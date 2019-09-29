from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from contact.game.consumers import ContactGameWSConsumer

application = ProtocolTypeRouter(
    {
        "websocket": AuthMiddlewareStack(
            URLRouter([path("ws/contact-game", ContactGameWSConsumer)])
        )
    }
)
