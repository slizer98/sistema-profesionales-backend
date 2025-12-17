# apps/users/models.py
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.ROLE_SYSTEM_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser debe tener is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_SYSTEM_ADMIN = "system_admin"
    ROLE_PROFESSIONAL = "professional"
    ROLE_STAFF = "staff"
    ROLE_CLIENT = "client"

    ROLE_CHOICES = [
        (ROLE_SYSTEM_ADMIN, "System admin"),
        (ROLE_PROFESSIONAL, "Profesional"),
        (ROLE_STAFF, "Staff"),
        (ROLE_CLIENT, "Cliente"),
    ]

    email = models.EmailField("Correo electrónico", unique=True)
    full_name = models.CharField("Nombre completo", max_length=150, blank=True)
    role = models.CharField(
        "Rol",
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_PROFESSIONAL,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.full_name or self.email
