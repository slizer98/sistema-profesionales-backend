# apps/core/models.py
from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta
import secrets
import uuid
class Workspace(models.Model):
    NICHE_DOCTOR = "doctor"
    NICHE_DENTIST = "dentist"
    NICHE_LAWYER = "lawyer"
    NICHE_PSYCHOLOGIST = "psychologist"
    NICHE_COACH = "coach"
    NICHE_OTHER = "other"

    NICHE_CHOICES = [
        (NICHE_DOCTOR, "Médico general"),
        (NICHE_DENTIST, "Dentista"),
        (NICHE_LAWYER, "Abogado"),
        (NICHE_PSYCHOLOGIST, "Psicólogo"),
        (NICHE_COACH, "Coach"),
        (NICHE_OTHER, "Otro"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_workspaces",
    )
    name = models.CharField("Nombre del negocio", max_length=150)
    slug = models.SlugField("Slug público", unique=True)
    niche = models.CharField(
        "Nich(o)",
        max_length=30,
        choices=NICHE_CHOICES,
        default=NICHE_OTHER,
    )

    # Personalización / tema
    logo = models.ImageField(
        "Logo",
        upload_to="workspaces/logos/",
        blank=True,
        null=True,
    )
    primary_color = models.CharField(
        "Color primario",
        max_length=7,
        default="#2563eb",  # azul tipo Tailwind blue-600
    )
    secondary_color = models.CharField(
        "Color secundario",
        max_length=7,
        default="#0f172a",
    )
    accent_color = models.CharField(
        "Color acento",
        max_length=7,
        default="#22c55e",
    )
    theme_mode = models.CharField(
        "Modo de tema",
        max_length=10,
        choices=[("light", "Claro"), ("dark", "Oscuro")],
        default="light",
    )
    theme_name = models.CharField(
        "Nombre del tema",
        max_length=50,
        default="light",
        help_text="Nombre del tema DaisyUI/Tailwind (light, dark, corporate, etc.)",
    )
    enable_video_calls = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"

    def __str__(self):
        return self.name


class WorkspaceMember(models.Model):
    ROLE_OWNER = "owner"
    ROLE_PROFESSIONAL = "professional"
    ROLE_ASSISTANT = "assistant"
    ROLE_CLIENT = "client"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Dueño"),
        (ROLE_PROFESSIONAL, "Profesional"),
        (ROLE_ASSISTANT, "Asistente / staff"),
        (ROLE_CLIENT, "Cliente / paciente"),
    ]

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField("Rol en el workspace", max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("workspace", "user")
        verbose_name = "Miembro de workspace"
        verbose_name_plural = "Miembros de workspace"

    def __str__(self):
        return f"{self.user} @ {self.workspace} ({self.role})"


class Client(models.Model):
    """
    Cliente/paciente del profesional.
    Puede o no tener usuario con login.
    """
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="clients",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_profile",
        help_text="Usuario con acceso al portal (opcional)",
    )

    full_name = models.CharField("Nombre completo", max_length=150)
    email = models.EmailField("Correo", blank=True)
    phone = models.CharField("Teléfono", max_length=20, blank=True)
    document_id = models.CharField(
        "ID / documento (RFC, CURP, etc.)",
        max_length=50,
        blank=True,
    )
    portal_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="portal_client_profiles",
        null=True,
        blank=True,
        help_text="Usuario que usa el portal de cliente",
    )
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    notes = models.TextField("Notas internas", blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.full_name


class ClientInvitation(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="client_invitations",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField(blank=True, null=True)
    token = models.CharField(
        max_length=64,
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return self.is_active and self.expires_at >= timezone.now()

class Service(models.Model):
    """
    Servicios que ofrece el profesional:
    - Consulta general
    - Limpieza dental
    - Asesoría legal, etc.
    """
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="services",
    )
    name = models.CharField("Nombre", max_length=150)
    description = models.TextField("Descripción", blank=True)
    default_duration_minutes = models.PositiveIntegerField(
        "Duración por defecto (minutos)",
        default=30,
    )
    price = models.DecimalField(
        "Precio",
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"

    def __str__(self):
        return self.name


class Appointment(models.Model):
    STATUS_SCHEDULED = "scheduled"
    STATUS_CONFIRMED = "confirmed"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_NO_SHOW = "no_show"

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, "Programada"),
        (STATUS_CONFIRMED, "Confirmada"),
        (STATUS_COMPLETED, "Completada"),
        (STATUS_CANCELLED, "Cancelada"),
        (STATUS_NO_SHOW, "No se presentó"),
    ]

    MODALITY_PRESENTIAL = "presential"
    MODALITY_ONLINE = "online"

    MODALITY_CHOICES = [
        (MODALITY_PRESENTIAL, "Presencial"),
        (MODALITY_ONLINE, "Online"),
    ]

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments_as_professional",
    )

    start = models.DateTimeField("Inicio")
    end = models.DateTimeField("Fin")

    status = models.CharField(
        "Estado",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
    )
    modality = models.CharField(
        "Modalidad",
        max_length=20,
        choices=MODALITY_CHOICES,
        default=MODALITY_PRESENTIAL,
    )

    notes_internal = models.TextField("Notas internas", blank=True)
    notes_for_client = models.TextField("Notas visibles para cliente", blank=True)
    video_room = models.UUIDField(default=uuid.uuid4, null=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def video_url(self):
        base = getattr(settings, "JITSI_BASE_URL", "https://meet.digitark.cloud").rstrip("/")
        return f"{base}/{self.video_room}"

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"

    def __str__(self):
        return f"{self.client} - {self.service} ({self.start})"


class AppointmentVideo(models.Model):
    appointment = models.OneToOneField("core.Appointment", on_delete=models.CASCADE, related_name="video")
    room_name = models.CharField(max_length=120, unique=True)
    room_passcode = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def gen_room(appointment):
        # room no adivinable
        return f"ws{appointment.workspace_id}-ap{appointment.id}-{secrets.token_urlsafe(10)}".replace("-", "")

    @staticmethod
    def gen_pass():
        return secrets.token_urlsafe(12)


class Consultation(models.Model):
    """
    Nota de consulta / sesión.
    'extra_data' se usará para campos dinámicos según el nicho.
    """
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="consultations",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="consultations",
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="consultations_as_professional",
    )
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultation",
    )

    title = models.CharField("Título", max_length=150, blank=True)
    notes = models.TextField("Notas de la consulta", blank=True)

    # Aquí metemos datos clínicos/legales según nicho (JSON)
    extra_data = models.JSONField(
        "Datos extra (dinámicos)",
        default=dict,
        blank=True,
        help_text="Campos dinámicos según el nicho (ej. signos vitales, juzgado, etc.)",
    )

    visible_to_client = models.BooleanField(
        "Visible para el cliente",
        default=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"

    def __str__(self):
        return self.title or f"Consulta de {self.client} ({self.created_at.date()})"


class CaseFile(models.Model):
    STATUS_OPEN = "open"
    STATUS_ON_HOLD = "on_hold"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Abierto"),
        (STATUS_ON_HOLD, "En pausa"),
        (STATUS_CLOSED, "Cerrado"),
    ]

    workspace = models.ForeignKey("core.Workspace", on_delete=models.CASCADE, related_name="casefiles")
    client = models.ForeignKey("core.Client", on_delete=models.CASCADE, related_name="casefiles")

    title = models.CharField(max_length=180, blank=True)  # "Expediente general", "Caso Laboral", etc.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)

    is_primary = models.BooleanField(default=True)  # para que todos tengan uno "principal"
    tags = models.JSONField(default=list, blank=True)  # etiquetas simples
    extra_data = models.JSONField(default=dict, blank=True)  # datos dinámicos por nicho

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "client", "status"]),
        ]

    def __str__(self):
        return self.title or f"Expediente {self.client.full_name}"
    

