"""Interfaz IProveedores (DEDS 3.2, tabla de interfaces) — RF-11."""
from django.core.exceptions import ValidationError

from .models import Proveedor


def crear_proveedor(datos_proveedor):
    proveedor = Proveedor(**datos_proveedor)
    proveedor.full_clean()
    proveedor.save()
    return proveedor


def desactivar_proveedor(proveedor_id):
    actualizados = Proveedor.objects.filter(pk=proveedor_id, activo=True).update(activo=False)
    return actualizados == 1


def activar_proveedor(proveedor_id):
    actualizados = Proveedor.objects.filter(pk=proveedor_id, activo=False).update(activo=True)
    return actualizados == 1


def proveedores_activos():
    return Proveedor.objects.filter(activo=True)


def obtener_proveedor_activo(proveedor_id):
    """Usada por Inventario al registrar una entrada: solo se aceptan proveedores activos."""
    proveedor = Proveedor.objects.filter(pk=proveedor_id, activo=True).first()
    if proveedor is None:
        raise ValidationError("Seleccione un proveedor activo.")
    return proveedor


def proveedor_por_nombre(nombre):
    """D-45: en la entrada el proveedor se ESCRIBE y es opcional. Vacío -> None. Si ya existe uno con ese nombre
    (sin importar mayúsculas ni espacios) se usa; si no, se crea. Uno desactivado no se acepta (RF-11)."""
    nombre = " ".join((nombre or "").split())
    if not nombre:
        return None
    proveedor = Proveedor.objects.filter(nombre__iexact=nombre).first()
    if proveedor is None:
        return crear_proveedor({"nombre": nombre})
    if not proveedor.activo:
        raise ValidationError(f"El proveedor «{proveedor}» está desactivado. Actívelo en Proveedores o escriba otro.")
    return proveedor
