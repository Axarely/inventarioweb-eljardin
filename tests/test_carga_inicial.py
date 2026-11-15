"""D-44: carga inicial de producción con el catálogo real (sin datos de demostración)."""
from decimal import Decimal

import pytest
from django.core.management import call_command

from inventario.models import Bodega, Existencia, MovimientoInventario, Sucursal
from proveedores.models import Proveedor
from usuarios.models import Categoria, Producto, Usuario

pytestmark = pytest.mark.django_db


def test_carga_el_catalogo_real_y_nada_de_demostracion():
    call_command("carga_inicial")
    assert Bodega.objects.get().nombre == "Bodega central"
    assert set(Sucursal.objects.values_list("nombre", flat=True)) == {"Santa Cruz", "Peña Blanca"}
    assert Categoria.objects.filter(nombre="Bebidas", es_base=False).exists()
    mozzarella = Producto.objects.get(nombre="Queso mozzarella")
    assert mozzarella.unidad_medida == "bolsa de 5 lb" and mozzarella.categoria.nombre == "Lácteos"
    assert Producto.objects.get(nombre="Alitas de pollo").controla_merma
    assert Producto.objects.filter(nombre__iexact="cebolla").exists()
    assert not MovimientoInventario.objects.exists() and not Existencia.objects.exists()
    assert not Proveedor.objects.exists() and not Usuario.objects.exists()


def test_solo_actua_la_primera_vez():
    call_command("carga_inicial")
    alitas = Producto.objects.get(nombre="Alitas de pollo")
    alitas.stock_minimo = Decimal("20")  # el dueño lo cambia en el sistema
    alitas.save()
    call_command("carga_inicial")  # siguiente despliegue
    alitas.refresh_from_db()
    assert alitas.stock_minimo == Decimal("20") and Bodega.objects.count() == 1
