# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WorkspaceViewSet,
    ClientViewSet,
    ServiceViewSet,
    AppointmentViewSet,
    ConsultationViewSet,
    MyWorkspaceView,
    ClientInvitationVerifyView,
    ClientInvitationAcceptView,   
    ClientPortalMeView,    
)

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"appointments", AppointmentViewSet, basename="appointment")
router.register(r"consultations", ConsultationViewSet, basename="consultation")

urlpatterns = [
    path("me/workspace/", MyWorkspaceView.as_view(), name="my-workspace"),
    # urls.py
    path("client-portal/invitations/<str:token>/", ClientInvitationVerifyView.as_view()),
    path("", include(router.urls)),
    path("client-portal/invitations/<str:token>/accept/", ClientInvitationAcceptView.as_view(), name="client-portal-invitation-accept"),
    path("client-portal/me/",ClientPortalMeView.as_view(), name="client-portal-me"),
]
