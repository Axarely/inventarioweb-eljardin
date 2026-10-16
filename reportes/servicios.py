"""
Interfaz IReportes (DEDS 3.2) y observador PanelIndicadoresService (DEDS 3.4, Fig. 23).

Consumo de una sucursal = SalidaInventario con origen = sucursal y destino = null, no anulada (D-02).
Todas las agregaciones se hacen en PostgreSQL (DEDS 3.5, RNF-01).
"""
import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from alertas.servicios import alertas_pendientes
from inventario.excepciones import formatear_cantidad
from inventario.models import Existencia, MovimientoInventario, Sucursal, Ubicacion
from inventario.observador import IObservadorExistencia

from .models import EstadoIndicadores


# --- Observer -----------------------------------------------------------------------------------

class PanelIndicadoresService(IObservadorExistencia):
    """RF-17: cada cambio de existencia marca los indicadores como desactualizados."""

    def actualizar(self, existencia):
        # Tras el commit: no alarga la transacción del movimiento ni bloquea la fila mientras tanto.
        # DEF-04 (aceptado): una salida cambia dos existencias y programa dos refrescos; es un UPDATE
        # extra de una fila, sin efecto en el resultado (ver docs/bitacora_defectos.md).
        transaction.on_commit(self.refrescar)

    @staticmethod
    def refrescar():
        actualizados = EstadoIndicadores.objects.filter(pk=1).update(
            version=F("version") + 1, actualizado_en=timezone.now()
        )
        if not actualizados:
            EstadoIndicadores.objects.get_or_create(pk=1, defaults={"version": 1, "actualizado_en": timezone.now()})


def estado_indicadores():
    return EstadoIndicadores.objects.filter(pk=1).first() or EstadoIndicadores(pk=1, version=0)


# --- Filtros ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Filtros:
    sucursal: object = None
    producto: object = None
    desde: date = None
    hasta: date = None

    def clave(self):
        return (
            getattr(self.sucursal, "pk", None), getattr(self.producto, "pk", None),
            self.desde and self.desde.isoformat(), self.hasta and self.hasta.isoformat(),
        )

    def describir(self, con_fechas=True):
        partes = [f"Sucursal: {self.sucursal or 'todas'}", f"Producto: {self.producto or 'todos'}"]
        if con_fechas:
            partes.append(f"Desde: {self.desde.strftime('%d/%m/%Y') if self.desde else 'inicio'}")
            partes.append(f"Hasta: {self.hasta.strftime('%d/%m/%Y') if self.hasta else 'hoy'}")
        return " · ".join(partes)


def _por_periodo(movimientos, filtros):
    if filtros.desde:
        movimientos = movimientos.filter(fecha__date__gte=filtros.desde)
    if filtros.hasta:
        movimientos = movimientos.filter(fecha__date__lte=filtros.hasta)
    if filtros.producto:
        movimientos = movimientos.filter(producto=filtros.producto)
    return movimientos


def consumos(filtros):  # RF-07
    movimientos = MovimientoInventario.objects.filter(
        tipo=MovimientoInventario.Tipo.SALIDA, destino__isnull=True,
        origen__tipo=Ubicacion.Tipo.SUCURSAL, anulado=False,
    )
    if filtros.sucursal:
        movimientos = movimientos.filter(origen=filtros.sucursal)
    return _por_periodo(movimientos, filtros)


def envios(filtros):
    movimientos = MovimientoInventario.objects.filter(
        tipo=MovimientoInventario.Tipo.SALIDA, destino__isnull=False, anulado=False,
    )
    if filtros.sucursal:
        movimientos = movimientos.filter(destino=filtros.sucursal)
    return _por_periodo(movimientos, filtros)


# --- Panel de indicadores (RF-07, RF-08, RF-17) --------------------------------------------------

@dataclass
class PanelIndicadores:
    """Retorno de IReportes.generar_indicadores (DEDS 3.2)."""

    filtros: Filtros
    sucursales: list
    kpis: list = field(default_factory=list)
    comparativo: dict = field(default_factory=dict)
    serie_diaria: dict = None
    alertas_activas: int = 0
    alertas_recientes: list = field(default_factory=list)
    actualizado_en: object = None


def generar_indicadores(filtros):
    """IReportes.generar_indicadores(filtros). Se recalcula cuando cambia la versión del observador."""
    estado = estado_indicadores()
    # DEF-05: la clave se reduce a un hash para que sea válida en cualquier backend de caché.
    clave = "panel:%s:%s" % (estado.version, hashlib.sha256(repr(filtros.clave()).encode()).hexdigest()[:32])
    datos = cache.get(clave)
    if datos is None:
        datos = _calcular_indicadores(filtros)
        cache.set(clave, datos, timeout=300)
    panel = PanelIndicadores(filtros=filtros, **datos)
    # Las alertas no dependen de Existencia (se atienden aparte): se consultan siempre.
    pendientes = alertas_pendientes()
    panel.alertas_activas = pendientes.count()
    panel.alertas_recientes = list(pendientes[:5])
    panel.actualizado_en = estado.actualizado_en
    return panel


