# apps/core/models.py
from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta


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
    portal_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="portal_client_profile",
        null=True,
        blank=True,
        help_text="Usuario que usa el portal de cliente"
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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"

    def __str__(self):
        return f"{self.client} - {self.service} ({self.start})"


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
