"""
Roles base del DEDS y sus permisos (RF-01, RNF-02, mínimo privilegio).

Los permisos de los tres roles base se fijan aquí y se sincronizan tras cada `migrate`
(señal post_migrate en usuarios/apps.py); no se editan desde la interfaz (D-13).
Los roles adicionales que cree el dueño sí son editables.
"""
from django.contrib.auth.models import Permission

PERMISOS_POR_ROL = {
    "dueno": [
        "usuarios.view_usuario", "usuarios.add_usuario", "usuarios.change_usuario",
        "usuarios.view_rol", "usuarios.add_rol", "usuarios.change_rol", "usuarios.delete_rol",
        "usuarios.view_producto", "usuarios.add_producto", "usuarios.change_producto",
        "usuarios.view_categoria", "usuarios.add_categoria", "usuarios.delete_categoria",
        "proveedores.view_proveedor", "proveedores.add_proveedor", "proveedores.change_proveedor",
        "inventario.consultar_existencias_todas", "inventario.ver_historial",
        "inventario.anular_movimiento", "inventario.view_discrepanciainventario",
        "alertas.view_alertainventario", "alertas.marcar_atendida",
        "reportes.ver_dashboard", "reportes.ver_reportes", "reportes.exportar_reportes",
    ],
    "bodeguero": [
        "inventario.registrar_entrada", "inventario.registrar_salida", "inventario.ver_historial",
        "inventario.anular_movimiento",  # RF-15: corrige los movimientos que registró por error
        # UC02 A1: si el producto no existe, el bodeguero puede crearlo antes de continuar.
        "usuarios.add_producto", "usuarios.add_categoria",
    ],
    "encargado": [
        "inventario.consultar_existencias_propias",
        "inventario.reportar_consumo", "inventario.add_discrepanciainventario",
    ],
}

# Apps cuyos permisos se ofrecen al crear roles personalizados.
APPS_CON_PERMISOS = ("usuarios", "proveedores", "inventario", "alertas", "reportes")


def _buscar_permisos(nombres):
    permisos = []
    for nombre in nombres:
        app_label, codename = nombre.split(".")
        permiso = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
        if permiso is not None:  # aún puede no existir durante el primer migrate
            permisos.append(permiso)
    return permisos


def sincronizar_roles_base():
    from .models import Rol

    for codigo, nombres in PERMISOS_POR_ROL.items():
        rol, _ = Rol.objects.get_or_create(codigo=codigo, defaults={"nombre": Rol.Codigo(codigo).label})
        rol.permisos.set(_buscar_permisos(nombres))


def sincronizar_categorias_base():
    """
    DEF-10 / D-32: las categorías fijas existen SIEMPRE, también después de un `flush` (que borra los
    datos de las migraciones). Se ejecuta en post_migrate, igual que los roles base.
    """
    from django.db import connection

    from .models import CATEGORIAS_BASE, Categoria

    if Categoria._meta.db_table not in connection.introspection.table_names():
        return  # migración parcial o revertida a antes de usuarios.0003
    for orden, nombre in enumerate(CATEGORIAS_BASE, start=1):
        categoria = Categoria.objects.filter(nombre__iexact=nombre).first()
        if categoria is None:
            Categoria.objects.create(nombre=nombre, es_base=True, orden=orden)
        elif (categoria.nombre, categoria.es_base, categoria.orden) != (nombre, True, orden):
            Categoria.objects.filter(pk=categoria.pk).update(nombre=nombre, es_base=True, orden=orden)


def rol_base(codigo):
    from .models import Rol

    return Rol.objects.get(codigo=codigo)
