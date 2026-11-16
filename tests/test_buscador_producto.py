"""D-53: en Entradas, Salidas y Reportar consumo el producto se busca escribiendo (y muestra su categoría)."""
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("rol, url", [
    ("bodeguero", "inventario:entrada"),
    ("bodeguero", "inventario:salida"),
    ("encargado_sc", "inventario:consumo"),
])
def test_campo_producto_es_buscador_con_categoria(request, cliente_de, rol, url, bodega):
    html = cliente_de(request.getfixturevalue(rol)).get(reverse(url)).content.decode()
    assert 'class="form-select buscador-producto"' in html or "buscador-producto" in html
    assert "Azúcar · Abarrotes" in html and "Ketchup bolsa · Latas y aderezos" in html
    assert "tom-select" in html and "Escriba o elija un producto…" in html
