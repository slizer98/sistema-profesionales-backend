from django.urls import path
from .views import MeView, RegisterProfessionalView, PasswordResetTestView

urlpatterns = [
    path("me/", MeView.as_view(), name="users-me"),
    path("register/professional/", RegisterProfessionalView.as_view(), name="register-professional"),
    path("password-reset/test/", PasswordResetTestView.as_view(), name="password-reset-test"),
]
