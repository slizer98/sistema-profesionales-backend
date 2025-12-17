from django.urls import path
from .views import MeView, RegisterProfessionalView

urlpatterns = [
    path("me/", MeView.as_view(), name="users-me"),
    path("register/professional/", RegisterProfessionalView.as_view(), name="register-professional"),
]
