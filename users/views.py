from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import MeSerializer, RegisterProfessionalSerializer, PasswordResetTestSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)


class MeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = MeSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class RegisterProfessionalView(APIView):
    """
    Registro de un profesional + creación de workspace.
    POST /api/users/register/professional/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterProfessionalSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            data = MeSerializer(user).data
            return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetTestView(APIView):
    """
    POST /api/users/password-reset/test/
    Body: { email, new_password, confirm_password }

    MODO PRUEBAS: si el correo existe, cambia password directo.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        s = PasswordResetTestSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        email = s.validated_data["email"]
        new_password = s.validated_data["new_password"]

        user = User.objects.get(email__iexact=email, is_active=True)
        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"detail": "Contraseña actualizada (modo pruebas)."},
            status=status.HTTP_200_OK
        )