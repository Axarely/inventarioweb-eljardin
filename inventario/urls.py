from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("entradas/", views.EntradaView.as_view(), name="entrada"),
    path("salidas/", views.SalidaView.as_view(), name="salida"),
    path("consumo/", views.ConsumoView.as_view(), name="consumo"),
    path("discrepancias/", views.DiscrepanciaView.as_view(), name="discrepancia"),
    path("existencias/", views.ExistenciasView.as_view(), name="existencias"),
    path("historial/", views.HistorialView.as_view(), name="historial"),
    path("movimientos/<int:pk>/anular/", views.AnularView.as_view(), name="anular"),
    path("movimientos/<int:pk>/corregir/", views.CorregirView.as_view(), name="corregir"),
    path("api/existencia-bodega/", views.existencia_bodega, name="existencia_bodega"),
]
