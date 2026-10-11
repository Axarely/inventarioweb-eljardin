"""
Módulo de Inventario (DEDS 3.2, Fig. 12): ubicaciones, existencias y movimientos.

Regla de diseño: este módulo NO importa alertas ni reportes (corrección 1 del DEDS v1.1).
Los observadores de Existencia se conectan en el Sprint 2 (patrón Observer).
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum

from .excepciones import ExistenciaInsuficiente, MovimientoInvalido


class Ubicacion(models.Model):
    """Ubicación física. Herencia multi-tabla hacia Bodega y Sucursal (nota de la Fig. 12)."""

    class Tipo(models.TextChoices):
        BODEGA = "bodega", "Bodega"
        SUCURSAL = "sucursal", "Sucursal"

    TIPO = None

    nombre = models.CharField("nombre", max_length=80, unique=True)
    direccion = models.CharField("dirección", max_length=150, blank=True)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices, editable=False)

    class Meta:
        verbose_name = "ubicación"
        verbose_name_plural = "ubicaciones"
        ordering = ["tipo", "nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if self.TIPO:
            self.tipo = self.TIPO
        super().save(*args, **kwargs)

    @property
    def es_bodega(self):
        return self.tipo == self.Tipo.BODEGA

    @property
    def es_sucursal(self):
        return self.tipo == self.Tipo.SUCURSAL

    def existencia_total(self):
        return self.existencias.aggregate(total=Sum("cantidad"))["total"] or Decimal("0")


class Bodega(Ubicacion):
    TIPO = Ubicacion.Tipo.BODEGA

    capacidad_max = models.PositiveIntegerField("capacidad máxima", null=True, blank=True)

    class Meta:
        verbose_name = "bodega"
        verbose_name_plural = "bodegas"

    @classmethod
    def central(cls):
        """El DEDS define una única bodega central que abastece a las sucursales."""
        bodega = cls.objects.order_by("pk").first()
        if bodega is None:
            raise MovimientoInvalido("No hay una bodega central registrada.")
        return bodega


class Sucursal(Ubicacion):
    TIPO = Ubicacion.Tipo.SUCURSAL

    horario = models.CharField("horario", max_length=60, blank=True)

    class Meta:
        verbose_name = "sucursal"
        verbose_name_plural = "sucursales"


class Existencia(models.Model):
    """
    RF-04: cantidad de un producto en una ubicación. Persistida, no calculada (nota de la Fig. 12,
    prioriza RNF-01). Solo cambia a través de MovimientoInventario.aplicar().
    """

    class Nivel(models.TextChoices):
        NORMAL = "normal", "Normal"
        BAJO = "bajo", "Bajo"
        AGOTADO = "agotado", "Agotado"

    CANTIDAD_MAXIMA = Decimal("99999999.99")  # límite de DecimalField(max_digits=10, decimal_places=2)

    producto = models.ForeignKey("usuarios.Producto", on_delete=models.PROTECT, related_name="existencias")
    ubicacion = models.ForeignKey(Ubicacion, on_delete=models.PROTECT, related_name="existencias")
    cantidad = models.DecimalField("cantidad", max_digits=10, decimal_places=2, default=Decimal("0"))
    actualizado_en = models.DateTimeField("actualizado en", auto_now=True)

    class Meta:
        verbose_name = "existencia"
        verbose_name_plural = "existencias"
        ordering = ["producto__nombre"]
        constraints = [
            models.UniqueConstraint(fields=["producto", "ubicacion"], name="existencia_unica_producto_ubicacion"),
            models.CheckConstraint(condition=models.Q(cantidad__gte=0), name="existencia_cantidad_no_negativa"),
        ]
        permissions = [
            ("consultar_existencias_propias", "Consultar existencias de su sucursal"),
            ("consultar_existencias_todas", "Consultar existencias de cualquier ubicación"),
        ]

    def __str__(self):
        return f"{self.producto} en {self.ubicacion}: {self.cantidad}"

    def nivel(self):
        """Estados de la Fig. 8: agotado si 0, bajo si < stock mínimo, normal en otro caso."""
        if self.cantidad == 0:
            return self.Nivel.AGOTADO
        if self.cantidad < self.producto.stock_minimo:
            return self.Nivel.BAJO
        return self.Nivel.NORMAL

    def esta_bajo_umbral(self):
        return self.cantidad < self.producto.stock_minimo

    def actualizar_cantidad(self, delta):
        """Aplica un delta (positivo o negativo). Sprint 2: aquí se llamará a notificar_observadores()."""
        nueva = self.cantidad + Decimal(delta)
        if nueva < 0:
            raise ExistenciaInsuficiente(self.cantidad, self.producto.unidad_medida, self.ubicacion)
        if nueva > self.CANTIDAD_MAXIMA:  # R-04: evita un DataError de numeric(10,2)
            raise MovimientoInvalido("La existencia resultante supera el máximo que el sistema puede registrar.")
        self.cantidad = nueva
        self.save(update_fields=["cantidad", "actualizado_en"])

    @classmethod
    def bloquear(cls, producto, ubicacion):
        """Obtiene (o crea en 0) la existencia con bloqueo de fila. Requiere transacción abierta (RNF-08)."""
        existencia, _ = cls.objects.select_for_update().get_or_create(producto=producto, ubicacion=ubicacion)
        return existencia


class MovimientoInventario(models.Model):
    """Fig. 12: movimiento abstracto de inventario. Subclases: EntradaInventario y SalidaInventario."""

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"

    TIPO = None

    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices, editable=False)
    producto = models.ForeignKey("usuarios.Producto", on_delete=models.PROTECT, related_name="movimientos")
    origen = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos_salientes"
    )
    destino = models.ForeignKey(
        Ubicacion, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos_entrantes"
    )
    cantidad = models.DecimalField(
        "cantidad", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="movimientos")
    fecha = models.DateTimeField("fecha", auto_now_add=True, db_index=True)
    anulado = models.BooleanField("anulado", default=False)
    motivo_anulacion = models.TextField("motivo de anulación", blank=True)  # D-04, RF-15 (Sprint 2)

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ["-fecha", "-pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="movimiento_cantidad_positiva"),
        ]
        permissions = [
            ("registrar_entrada", "Registrar entradas de mercadería"),
            ("registrar_salida", "Registrar salidas hacia sucursal"),
            ("ver_historial", "Consultar historial de movimientos"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.cantidad} {self.producto}"

    def save(self, *args, **kwargs):
        if self.TIPO:
            self.tipo = self.TIPO
        super().save(*args, **kwargs)

    def aplicar(self):
        raise NotImplementedError("Cada subclase define cómo afecta las existencias.")

    def _validar_comunes(self):
        # UC02/UC03 E1: cantidad numérica y positiva; el producto debe estar activo (RF-09).
        if self.cantidad is None or Decimal(self.cantidad) <= 0:
            raise MovimientoInvalido("La cantidad debe ser mayor que cero.")
        if not self.producto.activo:
            raise MovimientoInvalido(f"El producto «{self.producto}» está desactivado.")


class EntradaInventario(MovimientoInventario):
    """RF-02: mercadería que llega a la bodega desde un proveedor (RF-11)."""

    TIPO = MovimientoInventario.Tipo.ENTRADA

    proveedor = models.ForeignKey("proveedores.Proveedor", on_delete=models.PROTECT, related_name="entradas")

    class Meta:
        verbose_name = "entrada de inventario"
        verbose_name_plural = "entradas de inventario"

    def aplicar(self):  # RF-02, RNF-08
        self._validar_comunes()
        if self.destino is None or not self.destino.es_bodega:
            raise MovimientoInvalido("Las entradas solo pueden registrarse en la bodega.")
        if self.origen_id is not None:
            raise MovimientoInvalido("Una entrada no tiene ubicación de origen.")
        if not self.proveedor.activo:
            raise MovimientoInvalido(f"El proveedor «{self.proveedor}» está desactivado.")
        with transaction.atomic():
            self.save()
            Existencia.bloquear(self.producto, self.destino).actualizar_cantidad(self.cantidad)
        return self


class SalidaInventario(MovimientoInventario):
    """RF-03: envío de un producto de la bodega a una sucursal (un producto por movimiento)."""

    TIPO = MovimientoInventario.Tipo.SALIDA

    class Meta:
        verbose_name = "salida de inventario"
        verbose_name_plural = "salidas de inventario"

    def aplicar(self):  # RF-03, RNF-08
        self._validar_comunes()
        if self.origen is None or not self.origen.es_bodega:
            raise MovimientoInvalido("Las salidas deben partir de la bodega.")
        if self.destino is None or not self.destino.es_sucursal:
            raise MovimientoInvalido("El destino de una salida debe ser una sucursal.")
        with transaction.atomic():
            # Se bloquea primero el origen: dos salidas simultáneas no pueden sobregirar la bodega.
            existencia_origen = Existencia.bloquear(self.producto, self.origen)
            if existencia_origen.cantidad < self.cantidad:
                raise ExistenciaInsuficiente(existencia_origen.cantidad, self.producto.unidad_medida, self.origen)
            self.save()
            existencia_origen.actualizar_cantidad(-self.cantidad)
            Existencia.bloquear(self.producto, self.destino).actualizar_cantidad(self.cantidad)
        return self
