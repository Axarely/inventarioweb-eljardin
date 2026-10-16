from django.contrib import admin

from .models import Categoria, Producto, Rol, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "correo", "rol", "sucursal", "activo", "is_staff")
    list_filter = ("rol", "activo")
    search_fields = ("nombre", "correo")
    exclude = ("password", "user_permissions", "groups")

    def has_add_permission(self, request):
        # R-05: el alta se hace en Usuarios (RF-10) o con createsuperuser, que sí fijan contraseña.
        return False


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo")
    filter_horizontal = ("permisos",)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "es_base")

    def has_delete_permission(self, request, obj=None):
        return obj is None or not obj.es_base  # D-32: las fijas no se eliminan


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "unidad_medida", "stock_minimo", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre",)
