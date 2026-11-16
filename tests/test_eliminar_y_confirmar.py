"""D-49: eliminar productos sin movimientos y confirmación al cerrar sesión / eliminar."""
from decimal import Decimal

import pytest
from django.urls import reverse

from conftest import categoria_fija
from inventario import servicios
from usuarios.models import Producto

pytestmark = pytest.mark.django_db


@pytest.fixture
def nuevo(db):
    return Producto.objects.create(nombre="Producto de prueba", categoria=categoria_fija("Varios"),
                                   unidad_medida="unidad", stock_minimo=0)


def test_dueno_elimina_producto_sin_movimientos(cliente_de, dueno, nuevo):
    respuesta = cliente_de(dueno).post(reverse("usuarios:producto_eliminar", args=[nuevo.pk]), follow=True)
    assert not Producto.objects.filter(pk=nuevo.pk).exists()
    assert "Producto «Producto de prueba» eliminado." in respuesta.content.decode()


def test_producto_con_movimientos_no_se_elimina(cliente_de, dueno, bodeguero, bodega, nuevo, proveedor):
    servicios.registrar_entrada(nuevo.pk, Decimal("3"), proveedor.pk, bodeguero.pk)
    respuesta = cliente_de(dueno).post(reverse("usuarios:producto_eliminar", args=[nuevo.pk]), follow=True)
    assert Producto.objects.filter(pk=nuevo.pk).exists()
    assert "no se puede eliminar" in respuesta.content.decode()


@pytest.mark.parametrize("rol", ["bodeguero", "encargado_sc"])
def test_otros_roles_no_eliminan(request, rol, cliente_de, nuevo):
    respuesta = cliente_de(request.getfixturevalue(rol)).post(reverse("usuarios:producto_eliminar", args=[nuevo.pk]))
    assert respuesta.status_code == 403 and Producto.objects.filter(pk=nuevo.pk).exists()


def test_catalogo_muestra_eliminar_con_confirmacion(cliente_de, dueno, nuevo):
    html = cliente_de(dueno).get(reverse("usuarios:productos"), {"q": nuevo.nombre}).content.decode()
    assert reverse("usuarios:producto_eliminar", args=[nuevo.pk]) in html
    assert "¿Seguro que quiere eliminar el producto «Producto de prueba»?" in html and ">Eliminar</button>" in html


def test_cerrar_sesion_pide_confirmacion(cliente_de, bodeguero):
    html = cliente_de(bodeguero).get(reverse("inicio"), follow=True).content.decode()
    assert "¿Está seguro de que quiere cerrar sesión?" in html and 'id="modal-confirmar"' in html
    assert "Sí, cerrar sesión" in html
