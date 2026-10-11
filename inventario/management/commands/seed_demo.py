"""
Datos de demostración: bodega central, sucursales Santa Cruz y Peña Blanca, productos de los
wireframes (Fig. 17), proveedores (Fig. 19), un usuario por rol y movimientos iniciales.

Es idempotente: se puede ejecutar varias veces. Los movimientos iniciales solo se crean si todavía
no hay movimientos, y se registran con los mismos servicios que usa la aplicación, de modo que las
existencias quedan coherentes con el historial (RF-04).
"""
import os
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventario import servicios
from inventario.models import Bodega, MovimientoInventario, Sucursal
from proveedores.models import Proveedor
from usuarios.models import Producto, Rol, Usuario
from usuarios.roles import rol_base, sincronizar_roles_base

PASSWORD_DEMO_DEV = "JardinDemo-2026"

PRODUCTOS = [
    # nombre, categoría, unidad, stock mínimo
    ("Aceite vegetal 1L", "Abarrotes", "u.", 10),
    ("Pechuga de pollo", "Cárnicos", "kg", 10),
    ("Arroz 1 lb", "Abarrotes", "u.", 20),
    ("Servilletas", "Desechables", "paq.", 5),
    ("Refresco de cola 2L", "Bebidas", "u.", 12),
    ("Queso mozzarella", "Lácteos", "kg", 8),
]

PROVEEDORES = [
    ("Distribuidora Central S.A.", "9500-1234", True),
    ("Avícola El Progreso", "9500-5678", True),
    ("Lácteos Selectos", "9500-9012", False),
]

# producto -> (entrada a bodega, salida a Santa Cruz, salida a Peña Blanca)
MOVIMIENTOS = {
    "Aceite vegetal 1L": (60, 8, 30),
    "Pechuga de pollo": (128, 22, 25),
    "Arroz 1 lb": (150, 45, 40),
    "Servilletas": (30, 3, 10),
    "Refresco de cola 2L": (80, 30, 20),
    "Queso mozzarella": (40, 6, 15),
}


class Command(BaseCommand):
    help = "Carga datos de demostración (ubicaciones, catálogo, proveedores, usuarios por rol, movimientos)."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Contraseña de los usuarios demo (o variable DEMO_PASSWORD).")

    @transaction.atomic
    def handle(self, *args, **opciones):
        password = opciones.get("password") or os.environ.get("DEMO_PASSWORD")
        if not password:
            if not settings.DEBUG:
                raise CommandError("En producción indique --password o la variable DEMO_PASSWORD.")
            password = PASSWORD_DEMO_DEV

        sincronizar_roles_base()
        bodega, _ = Bodega.objects.get_or_create(
            nombre="Bodega central", defaults={"direccion": "Santa Cruz", "capacidad_max": 5000}
        )
        santa_cruz, _ = Sucursal.objects.get_or_create(
            nombre="Santa Cruz", defaults={"direccion": "Santa Cruz", "horario": "Lun-Dom 10:00-22:00"}
        )
        pena_blanca, _ = Sucursal.objects.get_or_create(
            nombre="Peña Blanca", defaults={"direccion": "Peña Blanca", "horario": "Lun-Dom 10:00-22:00"}
        )

        productos = {}
        for nombre, categoria, unidad, minimo in PRODUCTOS:
            productos[nombre], _ = Producto.objects.get_or_create(
                nombre=nombre,
                defaults={"categoria": categoria, "unidad_medida": unidad, "stock_minimo": Decimal(minimo)},
            )

        proveedores = []
        for nombre, contacto, activo in PROVEEDORES:
            proveedor, _ = Proveedor.objects.get_or_create(nombre=nombre, defaults={"contacto": contacto, "activo": activo})
            proveedores.append(proveedor)

        usuarios = [
            ("Dueña Demo", "duena@eljardin.test", Rol.Codigo.DUENO, None),
            ("Bodeguero Demo", "bodeguero@eljardin.test", Rol.Codigo.BODEGUERO, None),
            ("Encargado Santa Cruz", "encargado.santacruz@eljardin.test", Rol.Codigo.ENCARGADO, santa_cruz),
            ("Encargada Peña Blanca", "encargada.penablanca@eljardin.test", Rol.Codigo.ENCARGADO, pena_blanca),
        ]
        creados = 0
        for nombre, correo, codigo, sucursal in usuarios:
            usuario = Usuario.objects.filter(correo=correo).first()
            if usuario is None:
                Usuario.objects.create_user(
                    correo=correo, password=password, nombre=nombre, rol=rol_base(codigo), sucursal=sucursal
                )
                creados += 1

        movimientos = 0
        if not MovimientoInventario.objects.exists():
            bodeguero = Usuario.objects.get(correo="bodeguero@eljardin.test")
            for nombre, (entrada, a_santa_cruz, a_pena_blanca) in MOVIMIENTOS.items():
                producto = productos[nombre]
                proveedor = proveedores[1] if producto.categoria == "Cárnicos" else proveedores[0]
                servicios.registrar_entrada(producto.pk, Decimal(entrada), proveedor.pk, bodeguero.pk)
                servicios.registrar_salida(producto.pk, Decimal(a_santa_cruz), santa_cruz.pk, bodeguero.pk)
                servicios.registrar_salida(producto.pk, Decimal(a_pena_blanca), pena_blanca.pk, bodeguero.pk)
                movimientos += 3
            # Deja un producto agotado en bodega para ver el estado "Agotado" (Fig. 17).
            servilletas = productos["Servilletas"]
            restante = servicios.existencia_en_bodega(servilletas.pk).cantidad
            if restante:
                servicios.registrar_salida(servilletas.pk, restante, santa_cruz.pk, bodeguero.pk)
                movimientos += 1

        self.stdout.write(self.style.SUCCESS(
            f"Datos demo listos: {bodega}, {santa_cruz}, {pena_blanca}; {len(productos)} productos; "
            f"{len(proveedores)} proveedores; {creados} usuarios nuevos; {movimientos} movimientos nuevos."
        ))
        if creados:
            self.stdout.write("Usuarios demo (misma contraseña para todos):")
            for nombre, correo, codigo, _ in usuarios:
                self.stdout.write(f"  {Rol.Codigo(codigo).label:<22} {correo}")
