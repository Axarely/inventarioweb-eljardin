"""
D-32: la categoría del producto pasa de texto libre a la entidad Categoria.
Paso 1: crea Categoria con las categorías fijas y copia la categoría de texto de cada producto.
"""
import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models

CATEGORIAS_BASE = [
    "Proteínas", "Lácteos", "Congelados", "Concentrados", "Abarrotes", "Latas y aderezos", "Verduras",
    "Desechables y limpieza", "Varios",
]

# Texto anterior (sin mayúsculas) -> categoría fija equivalente. Lo que no aparezca se conserva como
# categoría agregada con su mismo nombre: ningún producto pierde su categoría.
EQUIVALENCIAS = {
    "cárnicos": "Proteínas", "carnicos": "Proteínas", "carnes": "Proteínas", "proteinas": "Proteínas",
    "lacteos": "Lácteos",
    "desechables": "Desechables y limpieza", "limpieza": "Desechables y limpieza",
    "latas": "Latas y aderezos", "aderezos": "Latas y aderezos",
}


def crear_base_y_copiar(apps, schema_editor):
    # Restricciones inmediatas: evita "pending trigger events" al alterar la tabla en la misma transacción.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    Categoria = apps.get_model("usuarios", "Categoria")
    Producto = apps.get_model("usuarios", "Producto")
    por_nombre = {}
    for orden, nombre in enumerate(CATEGORIAS_BASE, start=1):
        categoria = Categoria.objects.create(nombre=nombre, es_base=True, orden=orden)
        por_nombre[nombre.lower()] = categoria
    for producto in Producto.objects.all():
        texto = " ".join((producto.categoria or "Varios").split())
        clave = EQUIVALENCIAS.get(texto.lower(), texto).lower()
        categoria = por_nombre.get(clave)
        if categoria is None:
            categoria = Categoria.objects.create(nombre=texto[:1].upper() + texto[1:])
            por_nombre[clave] = categoria
        producto.categoria_nueva = categoria
        producto.save(update_fields=["categoria_nueva"])


def revertir(apps, schema_editor):
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    Producto = apps.get_model("usuarios", "Producto")
    for producto in Producto.objects.select_related("categoria_nueva"):
        producto.categoria = producto.categoria_nueva.nombre
        producto.save(update_fields=["categoria"])


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0002_alter_usuario_options_usuario_bloqueado_hasta_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="Categoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=60, verbose_name="nombre")),
                ("es_base", models.BooleanField(default=False, editable=False, verbose_name="fija")),
                ("orden", models.PositiveSmallIntegerField(default=100, editable=False)),
            ],
            options={
                "verbose_name": "categoría",
                "verbose_name_plural": "categorías",
                "ordering": ["orden", "nombre"],
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("nombre"), name="categoria_nombre_unico_sin_mayusculas"
                    )
                ],
            },
        ),
        # Permite que la reversa de 0004 vuelva a crear la columna de texto antes de rellenarla.
        migrations.AlterField(
            model_name="producto",
            name="categoria",
            field=models.CharField(max_length=60, null=True, verbose_name="categoría"),
        ),
        migrations.AddField(
            model_name="producto",
            name="categoria_nueva",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="usuarios.categoria"
            ),
        ),
        migrations.RunPython(crear_base_y_copiar, revertir),
    ]
