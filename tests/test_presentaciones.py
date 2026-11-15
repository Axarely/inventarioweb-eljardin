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
    """Producto de prueba por unidad, en paquete de 6 (los del catálogo real cambian con la clienta)."""
    return Producto.objects.create(
        nombre="Queso de prueba", categoria=categoria_fija("Lácteos"), unidad_medida="unidad", stock_minimo=0,
        presentacion="paquete", unidades_por_presentacion=6,
    )


@pytest.fixture
def leche(db):
    """Producto que llega por caja, pero todavía sin definir cuántas unidades trae."""
    return Producto.objects.create(
        nombre="Yogur bebible", categoria=categoria_fija("Lácteos"), unidad_medida="unidad", stock_minimo=0,
        presentacion="caja",
    )


def existencia(producto, ubicacion):
    fila = Existencia.objects.filter(producto=producto, ubicacion=ubicacion).first()
    return fila.cantidad if fila else Decimal("0")


def test_d37_catalogo_de_lacteos():
    lacteos = {p.nombre: (p.unidad_medida, p.presentacion, p.unidades_por_presentacion)
               for p in Producto.objects.filter(categoria__nombre="Lácteos")}
    assert lacteos == {  # con las correcciones de la clienta (migración usuarios.0009, D-38)
        "Leche entera": ("unidad", "caja", 24),
        "Queso mozzarella": ("lb", "bolsa", 5),  # queso rallado (D-39)
        "Queso Sula": ("unidad", "paquete", 16),
        "Margarina con ajo": ("unidad", "", None),
    }


def test_d37_textos_de_presentacion(queso, leche):
    assert queso.descripcion_presentacion() == "Paquete de 6 unidades"
    assert leche.descripcion_presentacion() == "Caja"  # sin cantidad definida: solo el nombre corto
    assert queso.en_presentaciones(Decimal("20")) == "3 paquetes + 2 unidades"
    assert queso.en_presentaciones(Decimal("6")) == "1 paquete"
    assert leche.en_presentaciones(Decimal("20")) == ""  # sin dato, no se inventa


def test_d37_entrada_por_paquetes(cliente_de, bodeguero, bodega, queso, proveedor):
    respuesta = cliente_de(bodeguero).post(reverse("inventario:entrada"), {
        "producto": queso.pk, "cantidad": "3", "medida": "presentacion", "proveedor": proveedor.pk,
    }, follow=True)
    assert existencia(queso, bodega) == Decimal("18")
    assert "Entrada registrada: +18 unidad (3 paquetes de 6) de Queso de prueba" in respuesta.content.decode()


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
    assert "no tiene configurado cuánto trae cada caja, paquete o bolsa" in str(respuesta.context["form"].errors["medida"])
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
    assert "Indique la presentación: caja, paquete o bolsa." in str(respuesta.context["form"].errors["presentacion"])


def test_d37_catalogo_muestra_falta_definir(cliente_de, dueno, leche):
    html = cliente_de(dueno).get(reverse("usuarios:productos"), {"categoria": categoria_fija("Lácteos").pk}).content.decode()
    assert "Paquete de 16 unidades" in html and "Bolsa de 5 lb" in html
    assert "<td>Caja</td>" in html and "Falta definir" not in html and "sin definir" not in html


def test_d38_queso_sula_paquete_de_16(cliente_de, bodeguero, bodega, proveedor):
    sula = Producto.objects.get(nombre="Queso Sula")
    assert sula.descripcion_presentacion() == "Paquete de 16 unidades"
    cliente_de(bodeguero).post(reverse("inventario:entrada"), {
        "producto": sula.pk, "cantidad": "2", "medida": "presentacion", "proveedor": proveedor.pk,
    })
    assert existencia(sula, bodega) == Decimal("32")


def test_d38_leche_entera_caja_de_24_y_margarina_por_unidad():
    leche = Producto.objects.get(nombre="Leche entera")
    assert leche.descripcion_presentacion() == "Caja de 24 unidades" and leche.en_presentaciones(Decimal("50")) == "2 cajas + 2 unidades"
    assert not Producto.objects.get(nombre="Margarina con ajo").usa_presentacion


