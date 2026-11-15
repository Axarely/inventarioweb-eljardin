"""
Volumen de datos para medir RNF-01 (respuestas < 2 s): por defecto 200 productos y 5 000 movimientos
repartidos en los últimos 60 días entre la bodega y las sucursales, generados con una semilla fija.

Se insertan en bloque (bulk_create y SQL parametrizado) para que la carga tarde segundos y no minutos,
pero respetan la invariante de RF-04: la existencia de cada producto en cada ubicación es exactamente la
suma de sus movimientos. No genera alertas ni correos. Requiere haber ejecutado antes `seed_demo`.
"""
import random
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from inventario.models import Bodega, Existencia, MovimientoInventario, Sucursal
from proveedores.models import Proveedor
from usuarios.models import Categoria, Producto, Usuario

PREFIJO = "Volumen "
UNIDADES = ["u.", "lb", "paq.", "L"]  # el restaurante no usa kilos


class Command(BaseCommand):
    help = "Carga un volumen de datos coherente para las pruebas de rendimiento (RNF-01)."

    def add_arguments(self, parser):
        parser.add_argument("--productos", type=int, default=200)
        parser.add_argument("--movimientos", type=int, default=5000)
        parser.add_argument("--semilla", type=int, default=2026)

    @transaction.atomic
    def handle(self, *args, productos, movimientos, semilla, **opciones):
        if Producto.objects.filter(nombre__startswith=PREFIJO).exists():
            self.stdout.write("El volumen ya estaba cargado; no se hace nada.")
            return
        try:
            bodega = Bodega.central()
            sucursales = list(Sucursal.objects.order_by("pk"))
            bodeguero = Usuario.objects.get(correo="bodeguero@eljardin.test")
            encargados = {u.sucursal_id: u for u in Usuario.objects.filter(sucursal__isnull=False)}
            proveedor = Proveedor.objects.filter(activo=True).first()
        except Exception as error:
            raise CommandError(f"Ejecute primero `seed_demo`: {error}") from error
        if not sucursales or proveedor is None:
            raise CommandError("Ejecute primero `seed_demo`.")

        azar = random.Random(semilla)
        categorias = list(Categoria.objects.filter(es_base=True))
        nuevos = Producto.objects.bulk_create([
            Producto(
                nombre=f"{PREFIJO}{i:03d}", categoria=azar.choice(categorias), unidad_medida=azar.choice(UNIDADES),
                stock_minimo=Decimal(azar.randint(5, 20)),
            )
            for i in range(1, productos + 1)
        ])

        ahora = timezone.now()
        saldo = defaultdict(Decimal)  # (producto_id, ubicacion_id) -> cantidad
        filas, entradas = [], []

        def agregar(producto, tipo, origen, destino, cantidad, usuario):
            filas.append(MovimientoInventario(
                tipo=tipo, producto=producto, origen=origen, destino=destino, cantidad=cantidad, usuario=usuario,
            ))
            if origen is not None:
                saldo[(producto.pk, origen.pk)] -= cantidad
            if destino is not None:
                saldo[(producto.pk, destino.pk)] += cantidad

        # 1) Una entrada grande por producto: la bodega siempre tiene de dónde enviar.
        for producto in nuevos:
            agregar(producto, "entrada", None, bodega, Decimal(azar.randint(400, 900)), bodeguero)
            entradas.append(len(filas) - 1)
        # 2) Envíos y consumos aleatorios, sin dejar nunca una existencia negativa.
        while len(filas) < movimientos:
            producto = azar.choice(nuevos)
            sucursal = azar.choice(sucursales)
            if azar.random() < 0.45:
                disponible = saldo[(producto.pk, bodega.pk)]
                cantidad = Decimal(azar.randint(1, 15))
                if disponible >= cantidad:
                    agregar(producto, "salida", bodega, sucursal, cantidad, bodeguero)
            else:
                disponible = saldo[(producto.pk, sucursal.pk)]
                cantidad = Decimal(azar.randint(1, 6))
                if disponible >= cantidad:
                    agregar(producto, "salida", sucursal, None, cantidad, encargados.get(sucursal.pk, bodeguero))

        creados = MovimientoInventario.objects.bulk_create(filas, batch_size=1000)
        # Fechas repartidas en 60 días (auto_now_add no permite fijarlas en bulk_create).
        fechas = [(ahora - timedelta(minutes=azar.randint(0, 60 * 24 * 60)), m.pk) for m in creados]
        with connection.cursor() as cursor:
            cursor.executemany("UPDATE inventario_movimientoinventario SET fecha = %s WHERE id = %s", fechas)
            # Filas hijas de la herencia multi-tabla (bulk_create no las crea).
            cursor.executemany(
                "INSERT INTO inventario_entradainventario (movimientoinventario_ptr_id, proveedor_id) VALUES (%s, %s)",
                [(creados[i].pk, proveedor.pk) for i in entradas],
            )
            cursor.executemany(
                "INSERT INTO inventario_salidainventario (movimientoinventario_ptr_id) VALUES (%s)",
                [(m.pk,) for m in creados if m.tipo == "salida"],
            )
        Existencia.objects.bulk_create(
            [Existencia(producto_id=p, ubicacion_id=u, cantidad=c) for (p, u), c in saldo.items()], batch_size=1000
        )
        self.stdout.write(self.style.SUCCESS(
            f"Volumen cargado: {len(nuevos)} productos, {len(creados)} movimientos, {len(saldo)} existencias."
        ))
