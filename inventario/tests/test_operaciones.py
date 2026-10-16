"""
Consumo de sucursal (D-02), anulación y corrección (RF-15) y discrepancias (RF-13).
"""
from decimal import Decimal

import pytest
from django.urls import reverse

from inventario import servicios
from inventario.excepciones import ExistenciaInsuficiente, MovimientoInvalido
from inventario.models import DiscrepanciaInventario, Existencia, MovimientoInventario

pytestmark = pytest.mark.django_db


def cantidad(producto, ubicacion):
    existencia = Existencia.objects.filter(producto=producto, ubicacion=ubicacion).first()
    return existencia.cantidad if existencia else Decimal("0")


@pytest.fixture
def con_envio(producto, bodega, santa_cruz, proveedor, bodeguero):
    """Bodega recibe 30 y envía 20 a Santa Cruz."""
    entrada = servicios.registrar_entrada(producto.pk, Decimal("30"), proveedor.pk, bodeguero.pk)
    salida = servicios.registrar_salida(producto.pk, Decimal("20"), santa_cruz.pk, bodeguero.pk)
    return entrada, salida


# --- Consumo de sucursal (RF-07, D-02) -----------------------------------------------------------

def test_rf07_consumo_descuenta_sucursal(con_envio, producto, bodega, santa_cruz, encargado_sc):
    consumo = servicios.registrar_consumo(producto.pk, Decimal("7.5"), santa_cruz.pk, encargado_sc.pk)
    assert consumo.es_consumo and consumo.tipo_texto == "Consumo"
    assert consumo.origen_id == santa_cruz.pk and consumo.destino_id is None
    assert cantidad(producto, santa_cruz) == Decimal("12.5")
    assert cantidad(producto, bodega) == Decimal("10")  # la bodega no cambia


def test_rf07_consumo_insuficiente(con_envio, producto, santa_cruz, encargado_sc):
    with pytest.raises(ExistenciaInsuficiente):
        servicios.registrar_consumo(producto.pk, Decimal("21"), santa_cruz.pk, encargado_sc.pk)


def test_rf07_consumo_solo_desde_sucursal(producto, bodega, bodeguero, con_existencia):
    from inventario.fabrica import MovimientoInventarioFactory

    con_existencia(producto, bodega, 10)
    consumo = MovimientoInventarioFactory.crear("salida", {
        "producto": producto, "cantidad": Decimal("1"), "origen": bodega, "destino": None, "usuario": bodeguero,
    })
    with pytest.raises(MovimientoInvalido, match="sucursal"):
        consumo.aplicar()


def test_rf07_vista_consumo_usa_su_sucursal(cliente_de, con_envio, producto, santa_cruz, encargado_sc):
    respuesta = cliente_de(encargado_sc).post(
        reverse("inventario:consumo"), {"producto": producto.pk, "cantidad": "5"}, follow=True
    )
    assert "Consumo registrado: 5 kg de Pechuga de pollo en Santa Cruz." in respuesta.content.decode()
    assert cantidad(producto, santa_cruz) == Decimal("15")


def test_rf07_vista_consumo_insuficiente_muestra_maximo(cliente_de, con_envio, producto, encargado_sc):
    respuesta = cliente_de(encargado_sc).post(reverse("inventario:consumo"), {"producto": producto.pk, "cantidad": "25"})
    assert "Solo hay 20 kg disponibles en Santa Cruz" in respuesta.content.decode()


def test_rf07_encargado_sin_sucursal_no_reporta(cliente_de, encargado_sc):
    type(encargado_sc).objects.filter(pk=encargado_sc.pk).update(sucursal=None)
    respuesta = cliente_de(encargado_sc).get(reverse("inventario:consumo"), follow=True)
    assert "no tiene una sucursal asignada" in respuesta.content.decode()


# --- Anulación (RF-15) ---------------------------------------------------------------------------

def test_rf15_anular_salida_revierte_y_no_borra(con_envio, producto, bodega, santa_cruz, bodeguero):
    _, salida = con_envio
    servicios.anular_movimiento(salida.pk, "Se registró por error", bodeguero)
    salida.refresh_from_db()
    assert salida.anulado and salida.motivo_anulacion == "Se registró por error"
    assert salida.anulado_por == bodeguero and salida.anulado_en is not None
    assert cantidad(producto, bodega) == Decimal("30") and cantidad(producto, santa_cruz) == Decimal("0")
    assert MovimientoInventario.objects.filter(pk=salida.pk).exists()


def test_rf15_anular_entrada(producto, bodega, proveedor, bodeguero):
    entrada = servicios.registrar_entrada(producto.pk, Decimal("12"), proveedor.pk, bodeguero.pk)
    servicios.anular_movimiento(entrada.pk, "Proveedor equivocado", bodeguero)
    assert cantidad(producto, bodega) == Decimal("0")


