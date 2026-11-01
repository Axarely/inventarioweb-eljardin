"""
D-33: proteínas con entrada en dos pasos. 1.ª entrada = peso que entrega el proveedor (bruto);
2.ª entrada = peso real tras limpieza o preparación. Merma = bruto - real (control interno).
"""
from decimal import Decimal

import pytest
from django.urls import reverse

from inventario import servicios
from inventario.excepciones import MovimientoInvalido
from inventario.fabrica import MovimientoInventarioFactory
from inventario.models import ControlMerma, Existencia, MermaInventario, MovimientoInventario
from reportes.servicios import Filtros, consumos
from usuarios.models import Producto

pytestmark = pytest.mark.django_db


def bodega_de(producto, bodega):
    fila = Existencia.objects.filter(producto=producto, ubicacion=bodega).first()
    return fila.cantidad if fila else Decimal("0")


@pytest.fixture
def recepcion(proteina_merma, bodega, proveedor, bodeguero):
    """El proveedor entrega 10 lb de alitas."""
    entrada = servicios.registrar_entrada(proteina_merma.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    return entrada.control_merma


# --- Catálogo de proteínas (migración usuarios.0006) ---------------------------------------------

def test_d33_catalogo_de_proteinas():
    proteinas = {p.nombre: (p.unidad_medida, p.controla_merma)
                 for p in Producto.objects.filter(categoria__nombre="Proteínas")}
    assert proteinas == {
        "Alitas de pollo": ("lb", True), "Pechuga de pollo": ("lb", True), "Tortas de res": ("lb", True),
        "Tortas de cerdo": ("lb", True), "Paquetes de res": ("unidad", False), "Paquetes de cerdo": ("unidad", False),
        "Camarón con cola": ("lb", True), "Camarón sin cola": ("lb", True), "Langosta": ("lb", True),
        "Filete": ("lb", True),
    }


# --- Primera entrada: peso del proveedor ---------------------------------------------------------

def test_d33_entrada_de_proteina_abre_control_pendiente(recepcion, proteina_merma, bodega):
    assert recepcion.estado == ControlMerma.Estado.PENDIENTE and recepcion.peso_bruto == Decimal("10")
    assert bodega_de(proteina_merma, bodega) == Decimal("10")  # hasta el peso real, la bodega tiene el bruto


def test_d33_producto_sin_merma_no_abre_control(producto, bodega, proveedor, bodeguero):
    entrada = servicios.registrar_entrada(producto.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    assert not ControlMerma.objects.filter(entrada=entrada).exists()


# --- Segunda entrada: peso real -----------------------------------------------------------------

def test_d33_peso_real_registra_merma_y_deja_el_peso_real(recepcion, proteina_merma, bodega, bodeguero):
    control = servicios.registrar_peso_real(recepcion.pk, Decimal("8"), bodeguero)
    assert control.estado == ControlMerma.Estado.PROCESADO and control.procesado_por == bodeguero
    assert control.merma == Decimal("2") and control.rendimiento == Decimal("80.0")
    assert bodega_de(proteina_merma, bodega) == Decimal("8")
    merma = control.movimiento_merma
    assert type(merma) is MermaInventario and merma.tipo == "merma" and merma.tipo_texto == "Merma"
    assert merma.origen_id == bodega.pk and merma.destino_id is None and merma.cantidad == Decimal("2")


def test_d33_peso_real_igual_sin_merma(recepcion, proteina_merma, bodega, bodeguero):
    control = servicios.registrar_peso_real(recepcion.pk, Decimal("10"), bodeguero)
    assert control.merma == Decimal("0") and control.movimiento_merma is None
    assert bodega_de(proteina_merma, bodega) == Decimal("10")


@pytest.mark.parametrize("peso, mensaje", [("10.5", "no puede superar"), ("-1", "negativo")])
def test_d33_peso_real_invalido(recepcion, bodeguero, peso, mensaje):
    with pytest.raises(MovimientoInvalido, match=mensaje):
        servicios.registrar_peso_real(recepcion.pk, Decimal(peso), bodeguero)
    recepcion.refresh_from_db()
    assert recepcion.estado == ControlMerma.Estado.PENDIENTE


def test_d33_peso_real_solo_una_vez(recepcion, bodeguero):
    servicios.registrar_peso_real(recepcion.pk, Decimal("8"), bodeguero)
    with pytest.raises(MovimientoInvalido, match="ya fue registrado"):
        servicios.registrar_peso_real(recepcion.pk, Decimal("7"), bodeguero)


def test_d33_merma_sin_existencia_suficiente_no_deja_cambios(recepcion, proteina_merma, bodega, santa_cruz, bodeguero):
    """Si se envió producto sin limpiar y ya no alcanza para descontar la merma, no se procesa nada."""
    servicios.registrar_salida(proteina_merma.pk, Decimal("9"), santa_cruz.pk, bodeguero.pk)
    with pytest.raises(MovimientoInvalido, match="Solo hay 1 lb"):
        servicios.registrar_peso_real(recepcion.pk, Decimal("7"), bodeguero)
    recepcion.refresh_from_db()
    assert recepcion.estado == ControlMerma.Estado.PENDIENTE and bodega_de(proteina_merma, bodega) == Decimal("1")


def test_d33_merma_no_es_consumo_de_sucursal(recepcion, bodeguero):
    servicios.registrar_peso_real(recepcion.pk, Decimal("8"), bodeguero)
    assert consumos(Filtros()).count() == 0


def test_d33_merma_respeta_la_invariante_rf04(recepcion, proteina_merma, bodega, santa_cruz, bodeguero):
    servicios.registrar_peso_real(recepcion.pk, Decimal("8.5"), bodeguero)
    servicios.registrar_salida(proteina_merma.pk, Decimal("3"), santa_cruz.pk, bodeguero.pk)
    for e in Existencia.objects.filter(producto=proteina_merma):
        vigentes = MovimientoInventario.objects.filter(producto=proteina_merma, anulado=False)
        entra = sum((m.cantidad for m in vigentes.filter(destino=e.ubicacion)), Decimal("0"))
        sale = sum((m.cantidad for m in vigentes.filter(origen=e.ubicacion)), Decimal("0"))
        assert e.cantidad == entra - sale


def test_d33_factory_crea_merma(proteina_merma, bodega, bodeguero):
    merma = MovimientoInventarioFactory.crear("merma", {
        "producto": proteina_merma, "cantidad": Decimal("1"), "origen": bodega, "destino": None, "usuario": bodeguero,
    })
    assert type(merma) is MermaInventario


# --- Anular y corregir ----------------------------------------------------------------------------

def test_d33_anular_merma_reabre_el_control(recepcion, proteina_merma, bodega, bodeguero):
    control = servicios.registrar_peso_real(recepcion.pk, Decimal("8"), bodeguero)
    servicios.anular_movimiento(control.movimiento_merma.pk, "Se pesó mal", bodeguero)
    recepcion.refresh_from_db()
    assert recepcion.estado == ControlMerma.Estado.PENDIENTE and recepcion.peso_real is None
    assert bodega_de(proteina_merma, bodega) == Decimal("10")
    assert servicios.registrar_peso_real(recepcion.pk, Decimal("9"), bodeguero).merma == Decimal("1")


def test_d33_corregir_entrada_pendiente_mueve_el_control(recepcion, bodeguero):
    nueva = servicios.corregir_movimiento(recepcion.entrada.pk, Decimal("12"), "Se pesó de nuevo", bodeguero)
    recepcion.refresh_from_db()
    assert recepcion.entrada_id == nueva.pk and recepcion.peso_bruto == Decimal("12")


def test_d33_no_corrige_entrada_ya_procesada_ni_la_merma(recepcion, bodeguero):
    control = servicios.registrar_peso_real(recepcion.pk, Decimal("8"), bodeguero)
    with pytest.raises(MovimientoInvalido, match="Anule primero la merma"):
        servicios.corregir_movimiento(recepcion.entrada.pk, Decimal("12"), "Corrección", bodeguero)
    with pytest.raises(MovimientoInvalido, match="La merma no se corrige"):
        servicios.corregir_movimiento(control.movimiento_merma.pk, Decimal("1"), "Corrección", bodeguero)


def test_d33_entrada_anulada_sale_de_pendientes(recepcion, bodeguero):
    servicios.anular_movimiento(recepcion.entrada.pk, "Entrada duplicada", bodeguero)
    assert not servicios.controles_merma(ControlMerma.Estado.PENDIENTE).exists()
    with pytest.raises(MovimientoInvalido, match="anulada"):
        servicios.registrar_peso_real(recepcion.pk, Decimal("8"), bodeguero)


# --- Registro en Entradas y control en Reportes -------------------------------------------------

def test_d33_pendientes_en_entradas_y_registro(cliente_de, recepcion, proteina_merma, bodega, bodeguero):
    cliente = cliente_de(bodeguero)
    pagina = cliente.get(reverse("inventario:entrada"))
    assert list(pagina.context["pendientes"]) == [recepcion] and "Pendientes de peso real" in pagina.content.decode()
    respuesta = cliente.post(reverse("inventario:peso_real"), {"control": recepcion.pk, "peso_real": "8"}, follow=True)
    assert "Peso real de Alitas de pollo: 8 lb (merma 2 lb, rendimiento 80.0 %)." in respuesta.content.decode()
    assert list(respuesta.context["pendientes"]) == []
    assert bodega_de(proteina_merma, bodega) == Decimal("8")


def test_d33_merma_no_esta_en_el_menu(cliente_de, bodeguero, dueno):
    for usuario in (bodeguero, dueno):
        menu = cliente_de(usuario).get(reverse("inicio"), follow=True).context["menu"]
        assert "Merma" not in [item["etiqueta"] for item in menu]


def test_d33_peso_real_error_controlado(cliente_de, recepcion, bodeguero):
    cliente = cliente_de(bodeguero)
    url = reverse("inventario:peso_real")
    assert "no puede superar" in cliente.post(url, {"control": recepcion.pk, "peso_real": "11"}, follow=True).content.decode()
    assert "Escriba un peso real válido" in cliente.post(url, {"control": recepcion.pk, "peso_real": "abc"}, follow=True).content.decode()
    assert cliente.post(url, {"control": 999999, "peso_real": "1"}).status_code == 404


def test_d33_solo_bodeguero_registra_peso_real(cliente_de, recepcion, dueno, encargado_sc):
    url = reverse("inventario:peso_real")
    for usuario in (dueno, encargado_sc):
        assert cliente_de(usuario).post(url, {"control": recepcion.pk, "peso_real": "8"}).status_code == 403


def test_d33_dueno_ve_control_en_reportes_y_exporta(cliente_de, recepcion, dueno, bodeguero, proveedor):
    servicios.registrar_peso_real(recepcion.pk, Decimal("8"), bodeguero)
    cliente = cliente_de(dueno)
    reporte = cliente.get(reverse("reportes:reportes"), {"tipo": "merma"}).context["reporte"]
    assert reporte.filas == [["Alitas de pollo", proveedor.nombre, "lb", 1, Decimal("10.00"), Decimal("8.00"),
                              Decimal("2.00"), Decimal("80.0")]]
    exportado = cliente.get(reverse("reportes:exportar", args=["pdf"]), {"tipo": "merma"})
    assert exportado.status_code == 200 and exportado.content.startswith(b"%PDF")


def test_d33_entrada_avisa_control_de_merma(cliente_de, bodeguero, proteina_merma, bodega, proveedor):
    cliente = cliente_de(bodeguero)
    datos = cliente.get(reverse("inventario:existencia_bodega"), {"producto": proteina_merma.pk}).json()
    assert datos["controla_merma"] is True
    respuesta = cliente.post(reverse("inventario:entrada"),
                             {"producto": proteina_merma.pk, "cantidad": "10", "proveedor": proveedor.pk}, follow=True)
    assert "Pendientes de peso real" in respuesta.content.decode()
