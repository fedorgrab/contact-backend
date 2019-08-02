from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from rom import util


class ContactGameAppsConfig(AppConfig):
    name = "contact.game"
    label = "game"
    verbose_name = _("Game")

    def ready(self):
        util.set_connection_settings(host="localhost", port=6379)
