from django.conf import settings
from django.conf.urls import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("game/", include("contact.game.urls")),
    path("api/users/", include("contact.users.urls")),
]

if settings.DEBUG:
    urlpatterns += static.static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
    urlpatterns += static.static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
