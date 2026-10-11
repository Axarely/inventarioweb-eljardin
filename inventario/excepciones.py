from django.core.exceptions import ValidationError


def formatear_cantidad(valor):
    """12.50 -> '12.5', 12.00 -> '12'."""
    return f"{valor:.2f}".rstrip("0").rstrip(".")


class MovimientoInvalido(ValidationError):
    """Un movimiento no cumple las reglas del DEDS (UC02 E1, UC03 E1)."""


class ExistenciaInsuficiente(MovimientoInvalido):
    """UC03 E1/A1: la ubicación no tiene la cantidad pedida; informa el máximo disponible."""

    def __init__(self, disponible, unidad="", ubicacion=""):
        self.disponible = disponible
        texto = f"Solo hay {formatear_cantidad(disponible)} {unidad}".rstrip()
        if ubicacion:
            texto += f" disponibles en {ubicacion}"
        else:
            texto += " disponibles"
        super().__init__(f"{texto}. Ajuste la cantidad o cancele el envío.")
