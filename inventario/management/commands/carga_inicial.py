"""
D-44: carga inicial de PRODUCCIÓN con el catálogo real del restaurante (inventario/datos/catalogo_inicial.json):
bodega, sucursales, categorías agregadas y productos tal como la clienta los configuró. NO carga movimientos,
existencias, proveedores ni usuarios de demostración: el inventario empieza en 0.

Se ejecuta en cada build de Render (build.sh) pero solo actúa la primera vez: si ya hay alguna ubicación
registrada no hace nada, para no pisar los cambios que el dueño haga después en el sistema.
"""
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from inventario.models import Bodega, Sucursal, Ubicacion
from usuarios.models import Categoria, Producto

ARCHIVO = Path(__file__).resolve().parents[2] / "datos" / "catalogo_inicial.json"


class Command(BaseCommand):
    help = "Carga, una sola vez, la bodega, las sucursales y el catálogo real del restaurante."

    @transaction.atomic
    def handle(self, *args, **opciones):
        if Ubicacion.objects.exists():
            self.stdout.write("Carga inicial omitida: el sistema ya tiene datos.")
            return
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        for b in datos["bodegas"]:
            Bodega.objects.create(**b)
        for s in datos["sucursales"]:
            Sucursal.objects.create(**s)
        for nombre in datos["categorias_agregadas"]:
            if Categoria.buscar_equivalente(nombre) is None:
                Categoria.objects.create(nombre=nombre)
        for p in datos["productos"]:
            campos = dict(p)
            nombre = campos.pop("nombre")
            campos["categoria"] = Categoria.buscar_equivalente(campos.pop("categoria"))
            campos["stock_minimo"] = Decimal(campos["stock_minimo"])
            producto = Producto.objects.filter(nombre__iexact=nombre).first() or Producto(nombre=nombre)
            for campo, valor in campos.items():
                setattr(producto, campo, valor)
            producto.save()
        self.stdout.write(self.style.SUCCESS(
            f"Carga inicial lista: {len(datos['bodegas']) + len(datos['sucursales'])} ubicaciones y "
            f"{len(datos['productos'])} productos."
        ))
