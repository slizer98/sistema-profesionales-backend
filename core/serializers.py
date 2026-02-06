# core/serializers.py
from rest_framework import serializers
from .models import (Workspace, Client, Service, Appointment, Consultation, ClientInvitation, CaseFile, CaseEvent, CaseAttachment)


class WorkspaceSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "slug",
            "niche",
            "primary_color",
            "secondary_color",
            "accent_color",
            "theme_mode",
            "theme_name",
            "logo",
            "logo_url",
            "enable_video_calls",
        ]
        read_only_fields = ["id"]

    def get_logo_url(self, obj):
        request = self.context.get("request")
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return None


# core/serializers.py
class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "workspace",
            "user",
            "full_name",
            "email",
            "phone",
            "document_id",
            "birth_date",
            "notes",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "workspace", "created_at"]


class ClientInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientInvitation
        fields = ["id", "token", "expires_at", "accepted_at", "is_active"]


class ClientPortalMeSerializer(serializers.Serializer):
    client = ClientSerializer()
    workspace = WorkspaceSerializer()



class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            "id",
            "workspace",
            "name",
            "description",
            "default_duration_minutes",
            "price",
            "is_active",
        ]
        read_only_fields = ["id", "workspace"]


class ClientPortalConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = [
            "id",
            "title",
            "notes",
            "extra_data",
            "visible_to_client",
            "created_at",
        ]


class AppointmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "workspace",
            "client",
            "client_name",
            "service",
            "service_name",
            "professional",
            "start",
            "end",
            "status",
            "modality",
            "notes_internal",
            "notes_for_client",
            "created_at",
            "video_room",
            "video_url",
        ]
        read_only_fields = ["id", "workspace", "created_at",  "video_room", "video_url"]


class ClientPortalAppointmentSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)
    can_video = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id","start","end","status","modality","service_name","notes_for_client",
            "can_video","video_room", "video_url"
        ]

    def get_can_video(self, obj):
        return obj.modality == Appointment.MODALITY_ONLINE and getattr(obj.workspace, "enable_video_calls", False)


class ConsultationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)

    class Meta:
        model = Consultation
        fields = [
            "id",
            "workspace",
            "client",
            "client_name",
            "professional",
            "appointment",
            "title",
            "notes",
            "extra_data",
            "visible_to_client",
            "created_at",
        ]
        read_only_fields = ["id", "workspace", "created_at"]

# -----------------------------------------
# CASE ATTACHMENTS
# -----------------------------------------
class CaseAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CaseAttachment
        fields = [
            "id",
            "workspace",
            "casefile",
            "event",
            "file",
            "file_url",
            "original_name",
            "mime_type",
            "size_bytes",
            "uploaded_by",
            "uploaded_at",
            "is_private",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "original_name",
            "mime_type",
            "size_bytes",
            "uploaded_by",
            "uploaded_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


# -----------------------------------------
# CASE EVENTS
# -----------------------------------------
class CaseEventSerializer(serializers.ModelSerializer):
    attachments = CaseAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = CaseEvent
        fields = [
            "id",
            "workspace",
            "casefile",
            "appointment",
            "consultation",
            "event_type",
            "title",
            "body",
            "happened_at",
            "visible_to_client",
            "created_by",
            "created_at",
            "extra_data",
            "attachments",
        ]
        read_only_fields = ["id", "workspace", "created_by", "created_at", "attachments"]


# -----------------------------------------
# CASE FILES (EXPEDIENTES)
# -----------------------------------------
class CaseFileSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    events_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CaseFile
        fields = [
            "id",
            "workspace",
            "client",
            "client_name",
            "title",
            "status",
            "is_primary",
            "tags",
            "extra_data",
            "opened_at",
            "closed_at",
            "events_count",
        ]
        read_only_fields = ["id", "workspace", "opened_at", "events_count"]

    def validate_status(self, value):
        if value in (None, ""):
            return CaseFile.STATUS_OPEN  # default seguro

        v = str(value).strip()

        # Quita comillas si vienen “pegadas” (ej: '"active"' o "'active'")
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1].strip()

        # Compat con frontend viejo
        mapping = {
            "active": CaseFile.STATUS_OPEN,
            "paused": CaseFile.STATUS_ON_HOLD,
            "onhold": CaseFile.STATUS_ON_HOLD,
            "inactive": CaseFile.STATUS_CLOSED,
        }
        v = mapping.get(v, v)

        allowed = {CaseFile.STATUS_OPEN, CaseFile.STATUS_ON_HOLD, CaseFile.STATUS_CLOSED}
        if v not in allowed:
            raise serializers.ValidationError(
                f"Estado inválido. Usa: {', '.join(sorted(allowed))}."
            )
        return v


# -----------------------------------------
# CLIENT PORTAL (lectura)
# -----------------------------------------
class ClientPortalCaseFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseFile
        fields = [
            "id",
            "title",
            "status",
            "is_primary",
            "tags",
            "opened_at",
            "closed_at",
        ]


class ClientPortalCaseAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CaseAttachment
        fields = ["id", "original_name", "mime_type", "size_bytes", "uploaded_at", "file_url"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class ClientPortalCaseEventSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = CaseEvent
        fields = [
            "id",
            "event_type",
            "title",
            "body",
            "happened_at",
            "extra_data",
            "attachments",
        ]

    def get_attachments(self, obj):
        # Solo attachments NO privados en el portal
        qs = obj.attachments.filter(is_private=False).order_by("-uploaded_at")
        return ClientPortalCaseAttachmentSerializer(qs, many=True, context=self.context).data