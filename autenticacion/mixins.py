from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied


class PermisoRequeridoMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    RF-01 / RNF-02: sin sesión -> redirige al login; con sesión pero sin permiso del rol -> 403.
    Las vistas declaran `permission_required` con permisos de Django asignados a los roles.
    """

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("Su rol no tiene acceso a esta función.")
        return super().handle_no_permission()
