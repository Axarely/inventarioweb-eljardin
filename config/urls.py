from django.contrib import admin
from django.urls import include, path

from autenticacion.views import InicioView

urlpatterns = [
    path("", InicioView.as_view(), name="inicio"),  # RF-01
    path("", include("autenticacion.urls")),
    path("", include("usuarios.urls")),
    path("inventario/", include("inventario.urls")),
    path("proveedores/", include("proveedores.urls")),
    path("admin/", admin.site.urls),
]
