# core/views.py
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, ValidationError
from .models import Workspace, Client, Service, Appointment, Consultation, ClientInvitation
from .serializers import (
    WorkspaceSerializer,
    ClientSerializer,
    ServiceSerializer,
    AppointmentSerializer,
    ConsultationSerializer,
    ClientInvitationSerializer
)
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User  # ajusta el import si tu app de usuario está en otro lado
User = get_user_model()


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
    
    @action(detail=True, methods=["post"], url_path="invite")
    def invite(self, request, pk=None):
        client = self.get_object()
        workspace = client.workspace

        invitation = ClientInvitation.objects.create(
            workspace=workspace,
            client=client,
            email=client.email or None,
        )

        frontend_base = settings.FRONTEND_URL  
        invite_url = f"{frontend_base}/portal/{workspace.slug}/invite/{invitation.token}"

        serializer = ClientInvitationSerializer(invitation)
        data = serializer.data
        data["invite_url"] = invite_url

        return Response(data, status=status.HTTP_201_CREATED)


class ClientInvitationVerifyView(APIView):
    permission_classes = []  # pública

    def get(self, request, token):
        try:
            inv = ClientInvitation.objects.select_related("workspace", "client").get(token=token)
        except ClientInvitation.DoesNotExist:
            raise NotFound("Invitación no encontrada.")

        if not inv.is_valid:
            raise ValidationError("La invitación ha expirado o ya no es válida.")

        workspace_serializer = WorkspaceSerializer(
            inv.workspace,
            context={"request": request},
        )
        client_serializer = ClientSerializer(inv.client)

        return Response(
            {
                "workspace": workspace_serializer.data,
                "client": client_serializer.data,
            }
        )


class ClientInvitationAcceptView(APIView):
    """
    POST /api/client-portal/invitations/<token>/accept/
    Body: { email, password, password_confirm }
    Crea/actualiza usuario del cliente, vincula Client.portal_user y devuelve tokens.
    """

    permission_classes = []  # pública, protegida solo por token de invitación

    def post(self, request, token):
        try:
            inv = ClientInvitation.objects.select_related("workspace", "client").get(token=token)
        except ClientInvitation.DoesNotExist:
            raise NotFound("Invitación no encontrada.")

        if not inv.is_valid:
            raise ValidationError("La invitación ha expirado o ya no es válida.")

        email = request.data.get("email") or inv.client.email
        password = request.data.get("password")
        password_confirm = request.data.get("password_confirm")

        if not email or not password:
            raise ValidationError("Correo y contraseña son obligatorios.")

        if password != password_confirm:
            raise ValidationError("Las contraseñas no coinciden.")

        # Buscar o crear usuario por email (sin 'username', tu modelo no lo tiene)
        user, created = User.objects.get_or_create(email=email)

        # Opcional: si tu User tiene full_name, lo rellenamos
        client = inv.client
        if created and hasattr(user, "full_name") and client.full_name:
            user.full_name = client.full_name

        user.set_password(password)
        user.save()

        client.portal_user = user
        if not client.email:
            client.email = email
        client.save(update_fields=["portal_user", "email"])

        # Marcar invitación como usada
        inv.accepted_at = timezone.now()
        inv.is_active = False
        inv.save(update_fields=["accepted_at", "is_active"])

        # Generar tokens JWT para el cliente
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        workspace_serializer = WorkspaceSerializer(
            inv.workspace,
            context={"request": request},
        )
        client_serializer = ClientSerializer(client)

        return Response(
            {
                "access": str(access),
                "refresh": str(refresh),
                "client": client_serializer.data,
                "workspace": workspace_serializer.data,
            },
            status=status.HTTP_200_OK,
        )



class ClientPortalMeView(APIView):
    """
    GET /api/client-portal/me/
    Devuelve client + workspace para el usuario autenticado (cliente).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        client = (
            Client.objects.select_related("workspace")
            .filter(portal_user=user)
            .first()
        )
        if not client:
            raise NotFound("No se encontró un cliente asociado a este usuario.")

        workspace = client.workspace

        workspace_serializer = WorkspaceSerializer(
            workspace,
            context={"request": request},
        )
        client_serializer = ClientSerializer(client)

        return Response(
            {
                "client": client_serializer.data,
                "workspace": workspace_serializer.data,
            }
        )



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
