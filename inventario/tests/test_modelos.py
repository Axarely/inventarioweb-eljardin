"""
Pruebas unitarias del Módulo de Inventario (plan de pruebas §2.2 y §5): RF-02, RF-03, RF-04, RNF-08.
"""
from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError, transaction

from inventario.excepciones import ExistenciaInsuficiente, MovimientoInvalido
from inventario.models import (
    EntradaInventario, Existencia, MovimientoInventario, SalidaInventario,
)

pytestmark = [pytest.mark.unitaria, pytest.mark.django_db]


def _entrada(producto, bodega, proveedor, usuario, cantidad):
    return EntradaInventario(
        producto=producto, destino=bodega, proveedor=proveedor, usuario=usuario, cantidad=Decimal(str(cantidad))
    )


def _salida(producto, bodega, sucursal, usuario, cantidad):
    return SalidaInventario(
        producto=producto, origen=bodega, destino=sucursal, usuario=usuario, cantidad=Decimal(str(cantidad))
    )


# --- RF-04: Existencia.nivel() y esta_bajo_umbral() (Fig. 8) -----------------------------------

@pytest.mark.parametrize(
    "cantidad, esperado",
    [("0", "agotado"), ("0.01", "bajo"), ("9.99", "bajo"), ("10", "normal"), ("50", "normal")],
)
def test_rf04_nivel_valores_limite(producto, bodega, cantidad, esperado):
    """CP-RF04-04: stock_minimo = 10."""
    existencia = Existencia(producto=producto, ubicacion=bodega, cantidad=Decimal(cantidad))
    assert existencia.nivel() == esperado


@pytest.mark.parametrize("cantidad, esperado", [("9.99", True), ("10", False), ("0", True)])
def test_rf04_esta_bajo_umbral_limite_exacto(producto, bodega, cantidad, esperado):
    existencia = Existencia(producto=producto, ubicacion=bodega, cantidad=Decimal(cantidad))
    assert existencia.esta_bajo_umbral() is esperado


def test_rf04_existencia_unica_por_producto_ubicacion(producto, bodega):
    """CP-RF04-03."""
    Existencia.objects.create(producto=producto, ubicacion=bodega)
    with pytest.raises(IntegrityError), transaction.atomic():
        Existencia.objects.create(producto=producto, ubicacion=bodega)


def test_rf04_actualizar_cantidad_rechaza_resultado_negativo(producto, bodega, con_existencia):
    existencia = con_existencia(producto, bodega, 3)
    with pytest.raises(ExistenciaInsuficiente) as error:
        existencia.actualizar_cantidad(Decimal("-5"))
    assert error.value.disponible == Decimal("3")
    existencia.refresh_from_db()
    assert existencia.cantidad == Decimal("3")


def test_rf04_ubicaciones_independientes(producto, bodega, santa_cruz, pena_blanca, proveedor, bodeguero):
    """CP-RF04-02: una salida a Santa Cruz no toca Peña Blanca."""
    _entrada(producto, bodega, proveedor, bodeguero, 50).aplicar()
    _salida(producto, bodega, pena_blanca, bodeguero, 5).aplicar()
    _salida(producto, bodega, santa_cruz, bodeguero, 10).aplicar()
    assert Existencia.objects.get(producto=producto, ubicacion=pena_blanca).cantidad == Decimal("5")
    assert Existencia.objects.get(producto=producto, ubicacion=santa_cruz).cantidad == Decimal("10")


def test_rf04_existencia_igual_suma_de_movimientos(
    producto, otro_producto, bodega, santa_cruz, pena_blanca, proveedor, bodeguero
):
    """CP-RF04-01: invariante principal. La existencia persistida = suma de movimientos vigentes."""
    secuencia = [
        ("E", producto, None, 40), ("E", otro_producto, None, 12.5), ("S", producto, santa_cruz, 15),
        ("S", producto, pena_blanca, 7.25), ("E", producto, None, 3), ("S", otro_producto, santa_cruz, 12.5),
        ("S", producto, santa_cruz, 20.75),
    ]
    for tipo, prod, sucursal, cantidad in secuencia:
        if tipo == "E":
            _entrada(prod, bodega, proveedor, bodeguero, cantidad).aplicar()
        else:
            _salida(prod, bodega, sucursal, bodeguero, cantidad).aplicar()

    for existencia in Existencia.objects.all():
        vigentes = MovimientoInventario.objects.filter(producto=existencia.producto, anulado=False)
        entra = sum((m.cantidad for m in vigentes.filter(destino=existencia.ubicacion)), Decimal("0"))
        sale = sum((m.cantidad for m in vigentes.filter(origen=existencia.ubicacion)), Decimal("0"))
        assert existencia.cantidad == entra - sale, existencia


