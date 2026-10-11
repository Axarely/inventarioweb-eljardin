from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class RolBackend(ModelBackend):
    """
    RF-01 / RNF-02: RBAC con el sistema de permisos de Django (DEDS 3.5).
    Los permisos de un usuario son los de su Rol (además de los individuales, si los hubiera).
    """

    def _get_group_permissions(self, user_obj):
        return Permission.objects.filter(roles__usuarios=user_obj)
