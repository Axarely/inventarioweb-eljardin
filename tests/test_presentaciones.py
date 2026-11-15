"""
D-37: productos que se cuentan por unidad pero se compran en cajas o paquetes (p. ej. paquete de 6).
"""
from decimal import Decimal

import pytest
from django.urls import reverse

from conftest import categoria_fija
from inventario.models import Existencia
from usuarios.models import Producto

pytestmark = pytest.mark.django_db


@pytest.fixture
def queso(db):
    """Queso Zula (migración usuarios.0008): por unidad, paquete de 6."""
    return Producto.objects.get(nombre="Queso Zula")


@pytest.fixture
def leche(db):
    """Leche entera: por caja, pero sin definir cuántas unidades trae."""
    return Producto.objects.get(nombre="Leche entera")


def existencia(producto, ubicacion):
    fila = Existencia.objects.filter(producto=producto, ubicacion=ubicacion).first()
    return fila.cantidad if fila else Decimal("0")


def test_d37_catalogo_de_lacteos():
    lacteos = {p.nombre: (p.unidad_medida, p.presentacion, p.unidades_por_presentacion)
               for p in Producto.objects.filter(categoria__nombre="Lácteos")}
    assert lacteos == {
        "Leche entera": ("unidad", "caja", None),
        "Queso mozzarella": ("unidad", "paquete", 6),
        "Queso Zula": ("unidad", "paquete", 6),
        "Margarina con ajo": ("unidad", "caja", None),
    }


def test_d37_textos_de_presentacion(queso, leche):
    assert queso.descripcion_presentacion() == "Paquete de 6 unidades"
    assert leche.descripcion_presentacion() == "Caja (unidades sin definir)"
    assert queso.en_presentaciones(Decimal("20")) == "3 paquetes + 2 unidades"
    assert queso.en_presentaciones(Decimal("6")) == "1 paquete"
    assert leche.en_presentaciones(Decimal("20")) == ""  # sin dato, no se inventa


def test_d37_entrada_por_paquetes(cliente_de, bodeguero, bodega, queso, proveedor):
    respuesta = cliente_de(bodeguero).post(reverse("inventario:entrada"), {
        "producto": queso.pk, "cantidad": "3", "medida": "presentacion", "proveedor": proveedor.pk,
    }, follow=True)
    assert existencia(queso, bodega) == Decimal("18")
    assert "Entrada registrada: +18 unidad (3 paquetes de 6) de Queso Zula" in respuesta.content.decode()


def test_d37_entrada_en_unidades_por_defecto(cliente_de, bodeguero, bodega, queso, proveedor):
    cliente_de(bodeguero).post(reverse("inventario:entrada"),
                               {"producto": queso.pk, "cantidad": "4", "proveedor": proveedor.pk})
    assert existencia(queso, bodega) == Decimal("4")


def test_d37_medio_paquete(cliente_de, bodeguero, bodega, queso, proveedor):
    cliente_de(bodeguero).post(reverse("inventario:entrada"), {
        "producto": queso.pk, "cantidad": "1 y media", "medida": "presentacion", "proveedor": proveedor.pk,
    })
    assert existencia(queso, bodega) == Decimal("9")


def test_d37_sin_unidades_definidas_no_se_registra_por_caja(cliente_de, bodeguero, bodega, leche, proveedor):
    respuesta = cliente_de(bodeguero).post(reverse("inventario:entrada"), {
        "producto": leche.pk, "cantidad": "2", "medida": "presentacion", "proveedor": proveedor.pk,
    })
    assert "no tiene configurado cuántas unidades trae" in str(respuesta.context["form"].errors["medida"])
    assert existencia(leche, bodega) == Decimal("0")


def test_d37_salida_por_paquetes_y_validacion_en_unidades(cliente_de, bodeguero, bodega, santa_cruz, queso,
                                                          con_existencia):
    con_existencia(queso, bodega, 20)
    cliente = cliente_de(bodeguero)
    respuesta = cliente.post(reverse("inventario:salida"), {
        "sucursal": santa_cruz.pk, "producto": queso.pk, "cantidad": "4", "medida": "presentacion",
    })  # 4 paquetes = 24 unidades > 20
    assert "Solo hay 20 unidad disponibles" in respuesta.content.decode()
    respuesta = cliente.post(reverse("inventario:salida"), {
        "sucursal": santa_cruz.pk, "producto": queso.pk, "cantidad": "2", "medida": "presentacion",
    }, follow=True)
    assert "Salida registrada: 12 unidad (2 paquetes de 6)" in respuesta.content.decode()
    assert existencia(queso, bodega) == Decimal("8") and existencia(queso, santa_cruz) == Decimal("12")


def test_d37_consumo_por_paquetes(cliente_de, encargado_sc, santa_cruz, queso, con_existencia):
    con_existencia(queso, santa_cruz, 12)
    cliente_de(encargado_sc).post(reverse("inventario:consumo"),
                                  {"producto": queso.pk, "cantidad": "1", "medida": "presentacion"})
    assert existencia(queso, santa_cruz) == Decimal("6")


def test_d37_panel_y_existencias_muestran_paquetes(cliente_de, bodeguero, dueno, bodega, queso, con_existencia):
    con_existencia(queso, bodega, 20)
    datos = cliente_de(bodeguero).get(reverse("inventario:existencia_bodega"), {"producto": queso.pk}).json()
    assert datos["presentacion"] == "paquetes" and datos["unidades_por_presentacion"] == 6
    assert datos["equivalente"] == "3 paquetes + 2 unidades"
    html = cliente_de(dueno).get(reverse("inventario:existencias"), {"ubicacion": bodega.pk}).content.decode()
    assert "3 paquetes + 2 unidades" in html


def test_d37_dueno_define_unidades_por_caja(cliente_de, dueno, bodeguero, bodega, leche, proveedor):
    cliente_de(dueno).post(reverse("usuarios:producto_editar", args=[leche.pk]), {
        "nombre": leche.nombre, "categoria": leche.categoria_id, "unidad_medida": "unidad",
        "presentacion": "caja", "unidades_por_presentacion": "12", "stock_minimo": "0",
    })
    leche.refresh_from_db()
    assert leche.usa_presentacion and leche.unidades_por_presentacion == 12
    cliente_de(bodeguero).post(reverse("inventario:entrada"), {
        "producto": leche.pk, "cantidad": "2", "medida": "presentacion", "proveedor": proveedor.pk,
    })
    assert existencia(leche, bodega) == Decimal("24")


def test_d37_unidades_sin_presentacion_se_rechaza(cliente_de, dueno):
    respuesta = cliente_de(dueno).post(reverse("usuarios:producto_crear"), {
        "nombre": "Yogur", "categoria": categoria_fija("Lácteos").pk, "unidad_medida": "unidad",
        "presentacion": "", "unidades_por_presentacion": "6", "stock_minimo": "0",
    })
    assert "Indique si son cajas o paquetes." in str(respuesta.context["form"].errors["presentacion"])


def test_d37_catalogo_muestra_falta_definir(cliente_de, dueno):
    html = cliente_de(dueno).get(reverse("usuarios:productos"), {"categoria": categoria_fija("Lácteos").pk}).content.decode()
    assert "Paquete de 6 unidades" in html and "Falta definir" in html