# --- RF-02: EntradaInventario.aplicar() ----------------------------------------------------------

def test_rf02_entrada_suma_cantidad_exacta(producto, bodega, proveedor, bodeguero, con_existencia):
    """CP-RF02-01: 128 + 12.5 = 140.5 exactos (Decimal)."""
    con_existencia(producto, bodega, 128)
    _entrada(producto, bodega, proveedor, bodeguero, "12.5").aplicar()
    assert Existencia.objects.get(producto=producto, ubicacion=bodega).cantidad == Decimal("140.50")


def test_rf02_entrada_crea_existencia_si_no_existe(producto, bodega, proveedor, bodeguero):
    """CP-RF02-02."""
    entrada = _entrada(producto, bodega, proveedor, bodeguero, 10).aplicar()
    assert entrada.pk is not None
    assert entrada.tipo == MovimientoInventario.Tipo.ENTRADA
    assert Existencia.objects.get(producto=producto, ubicacion=bodega).cantidad == Decimal("10")


@pytest.mark.parametrize("cantidad", ["0", "-1"])
def test_rf02_cantidad_invalida_rechazada(producto, bodega, proveedor, bodeguero, cantidad):
    """CP-RF02-04 (UC02 E1)."""
    with pytest.raises(MovimientoInvalido):
        _entrada(producto, bodega, proveedor, bodeguero, cantidad).aplicar()
    assert not MovimientoInventario.objects.exists()
    assert not Existencia.objects.exists()


def test_rf02_requiere_proveedor_activo(producto, bodega, proveedor_inactivo, bodeguero):
    """CP-RF02-05 / RF-11."""
    with pytest.raises(MovimientoInvalido, match="desactivado"):
        _entrada(producto, bodega, proveedor_inactivo, bodeguero, 5).aplicar()
    assert not MovimientoInventario.objects.exists()


def test_rf02_rechaza_producto_inactivo(producto, bodega, proveedor, bodeguero):
    producto.activo = False
    producto.save()
    with pytest.raises(MovimientoInvalido, match="desactivado"):
        _entrada(producto, bodega, proveedor, bodeguero, 5).aplicar()


def test_rf02_entrada_solo_en_bodega(producto, santa_cruz, proveedor, bodeguero):
    with pytest.raises(MovimientoInvalido, match="bodega"):
        _entrada(producto, santa_cruz, proveedor, bodeguero, 5).aplicar()


def test_rf02_falla_no_deja_cambios_parciales(producto, bodega, proveedor, bodeguero):
    """CP-RF02-06 (UC02 E2, RNF-08): si falla la actualización de la existencia no queda el movimiento."""
    with mock.patch.object(Existencia, "actualizar_cantidad", side_effect=RuntimeError("falla de BD")):
        with pytest.raises(RuntimeError):
            _entrada(producto, bodega, proveedor, bodeguero, 5).aplicar()
    assert not MovimientoInventario.objects.exists()
    assert not Existencia.objects.filter(cantidad__gt=0).exists()


# --- RF-03: SalidaInventario.aplicar() ------------------------------------------------------------

def test_rf03_salida_resta_bodega_y_suma_sucursal(producto, bodega, santa_cruz, bodeguero, con_existencia):
    """CP-RF03-01: bodega 18 y Santa Cruz 5; se envían 8 -> 10 y 13."""
    con_existencia(producto, bodega, 18)
    con_existencia(producto, santa_cruz, 5)
    salida = _salida(producto, bodega, santa_cruz, bodeguero, 8).aplicar()
    assert salida.tipo == MovimientoInventario.Tipo.SALIDA
    assert Existencia.objects.get(producto=producto, ubicacion=bodega).cantidad == Decimal("10")
    assert Existencia.objects.get(producto=producto, ubicacion=santa_cruz).cantidad == Decimal("13")


def test_rf03_salida_crea_existencia_en_sucursal(producto, bodega, santa_cruz, bodeguero, con_existencia):
    """CP-RF03-02."""
    con_existencia(producto, bodega, 10)
    _salida(producto, bodega, santa_cruz, bodeguero, 4).aplicar()
    assert Existencia.objects.get(producto=producto, ubicacion=santa_cruz).cantidad == Decimal("4")


