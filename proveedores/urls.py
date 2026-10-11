from django.urls import path

from . import views

app_name = "proveedores"

urlpatterns = [
    path("", views.ProveedorListView.as_view(), name="lista"),
    path("nuevo/", views.ProveedorCrearView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.ProveedorEditarView.as_view(), name="editar"),
    path("<int:pk>/activar/", views.ProveedorActivarView.as_view(), name="activar"),
]
