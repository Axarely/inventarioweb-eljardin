from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("entradas/", views.EntradaView.as_view(), name="entrada"),
    path("salidas/", views.SalidaView.as_view(), name="salida"),
    path("existencias/", views.ExistenciasView.as_view(), name="existencias"),
    path("historial/", views.HistorialView.as_view(), name="historial"),
    path("api/existencia-bodega/", views.existencia_bodega, name="existencia_bodega"),
]
