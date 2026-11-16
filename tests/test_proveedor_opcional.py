"""D-45: en la entrada el proveedor es opcional y se escribe (sugiere los existentes, crea los nuevos)."""
from decimal import Decimal

import pytest
from django.urls import reverse

from inventario.models import EntradaInventario
from proveedores.models import Proveedor

pytestmark = pytest.mark.django_db
URL = reverse("inventario:entrada")


def test_entrada_sin_proveedor(cliente_de, bodeguero, bodega, producto):
    respuesta = cliente_de(bodeguero).post(URL, {"producto": producto.pk, "cantidad": "5", "proveedor": ""})
    assert respuesta.status_code == 302
    entrada = EntradaInventario.objects.get()
    assert entrada.proveedor is None and entrada.cantidad == Decimal("5")
    historial = cliente_de(bodeguero).get(reverse("inventario:historial")).content.decode()
    assert "obligatorio" not in historial


def test_proveedor_escrito_nuevo_se_crea(cliente_de, bodeguero, bodega, producto):
    cliente_de(bodeguero).post(URL, {"producto": producto.pk, "cantidad": "5", "proveedor": "  Pollos  Doña Marta "})
    assert EntradaInventario.objects.get().proveedor.nombre == "Pollos Doña Marta"


def test_proveedor_escrito_existente_se_reutiliza(cliente_de, bodeguero, bodega, producto, proveedor):
    cliente_de(bodeguero).post(URL, {"producto": producto.pk, "cantidad": "5", "proveedor": proveedor.nombre.upper()})
    assert EntradaInventario.objects.get().proveedor == proveedor and Proveedor.objects.count() == 1


def test_proveedor_desactivado_se_rechaza(cliente_de, bodeguero, bodega, producto, proveedor_inactivo):
    respuesta = cliente_de(bodeguero).post(URL, {"producto": producto.pk, "cantidad": "5", "proveedor": proveedor_inactivo.nombre})
    assert "desactivado" in respuesta.context["form"].errors["proveedor"][0]
    assert not EntradaInventario.objects.exists()


def test_formulario_sugiere_proveedores_activos(cliente_de, bodeguero, bodega, proveedor, proveedor_inactivo):
    html = cliente_de(bodeguero).get(URL).content.decode()
    assert 'list="lista-proveedores"' in html and f'<option value="{proveedor.nombre}">' in html
    assert proveedor_inactivo.nombre not in html and "Proveedor (opcional)" in html
