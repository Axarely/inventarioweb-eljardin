"""
Módulo de Reportes: indicadores (RF-07, RF-08, RF-17), observador PanelIndicadoresService y
exportación (RF-14).
"""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.urls import reverse
from django.utils import timezone

from inventario import servicios as inventario
from inventario.models import MovimientoInventario
from reportes import exportadores, servicios
from reportes.forms import FiltrosForm
from reportes.models import EstadoIndicadores
from reportes.servicios import Filtros

pytestmark = pytest.mark.django_db


@pytest.fixture
def escenario(producto, otro_producto, bodega, santa_cruz, pena_blanca, proveedor, bodeguero, encargado_sc, encargado_pb):
    """Envíos a ambas sucursales y consumos: SC 8 kg de pollo (hoy), PB 3 kg (hace 10 días) y 4 paq."""
    for prod, total in ((producto, 60), (otro_producto, 30)):
        inventario.registrar_entrada(prod.pk, Decimal(total), proveedor.pk, bodeguero.pk)
        inventario.registrar_salida(prod.pk, Decimal(20), santa_cruz.pk, bodeguero.pk)
        inventario.registrar_salida(prod.pk, Decimal(10), pena_blanca.pk, bodeguero.pk)
    inventario.registrar_consumo(producto.pk, Decimal("5"), santa_cruz.pk, encargado_sc.pk)
    inventario.registrar_consumo(producto.pk, Decimal("3"), santa_cruz.pk, encargado_sc.pk)
    viejo = inventario.registrar_consumo(producto.pk, Decimal("3"), pena_blanca.pk, encargado_pb.pk)
    MovimientoInventario.objects.filter(pk=viejo.pk).update(fecha=timezone.now() - timedelta(days=10))
    inventario.registrar_consumo(otro_producto.pk, Decimal("4"), pena_blanca.pk, encargado_pb.pk)
    anulado = inventario.registrar_consumo(producto.pk, Decimal("1"), santa_cruz.pk, encargado_sc.pk)
    inventario.anular_movimiento(anulado.pk, "Consumo duplicado", bodeguero)
    return {"sc": santa_cruz, "pb": pena_blanca, "pollo": producto, "servilletas": otro_producto}


def hoy():
    return timezone.localdate()


# --- RF-07: consumo = salida desde la sucursal, sin anulados -------------------------------------

def test_rf07_consumos_filtran_por_sucursal_producto_y_fechas(escenario):
    todos = servicios.consumos(Filtros())
    assert todos.count() == 4  # el anulado no cuenta y los envíos de bodega tampoco
    assert servicios.consumos(Filtros(sucursal=escenario["sc"])).count() == 2
    assert servicios.consumos(Filtros(producto=escenario["servilletas"])).count() == 1
    recientes = servicios.consumos(Filtros(desde=hoy() - timedelta(days=5), hasta=hoy()))
    assert recientes.count() == 3


def test_rf07_reporte_consumo_totales(escenario):
    reporte = servicios.reporte_consumo(Filtros())
    assert reporte.columnas == ["Sucursal", "Producto", "Categoría", "Unidad", "Total consumido", "Registros"]
    assert reporte.filas == [
        ["Peña Blanca", "Pechuga de pollo", "Cárnicos", "kg", Decimal("3.00"), 1],
        ["Peña Blanca", "Servilletas", "Desechables", "paq.", Decimal("4.00"), 1],
        ["Santa Cruz", "Pechuga de pollo", "Cárnicos", "kg", Decimal("8.00"), 2],
    ]


def test_rf14_reporte_existencias(escenario):
    reporte = servicios.reporte_existencias(Filtros(sucursal=escenario["sc"]))
    assert [fila[:4] for fila in reporte.filas] == [
        ["Santa Cruz", "Pechuga de pollo", "Cárnicos", Decimal("12.00")],
        ["Santa Cruz", "Servilletas", "Desechables", Decimal("20.00")],
    ]
    assert reporte.filas[0][-1] == "Normal" and "Desde" not in reporte.filtros


# --- RF-08 / RF-17: panel de indicadores ---------------------------------------------------------

def test_rf08_comparativo_sucursales_lado_a_lado(escenario):
    panel = servicios.generar_indicadores(Filtros())
    assert panel.sucursales == ["Peña Blanca", "Santa Cruz"]
    assert panel.comparativo["etiquetas"] == ["Pechuga de pollo (kg)", "Servilletas (paq.)"]
    assert panel.comparativo["series"] == [
        {"nombre": "Peña Blanca", "datos": [3.0, 4.0]},
        {"nombre": "Santa Cruz", "datos": [8.0, 0]},
    ]
    assert panel.serie_diaria is None  # sin producto no se suman unidades distintas
    kpi_sc = next(k for k in panel.kpis if k["sucursal"] == "Santa Cruz")
    assert kpi_sc == {"sucursal": "Santa Cruz", "consumos": 2, "total": None, "envios": 2}


def test_rf07_indicadores_con_producto_y_serie_diaria(escenario):
    panel = servicios.generar_indicadores(Filtros(producto=escenario["pollo"]))
    totales = {k["sucursal"]: k["total"] for k in panel.kpis}
    assert totales == {"Peña Blanca": "3 kg", "Santa Cruz": "8 kg"}
    serie = panel.serie_diaria
    assert serie["unidad"] == "kg" and len(serie["etiquetas"]) == 2
    assert serie["series"][1] == {"nombre": "Santa Cruz", "datos": [0, 8.0]}


