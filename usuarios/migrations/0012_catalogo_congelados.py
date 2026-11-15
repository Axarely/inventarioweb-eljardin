"""
D-40: catálogo de Congelados (dato de la clienta, 2026-11-15).

- Nuggets de pollo y Dedos de queso: por unidad, se compran en paquete.
- Papas: por unidad, se compran en caja.
- Tocino y Yuca: por libra, sin presentación.

Las unidades que trae cada paquete o caja NO se conocen todavía: quedan en blanco ("Falta definir" en el
Catálogo) y, hasta que el dueño las defina, esos productos se registran solo por unidad. Sin merma: es
exclusiva de Proteínas (D-38). Stock mínimo en 0 (lo define el dueño). No duplica productos existentes.
"""
from django.db import migrations

# nombre, unidad de medida, presentación
CONGELADOS = [
    ("Nuggets de pollo", "unidad", "paquete"),
    ("Papas", "unidad", "caja"),
    ("Dedos de queso", "unidad", "paquete"),
    ("Tocino", "lb", ""),
    ("Yuca", "lb", ""),
]


def crear_congelados(apps, schema_editor):
    Categoria = apps.get_model("usuarios", "Categoria")
    Producto = apps.get_model("usuarios", "Producto")
    congelados = Categoria.objects.filter(nombre__iexact="Congelados").first()
    if congelados is None:
        congelados = Categoria.objects.create(nombre="Congelados", es_base=True, orden=3)
    for nombre, unidad, presentacion in CONGELADOS:
        if Producto.objects.filter(nombre__iexact=nombre).exists():
            continue
        Producto.objects.create(
            nombre=nombre, categoria=congelados, unidad_medida=unidad, stock_minimo=0,
            presentacion=presentacion, unidades_por_presentacion=None, controla_merma=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0011_mozzarella_bolsa"),
    ]

    operations = [
        migrations.RunPython(crear_congelados, migrations.RunPython.noop),
    ]
