from django.contrib import admin

from .models import Producto, Rol, Usuario


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


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "unidad_medida", "stock_minimo", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre",)
