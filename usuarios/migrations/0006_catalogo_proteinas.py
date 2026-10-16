"""
D-33/D-34: catálogo de proteínas del restaurante. Se registran en LIBRAS (no kilos), salvo los paquetes
de res y de cerdo, que van por unidad y llegan empacados (sin merma).

El stock mínimo queda en 0: lo define el dueño desde Catálogo (sin él solo se alerta al agotarse).
Si ya existe un producto con el mismo nombre, no se duplica: se pasa a Proteínas y se activa su control de
merma; su unidad solo se cambia a libras si todavía no tiene movimientos (para no reinterpretar cantidades).
"""
from django.db import migrations

# nombre, unidad, controla merma (entrada en dos pasos)
PROTEINAS = [
    ("Alitas de pollo", "lb", True),
    ("Pechuga de pollo", "lb", True),
    ("Tortas de res", "lb", True),        # el proveedor entrega carne molida; producción forma las tortas
    ("Tortas de cerdo", "lb", True),
    ("Paquetes de res", "unidad", False),
    ("Paquetes de cerdo", "unidad", False),
    ("Camarón con cola", "lb", True),
    ("Camarón sin cola", "lb", True),
    ("Langosta", "lb", True),
    ("Filete", "lb", True),
]


def crear_proteinas(apps, schema_editor):
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    Categoria = apps.get_model("usuarios", "Categoria")
    Producto = apps.get_model("usuarios", "Producto")
    MovimientoInventario = apps.get_model("inventario", "MovimientoInventario")
    proteinas = Categoria.objects.filter(nombre__iexact="Proteínas").first()
    if proteinas is None:
        proteinas = Categoria.objects.create(nombre="Proteínas", es_base=True, orden=1)
    for nombre, unidad, merma in PROTEINAS:
        producto = Producto.objects.filter(nombre__iexact=nombre).first()
        if producto is None:
            Producto.objects.create(
                nombre=nombre, categoria=proteinas, unidad_medida=unidad, stock_minimo=0, controla_merma=merma,
            )
            continue
        producto.categoria = proteinas
        producto.controla_merma = merma
        campos = ["categoria", "controla_merma"]
        if not MovimientoInventario.objects.filter(producto_id=producto.pk).exists():
            producto.unidad_medida = unidad
            campos.append("unidad_medida")
        producto.save(update_fields=campos)


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0005_producto_controla_merma"),
        ("inventario", "0004_mermainventario_alter_movimientoinventario_tipo_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_proteinas, migrations.RunPython.noop),
    ]
