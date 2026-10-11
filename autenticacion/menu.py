"""
Menú lateral filtrado por rol (DEDS 3.5 "Diseño de la navegación", mínimo privilegio).

Cada opción declara los permisos que la habilitan (basta con uno). El orden produce:
- Bodeguero: Inicio, Entradas, Salidas, Historial
- Encargado: Inicio, Existencias
- Dueño: Inicio, Catálogo, Usuarios, Roles, Proveedores, Existencias, Historial
Sprint 2 agrega Dashboard, Alertas, Reportes, Reportar consumo y Reportar discrepancia.
"""
from django.urls import reverse

OPCIONES_MENU = [
    ("Inicio", "inicio", ()),
    ("Entradas", "inventario:entrada", ("inventario.registrar_entrada",)),
    ("Salidas", "inventario:salida", ("inventario.registrar_salida",)),
    ("Catálogo", "usuarios:productos", ("usuarios.view_producto",)),
    ("Usuarios", "usuarios:usuarios", ("usuarios.view_usuario",)),
    ("Roles", "usuarios:roles", ("usuarios.view_rol",)),
    ("Proveedores", "proveedores:lista", ("proveedores.view_proveedor",)),
    ("Existencias", "inventario:existencias",
     ("inventario.consultar_existencias_propias", "inventario.consultar_existencias_todas")),
    ("Historial", "inventario:historial", ("inventario.ver_historial",)),
]


def opciones_para(usuario):
    return [
        (etiqueta, nombre_url)
        for etiqueta, nombre_url, permisos in OPCIONES_MENU
        if not permisos or any(usuario.has_perm(p) for p in permisos)
    ]


def menu(request):
    """Context processor: expone `menu` con las opciones del rol del usuario autenticado."""
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    items = []
    for etiqueta, nombre_url in opciones_para(usuario):
        url = reverse(nombre_url)
        activo = request.path == url if url == "/" else request.path.startswith(url)
        items.append({"etiqueta": etiqueta, "url": url, "activo": activo})
    return {"menu": items}
