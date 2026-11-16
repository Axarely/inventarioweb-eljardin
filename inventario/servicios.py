"""
Interfaz IInventario (DEDS 3.2, tabla de interfaces).

Los movimientos se crean SIEMPRE con MovimientoInventarioFactory (patrón Factory Method, DEDS 3.4):
ni este módulo ni las vistas instancian EntradaInventario o SalidaInventario directamente.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from proveedores.servicios import obtener_proveedor_activo
from usuarios.models import Producto

from .excepciones import MovimientoInvalido, formatear_cantidad
from .fabrica import MovimientoInventarioFactory
from .models import Bodega, ControlMerma, DiscrepanciaInventario, Existencia, MovimientoInventario, Sucursal

ENTRADA = MovimientoInventario.Tipo.ENTRADA
SALIDA = MovimientoInventario.Tipo.SALIDA
MERMA = MovimientoInventario.Tipo.MERMA


def registrar_entrada(producto_id, cantidad, proveedor_id, usuario_id):  # RF-02, RF-11
    """Para proteínas con control de merma (D-33) esta es la PRIMERA entrada: el peso bruto del proveedor.
    Queda pendiente registrar el peso real (registrar_peso_real)."""
    producto = Producto.objects.get(pk=producto_id)
    entrada = MovimientoInventarioFactory.crear(ENTRADA, {
        "producto": producto,
        "cantidad": cantidad,
        "proveedor": obtener_proveedor_activo(proveedor_id) if proveedor_id is not None else None,  # D-45
        "destino": Bodega.central(),
        "usuario_id": usuario_id,
    })
    with transaction.atomic():
        entrada.aplicar()
        if producto.controla_merma:
            ControlMerma.objects.create(entrada=entrada)
    return entrada


def registrar_peso_real(control_id, peso_real, usuario):  # D-33: SEGUNDA entrada de proteínas
    """
    Registra el peso real después de limpieza o preparación. La merma (bruto - real) se descuenta de la
    bodega como MermaInventario, creada por la Factory, para que la existencia quede en el peso real.
    """
    peso_real = Decimal(peso_real)
    with transaction.atomic():
        # DEF-13: se bloquea solo la fila del control; destino es nullable (outer join) y PostgreSQL no admite
        # FOR UPDATE sobre el lado nulo de un outer join.
        control = ControlMerma.objects.select_for_update(of=("self",)).select_related(
            "entrada__producto", "entrada__destino"
        ).get(pk=control_id)
        entrada = control.entrada
        if control.estado != ControlMerma.Estado.PENDIENTE:
            raise MovimientoInvalido("El peso real de esta entrada ya fue registrado.")
        if entrada.anulado:
            raise MovimientoInvalido("La entrada del proveedor está anulada.")
        if peso_real < 0:
            raise MovimientoInvalido("El peso real no puede ser negativo.")
        if peso_real > entrada.cantidad:
            raise MovimientoInvalido(
                f"El peso real no puede superar el peso entregado por el proveedor "
                f"({formatear_cantidad(entrada.cantidad)} {entrada.producto.unidad_medida})."
            )
        merma = entrada.cantidad - peso_real
        if merma > 0:
            control.movimiento_merma = MovimientoInventarioFactory.crear(MERMA, {
                "producto": entrada.producto,
                "cantidad": merma,
                "origen": entrada.destino,
                "destino": None,
                "usuario": usuario,
            }).aplicar()
        control.peso_real = peso_real
        control.merma = merma
        control.estado = ControlMerma.Estado.PROCESADO
        control.procesado_por = usuario
        control.procesado_en = timezone.now()
        control.save()
    return control


def controles_merma(estado=None, producto_id=None):  # D-33
    controles = ControlMerma.objects.filter(entrada__anulado=False).select_related(
        "entrada__producto", "entrada__proveedor", "entrada__usuario", "procesado_por"
    )
    if estado:
        controles = controles.filter(estado=estado)
    if producto_id:
        controles = controles.filter(entrada__producto_id=producto_id)
    return controles


def registrar_salida(producto_id, cantidad, sucursal_id, usuario_id):  # RF-03
    salida = MovimientoInventarioFactory.crear(SALIDA, {
        "producto": Producto.objects.get(pk=producto_id),
        "cantidad": cantidad,
        "origen": Bodega.central(),
        "destino": Sucursal.objects.get(pk=sucursal_id),
        "usuario_id": usuario_id,
    })
    return salida.aplicar()


def registrar_consumo(producto_id, cantidad, sucursal_id, usuario_id):  # RF-07 (D-02)
    """Consumo reportado por el encargado: salida con origen = su sucursal y sin destino."""
    consumo = MovimientoInventarioFactory.crear(SALIDA, {
        "producto": Producto.objects.get(pk=producto_id),
        "cantidad": cantidad,
        "origen": Sucursal.objects.get(pk=sucursal_id),
        "destino": None,
        "usuario_id": usuario_id,
    })
    return consumo.aplicar()


def anular_movimiento(movimiento_id, motivo, usuario):  # RF-15
    movimiento = MovimientoInventario.objects.select_related("producto", "origen", "destino").get(pk=movimiento_id)
    return movimiento.anular(motivo, usuario)


def corregir_movimiento(movimiento_id, nueva_cantidad, motivo, usuario):  # RF-15 "editar" (D-18)
    """
    Corrige la cantidad de un movimiento: lo anula con su motivo y registra uno nuevo con la cantidad
    correcta que lo reemplaza. Todo en una transacción: si el nuevo no se puede aplicar, nada cambia.
    """
    nueva_cantidad = Decimal(nueva_cantidad)
    with transaction.atomic():
        original = MovimientoInventario.objects.select_related(
            "producto", "origen", "destino", "entradainventario__proveedor"
        ).get(pk=movimiento_id)
        if nueva_cantidad == original.cantidad:
            raise MovimientoInvalido("La cantidad corregida es igual a la registrada.")
        if original.tipo == MERMA:  # D-33
            raise MovimientoInvalido("La merma no se corrige: anúlela y vuelva a registrar el peso real.")
        control = ControlMerma.objects.filter(entrada_id=original.pk).first() if original.tipo == ENTRADA else None
        if control is not None and control.estado == ControlMerma.Estado.PROCESADO:
            raise MovimientoInvalido(
                "Esta entrada ya tiene registrado su peso real. Anule primero la merma (Historial) y luego corrija."
            )
        original.anular(motivo, usuario)
        datos = {
            "producto": original.producto,
            "cantidad": nueva_cantidad,
            "origen": original.origen,
            "destino": original.destino,
            "usuario": usuario,
            "reemplaza_a": original,
        }
        if original.tipo == ENTRADA:
            datos["proveedor"] = original.entradainventario.proveedor
        nuevo = MovimientoInventarioFactory.crear(original.tipo, datos).aplicar()
        if control is not None:  # D-33: el control pendiente pasa a la entrada corregida
            control.entrada = nuevo
            control.save(update_fields=["entrada"])
        return nuevo


def reportar_discrepancia(movimiento_id, cantidad_recibida, usuario):  # RF-13 (D-03)
    cantidad_recibida = Decimal(cantidad_recibida)
    movimiento = MovimientoInventario.objects.select_related("destino").get(pk=movimiento_id)
    if movimiento.tipo != SALIDA or movimiento.destino_id is None:
        raise MovimientoInvalido("Solo se reportan discrepancias sobre envíos de la bodega a una sucursal.")
    if movimiento.anulado:
        raise MovimientoInvalido("El envío está anulado.")
    if usuario.sucursal_id != movimiento.destino_id:
        raise MovimientoInvalido("Solo puede reportar discrepancias de envíos a su sucursal.")
    if DiscrepanciaInventario.objects.filter(movimiento_id=movimiento.pk).exists():
        raise MovimientoInvalido("Ya se reportó una discrepancia para este envío.")
    if cantidad_recibida < 0:
        raise MovimientoInvalido("La cantidad recibida no puede ser negativa.")
    if cantidad_recibida == movimiento.cantidad:
        raise MovimientoInvalido("La cantidad recibida coincide con la enviada: no hay discrepancia.")
    return DiscrepanciaInventario.objects.create(
        movimiento_id=movimiento.pk,
        cantidad_enviada=movimiento.cantidad,
        cantidad_recibida=cantidad_recibida,
        diferencia=cantidad_recibida - movimiento.cantidad,
        usuario=usuario,
    )


def envios_sin_discrepancia(sucursal_id):
    """Envíos vigentes a una sucursal sobre los que aún se puede reportar una discrepancia."""
    return (
        MovimientoInventario.objects.filter(
            tipo=SALIDA, destino_id=sucursal_id, anulado=False, salidainventario__discrepancia__isnull=True
        )
        .select_related("producto")
        .order_by("-fecha")
    )


def consultar_existencias(ubicacion_id, filtros=None):  # RF-04, RF-05
    """Existencias de una ubicación (productos activos), con filtros opcionales `texto` y `categoria`."""
    filtros = filtros or {}
    existencias = Existencia.objects.filter(ubicacion_id=ubicacion_id, producto__activo=True).select_related(
        "producto__categoria"
    )
    if filtros.get("texto"):
        existencias = existencias.filter(producto__nombre__icontains=filtros["texto"])
    if str(filtros.get("categoria") or "").isdigit():
        existencias = existencias.filter(producto__categoria_id=filtros["categoria"])
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
        "producto", "origen", "destino", "usuario__rol", "usuario__sucursal", "anulado_por", "reemplaza_a",
        "entradainventario__proveedor", "salidainventario__discrepancia",
    )
    if producto_id:
        movimientos = movimientos.filter(producto_id=producto_id)
    if ubicacion_id:
        movimientos = movimientos.filter(Q(origen_id=ubicacion_id) | Q(destino_id=ubicacion_id))
    return movimientos
