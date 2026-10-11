from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sincronizar_roles(sender, **kwargs):
    from .roles import sincronizar_roles_base

    sincronizar_roles_base()


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "usuarios"
    verbose_name = "Usuarios, roles y catálogo"

    def ready(self):
        # Se ejecuta tras el migrate de cada app: la última pasada ya ve todos los permisos.
        post_migrate.connect(_sincronizar_roles, dispatch_uid="usuarios_sincronizar_roles")