def test_rf03_existencia_insuficiente_rechaza_y_sugiere_maximo(
    producto, bodega, santa_cruz, bodeguero, con_existencia
):
    """CP-RF03-03 (UC03 E1 + A1): se informa el máximo disponible y nada cambia."""
    con_existencia(producto, bodega, 12)
    with pytest.raises(ExistenciaInsuficiente) as error:
        _salida(producto, bodega, santa_cruz, bodeguero, 15).aplicar()
    assert error.value.disponible == Decimal("12")
    assert "Solo hay 12 kg disponibles en Bodega central" in error.value.messages[0]
    assert Existencia.objects.get(producto=producto, ubicacion=bodega).cantidad == Decimal("12")
    assert not Existencia.objects.filter(ubicacion=santa_cruz).exists()
    assert not MovimientoInventario.objects.exists()


def test_rf03_sin_existencia_en_bodega_disponible_cero(producto, bodega, santa_cruz, bodeguero):
    with pytest.raises(ExistenciaInsuficiente) as error:
        _salida(producto, bodega, santa_cruz, bodeguero, 1).aplicar()
    assert error.value.disponible == Decimal("0")


def test_rf03_salida_por_el_total_deja_agotado(producto, bodega, santa_cruz, bodeguero, con_existencia):
    """CP-RF03-04: límite exacto."""
    con_existencia(producto, bodega, 12)
    _salida(producto, bodega, santa_cruz, bodeguero, 12).aplicar()
    existencia = Existencia.objects.get(producto=producto, ubicacion=bodega)
    assert existencia.cantidad == Decimal("0")
    assert existencia.nivel() == Existencia.Nivel.AGOTADO


def test_rf03_origen_bodega_destino_sucursal(producto, bodega, santa_cruz, pena_blanca, bodeguero, con_existencia):
    """CP-RF03-07."""
    con_existencia(producto, bodega, 10)
    con_existencia(producto, santa_cruz, 10)
    with pytest.raises(MovimientoInvalido, match="partir de la bodega"):
        _salida(producto, santa_cruz, pena_blanca, bodeguero, 1).aplicar()
    with pytest.raises(MovimientoInvalido, match="debe ser una sucursal"):
        _salida(producto, bodega, bodega, bodeguero, 1).aplicar()


def test_rf03_falla_en_destino_revierte_origen(producto, bodega, santa_cruz, bodeguero, con_existencia):
    """RNF-08: si falla la suma en la sucursal, la resta en bodega también se revierte."""
    con_existencia(producto, bodega, 10)
    original = Existencia.actualizar_cantidad
    llamadas = []

    def falla_en_segunda(self, delta):
        llamadas.append(delta)
        if len(llamadas) == 2:
            raise RuntimeError("falla al actualizar la sucursal")
        return original(self, delta)

    with mock.patch.object(Existencia, "actualizar_cantidad", falla_en_segunda):
        with pytest.raises(RuntimeError):
            _salida(producto, bodega, santa_cruz, bodeguero, 4).aplicar()
    assert Existencia.objects.get(producto=producto, ubicacion=bodega).cantidad == Decimal("10")
    assert not MovimientoInventario.objects.exists()


def test_rf02_existencia_maxima_controlada(producto, bodega, proveedor, bodeguero, con_existencia):
    """Regresión R-04: superar numeric(10,2) da un error controlado, no un DataError (500)."""
    con_existencia(producto, bodega, "99999999.00")
    with pytest.raises(MovimientoInvalido, match="supera el máximo"):
        _entrada(producto, bodega, proveedor, bodeguero, 5).aplicar()
    assert Existencia.objects.get(producto=producto, ubicacion=bodega).cantidad == Decimal("99999999.00")


def test_rf04_aplicar_base_no_implementado(producto, bodeguero):
    with pytest.raises(NotImplementedError):
        MovimientoInventario(producto=producto, usuario=bodeguero, cantidad=1).aplicar()


def test_rf04_ubicacion_tipo_automatico(bodega, santa_cruz):
    assert bodega.tipo == "bodega" and bodega.es_bodega
    assert santa_cruz.tipo == "sucursal" and santa_cruz.es_sucursal


def test_rf04_existencia_total_de_ubicacion(producto, otro_producto, bodega, con_existencia):
    con_existencia(producto, bodega, "10.5")
    con_existencia(otro_producto, bodega, 4)
    assert bodega.existencia_total() == Decimal("14.5")
