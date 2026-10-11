from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from inventario.models import Bodega, Existencia, MovimientoInventario, Sucursal
from usuarios.models import Usuario

pytestmark = pytest.mark.django_db


def test_rf04_seed_demo_idempotente_y_coherente(settings):
    settings.DEBUG = True
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)
    assert Bodega.objects.count() == 1
    assert set(Sucursal.objects.values_list("nombre", flat=True)) == {"Santa Cruz", "Peña Blanca"}
    assert Usuario.objects.count() == 4
    assert MovimientoInventario.objects.count() == 19
    # RF-04: cada existencia coincide con la suma de sus movimientos
    for existencia in Existencia.objects.all():
        movs = MovimientoInventario.objects.filter(producto=existencia.producto)
        entra = sum((m.cantidad for m in movs.filter(destino=existencia.ubicacion)), Decimal("0"))
        sale = sum((m.cantidad for m in movs.filter(origen=existencia.ubicacion)), Decimal("0"))
        assert existencia.cantidad == entra - sale
    encargado = Usuario.objects.get(correo="encargado.santacruz@eljardin.test")
    assert encargado.sucursal.nombre == "Santa Cruz"
    assert encargado.check_password("JardinDemo-2026")


def test_seed_demo_exige_password_en_produccion(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo", verbosity=0)
