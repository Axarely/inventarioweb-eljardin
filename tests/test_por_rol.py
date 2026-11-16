"""
Recorrido por ROL (pedido de la clienta, 2026-11-15): con cada rol base se abren todas las páginas de su menú
y se usan las funciones que le tocan (proveedor escrito D-45, presentación escrita D-46, presentaciones D-37).
"""
import re
from decimal import Decimal

import pytest
from django.urls import reverse

from conftest import categoria_fija
from inventario.models import EntradaInventario, Existencia
from usuarios.models import Producto, Usuario

pytestmark = pytest.mark.django_db


def enlaces_del_menu(cliente):
    html = cliente.get(reverse("inicio"), follow=True).content.decode()  # el dueño va directo al Dashboard
    enlaces = set(re.findall(r'href="(/[^"#?]*)"', html))
    return sorted(e for e in enlaces if not e.startswith("/static") and "salir" not in e and "logout" not in e)


@pytest.mark.parametrize("rol", ["dueno", "bodeguero", "encargado_sc", "superusuario"])
def test_todas_las_paginas_del_menu_abren(request, rol, cliente_de, bodega, producto, proveedor):
    if rol == "superusuario":
        usuario = Usuario.objects.create_superuser("admin@eljardin.test", "Clave-segura-2026", nombre="Admin")
    else:
        usuario = request.getfixturevalue(rol)
    cliente = cliente_de(usuario)
    enlaces = enlaces_del_menu(cliente)
    assert len(enlaces) >= 3, enlaces
    for enlace in enlaces:
        respuesta = cliente.get(enlace, follow=True)
        assert respuesta.status_code == 200, (rol, enlace, respuesta.status_code)


def test_bodeguero_crea_producto_con_presentacion_escrita_y_registra_con_proveedor_escrito(cliente_de, bodeguero, bodega):
    cliente = cliente_de(bodeguero)
    html = cliente.get(reverse("usuarios:producto_crear")).content.decode()
    assert 'list="lista-presentacion"' in html
    cliente.post(reverse("usuarios:producto_crear"), {
        "nombre": "Maicena", "categoria": categoria_fija("Abarrotes").pk, "unidad_medida": "lb",
        "presentacion": "saco", "unidades_por_presentacion": "50", "stock_minimo": "0",
    })
    harina = Producto.objects.get(nombre="Maicena")
    assert harina.descripcion_presentacion() == "Saco de 50 lb"
    html = cliente.get(reverse("inventario:entrada")).content.decode()
    assert "Proveedor (opcional)" in html
    cliente.post(reverse("inventario:entrada"), {
        "producto": harina.pk, "cantidad": "2", "medida": "presentacion", "proveedor": "Molino Nuevo",
    })
    entrada = EntradaInventario.objects.get()
    assert entrada.cantidad == Decimal("100") and entrada.proveedor.nombre == "Molino Nuevo"
    cliente.post(reverse("inventario:entrada"), {"producto": harina.pk, "cantidad": "5", "proveedor": ""})
    assert Existencia.objects.get(producto=harina, ubicacion=bodega).cantidad == Decimal("105")


def test_dueno_edita_presentacion_escrita(cliente_de, dueno, producto):
    cliente = cliente_de(dueno)
    assert 'list="lista-presentacion"' in cliente.get(reverse("usuarios:producto_editar", args=[producto.pk])).content.decode()
    cliente.post(reverse("usuarios:producto_editar", args=[producto.pk]), {
        "nombre": producto.nombre, "categoria": producto.categoria_id, "unidad_medida": "unidad",
        "presentacion": "Bote", "unidades_por_presentacion": "4", "stock_minimo": "0",
    })
    producto.refresh_from_db()
    assert producto.descripcion_presentacion() == "Bote de 4 unidades"
    assert "Bote de 4 unidades" in cliente.get(reverse("usuarios:productos"), {"q": producto.nombre}).content.decode()


def test_encargado_reporta_consumo_por_presentacion_escrita(cliente_de, encargado_sc, santa_cruz, producto, con_existencia):
    Producto.objects.filter(pk=producto.pk).update(unidad_medida="unidad", presentacion="bote", unidades_por_presentacion=4)
    con_existencia(producto, santa_cruz, 20)
    respuesta = cliente_de(encargado_sc).post(reverse("inventario:consumo"), {
        "producto": producto.pk, "cantidad": "2", "medida": "presentacion",
    })
    assert respuesta.status_code in (200, 302)
    assert Existencia.objects.get(producto=producto, ubicacion=santa_cruz).cantidad == Decimal("12")


def test_historial_muestra_rol_de_cada_usuario(cliente_de, dueno, bodeguero, encargado_sc, bodega, santa_cruz, producto, proveedor):
    """D-54: el dueño distingue quién registró cada movimiento por su rol (y la sucursal del encargado)."""
    from inventario import servicios
    servicios.registrar_entrada(producto.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    servicios.registrar_salida(producto.pk, Decimal("4"), santa_cruz.pk, bodeguero.pk)
    cliente_de(encargado_sc).post(reverse("inventario:consumo"), {"producto": producto.pk, "cantidad": "1"})
    html = cliente_de(dueno).get(reverse("inventario:historial")).content.decode()
    assert "<th>Rol</th>" in html
    assert "Bodeguero</td>" in html and "Encargado de sucursal · Santa Cruz</td>" in html
