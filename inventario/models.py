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

from django.utils import timezone

from .excepciones import ExistenciaInsuficiente, MovimientoInvalido, formatear_cantidad
from .observador import IObservadorExistencia


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
    prioriza RNF-01). Solo cambia a través de MovimientoInventario.aplicar() y anular().
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

    # --- Patrón Observer (DEDS 3.4, Fig. 23): Existencia es el sujeto --------------------------
    # Los observadores se guardan a nivel de clase: cada consulta del ORM crea instancias nuevas de
    # Existencia, así que una lista por instancia se perdería (D-17).
    _observadores = []

    @classmethod
    def agregar_observador(cls, observador):
        if not isinstance(observador, IObservadorExistencia):
            raise TypeError("El observador debe implementar IObservadorExistencia.")
        if not any(type(o) is type(observador) for o in cls._observadores):
            cls._observadores.append(observador)

    @classmethod
    def quitar_observador(cls, observador):
        if observador in cls._observadores:
            cls._observadores.remove(observador)

    def notificar_observadores(self):
        for observador in list(type(self)._observadores):
            observador.actualizar(self)

    def actualizar_cantidad(self, delta):
        """Aplica un delta (positivo o negativo), persiste y notifica a los observadores (RF-06, RF-17)."""
        delta = Decimal(delta)
        nueva = self.cantidad + delta
        if nueva < 0:
            raise ExistenciaInsuficiente(self.cantidad, self.producto.unidad_medida, self.ubicacion)
        if nueva > self.CANTIDAD_MAXIMA:  # R-04: evita un DataError de numeric(10,2)
            raise MovimientoInvalido("La existencia resultante supera el máximo que el sistema puede registrar.")
        self.nivel_anterior = self.nivel()
        self.delta = delta
        self.cantidad = nueva
        self.save(update_fields=["cantidad", "actualizado_en"])
        self.notificar_observadores()

    @classmethod
    def bloquear(cls, producto, ubicacion):
        """Obtiene (o crea en 0) la existencia con bloqueo de fila. Requiere transacción abierta (RNF-08)."""
        return cls.bloquear_varias(producto, [ubicacion])[ubicacion.pk]

    @classmethod
    def bloquear_varias(cls, producto, ubicaciones):
        """
        Bloquea las existencias de un producto en varias ubicaciones SIEMPRE en el mismo orden (por id
        de ubicación), para que dos transacciones concurrentes (p. ej. una salida y una anulación)
        no se bloqueen mutuamente (deadlock). Devuelve {ubicacion_id: existencia}.
        """
        bloqueadas = {}
        for ubicacion in sorted(ubicaciones, key=lambda u: u.pk):
            existencia, _ = cls.objects.select_for_update().get_or_create(producto=producto, ubicacion=ubicacion)
            bloqueadas[ubicacion.pk] = existencia
        return bloqueadas


class MovimientoInventario(models.Model):
    """Fig. 12: movimiento abstracto de inventario. Subclases: EntradaInventario y SalidaInventario."""

    class Tipo(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"
        MERMA = "merma", "Merma"  # D-33

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
    motivo_anulacion = models.TextField("motivo de anulación", blank=True)  # D-04, RF-15
    # D-19: trazabilidad de la anulación y de la corrección (RF-15 "editar" = anular + reemplazar).
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="anulaciones"
    )
    anulado_en = models.DateTimeField("anulado en", null=True, blank=True)
    reemplaza_a = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="reemplazado_por"
    )

    MOTIVO_MINIMO = 5

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
            ("reportar_consumo", "Reportar consumo de su sucursal"),
            ("anular_movimiento", "Anular o corregir movimientos con justificación"),
            ("ver_historial", "Consultar historial de movimientos"),
        ]

    def __str__(self):
        return f"{self.tipo_texto} de {formatear_cantidad(self.cantidad)} {self.producto}"

    def save(self, *args, **kwargs):
        if self.TIPO:
            self.tipo = self.TIPO
        super().save(*args, **kwargs)

    @property
    def es_consumo(self):
        """D-02: el consumo de sucursal es una salida con origen = sucursal y sin destino."""
        return self.tipo == self.Tipo.SALIDA and self.destino_id is None

    @property
    def tipo_texto(self):
        return "Consumo" if self.es_consumo else self.get_tipo_display()

    def aplicar(self):
        raise NotImplementedError("Cada subclase define cómo afecta las existencias.")

    def anular(self, motivo, usuario=None):  # RF-15
        """
        Revierte el efecto del movimiento sobre las existencias y lo marca como anulado.
        No borra el registro: queda en el historial con su motivo (criterio de aceptación RF-15).
        """
        motivo = (motivo or "").strip()
        if len(motivo) < self.MOTIVO_MINIMO:
            raise MovimientoInvalido(
                f"Indique el motivo de la anulación (mínimo {self.MOTIVO_MINIMO} caracteres)."
            )
        with transaction.atomic():
            actual = MovimientoInventario.objects.select_for_update().get(pk=self.pk)
            if actual.anulado:
                raise MovimientoInvalido("El movimiento ya está anulado.")
            ubicaciones = [u for u in (self.origen, self.destino) if u is not None]
            existencias = Existencia.bloquear_varias(self.producto, ubicaciones)
            if self.destino_id:
                try:
                    existencias[self.destino_id].actualizar_cantidad(-self.cantidad)
                except ExistenciaInsuficiente as error:
                    raise MovimientoInvalido(
                        f"No se puede anular: {self.destino} ya no tiene la cantidad del movimiento. "
                        f"{error.messages[0].split('.')[0]}."
                    ) from error
            if self.origen_id:
                existencias[self.origen_id].actualizar_cantidad(self.cantidad)
            self.anulado = True
            self.motivo_anulacion = motivo
            self.anulado_por = usuario
            self.anulado_en = timezone.now()
            self.save(update_fields=["anulado", "motivo_anulacion", "anulado_por", "anulado_en"])
            # D-33: anular la merma reabre su control para volver a registrar el peso real.
            ControlMerma.objects.filter(movimiento_merma_id=self.pk).update(
                estado=ControlMerma.Estado.PENDIENTE, peso_real=None, merma=None, movimiento_merma=None,
                procesado_por=None, procesado_en=None,
            )
        return self

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
    """
    RF-03: envío de un producto de la bodega a una sucursal (un producto por movimiento).
    D-02: con origen = sucursal y destino = null representa el consumo reportado por la sucursal.
    """

    TIPO = MovimientoInventario.Tipo.SALIDA

    class Meta:
        verbose_name = "salida de inventario"
        verbose_name_plural = "salidas de inventario"

    def aplicar(self):  # RF-03, RF-07 (consumo), RNF-08
        self._validar_comunes()
        if self.destino is None:
            if self.origen is None or not self.origen.es_sucursal:
                raise MovimientoInvalido("El consumo debe registrarse sobre una sucursal.")
        else:
            if self.origen is None or not self.origen.es_bodega:
                raise MovimientoInvalido("Las salidas deben partir de la bodega.")
            if not self.destino.es_sucursal:
                raise MovimientoInvalido("El destino de una salida debe ser una sucursal.")
        with transaction.atomic():
            ubicaciones = [self.origen] + ([self.destino] if self.destino else [])
            existencias = Existencia.bloquear_varias(self.producto, ubicaciones)
            existencia_origen = existencias[self.origen.pk]
            # Con la fila bloqueada, dos salidas simultáneas no pueden sobregirar el origen (RNF-06/08).
            if existencia_origen.cantidad < self.cantidad:
                raise ExistenciaInsuficiente(existencia_origen.cantidad, self.producto.unidad_medida, self.origen)
            self.save()
            existencia_origen.actualizar_cantidad(-self.cantidad)
            if self.destino:
                existencias[self.destino.pk].actualizar_cantidad(self.cantidad)
        return self


