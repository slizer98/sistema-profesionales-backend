from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import User
from .serializers import MeSerializer, RegisterProfessionalSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = MeSerializer(request.user)
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
