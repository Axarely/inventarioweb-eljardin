"""
D-47: catálogo de Concentrados (dato de la clienta, 2026-11-15). Todos vienen en BOLSA pero se cuentan por
UNIDAD (cada bolsa es una unidad): unidad de medida "unidad" y presentación "bolsa", sin cantidad por
presentación. Sin merma (exclusiva de Proteínas, D-38). Stock mínimo en 0 (lo define el dueño). No duplica.
"""
from django.db import migrations

CONCENTRADOS = [
    "Salsa jalapeña",
    "Salsa de piña chipotle",
    "Concentrado tamarindo",
    "Concentrado limonada",
    "Concentrado maracuyá",
    "Concentrado Jamaica",
    "Concentrado ajillo",
]


def crear_concentrados(apps, schema_editor):
    Categoria = apps.get_model("usuarios", "Categoria")
    Producto = apps.get_model("usuarios", "Producto")
    concentrados = Categoria.objects.filter(nombre__iexact="Concentrados").first()
    if concentrados is None:
        concentrados = Categoria.objects.create(nombre="Concentrados", es_base=True, orden=4)
    for nombre in CONCENTRADOS:
        if Producto.objects.filter(nombre__iexact=nombre).exists():
            continue
        Producto.objects.create(
            nombre=nombre, categoria=concentrados, unidad_medida="unidad", stock_minimo=0,
            presentacion="bolsa", unidades_por_presentacion=None, controla_merma=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0015_presentacion_texto_libre"),
    ]

    operations = [
        migrations.RunPython(crear_concentrados, migrations.RunPython.noop),
    ]
