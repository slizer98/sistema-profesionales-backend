# core/views.py
from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .models import Workspace, Client, Service, Appointment, Consultation
from .serializers import (
    WorkspaceSerializer,
    ClientSerializer,
    ServiceSerializer,
    AppointmentSerializer,
    ConsultationSerializer,
)
from users.models import User  # ajusta el import si tu app de usuario está en otro lado


def get_current_workspace_for_user(user):
    """
    Regresa el primer workspace asociado al usuario (owner o miembro).
    Para MVP está bien así; luego podemos manejar selección explícita.
    """
    qs = Workspace.objects.filter(
        Q(owner=user) | Q(memberships__user=user)
    ).distinct()

    return qs.first()


class WorkspaceViewSet(viewsets.ModelViewSet):
    """
    CRUD de workspaces.
    Normalmente el pro solo verá/editará el suyo.
    """
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser] 

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser or getattr(user, "role", None) == User.ROLE_SYSTEM_ADMIN:
            return Workspace.objects.all()

        return Workspace.objects.filter(
            Q(owner=user) | Q(memberships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        if not (user.is_superuser or getattr(user, "role", None) in [User.ROLE_SYSTEM_ADMIN, User.ROLE_PROFESSIONAL]):
            raise PermissionDenied("No tiene permisos para crear workspaces.")

        workspace = serializer.save(owner=user)
        from .models import WorkspaceMember
        WorkspaceMember.objects.get_or_create(
            workspace=workspace,
            user=user,
            defaults={"role": WorkspaceMember.ROLE_OWNER},
        )


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Client.objects.filter(
            workspace__in=Workspace.objects.filter(
                Q(owner=user) | Q(memberships__user=user)
            )
        ).distinct()

    def perform_create(self, serializer):
        workspace = get_current_workspace_for_user(self.request.user)
        if not workspace:
            raise NotFound("No hay workspace asociado al usuario.")
        serializer.save(workspace=workspace)



class ServiceViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Service.objects.filter(
            workspace__in=Workspace.objects.filter(
                Q(owner=user) | Q(memberships__user=user)
            )
        ).distinct()

    def perform_create(self, serializer):
        workspace = get_current_workspace_for_user(self.request.user)
        if not workspace:
            raise NotFound("No hay workspace asociado al usuario.")
        serializer.save(workspace=workspace)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Appointment.objects.filter(
            workspace__in=Workspace.objects.filter(
                Q(owner=user) | Q(memberships__user=user)
            )
        ).select_related("client", "service").distinct()

    def perform_create(self, serializer):
        workspace = get_current_workspace_for_user(self.request.user)
        if not workspace:
            raise NotFound("No hay workspace asociado al usuario.")
        # Si no mandan professional, asignar el usuario actual
        professional = serializer.validated_data.get("professional") or self.request.user
        serializer.save(workspace=workspace, professional=professional)


class ConsultationViewSet(viewsets.ModelViewSet):
    serializer_class = ConsultationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Consultation.objects.filter(
            workspace__in=Workspace.objects.filter(
                Q(owner=user) | Q(memberships__user=user)
            )
        ).select_related("client").distinct()

    def perform_create(self, serializer):
        workspace = get_current_workspace_for_user(self.request.user)
        if not workspace:
            raise NotFound("No hay workspace asociado al usuario.")
        professional = serializer.validated_data.get("professional") or self.request.user
        serializer.save(workspace=workspace, professional=professional)


class MyWorkspaceView(APIView):
    """
    Endpoint para que el frontend (Vue) obtenga el tema del profesional.
    GET /api/me/workspace/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        workspace = get_current_workspace_for_user(request.user)
        if not workspace:
            raise NotFound("No hay workspace asociado a este usuario.")
        serializer = WorkspaceSerializer(
            workspace,
            context={"request": request},
        )
        return Response(serializer.data)