def _calcular_indicadores(filtros):
    sucursales = [filtros.sucursal] if filtros.sucursal else list(Sucursal.objects.order_by("nombre"))
    por_sucursal = {
        fila["origen_id"]: fila
        for fila in consumos(filtros).values("origen_id").annotate(registros=Count("id"), total=Sum("cantidad"))
    }
    envios_por_sucursal = {
        fila["destino_id"]: fila["registros"]
        for fila in envios(filtros).values("destino_id").annotate(registros=Count("id"))
    }
    kpis = []
    for sucursal in sucursales:
        fila = por_sucursal.get(sucursal.pk, {"registros": 0, "total": None})
        total = None
        if filtros.producto:  # sumar kg con unidades no tiene sentido: el total solo con un producto
            total = f"{formatear_cantidad(fila['total'] or Decimal('0'))} {filtros.producto.unidad_medida}"
        kpis.append({
            "sucursal": sucursal.nombre,
            "consumos": fila["registros"],
            "total": total,
            "envios": envios_por_sucursal.get(sucursal.pk, 0),
        })

    # RF-08: consumo de cada producto, sucursales lado a lado.
    filas = (
        consumos(filtros)
        .values("producto__nombre", "producto__unidad_medida", "origen_id")
        .annotate(total=Sum("cantidad"))
        .order_by("producto__nombre")
    )
    etiquetas, valores = [], {s.pk: {} for s in sucursales}
    for fila in filas:
        etiqueta = f"{fila['producto__nombre']} ({fila['producto__unidad_medida']})"
        if etiqueta not in etiquetas:
            etiquetas.append(etiqueta)
        if fila["origen_id"] in valores:
            valores[fila["origen_id"]][etiqueta] = float(fila["total"])
    comparativo = {
        "etiquetas": etiquetas,
        "series": [
            {"nombre": s.nombre, "datos": [valores[s.pk].get(e, 0) for e in etiquetas]} for s in sucursales
        ],
    }

    serie_diaria = None
    if filtros.producto:  # evolución diaria: solo con un producto (unidad homogénea)
        diarias = (
            consumos(filtros)
            .annotate(dia=TruncDate("fecha"))
            .values("dia", "origen_id")
            .annotate(total=Sum("cantidad"))
            .order_by("dia")
        )
        dias = sorted({fila["dia"] for fila in diarias})
        por_dia = {(fila["dia"], fila["origen_id"]): float(fila["total"]) for fila in diarias}
        serie_diaria = {
            "etiquetas": [d.strftime("%d/%m") for d in dias],
            "unidad": filtros.producto.unidad_medida,
            "series": [
                {"nombre": s.nombre, "datos": [por_dia.get((d, s.pk), 0) for d in dias]} for s in sucursales
            ],
        }
    return {
        "sucursales": [s.nombre for s in sucursales],
        "kpis": kpis,
        "comparativo": comparativo,
        "serie_diaria": serie_diaria,
    }


# --- Reportes tabulares exportables (RF-07, RF-14) ----------------------------------------------

@dataclass
class Reporte:
    titulo: str
    filtros: str
    columnas: list
    filas: list
    generado_en: object = field(default_factory=timezone.now)


def reporte_consumo(filtros):  # RF-07
    filas = (
        consumos(filtros)
        .values("origen__nombre", "producto__nombre", "producto__categoria__nombre", "producto__unidad_medida")
        .annotate(total=Sum("cantidad"), registros=Count("id"))
        .order_by("origen__nombre", "producto__nombre")
    )
    return Reporte(
        titulo="Consumo por sucursal y producto",
        filtros=filtros.describir(),
        columnas=["Sucursal", "Producto", "Categoría", "Unidad", "Total consumido", "Registros"],
        filas=[
            [f["origen__nombre"], f["producto__nombre"], f["producto__categoria__nombre"], f["producto__unidad_medida"],
             f["total"], f["registros"]]
            for f in filas
        ],
    )


def reporte_existencias(filtros):  # RF-14: existencias actuales (las fechas no aplican)
    existencias = Existencia.objects.select_related("producto__categoria", "ubicacion").filter(producto__activo=True)
    if filtros.sucursal:
        existencias = existencias.filter(ubicacion=filtros.sucursal)
    if filtros.producto:
        existencias = existencias.filter(producto=filtros.producto)
    existencias = existencias.order_by("ubicacion__tipo", "ubicacion__nombre", "producto__nombre")
    return Reporte(
        titulo="Existencias actuales por ubicación",
        filtros=filtros.describir(con_fechas=False),
        columnas=["Ubicación", "Producto", "Categoría", "Cantidad", "Unidad", "Stock mínimo", "Estado"],
        filas=[
            [e.ubicacion.nombre, e.producto.nombre, e.producto.categoria.nombre, e.cantidad, e.producto.unidad_medida,
             e.producto.stock_minimo, e.nivel().label]
            for e in existencias
        ],
    )


REPORTES = {"consumo": reporte_consumo, "existencias": reporte_existencias}
