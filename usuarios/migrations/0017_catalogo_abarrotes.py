"""
D-48: catálogo de Abarrotes (dato de la clienta, 2026-11-15).

- Pan clásico y Pan reina: se cuentan por PAQUETE y se compran en CAJA.
- Harina y Azúcar: se cuentan por UNIDAD (cada paquete es una unidad) y se compran en FARDO.
- Pasta linguini: por unidad, en caja.  Almendras, Pecanas y Nueces: por unidad, en bolsa.
- Adobo, Paprika y Cilantro: por unidad, en bote.  Consomé y Empanizador: por unidad, en saco.
- Nachos, Rotisserie chicken, Sal, Pimienta y Ajo en polvo: por unidad, sin presentación.

Cuánto trae cada caja o fardo NO se conoce (los números que dio la clienta eran ejemplos): queda en blanco y,
hasta que el dueño lo defina, se registran en la unidad de medida. La "paprika" que ya existía (creada por la
clienta) se actualiza en vez de duplicarse; ningún otro producto existente se modifica.
"""
from django.db import migrations

# nombre, unidad de medida, presentación
ABARROTES = [
    ("Pan clásico", "paquete", "caja"),
    ("Pan reina", "paquete", "caja"),
    ("Nachos", "unidad", ""),
    ("Almendras", "unidad", "bolsa"),
    ("Pecanas", "unidad", "bolsa"),
    ("Nueces", "unidad", "bolsa"),
    ("Adobo", "unidad", "bote"),
    ("Paprika", "unidad", "bote"),
    ("Rotisserie chicken", "unidad", ""),
    ("Sal", "unidad", ""),
    ("Pimienta", "unidad", ""),
    ("Consomé", "unidad", "saco"),
    ("Empanizador", "unidad", "saco"),
    ("Cilantro", "unidad", "bote"),
    ("Ajo en polvo", "unidad", ""),
    ("Harina", "unidad", "fardo"),
    ("Azúcar", "unidad", "fardo"),
    ("Pasta linguini", "unidad", "caja"),
]


def crear_abarrotes(apps, schema_editor):
    Categoria = apps.get_model("usuarios", "Categoria")
    Producto = apps.get_model("usuarios", "Producto")
    abarrotes = Categoria.objects.filter(nombre__iexact="Abarrotes").first()
    if abarrotes is None:
        abarrotes = Categoria.objects.create(nombre="Abarrotes", es_base=True, orden=5)
    for nombre, unidad, presentacion in ABARROTES:
        existente = Producto.objects.filter(nombre__iexact=nombre).first()
        if existente is not None:
            if nombre == "Paprika":  # la creó la clienta con unidad "u" y sin presentación
                existente.nombre, existente.unidad_medida, existente.presentacion = nombre, unidad, presentacion
                existente.categoria = abarrotes
                existente.save(update_fields=["nombre", "unidad_medida", "presentacion", "categoria"])
            continue
        Producto.objects.create(
            nombre=nombre, categoria=abarrotes, unidad_medida=unidad, stock_minimo=0,
            presentacion=presentacion, unidades_por_presentacion=None, controla_merma=False,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0016_catalogo_concentrados"),
    ]

    operations = [
        migrations.RunPython(crear_abarrotes, migrations.RunPython.noop),
    ]
