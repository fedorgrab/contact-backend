from django.urls import path

from contact.game.consumers import ContactGameWSConsumer

websocket_urlpatterns = [path("ws/contact-game", ContactGameWSConsumer)]
