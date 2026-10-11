from django.contrib import admin

from .models import Bodega, Existencia, MovimientoInventario, Sucursal


@admin.register(Bodega)
class BodegaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "direccion", "capacidad_max")


@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ("nombre", "direccion", "horario")


class SoloLecturaAdmin(admin.ModelAdmin):
    """Existencias y movimientos solo cambian con aplicar() (RF-04, RNF-08): el admin no los edita."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Existencia)
class ExistenciaAdmin(SoloLecturaAdmin):
    list_display = ("producto", "ubicacion", "cantidad", "actualizado_en")
    list_filter = ("ubicacion",)


@admin.register(MovimientoInventario)
class MovimientoAdmin(SoloLecturaAdmin):
    list_display = ("fecha", "tipo", "producto", "cantidad", "origen", "destino", "usuario", "anulado")
    list_filter = ("tipo", "anulado")