def test_rf17_indicadores_reflejan_movimiento_nuevo(escenario, encargado_sc, django_capture_on_commit_callbacks):
    """RF-17: el observador invalida los indicadores; la consulta siguiente ya incluye el movimiento."""
    filtros = Filtros(sucursal=escenario["sc"], producto=escenario["pollo"])
    assert servicios.generar_indicadores(filtros).kpis[0]["total"] == "8 kg"
    version = servicios.estado_indicadores().version
    with django_capture_on_commit_callbacks(execute=True):
        inventario.registrar_consumo(escenario["pollo"].pk, Decimal("2"), escenario["sc"].pk, encargado_sc.pk)
    assert servicios.estado_indicadores().version > version
    assert servicios.generar_indicadores(filtros).kpis[0]["total"] == "10 kg"


def test_rf17_observador_crea_estado_si_no_existe():
    EstadoIndicadores.objects.all().delete()
    servicios.PanelIndicadoresService.refrescar()
    servicios.PanelIndicadoresService.refrescar()
    assert EstadoIndicadores.objects.get(pk=1).version == 2


def test_rf17_alertas_en_el_panel(escenario):
    panel = servicios.generar_indicadores(Filtros())
    # Bodega: servilletas en 0 (Agotado). Peña Blanca: pollo en 7 kg < 10 (Bajo). Santa Cruz: 12 kg, sin alerta.
    assert panel.alertas_activas == 2
    assert {(a.existencia.ubicacion.nombre, a.nivel_texto) for a in panel.alertas_recientes} == {
        ("Bodega central", "Agotado"), ("Peña Blanca", "Bajo"),
    }


# --- Filtros ------------------------------------------------------------------------------------

def test_rf07_filtros_por_defecto_ultimos_30_dias():
    form = FiltrosForm(None)
    filtros = form.filtros()
    assert filtros.hasta == hoy() and filtros.desde == hoy() - timedelta(days=30)


def test_rf07_filtros_rango_invalido():
    form = FiltrosForm({"desde": "2026-10-10", "hasta": "2026-10-01"})
    assert form.filtros() is None and "posterior" in str(form.errors)


# --- Vistas -------------------------------------------------------------------------------------

def test_rf08_dashboard_dueno(cliente_de, dueno, escenario):
    respuesta = cliente_de(dueno).get(reverse("reportes:dashboard"), {"producto": escenario["pollo"].pk})
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert 'id="datos-graficos"' in html and "chart.js@4.4.1" in html
    assert 'id="grafico-comparativo"' in html and 'id="grafico-diario"' in html
    assert respuesta.context["graficos"]["diaria"]["unidad"] == "kg"


def test_rf07_reportes_vista_y_filtros_invalidos(cliente_de, dueno, escenario):
    cliente = cliente_de(dueno)
    respuesta = cliente.get(reverse("reportes:reportes"), {"tipo": "consumo"})
    assert len(respuesta.context["reporte"].filas) == 3
    assert cliente.get(reverse("reportes:reportes"), {"tipo": "otro"}).status_code == 404
    respuesta = cliente.get(reverse("reportes:reportes"), {"desde": "2026-10-10", "hasta": "2026-10-01"})
    assert "reporte" not in respuesta.context and "posterior" in respuesta.content.decode()


# --- RF-14: exportación con la misma información que en pantalla -------------------------------

def test_rf14_exportar_excel_igual_a_pantalla(cliente_de, dueno, escenario):
    from openpyxl import load_workbook

    parametros = {"tipo": "consumo"}
    pantalla = cliente_de(dueno).get(reverse("reportes:reportes"), parametros).context["reporte"]
    respuesta = cliente_de(dueno).get(reverse("reportes:exportar", args=["excel"]), parametros)
    assert respuesta["Content-Type"].startswith("application/vnd.openxmlformats")
    assert respuesta["Content-Disposition"].startswith('attachment; filename="reporte_consumo_')
    hoja = load_workbook(BytesIO(respuesta.content)).active
    filas = [list(f) for f in hoja.iter_rows(min_row=5, values_only=True)]
    assert filas[0] == pantalla.columnas
    assert len(filas) - 1 == len(pantalla.filas) == 3
    for fila_excel, fila_pantalla in zip(filas[1:], pantalla.filas):
        assert fila_excel[:4] == fila_pantalla[:4]  # textos idénticos
        assert Decimal(str(fila_excel[4])) == fila_pantalla[4]  # total consumido
        assert fila_excel[5] == fila_pantalla[5]  # registros


def test_rf14_exportar_pdf(cliente_de, dueno, escenario):
    respuesta = cliente_de(dueno).get(reverse("reportes:exportar", args=["pdf"]), {"tipo": "existencias"})
    assert respuesta["Content-Type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")
    assert respuesta["Content-Disposition"].endswith('.pdf"')


def test_rf14_pdf_generado_con_filas():
    reporte = servicios.Reporte(titulo="Prueba", filtros="Todo", columnas=["A", "B"], filas=[["Arroz", Decimal("2.50")]])
    contenido = exportadores.a_pdf(reporte)
    assert contenido.startswith(b"%PDF") and contenido.rstrip().endswith(b"%%EOF")


def test_rf14_pdf_sin_datos():
    reporte = servicios.Reporte(titulo="Vacío", filtros="Todo", columnas=["A", "B"], filas=[])
    assert exportadores.a_pdf(reporte).startswith(b"%PDF")


@pytest.mark.parametrize("url", ["excel", "csv"])
def test_rf14_formatos_y_permisos(cliente_de, encargado_sc, dueno, url):
    destino = reverse("reportes:exportar", args=[url])
    assert cliente_de(encargado_sc).get(destino).status_code == 403
    assert cliente_de(dueno).get(destino).status_code == (200 if url == "excel" else 404)
