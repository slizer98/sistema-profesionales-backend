# core/views.py
from django.conf import settings
from rest_framework import status
from datetime import timedelta
from django.db.models import Count
from rest_framework.decorators import action
from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, ValidationError
from .models import Workspace, Client, Service, Appointment, Consultation, ClientInvitation, CaseFile, CaseEvent, CaseAttachment
from .serializers import (
    WorkspaceSerializer,
    ClientSerializer,
    ServiceSerializer,
    AppointmentSerializer,
    ConsultationSerializer,
    ClientInvitationSerializer,
    ClientPortalAppointmentSerializer,
    ClientPortalConsultationSerializer,
    CaseFileSerializer, CaseEventSerializer, CaseAttachmentSerializer, ClientPortalCaseFileSerializer, ClientPortalCaseEventSerializer
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


def get_portal_clients_for_user(user, workspace_slug=None):
    qs = Client.objects.select_related("workspace").filter(
        portal_user=user,
        is_active=True,
    )
    if workspace_slug:
        qs = qs.filter(workspace__slug=workspace_slug)
    return qs

def get_allowed_workspaces_for_user(user):
    return Workspace.objects.filter(Q(owner=user) | Q(memberships__user=user)).distinct()


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

        email = (serializer.validated_data.get("email") or "").strip()
        if email:
            exists = Client.objects.filter(workspace=workspace, email__iexact=email).exists()
            if exists:
                raise ValidationError({"email": "Ya existe un cliente con este correo en este workspace."})

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

        email = (request.data.get("email") or inv.client.email or "").strip().lower()
        password = request.data.get("password")
        password_confirm = request.data.get("password_confirm")

        if not email or not password:
            raise ValidationError("Correo y contraseña son obligatorios.")

        if password != password_confirm:
            raise ValidationError("Las contraseñas no coinciden.")

        # Buscar o crear usuario por email (sin 'username', tu modelo no lo tiene)
        user = User.objects.filter(email__iexact=email).first()
        created = False
        if not user:
            user = User(email=email)
            created = True

        client = inv.client

        if created:
            # Opcional: si tu User tiene full_name, lo rellenamos
            if hasattr(user, "full_name") and client.full_name:
                user.full_name = client.full_name
            user.set_password(password)
            user.save()
        else:
            if not user.check_password(password):
                raise ValidationError(
                    "El correo ya está registrado. Usa la contraseña existente."
                )

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
        clients = list(get_portal_clients_for_user(user))
        if not clients:
            raise NotFound("No se encontró un cliente asociado a este usuario.")

        entries = []
        for c in clients:
            entries.append({
                "workspace": WorkspaceSerializer(c.workspace, context={"request": request}).data,
                "client": ClientSerializer(c).data,
            })

        return Response({"entries": entries})



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

        validated = serializer.validated_data
        professional = validated.get("professional") or self.request.user
        service = validated.get("service")
        start = validated["start"]
        end = validated.get("end")

        # Si no mandan 'end', lo calculamos
        if end is None:
            minutes = 30
            if service and service.default_duration_minutes:
                minutes = service.default_duration_minutes
            end = start + timedelta(minutes=minutes)

        serializer.save(
            workspace=workspace,
            professional=professional,
            end=end,
        )

class ClientPortalAppointmentsView(APIView):
    """
    GET /api/client-portal/appointments/
    Devuelve las citas del cliente autenticado (portal_user).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        workspace_slug = request.query_params.get("workspace_slug")
        clients = list(get_portal_clients_for_user(user, workspace_slug=workspace_slug))
        if not clients:
            raise NotFound("No se encontró un cliente asociado a este usuario.")

        qs = (
            Appointment.objects
            .filter(client__in=clients)
            .select_related("service")
            .order_by("start")
        )

        serializer = ClientPortalAppointmentSerializer(qs, many=True)
        return Response(serializer.data)


class ClientPortalConsultationsView(APIView):
    """
    GET /api/client-portal/consultations/
    Devuelve las consultas visibles para el cliente autenticado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        workspace_slug = request.query_params.get("workspace_slug")
        clients = list(get_portal_clients_for_user(user, workspace_slug=workspace_slug))
        if not clients:
            raise NotFound("No se encontró un cliente asociado a este usuario.")

        qs = (
            Consultation.objects
            .filter(client__in=clients, visible_to_client=True)
            .order_by("-created_at")
        )

        serializer = ClientPortalConsultationSerializer(qs, many=True)
        return Response(serializer.data)

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


class CaseFileViewSet(viewsets.ModelViewSet):
    serializer_class = CaseFileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = CaseFile.objects.filter(
            workspace__in=get_allowed_workspaces_for_user(user)
        ).select_related("client").annotate(events_count=Count("events")).distinct()

        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)

        return qs.order_by("-opened_at", "-id")

    def perform_create(self, serializer):
        workspace = get_current_workspace_for_user(self.request.user)
        if not workspace:
            raise NotFound("No hay workspace asociado al usuario.")

        client = serializer.validated_data.get("client")
        if not client or client.workspace_id != workspace.id:
            raise ValidationError({"client": "El cliente no pertenece al workspace actual."})

        serializer.save(workspace=workspace)


