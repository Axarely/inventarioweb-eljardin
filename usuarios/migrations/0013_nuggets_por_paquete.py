"""
D-41: los Nuggets de pollo se cuentan por PAQUETE (dato de la clienta, 2026-11-15): no se van a contar las
unidades que trae cada paquete. La unidad de medida pasa a "paquete" y se quita la presentación (ya es la unidad).
Solo se cambia si el producto no tiene movimientos, para no reinterpretar cantidades registradas.
"""
from django.db import migrations


def nuggets_por_paquete(apps, schema_editor):
    Producto = apps.get_model("usuarios", "Producto")
    MovimientoInventario = apps.get_model("inventario", "MovimientoInventario")
    for nuggets in Producto.objects.filter(nombre__iexact="Nuggets de pollo"):
        if MovimientoInventario.objects.filter(producto=nuggets).exists():
            continue
        nuggets.unidad_medida = "paquete"
        nuggets.presentacion = ""
        nuggets.unidades_por_presentacion = None
        nuggets.save(update_fields=["unidad_medida", "presentacion", "unidades_por_presentacion"])


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0012_catalogo_congelados"),
        ("inventario", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(nuggets_por_paquete, migrations.RunPython.noop),
    ]
