"""
Patrón Factory Method (DEDS 3.4, Fig. 22): MovimientoInventarioFactory centraliza qué subclase de
MovimientoInventario se instancia, de modo que servicios y vistas no conocen EntradaInventario ni
SalidaInventario.
"""
from .excepciones import MovimientoInvalido
from .models import EntradaInventario, MermaInventario, MovimientoInventario, SalidaInventario


class MovimientoInventarioFactory:
    _tipos = {
        MovimientoInventario.Tipo.ENTRADA: EntradaInventario,
        MovimientoInventario.Tipo.SALIDA: SalidaInventario,
        MovimientoInventario.Tipo.MERMA: MermaInventario,  # D-33
    }

    @classmethod
    def crear(cls, tipo, datos):
        """Devuelve la subclase concreta SIN guardar; quien la recibe llama a aplicar()."""
        clase = cls._tipos.get(tipo)
        if clase is None:
            raise MovimientoInvalido(f"Tipo de movimiento desconocido: «{tipo}».")
        campos_validos = set()
        for campo in clase._meta.get_fields():
            campos_validos.add(campo.name)
            if getattr(campo, "attname", None):
                campos_validos.add(campo.attname)  # p. ej. usuario_id
        desconocidos = set(datos) - campos_validos
        if desconocidos:
            raise MovimientoInvalido(f"Datos no válidos para {tipo}: {', '.join(sorted(desconocidos))}.")
        return clase(**datos)

    @classmethod
    def registrar(cls, tipo, clase):
        """Punto de extensión: un nuevo tipo de movimiento se agrega sin tocar a los clientes."""
        cls._tipos[tipo] = clase
