"""
D-50: catálogo de Latas y aderezos (dato de la clienta, 2026-11-15). Todos se cuentan por UNIDAD.

Cuando el mismo producto viene en varios envases, el envase va en el NOMBRE (Ketchup bote / bolsa / lata,
Jalapeño lata / bote), porque el nombre de producto es único y así el bodeguero no los confunde al elegirlos.
La presentación se usa solo cuando el producto llega agrupado: Ketchup bolsa viene en CAJA (cantidad por caja
aún sin definir). Sin merma. Stock mínimo en 0. No duplica productos existentes.
"""
from django.db import migrations

# nombre, presentación
LATAS_Y_ADEREZOS = [
    ("Ketchup bote", ""),
    ("Ketchup bolsa", "caja"),
    ("Ketchup lata", ""),
    ("Jalapeño lata", ""),
    ("Jalapeño bote", ""),
    ("Queso lata", ""),
    ("Chile Olancho", ""),
    ("Barbacoa", ""),
    ("Ranch", ""),
    ("Mayonesa", ""),
    ("Vinagre blanco", ""),
]


def crear_latas_y_aderezos(apps, schema_editor):
    Categoria = apps.get_model("usuarios", "Categoria")
    Producto = apps.get_model("usuarios", "Producto")
    categoria = Categoria.objects.filter(nombre__iexact="Latas y aderezos").first()
    if categoria is None:
        categoria = Categoria.objects.create(nombre="Latas y aderezos", es_base=True, orden=6)
    for nombre, presentacion in LATAS_Y_ADEREZOS:
        if Producto.objects.filter(nombre__iexact=nombre).exists():
            continue
        Producto.objects.create(
            nombre=nombre, categoria=categoria, unidad_medida="unidad", stock_minimo=0,
            presentacion=presentacion, unidades_por_presentacion=None, controla_merma=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0017_catalogo_abarrotes"),
    ]

    operations = [
        migrations.RunPython(crear_latas_y_aderezos, migrations.RunPython.noop),
    ]
