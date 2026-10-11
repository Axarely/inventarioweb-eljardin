"""
Interfaz IInventario (DEDS 3.2, tabla de interfaces).

Sprint 1: los movimientos se construyen aquí directamente. En el Sprint 2 (S2-01) la creación
pasa a MovimientoInventarioFactory.crear(tipo, datos) (patrón Factory Method).
"""
from django.db.models import Q

from proveedores.servicios import obtener_proveedor_activo
from usuarios.models import Producto

from .models import Bodega, EntradaInventario, Existencia, MovimientoInventario, SalidaInventario, Sucursal


def registrar_entrada(producto_id, cantidad, proveedor_id, usuario_id):  # RF-02, RF-11
    entrada = EntradaInventario(
        producto=Producto.objects.get(pk=producto_id),
        cantidad=cantidad,
        proveedor=obtener_proveedor_activo(proveedor_id),
        destino=Bodega.central(),
        usuario_id=usuario_id,
    )
    return entrada.aplicar()


def registrar_salida(producto_id, cantidad, sucursal_id, usuario_id):  # RF-03
    salida = SalidaInventario(
        producto=Producto.objects.get(pk=producto_id),
        cantidad=cantidad,
        origen=Bodega.central(),
        destino=Sucursal.objects.get(pk=sucursal_id),
        usuario_id=usuario_id,
    )
    return salida.aplicar()


def consultar_existencias(ubicacion_id, filtros=None):  # RF-04, RF-05
    """Existencias de una ubicación (productos activos), con filtros opcionales `texto` y `categoria`."""
    filtros = filtros or {}
    existencias = Existencia.objects.filter(ubicacion_id=ubicacion_id, producto__activo=True).select_related(
        "producto"
    )
    if filtros.get("texto"):
        existencias = existencias.filter(producto__nombre__icontains=filtros["texto"])
    if filtros.get("categoria"):
        existencias = existencias.filter(producto__categoria=filtros["categoria"])
    return existencias.order_by("producto__nombre")


def existencia_en_bodega(producto_id):
    """Contexto de los formularios de entrada y salida (Fig. 15 y 16)."""
    return (
        Existencia.objects.select_related("producto")
        .filter(producto_id=producto_id, ubicacion=Bodega.central())
        .first()
    )


def historial(producto_id=None, ubicacion_id=None):  # RF-12: orden cronológico descendente
    movimientos = MovimientoInventario.objects.select_related(
        "producto", "origen", "destino", "usuario", "entradainventario__proveedor"
    )
    if producto_id:
        movimientos = movimientos.filter(producto_id=producto_id)
    if ubicacion_id:
        movimientos = movimientos.filter(Q(origen_id=ubicacion_id) | Q(destino_id=ubicacion_id))
    return movimientos
