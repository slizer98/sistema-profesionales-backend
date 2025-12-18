# core/serializers.py
from rest_framework import serializers
from .models import Workspace, Client, Service, Appointment, Consultation, ClientInvitation


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
        ]
        read_only_fields = ["id", "workspace", "created_at"]


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