class MermaInventario(MovimientoInventario):
    """
    D-33: pérdida de peso al limpiar o preparar una proteína en producción. Sale de la bodega y no va a
    ninguna parte (destino = null). No es consumo de sucursal: los reportes de consumo no la cuentan.
    """

    TIPO = MovimientoInventario.Tipo.MERMA

    class Meta:
        verbose_name = "merma de inventario"
        verbose_name_plural = "mermas de inventario"

    def aplicar(self):  # D-33, RNF-08
        self._validar_comunes()
        if self.origen is None or not self.origen.es_bodega or self.destino_id is not None:
            raise MovimientoInvalido("La merma se descuenta de la bodega y no tiene destino.")
        with transaction.atomic():
            existencia = Existencia.bloquear(self.producto, self.origen)
            if existencia.cantidad < self.cantidad:
                raise ExistenciaInsuficiente(existencia.cantidad, self.producto.unidad_medida, self.origen)
            self.save()
            existencia.actualizar_cantidad(-self.cantidad)
        return self


class ControlMerma(models.Model):
    """
    D-33: control interno de merma de proteínas. Primera entrada = peso bruto que entrega el proveedor
    (EntradaInventario). Segunda entrada = peso real después de limpieza o preparación en producción.
    Merma = bruto - real, registrada como MermaInventario para que la existencia quede en el peso real.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de peso real"
        PROCESADO = "procesado", "Procesado"

    entrada = models.OneToOneField(EntradaInventario, on_delete=models.PROTECT, related_name="control_merma")
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    peso_real = models.DecimalField(
        "peso real", max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    merma = models.DecimalField("merma", max_digits=10, decimal_places=2, null=True, blank=True)
    movimiento_merma = models.OneToOneField(
        MermaInventario, on_delete=models.PROTECT, null=True, blank=True, related_name="control_merma"
    )
    procesado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="controles_merma"
    )
    procesado_en = models.DateTimeField("procesado en", null=True, blank=True)

    class Meta:
        verbose_name = "control de merma"
        verbose_name_plural = "controles de merma"
        ordering = ["-entrada__fecha"]
        permissions = [("registrar_peso_real", "Registrar el peso real (merma) de proteínas")]

    def __str__(self):
        return f"Merma de {self.entrada.producto} ({self.get_estado_display().lower()})"

    @property
    def peso_bruto(self):
        return self.entrada.cantidad

    @property
    def rendimiento(self):
        """Porcentaje del peso bruto que quedó utilizable."""
        if self.peso_real is None or not self.peso_bruto:
            return None
        return (self.peso_real / self.peso_bruto * 100).quantize(Decimal("0.1"))


class DiscrepanciaInventario(models.Model):
    """
    RF-13 (D-03): diferencia entre lo enviado por la bodega y lo recibido en la sucursal.
    Solo deja trazabilidad: no modifica existencias (el ajuste, si corresponde, se hace con RF-15).
    """

    movimiento = models.OneToOneField(SalidaInventario, on_delete=models.PROTECT, related_name="discrepancia")
    cantidad_enviada = models.DecimalField("cantidad enviada", max_digits=10, decimal_places=2)
    cantidad_recibida = models.DecimalField(
        "cantidad recibida", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    diferencia = models.DecimalField("diferencia", max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="discrepancias")
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "discrepancia de inventario"
        verbose_name_plural = "discrepancias de inventario"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad_recibida__gte=0), name="discrepancia_recibida_no_negativa"),
        ]

    def __str__(self):
        return f"Discrepancia en {self.movimiento}: recibido {formatear_cantidad(self.cantidad_recibida)}"
