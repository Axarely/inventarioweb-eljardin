"""
D-35: las cantidades se escriben a mano (sin flechas de subir y bajar) y aceptan decimales con punto o coma y
fracciones: libra y media = "1.5", "1,5", "1 1/2" o "1 y media".
"""
from decimal import Decimal

import pytest
from django.urls import reverse

from config.ui import CampoCantidad, interpretar_cantidad
from inventario.models import Existencia

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("texto, esperado", [
    ("1.5", "1.50"), ("1,5", "1.50"), ("1 1/2", "1.50"), ("1 y 1/2", "1.50"), ("1 y media", "1.50"),
    ("media", "0.50"), ("1/2", "0.50"), ("3", "3.00"), ("2 y cuarto", "2.25"), ("2 y tres cuartos", "2.75"),
    ("0,25", "0.25"), ("  10 ", "10.00"), ("10.333", "10.33"),
])
def test_d35_interpretar_cantidad(texto, esperado):
    assert interpretar_cantidad(texto) == Decimal(esperado)


@pytest.mark.parametrize("texto", ["abc", "1 5", "1/0", "", "1 1/2 3", "uno"])
def test_d35_cantidades_invalidas(texto):
    with pytest.raises((ValueError, ArithmeticError)):
        interpretar_cantidad(texto)


def test_d35_campo_es_de_texto_sin_flechas():
    html = CampoCantidad(label="Cantidad").widget.render("cantidad", "")
    assert 'type="text"' in html and 'inputmode="decimal"' in html
    assert "step=" not in html and 'type="number"' not in html


@pytest.mark.parametrize("escrito", ["1,5", "1 1/2", "1 y media"])
def test_d35_entrada_de_libra_y_media(cliente_de, bodeguero, bodega, proteina_merma, proveedor, escrito):
    respuesta = cliente_de(bodeguero).post(
        reverse("inventario:entrada"),
        {"producto": proteina_merma.pk, "cantidad": escrito, "proveedor": proveedor.nombre}, follow=True,
    )
    assert "Entrada registrada: +1.5 lb de Alitas de pollo" in respuesta.content.decode()
    assert Existencia.objects.get(producto=proteina_merma, ubicacion=bodega).cantidad == Decimal("1.5")


def test_d35_formularios_sin_campos_numericos_con_flechas(cliente_de, bodeguero, dueno, encargado_sc, bodega):
    paginas = [
        (bodeguero, reverse("inventario:entrada")), (bodeguero, reverse("inventario:salida")),
        (encargado_sc, reverse("inventario:consumo")), (dueno, reverse("usuarios:producto_crear")),
    ]
    for usuario, url in paginas:
        html = cliente_de(usuario).get(url).content.decode()
        assert 'type="number"' not in html, url
        assert 'inputmode="decimal"' in html, url


def test_d35_stock_minimo_escrito_con_coma(cliente_de, dueno):
    from conftest import categoria_fija
    from usuarios.models import Producto

    cliente_de(dueno).post(reverse("usuarios:producto_crear"), {
        "nombre": "Camarón jumbo", "categoria": categoria_fija("Proteínas").pk, "unidad_medida": "lb",
        "stock_minimo": "2,5",
    })
    assert Producto.objects.get(nombre="Camarón jumbo").stock_minimo == Decimal("2.5")


def test_d35_peso_real_escrito_como_fraccion(cliente_de, bodeguero, bodega, proteina_merma, proveedor):
    from inventario import servicios

    entrada = servicios.registrar_entrada(proteina_merma.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    cliente_de(bodeguero).post(reverse("inventario:peso_real"), {"control": entrada.control_merma.pk, "peso_real": "8 1/2"})
    entrada.control_merma.refresh_from_db()
    assert entrada.control_merma.peso_real == Decimal("8.5")