def test_d38_merma_solo_en_proteinas():
    assert not Producto.objects.filter(controla_merma=True).exclude(categoria__nombre="Proteínas").exists()
    assert Producto.objects.filter(controla_merma=True, categoria__nombre="Proteínas").count() == 8


def test_d38_no_se_activa_merma_fuera_de_proteinas(cliente_de, dueno):
    respuesta = cliente_de(dueno).post(reverse("usuarios:producto_crear"), {
        "nombre": "Crema ácida", "categoria": categoria_fija("Lácteos").pk, "unidad_medida": "unidad",
        "controla_merma": "on", "stock_minimo": "0",
    })
    assert "solo aplica a productos de la categoría Proteínas" in str(respuesta.context["form"].errors["controla_merma"])
    assert not Producto.objects.filter(nombre="Crema ácida").exists()


def test_d38_merma_si_se_activa_en_proteinas(cliente_de, dueno):
    cliente_de(dueno).post(reverse("usuarios:producto_crear"), {
        "nombre": "Costilla de cerdo", "categoria": categoria_fija("Proteínas").pk, "unidad_medida": "lb",
        "controla_merma": "on", "stock_minimo": "0",
    })
    assert Producto.objects.get(nombre="Costilla de cerdo").controla_merma


def test_d38_formulario_oculta_merma_segun_categoria(cliente_de, dueno):
    html = cliente_de(dueno).get(reverse("usuarios:producto_crear")).content.decode()
    assert 'id="id_controla_merma"' in html
    assert f'var idProteinas = "{categoria_fija("Proteínas").pk}"' in html


def test_d39_mozzarella_rallado_en_bolsas_de_5_lb(cliente_de, bodeguero, bodega, proveedor):
    mozzarella = Producto.objects.get(nombre="Queso mozzarella")
    assert mozzarella.descripcion_presentacion() == "Bolsa de 5 lb"
    respuesta = cliente_de(bodeguero).post(reverse("inventario:entrada"), {
        "producto": mozzarella.pk, "cantidad": "3", "medida": "presentacion", "proveedor": proveedor.pk,
    }, follow=True)
    assert existencia(mozzarella, bodega) == Decimal("15")
    assert "+15 lb (3 bolsas de 5) de Queso mozzarella" in respuesta.content.decode()
    assert mozzarella.en_presentaciones(Decimal("12.5")) == "2 bolsas + 2.5 lb"
    datos = cliente_de(bodeguero).get(reverse("inventario:existencia_bodega"), {"producto": mozzarella.pk}).json()
    assert datos["presentacion"] == "bolsas" and datos["unidades_por_presentacion"] == 5 and datos["unidad"] == "lb"


def test_d40_catalogo_de_congelados():
    congelados = {p.nombre: (p.unidad_medida, p.presentacion, p.unidades_por_presentacion, p.controla_merma)
                  for p in Producto.objects.filter(categoria__nombre="Congelados")}
    assert congelados == {
        "Nuggets de pollo": ("unidad", "paquete", None, False),
        "Papas": ("unidad", "caja", None, False),
        "Dedos de queso": ("unidad", "paquete", None, False),
        "Tocino": ("lb", "", None, False),
        "Yuca": ("lb", "", None, False),
    }


def test_d40_congelados_sin_cantidad_definida_se_registran_por_unidad(cliente_de, bodeguero, bodega, proveedor):
    nuggets = Producto.objects.get(nombre="Nuggets de pollo")
    cliente = cliente_de(bodeguero)
    por_paquete = cliente.post(reverse("inventario:entrada"), {
        "producto": nuggets.pk, "cantidad": "2", "medida": "presentacion", "proveedor": proveedor.pk,
    })
    assert "medida" in por_paquete.context["form"].errors
    cliente.post(reverse("inventario:entrada"), {"producto": nuggets.pk, "cantidad": "30", "proveedor": proveedor.pk})
    assert existencia(nuggets, bodega) == Decimal("30")
