"""
D-37: catálogo de Lácteos. Se cuentan por UNIDAD, pero se compran en cajas o paquetes.

- Queso mozzarella y Queso Zula: paquete de 6 unidades (dato de la clienta).
- Leche entera y Margarina con ajo: por caja. Las unidades por caja NO se conocen todavía: quedan en blanco y,
  hasta que el dueño las defina en Catálogo, esos productos se registran solo en unidades.

El stock mínimo queda en 0 (lo define el dueño). Si un producto ya existe no se duplica: se pasa a Lácteos
con su presentación; su unidad solo cambia si todavía no tiene movimientos (para no reinterpretar cantidades).
"""
from django.db import migrations

# nombre, presentación, unidades por presentación (None = sin definir)
LACTEOS = [
    ("Leche entera", "caja", None),
    ("Queso mozzarella", "paquete", 6),
    ("Queso Zula", "paquete", 6),
    ("Margarina con ajo", "caja", None),
]


def crear_lacteos(apps, schema_editor):
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    Categoria = apps.get_model("usuarios", "Categoria")
    Producto = apps.get_model("usuarios", "Producto")
    MovimientoInventario = apps.get_model("inventario", "MovimientoInventario")
    lacteos = Categoria.objects.filter(nombre__iexact="Lácteos").first()
    if lacteos is None:
        lacteos = Categoria.objects.create(nombre="Lácteos", es_base=True, orden=2)
    for nombre, presentacion, unidades in LACTEOS:
        producto = Producto.objects.filter(nombre__iexact=nombre).first()
        if producto is None:
            Producto.objects.create(
                nombre=nombre, categoria=lacteos, unidad_medida="unidad", stock_minimo=0,
                presentacion=presentacion, unidades_por_presentacion=unidades,
            )
            continue
        producto.categoria = lacteos
        producto.presentacion = presentacion
        producto.unidades_por_presentacion = unidades
        campos = ["categoria", "presentacion", "unidades_por_presentacion"]
        if not MovimientoInventario.objects.filter(producto_id=producto.pk).exists():
            producto.unidad_medida = "unidad"
            campos.append("unidad_medida")
        producto.save(update_fields=campos)


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0007_producto_presentacion"),
        ("inventario", "0005_alter_controlmerma_options"),
    ]

    operations = [
        migrations.RunPython(crear_lacteos, migrations.RunPython.noop),
    ]
