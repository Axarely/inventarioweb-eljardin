"""
D-39: el Queso mozzarella es queso RALLADO: se cuenta en libras y se compra en bolsas de 5 lb (dato de la
clienta, 2026-11-15). Se cambia la unidad aunque haya movimientos porque la clienta lo indicó expresamente;
en la BD de desarrollo esos movimientos eran datos de prueba y no se convierten.
"""
from django.db import migrations


def corregir_mozzarella(apps, schema_editor):
    Producto = apps.get_model("usuarios", "Producto")
    Producto.objects.filter(nombre__iexact="Queso mozzarella").update(
        unidad_medida="lb", presentacion="bolsa", unidades_por_presentacion=5,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0010_presentacion_bolsa"),
    ]

    operations = [
        migrations.RunPython(corregir_mozzarella, migrations.RunPython.noop),
    ]
