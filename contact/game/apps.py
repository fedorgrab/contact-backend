from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ContactGameAppsConfig(AppConfig):
    name = "contact.game"
    label = "game"
    verbose_name = _("Game")
