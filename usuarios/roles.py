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
        "proveedores.view_proveedor", "proveedores.add_proveedor", "proveedores.change_proveedor",
        "inventario.consultar_existencias_todas", "inventario.ver_historial",
    ],
    "bodeguero": [
        "inventario.registrar_entrada", "inventario.registrar_salida", "inventario.ver_historial",
        # UC02 A1: si el producto no existe, el bodeguero puede crearlo antes de continuar.
        "usuarios.add_producto",
    ],
    "encargado": [
        "inventario.consultar_existencias_propias",
    ],
}

# Apps cuyos permisos se ofrecen al crear roles personalizados.
APPS_CON_PERMISOS = ("usuarios", "proveedores", "inventario")


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


def rol_base(codigo):
    from .models import Rol

    return Rol.objects.get(codigo=codigo)
