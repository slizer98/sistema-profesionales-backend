from rest_framework import serializers
from django.db import transaction
from .models import User
from core.models import Workspace, WorkspaceMember


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "date_joined"]


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
