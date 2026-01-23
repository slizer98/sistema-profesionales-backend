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
    ClientPortalAppointmentsView,
    ClientPortalConsultationsView,
    CaseFileViewSet,
    CaseEventViewSet,
    CaseAttachmentViewSet,
    ClientPortalCaseFilesView,
    ClientPortalCaseFileEventsView,
)

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"services", ServiceViewSet, basename="service")
router.register(r"appointments", AppointmentViewSet, basename="appointment")
router.register(r"consultations", ConsultationViewSet, basename="consultation")
router.register(r"casefiles", CaseFileViewSet, basename="casefile")
router.register(r"caseevents", CaseEventViewSet, basename="caseevent")
router.register(r"caseattachments", CaseAttachmentViewSet, basename="caseattachment")


urlpatterns = [
    path("me/workspace/", MyWorkspaceView.as_view(), name="my-workspace"),
    # urls.py
    path("client-portal/invitations/<str:token>/", ClientInvitationVerifyView.as_view()),
    path("", include(router.urls)),
    path("client-portal/invitations/<str:token>/accept/", ClientInvitationAcceptView.as_view(), name="client-portal-invitation-accept"),
    path("client-portal/me/",ClientPortalMeView.as_view(), name="client-portal-me"),
    path("client-portal/appointments/",ClientPortalAppointmentsView.as_view(),name="client-portal-appointments"),
    path("client-portal/consultations/",ClientPortalConsultationsView.as_view(),name="client-portal-consultations"),
    path("client-portal/casefiles/", ClientPortalCaseFilesView.as_view(), name="client-portal-casefiles"),
    path("client-portal/casefiles/<int:casefile_id>/events/", ClientPortalCaseFileEventsView.as_view(), name="client-portal-casefile-events"),   
]