def test_rf15_anular_consumo(con_envio, producto, santa_cruz, encargado_sc, dueno):
    consumo = servicios.registrar_consumo(producto.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    servicios.anular_movimiento(consumo.pk, "Consumo duplicado", dueno)
    assert cantidad(producto, santa_cruz) == Decimal("20")


@pytest.mark.parametrize("motivo", ["", "   ", "abc"])
def test_rf15_anular_exige_motivo(con_envio, bodeguero, motivo, producto, bodega):
    _, salida = con_envio
    with pytest.raises(MovimientoInvalido, match="motivo"):
        servicios.anular_movimiento(salida.pk, motivo, bodeguero)
    salida.refresh_from_db()
    assert not salida.anulado and cantidad(producto, bodega) == Decimal("10")


def test_rf15_no_anula_dos_veces(con_envio, bodeguero, producto, bodega):
    _, salida = con_envio
    servicios.anular_movimiento(salida.pk, "Primera anulación", bodeguero)
    with pytest.raises(MovimientoInvalido, match="ya está anulado"):
        servicios.anular_movimiento(salida.pk, "Segunda anulación", bodeguero)
    assert cantidad(producto, bodega) == Decimal("30")


def test_rf15_no_anula_si_el_destino_ya_consumio(con_envio, producto, bodega, santa_cruz, bodeguero, encargado_sc):
    _, salida = con_envio
    servicios.registrar_consumo(producto.pk, Decimal("15"), santa_cruz.pk, encargado_sc.pk)
    with pytest.raises(MovimientoInvalido, match="No se puede anular"):
        servicios.anular_movimiento(salida.pk, "Error de registro", bodeguero)
    salida.refresh_from_db()
    assert not salida.anulado
    assert cantidad(producto, bodega) == Decimal("10") and cantidad(producto, santa_cruz) == Decimal("5")


def test_rf15_corregir_reemplaza_movimiento(con_envio, producto, bodega, santa_cruz, bodeguero):
    _, salida = con_envio
    nueva = servicios.corregir_movimiento(salida.pk, Decimal("18"), "Se contaron mal las cajas", bodeguero)
    salida.refresh_from_db()
    assert salida.anulado and nueva.reemplaza_a_id == salida.pk and nueva.cantidad == Decimal("18")
    assert nueva.tipo == "salida" and nueva.destino_id == santa_cruz.pk
    assert cantidad(producto, bodega) == Decimal("12") and cantidad(producto, santa_cruz) == Decimal("18")


def test_rf15_corregir_entrada_conserva_proveedor(producto, bodega, proveedor, bodeguero):
    entrada = servicios.registrar_entrada(producto.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    nueva = servicios.corregir_movimiento(entrada.pk, Decimal("12"), "Faltó contar una caja", bodeguero)
    assert nueva.entradainventario.proveedor == proveedor
    assert cantidad(producto, bodega) == Decimal("12")


def test_rf15_corregir_fallida_no_deja_cambios(con_envio, producto, bodega, santa_cruz, bodeguero):
    """Si el reemplazo no se puede aplicar, tampoco queda la anulación (transacción única)."""
    _, salida = con_envio
    with pytest.raises(ExistenciaInsuficiente):
        servicios.corregir_movimiento(salida.pk, Decimal("40"), "Corrección imposible", bodeguero)
    salida.refresh_from_db()
    assert not salida.anulado
    assert cantidad(producto, bodega) == Decimal("10") and cantidad(producto, santa_cruz) == Decimal("20")


def test_rf15_corregir_misma_cantidad(con_envio, bodeguero):
    _, salida = con_envio
    with pytest.raises(MovimientoInvalido, match="igual"):
        servicios.corregir_movimiento(salida.pk, Decimal("20"), "Sin cambios reales", bodeguero)


def test_rf15_vistas_anular_y_corregir(cliente_de, con_envio, bodeguero, producto, bodega):
    entrada, salida = con_envio
    cliente = cliente_de(bodeguero)
    assert cliente.get(reverse("inventario:anular", args=[salida.pk])).status_code == 200
    respuesta = cliente.post(reverse("inventario:anular", args=[salida.pk]), {"motivo": "abc"})
    assert respuesta.context["form"].errors["motivo"]
    cliente.post(reverse("inventario:anular", args=[salida.pk]), {"motivo": "Envío duplicado"})
    salida.refresh_from_db()
    assert salida.anulado
    assert cliente.get(reverse("inventario:anular", args=[salida.pk])).status_code == 302  # ya anulado

    respuesta = cliente.post(
        reverse("inventario:corregir", args=[entrada.pk]), {"cantidad": "28", "motivo": "Recuento"}, follow=True
    )
    assert "queda anulado y lo reemplaza" in respuesta.content.decode()
    assert cantidad(producto, bodega) == Decimal("28")
    html = cliente.get(reverse("inventario:historial")).content.decode()
    assert "Motivo: Envío duplicado" in html and f"Corrige al #{entrada.pk}" in html


def test_rf15_vista_anular_error_controlado(cliente_de, con_envio, producto, santa_cruz, bodeguero, encargado_sc):
    _, salida = con_envio
    servicios.registrar_consumo(producto.pk, Decimal("15"), santa_cruz.pk, encargado_sc.pk)
    respuesta = cliente_de(bodeguero).post(reverse("inventario:anular", args=[salida.pk]), {"motivo": "Error de registro"})
    assert respuesta.status_code == 200 and "No se puede anular" in respuesta.content.decode()


def test_rf15_encargado_no_anula(cliente_de, con_envio, encargado_sc):
    _, salida = con_envio
    assert cliente_de(encargado_sc).post(
        reverse("inventario:anular", args=[salida.pk]), {"motivo": "Intento indebido"}
    ).status_code == 403


# --- Discrepancias (RF-13) -----------------------------------------------------------------------

def test_rf13_discrepancia_ligada_al_movimiento(con_envio, encargado_sc, producto, santa_cruz):
    """CP-RF13-01 y CP-RF13-06."""
    _, salida = con_envio
    discrepancia = servicios.reportar_discrepancia(salida.pk, Decimal("18"), encargado_sc)
    assert discrepancia.movimiento_id == salida.pk and discrepancia.usuario == encargado_sc
    assert discrepancia.cantidad_enviada == Decimal("20") and discrepancia.diferencia == Decimal("-2")
    assert cantidad(producto, santa_cruz) == Decimal("20")  # no altera existencias


def test_rf13_solo_movimientos_de_su_sucursal(con_envio, encargado_pb):
    """CP-RF13-02."""
    _, salida = con_envio
    with pytest.raises(MovimientoInvalido, match="su sucursal"):
        servicios.reportar_discrepancia(salida.pk, Decimal("18"), encargado_pb)


@pytest.mark.parametrize("recibida, mensaje", [("-1", "negativa"), ("20", "no hay discrepancia")])
def test_rf13_cantidad_recibida_valida(con_envio, encargado_sc, recibida, mensaje):
    """CP-RF13-03."""
    _, salida = con_envio
    with pytest.raises(MovimientoInvalido, match=mensaje):
        servicios.reportar_discrepancia(salida.pk, Decimal(recibida), encargado_sc)


def test_rf13_solo_salidas_vigentes(con_envio, encargado_sc, bodeguero):
    """CP-RF13-04."""
    entrada, salida = con_envio
    with pytest.raises(MovimientoInvalido, match="envíos"):
        servicios.reportar_discrepancia(entrada.pk, Decimal("1"), encargado_sc)
    servicios.anular_movimiento(salida.pk, "Envío cancelado", bodeguero)
    with pytest.raises(MovimientoInvalido, match="anulado"):
        servicios.reportar_discrepancia(salida.pk, Decimal("1"), encargado_sc)


def test_rf13_una_discrepancia_por_envio(con_envio, encargado_sc):
    _, salida = con_envio
    servicios.reportar_discrepancia(salida.pk, Decimal("19"), encargado_sc)
    with pytest.raises(MovimientoInvalido, match="Ya se reportó"):
        servicios.reportar_discrepancia(salida.pk, Decimal("18"), encargado_sc)


def test_rf13_vista_y_visible_en_historial(cliente_de, con_envio, encargado_sc, dueno):
    """CP-RF13-05: el dueño ve la discrepancia en el historial."""
    _, salida = con_envio
    cliente = cliente_de(encargado_sc)
    formulario = cliente.get(reverse("inventario:discrepancia")).context["form"]
    assert list(formulario.fields["movimiento"].queryset) == [salida.movimientoinventario_ptr]
    respuesta = cliente.post(
        reverse("inventario:discrepancia"), {"movimiento": salida.pk, "cantidad_recibida": "17.5"}, follow=True
    )
    assert "diferencia de -2.5 kg" in respuesta.content.decode()
    assert DiscrepanciaInventario.objects.count() == 1
    html = cliente_de(dueno).get(reverse("inventario:historial")).content.decode()
    assert "Discrepancia</span> recibido 17.5 (dif. -2.5)" in html


def test_rf13_vista_rechaza_envio_de_otra_sucursal(cliente_de, con_envio, encargado_pb):
    _, salida = con_envio
    respuesta = cliente_de(encargado_pb).post(
        reverse("inventario:discrepancia"), {"movimiento": salida.pk, "cantidad_recibida": "1"}
    )
    assert respuesta.context["form"].errors["movimiento"]  # no está entre sus envíos
    assert not DiscrepanciaInventario.objects.exists()
