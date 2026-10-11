"""
Fixtures compartidas (plan de pruebas §3.3): ubicaciones, productos, proveedores y un usuario por rol.
Cada prueba crea sus propios datos; no hay estado compartido entre pruebas.
"""
from decimal import Decimal

import pytest

from inventario.models import Bodega, Existencia, Sucursal
from proveedores.models import Proveedor
from usuarios.models import Producto, Rol, Usuario
from usuarios.roles import rol_base

PASSWORD = "Clave-segura-123"


@pytest.fixture
def bodega(db):
    return Bodega.objects.create(nombre="Bodega central", capacidad_max=5000)


@pytest.fixture
def santa_cruz(db):
    return Sucursal.objects.create(nombre="Santa Cruz")


@pytest.fixture
def pena_blanca(db):
    return Sucursal.objects.create(nombre="Peña Blanca")


@pytest.fixture
def producto(db):
    return Producto.objects.create(
        nombre="Pechuga de pollo", categoria="Cárnicos", unidad_medida="kg", stock_minimo=Decimal("10")
    )


@pytest.fixture
def otro_producto(db):
    return Producto.objects.create(
        nombre="Servilletas", categoria="Desechables", unidad_medida="paq.", stock_minimo=Decimal("5")
    )


@pytest.fixture
def proveedor(db):
    return Proveedor.objects.create(nombre="Avícola El Progreso", contacto="9500-5678")


@pytest.fixture
def proveedor_inactivo(db):
    return Proveedor.objects.create(nombre="Lácteos Selectos", contacto="9500-9012", activo=False)


def _usuario(correo, codigo, nombre, sucursal=None):
    return Usuario.objects.create_user(
        correo=correo, password=PASSWORD, nombre=nombre, rol=rol_base(codigo), sucursal=sucursal
    )


@pytest.fixture
def dueno(db):
    return _usuario("duena@eljardin.test", Rol.Codigo.DUENO, "Dueña")


@pytest.fixture
def bodeguero(db):
    return _usuario("bodeguero@eljardin.test", Rol.Codigo.BODEGUERO, "Bodeguero")


@pytest.fixture
def encargado_sc(db, santa_cruz):
    return _usuario("enc.sc@eljardin.test", Rol.Codigo.ENCARGADO, "Encargado SC", santa_cruz)


@pytest.fixture
def encargado_pb(db, pena_blanca):
    return _usuario("enc.pb@eljardin.test", Rol.Codigo.ENCARGADO, "Encargada PB", pena_blanca)


@pytest.fixture
def cliente_de(client):
    """Devuelve un cliente HTTP con sesión iniciada para el usuario indicado."""

    def _cliente(usuario):
        client.force_login(usuario)
        return client

    return _cliente


@pytest.fixture
def con_existencia():
    """Fija la existencia de un producto en una ubicación (solo para preparar escenarios de prueba)."""

    def _fijar(producto, ubicacion, cantidad):
        existencia, _ = Existencia.objects.update_or_create(
            producto=producto, ubicacion=ubicacion, defaults={"cantidad": Decimal(str(cantidad))}
        )
        return existencia

    return _fijar
