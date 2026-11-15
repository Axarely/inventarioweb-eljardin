"""
D-38: correcciones de la clienta al catálogo de Lácteos (2026-11-15) y merma exclusiva de Proteínas.

- "Queso Zula" se llama Queso Sula: paquete grande con 4 filas de 4 unidades = 16 unidades por paquete.
- Margarina con ajo: es por UNIDAD (un bote), no por caja.
- Leche entera: caja de 24 unidades.
- La merma (entrada en dos pasos) es solo para Proteínas: se desactiva en cualquier otra categoría.
"""
from django.db import migrations


def corregir(apps, schema_editor):
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    Producto = apps.get_model("usuarios", "Producto")

    sula = Producto.objects.filter(nombre__iexact="Queso Sula").first()
    zula = Producto.objects.filter(nombre__iexact="Queso Zula").first()
    if sula is None and zula is not None:
        zula.nombre = "Queso Sula"
        sula = zula
    if sula is not None:
        sula.presentacion, sula.unidades_por_presentacion = "paquete", 16
        sula.save(update_fields=["nombre", "presentacion", "unidades_por_presentacion"])

    Producto.objects.filter(nombre__iexact="Margarina con ajo").update(presentacion="", unidades_por_presentacion=None)
    Producto.objects.filter(nombre__iexact="Leche entera").update(presentacion="caja", unidades_por_presentacion=24)

    Producto.objects.filter(controla_merma=True).exclude(categoria__nombre="Proteínas").update(controla_merma=False)


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0008_catalogo_lacteos"),
    ]

    operations = [
        migrations.RunPython(corregir, migrations.RunPython.noop),
    ]
