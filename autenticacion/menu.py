"""
Menú lateral filtrado por rol (DEDS 3.5 "Diseño de la navegación", mínimo privilegio).

Cada opción declara los permisos que la habilitan (basta con uno) y, opcionalmente, un permiso que
la oculta. El orden produce:
- Bodeguero: Inicio, Entradas, Salidas, Historial
- Encargado: Inicio, Existencias, Reportar consumo, Reportar discrepancia
- Dueño: Dashboard, Alertas, Existencias, Catálogo, Usuarios, Roles, Proveedores, Reportes, Historial
"""
from django.urls import reverse

DASHBOARD = "reportes.ver_dashboard"

# (etiqueta, nombre de URL, permisos que la habilitan, permiso que la oculta)
OPCIONES_MENU = [
    ("Inicio", "inicio", (), DASHBOARD),  # el Dueño entra directo a su Dashboard
    ("Dashboard", "reportes:dashboard", (DASHBOARD,), None),
    ("Alertas", "alertas:lista", ("alertas.view_alertainventario",), None),
    ("Entradas", "inventario:entrada", ("inventario.registrar_entrada",), None),
    ("Salidas", "inventario:salida", ("inventario.registrar_salida",), None),
    ("Existencias", "inventario:existencias",
     ("inventario.consultar_existencias_propias", "inventario.consultar_existencias_todas"), None),
    ("Reportar consumo", "inventario:consumo", ("inventario.reportar_consumo",), None),
    ("Reportar discrepancia", "inventario:discrepancia", ("inventario.add_discrepanciainventario",), None),
    ("Catálogo", "usuarios:productos", ("usuarios.view_producto",), None),
    ("Usuarios", "usuarios:usuarios", ("usuarios.view_usuario",), None),
    ("Roles", "usuarios:roles", ("usuarios.view_rol",), None),
    ("Proveedores", "proveedores:lista", ("proveedores.view_proveedor",), None),
    ("Reportes", "reportes:reportes", ("reportes.ver_reportes",), None),
    ("Historial", "inventario:historial", ("inventario.ver_historial",), None),
]


def opciones_para(usuario):
    return [
        (etiqueta, nombre_url)
        for etiqueta, nombre_url, permisos, ocultar_con in OPCIONES_MENU
        if (not permisos or any(usuario.has_perm(p) for p in permisos))
        and not (ocultar_con and usuario.has_perm(ocultar_con))
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
