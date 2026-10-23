from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView

from autenticacion.views import InicioView


class IconoSitioView(RedirectView):
    """Los navegadores piden /favicon.ico por su cuenta: se redirige al ícono de static (con hash en producción)."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return static("img/favicon.ico")


urlpatterns = [
    path("", InicioView.as_view(), name="inicio"),  # RF-01
    path("favicon.ico", IconoSitioView.as_view()),
    path("", include("autenticacion.urls")),
    path("", include("usuarios.urls")),
    path("inventario/", include("inventario.urls")),
    path("proveedores/", include("proveedores.urls")),
    path("alertas/", include("alertas.urls")),
    path("", include("reportes.urls")),
    path("admin/", admin.site.urls),
]
