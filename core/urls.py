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
)

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"appointments", AppointmentViewSet, basename="appointment")
router.register(r"consultations", ConsultationViewSet, basename="consultation")

urlpatterns = [
    path("me/workspace/", MyWorkspaceView.as_view(), name="my-workspace"),
    path("", include(router.urls)),
]
