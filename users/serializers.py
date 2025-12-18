from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import User
from core.models import Workspace, WorkspaceMember, Client

User = get_user_model()

class MeSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    workspace_slug = serializers.SerializerMethodField()
    workspace_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",    
            "role",
            "workspace_slug",
            "workspace_name",
        ]

    # 1) Rol "global" del usuario
    def get_role(self, obj):
        # Profesional si es owner o miembro de un workspace
        if Workspace.objects.filter(owner=obj).exists():
            return "professional"

        if WorkspaceMember.objects.filter(
            workspace__owner=obj
        ).exists():
            return "professional"

        # Cliente si está ligado como portal_user en Client
        if Client.objects.filter(portal_user=obj, is_active=True).exists():
            return "client"

        return "unknown"

    # 2) workspace_slug principal
    def get_workspace_slug(self, obj):
        # Profesional: primer workspace donde es owner o miembro
        ws = Workspace.objects.filter(owner=obj).first()
        if not ws:
            ws = Workspace.objects.filter(memberships__user=obj).first()
        if ws:
            return ws.slug

        # Cliente: workspace del cliente
        client = (
            Client.objects.select_related("workspace")
            .filter(portal_user=obj, is_active=True)
            .first()
        )
        if client and client.workspace:
            return client.workspace.slug

        return None

    # 3) nombre del workspace (solo para comodidad de front)
    def get_workspace_name(self, obj):
        ws_slug = self.get_workspace_slug(obj)
        if not ws_slug:
            return None
        ws = Workspace.objects.filter(slug=ws_slug).first()
        return ws.name if ws else None


class RegisterProfessionalSerializer(serializers.Serializer):
    # Datos de usuario
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    # Datos de workspace
    workspace_name = serializers.CharField(max_length=150)
    niche = serializers.ChoiceField(
        choices=Workspace.NICHE_CHOICES,
        default=Workspace.NICHE_OTHER,
    )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Las contraseñas no coinciden."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"]
        full_name = validated_data["full_name"]
        password = validated_data["password"]
        workspace_name = validated_data["workspace_name"]
        niche = validated_data["niche"]

        # Crear usuario profesional
        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            role=User.ROLE_PROFESSIONAL,
        )

        # Crear workspace
        from django.utils.text import slugify

        base_slug = slugify(workspace_name)
        slug = base_slug
        i = 1
        while Workspace.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{i}"
            i += 1

        workspace = Workspace.objects.create(
            owner=user,
            name=workspace_name,
            slug=slug,
            niche=niche,
        )

        # Crear membership como dueño
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role=WorkspaceMember.ROLE_OWNER,
        )

        return user
