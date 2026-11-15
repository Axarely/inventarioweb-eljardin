from django import template

from ..excepciones import formatear_cantidad

register = template.Library()


@register.filter
def cantidad(valor):
    """Decimal sin ceros sobrantes: 12.50 -> 12.5."""
    return "" if valor is None else formatear_cantidad(valor)


@register.filter
def en_presentaciones(producto, cantidad):
    """D-37: 20 unidades de un paquete de 6 -> "3 paquetes + 2 unidad"."""
    return producto.en_presentaciones(cantidad)


@register.inclusion_tag("inventario/_pill.html")
def pill_nivel(nivel):
    """Guía de estilo (Fig. 21): el estado se muestra SIEMPRE con color y texto."""
    return {"nivel": nivel.value, "texto": nivel.label}
