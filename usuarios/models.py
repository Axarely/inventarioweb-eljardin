"""
Módulo de Usuarios y Roles (DEDS 3.2, Fig. 12).

Fase 1: solo el Usuario base, para fijar AUTH_USER_MODEL desde la primera migración.
Rol y sucursal se agregan en el Sprint 1 (ver docs/backlog.md).
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, correo, password=None, **campos):
        if not correo:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(correo=self.normalize_email(correo), **campos)
        usuario.set_password(password)  # RNF-02: se guarda solo el hash
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, password=None, **campos):
        campos.setdefault("is_staff", True)
        campos.setdefault("is_superuser", True)
        return self.create_user(correo, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """RF-01: el correo es el identificador de inicio de sesión."""

    nombre = models.CharField("nombre", max_length=120)
    correo = models.EmailField("correo", unique=True)
    activo = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al admin", default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "correo"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    @property
    def is_active(self):
        # Django consulta is_active al autenticar; en el DEDS el atributo se llama "activo".
        return self.activo

    def __str__(self):
        return f"{self.nombre} <{self.correo}>"