class CaseEventViewSet(viewsets.ModelViewSet):
    serializer_class = CaseEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        user = self.request.user
        qs = CaseEvent.objects.filter(
            workspace__in=get_allowed_workspaces_for_user(user)
        ).select_related("casefile", "appointment", "consultation").prefetch_related("attachments").distinct()

        casefile_id = self.request.query_params.get("casefile")
        if casefile_id:
            qs = qs.filter(casefile_id=casefile_id)

        return qs.order_by("-happened_at", "-id")

    def perform_create(self, serializer):
        workspace = get_current_workspace_for_user(self.request.user)
        if not workspace:
            raise NotFound("No hay workspace asociado al usuario.")

        casefile = serializer.validated_data.get("casefile")
        if not casefile or casefile.workspace_id != workspace.id:
            raise ValidationError({"casefile": "El expediente no pertenece al workspace actual."})

        happened_at = serializer.validated_data.get("happened_at")
        if not happened_at:
            happened_at = timezone.now()

        serializer.save(
            workspace=workspace,
            created_by=self.request.user,
            happened_at=happened_at,
        )

    @action(detail=True, methods=["post"], url_path="attachments")
    def upload_attachments(self, request, pk=None):
        """
        POST /api/caseevents/<id>/attachments/
        FormData:
          - file: <File>  (uno)
          - o files: <File[]> (multiples)
          - is_private: true/false (opcional, default false)
        """
        event = self.get_object()
        workspace = event.workspace

        is_private = str(request.data.get("is_private", "false")).lower() in ["1", "true", "yes", "y"]

        files = []
        if "files" in request.FILES:
            files = request.FILES.getlist("files")
        elif "file" in request.FILES:
            files = [request.FILES["file"]]

        if not files:
            raise ValidationError({"file": "Debes enviar 'file' o 'files' en multipart/form-data."})

        created = []
        for f in files:
            att = CaseAttachment.objects.create(
                workspace=workspace,
                casefile=event.casefile,
                event=event,
                file=f,
                original_name=getattr(f, "name", "") or "",
                mime_type=getattr(f, "content_type", "") or "",
                size_bytes=getattr(f, "size", 0) or 0,
                uploaded_by=request.user,
                is_private=is_private,
            )
            created.append(att)

        ser = CaseAttachmentSerializer(created, many=True, context={"request": request})
        return Response(ser.data, status=status.HTTP_201_CREATED)


class CaseAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = CaseAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [FormParser, MultiPartParser]

    def get_queryset(self):
        user = self.request.user
        return CaseAttachment.objects.filter(
            workspace__in=get_allowed_workspaces_for_user(user)
        ).select_related("casefile", "event").distinct()

    def perform_create(self, serializer):
        # Recomiendo CREAR por el action de CaseEventViewSet para mantener coherencia.
        raise ValidationError("Usa /caseevents/<id>/attachments/ para subir archivos.")

class ClientPortalCaseFilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        workspace_slug = request.query_params.get("workspace_slug")
        clients = list(get_portal_clients_for_user(user, workspace_slug=workspace_slug))
        if not clients:
            raise NotFound("No se encontró un cliente asociado a este usuario.")

        qs = CaseFile.objects.filter(client__in=clients).order_by("-opened_at", "-id")
        ser = ClientPortalCaseFileSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)


class ClientPortalCaseFileEventsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, casefile_id):
        user = request.user
        workspace_slug = request.query_params.get("workspace_slug")
        clients = list(get_portal_clients_for_user(user, workspace_slug=workspace_slug))
        if not clients:
            raise NotFound("No se encontró un cliente asociado a este usuario.")

        casefile = CaseFile.objects.filter(id=casefile_id, client__in=clients).first()
        if not casefile:
            raise NotFound("Expediente no encontrado para este cliente/workspace.")

        qs = (
            CaseEvent.objects
            .filter(casefile=casefile, visible_to_client=True)
            .prefetch_related("attachments")
            .order_by("-happened_at", "-id")
        )

        ser = ClientPortalCaseEventSerializer(qs, many=True, context={"request": request})
        return Response(ser.data)
