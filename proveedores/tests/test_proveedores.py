"""Pruebas del Módulo de Proveedores (Fig. 19, interfaz IProveedores) — RF-11."""
import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from proveedores import servicios
from proveedores.models import Proveedor

pytestmark = pytest.mark.django_db


@pytest.mark.unitaria
def test_rf11_crear_y_desactivar_proveedor():
    proveedor = servicios.crear_proveedor({"nombre": "Distribuidora Central S.A.", "contacto": "9500-1234"})
    assert proveedor.activo
    assert servicios.desactivar_proveedor(proveedor.pk) is True
    assert servicios.desactivar_proveedor(proveedor.pk) is False  # ya estaba inactivo
    assert servicios.activar_proveedor(proveedor.pk) is True


@pytest.mark.unitaria
def test_rf11_crear_proveedor_valida_nombre_unico(proveedor):
    with pytest.raises(ValidationError):
        servicios.crear_proveedor({"nombre": proveedor.nombre})


@pytest.mark.unitaria
def test_rf11_obtener_proveedor_activo(proveedor, proveedor_inactivo):
    assert servicios.obtener_proveedor_activo(proveedor.pk) == proveedor
    with pytest.raises(ValidationError):
        servicios.obtener_proveedor_activo(proveedor_inactivo.pk)
    assert list(servicios.proveedores_activos()) == [proveedor]


@pytest.mark.unitaria
def test_rf11_metodos_del_modelo(proveedor):
    proveedor.actualizar_contacto("9999-0000")
    proveedor.desactivar()
    proveedor.refresh_from_db()
    assert proveedor.contacto == "9999-0000" and not proveedor.activo


def test_rf11_crud_proveedores_dueno(cliente_de, dueno):
    cliente = cliente_de(dueno)
    cliente.post(reverse("proveedores:crear"), {"nombre": "Avícola El Progreso", "contacto": "9500-5678"})
    proveedor = Proveedor.objects.get()
    cliente.post(reverse("proveedores:editar", args=[proveedor.pk]), {"nombre": "Avícola El Progreso", "contacto": "9500-0000"})
    cliente.post(reverse("proveedores:activar", args=[proveedor.pk]))
    proveedor.refresh_from_db()
    assert proveedor.contacto == "9500-0000" and not proveedor.activo
    cliente.post(reverse("proveedores:activar", args=[proveedor.pk]))
    proveedor.refresh_from_db()
    assert proveedor.activo


def test_rf11_busqueda_proveedores(cliente_de, dueno, proveedor, proveedor_inactivo):
    lista = cliente_de(dueno).get(reverse("proveedores:lista"), {"q": "lácteos"}).context["object_list"]
    assert list(lista) == [proveedor_inactivo]


def test_rf11_bodeguero_no_gestiona_proveedores(cliente_de, bodeguero, proveedor):
    cliente = cliente_de(bodeguero)
    assert cliente.post(reverse("proveedores:activar", args=[proveedor.pk])).status_code == 403
    proveedor.refresh_from_db()
    assert proveedor.activo
