from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios"),
    path("usuarios/nuevo/", views.UsuarioCrearView.as_view(), name="usuario_crear"),
    path("usuarios/<int:pk>/editar/", views.UsuarioEditarView.as_view(), name="usuario_editar"),
    path("usuarios/<int:pk>/password/", views.UsuarioPasswordView.as_view(), name="usuario_password"),
    path("usuarios/<int:pk>/activar/", views.UsuarioActivarView.as_view(), name="usuario_activar"),
    path("roles/", views.RolListView.as_view(), name="roles"),
    path("roles/nuevo/", views.RolCrearView.as_view(), name="rol_crear"),
    path("roles/<int:pk>/editar/", views.RolEditarView.as_view(), name="rol_editar"),
    path("roles/<int:pk>/eliminar/", views.RolEliminarView.as_view(), name="rol_eliminar"),
    path("catalogo/", views.ProductoListView.as_view(), name="productos"),
    path("catalogo/nuevo/", views.ProductoCrearView.as_view(), name="producto_crear"),
    path("catalogo/<int:pk>/editar/", views.ProductoEditarView.as_view(), name="producto_editar"),
    path("catalogo/<int:pk>/activar/", views.ProductoActivarView.as_view(), name="producto_activar"),
]
