"""D-32, paso 2: reemplaza el campo de texto por la clave foránea ya poblada en 0003."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0003_categoria"),
    ]

    operations = [
        migrations.RemoveField(model_name="producto", name="categoria"),
        migrations.RenameField(model_name="producto", old_name="categoria_nueva", new_name="categoria"),
        migrations.AlterField(
            model_name="producto",
            name="categoria",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, related_name="productos", to="usuarios.categoria",
                verbose_name="categoría",
            ),
        ),
    ]
