"""
D-43: el Queso mozzarella rallado se cuenta por BOLSA (dato de la clienta, 2026-11-15): en la existencia se
anota "hay 5 bolsas" y ya se sabe que cada una es de 5 lb. La unidad de medida pasa a "bolsa de 5 lb" y se
quita la presentación (la bolsa ya es la unidad). Como en D-39, se cambia aunque haya movimientos porque la
clienta lo indicó expresamente; en la BD de desarrollo eran datos de prueba y no se convierten.
"""
from django.db import migrations


def mozzarella_por_bolsa(apps, schema_editor):
    Producto = apps.get_model("usuarios", "Producto")
    Producto.objects.filter(nombre__iexact="Queso mozzarella").update(
        unidad_medida="bolsa de 5 lb", presentacion="", unidades_por_presentacion=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0013_nuggets_por_paquete"),
    ]

    operations = [
        migrations.RunPython(mozzarella_por_bolsa, migrations.RunPython.noop),
    ]
