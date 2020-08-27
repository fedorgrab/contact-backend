from django.urls import path

from contact.users import views

urlpatterns = [
    path("", views.UserProfileAPIView.as_view(), name="user"),
    path("sign-in", views.SignInAPIView.as_view(), name="sign-in"),
    path(
        "sign-in-with-token",
        views.SingInWithCookiesAPIView.as_view(),
        name="sign-in-with-token",
    ),
    path("sign-up", views.SignUpAPIView.as_view(), name="sign-up"),
]