class CaseEvent(models.Model):
    TYPE_NOTE = "note"
    TYPE_CALL = "call"
    TYPE_VISIT = "visit"
    TYPE_APPOINTMENT = "appointment"
    TYPE_DOCUMENT = "document"
    TYPE_STATUS = "status"
    TYPE_PAYMENT = "payment"
    TYPE_OTHER = "other"

    TYPE_CHOICES = [
        (TYPE_NOTE, "Nota"),
        (TYPE_CALL, "Llamada"),
        (TYPE_VISIT, "Visita"),
        (TYPE_APPOINTMENT, "Cita"),
        (TYPE_DOCUMENT, "Documento"),
        (TYPE_STATUS, "Cambio de estado"),
        (TYPE_PAYMENT, "Pago"),
        (TYPE_OTHER, "Otro"),
    ]

    workspace = models.ForeignKey("core.Workspace", on_delete=models.CASCADE, related_name="caseevents")
    casefile = models.ForeignKey(CaseFile, on_delete=models.CASCADE, related_name="events")

    # opcional: liga a entidades existentes
    appointment = models.ForeignKey("core.Appointment", on_delete=models.SET_NULL, null=True, blank=True)
    consultation = models.ForeignKey("core.Consultation", on_delete=models.SET_NULL, null=True, blank=True)

    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_NOTE)
    title = models.CharField(max_length=180, blank=True)
    body = models.TextField(blank=True)

    # Para seguimiento: fecha del evento (no siempre coincide con created_at)
    happened_at = models.DateTimeField()

    # visibilidad para cliente
    visible_to_client = models.BooleanField(default=True)

    # trazabilidad
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_caseevents")
    created_at = models.DateTimeField(auto_now_add=True)

    # datos extra (recetas, juzgado, signos vitales, etc.)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-happened_at", "-id"]
        indexes = [
            models.Index(fields=["workspace", "casefile", "happened_at"]),
            models.Index(fields=["workspace", "event_type", "happened_at"]),
        ]

    def __str__(self):
        return self.title or f"{self.get_event_type_display()} - {self.happened_at.date()}" 
    


def case_attachment_upload_to(instance, filename):
    return f"casefiles/{instance.workspace_id}/{instance.casefile_id}/{instance.event_id}/{filename}"

class CaseAttachment(models.Model):
    workspace = models.ForeignKey("core.Workspace", on_delete=models.CASCADE, related_name="caseattachments")
    casefile = models.ForeignKey(CaseFile, on_delete=models.CASCADE, related_name="attachments")
    event = models.ForeignKey(CaseEvent, on_delete=models.CASCADE, related_name="attachments")

    file = models.FileField(upload_to=case_attachment_upload_to)
    original_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    size_bytes = models.BigIntegerField(default=0)

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="uploaded_caseattachments")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    is_private = models.BooleanField(default=False)  

    def __str__(self):
        return self.original_name or self.file.name