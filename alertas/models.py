"""Módulo de Alertas (DEDS 3.2, Fig. 12) — RF-06, RF-16."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from inventario.excepciones import formatear_cantidad


class AlertaInventario(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ATENDIDA = "atendida", "Atendida"

    existencia = models.ForeignKey("inventario.Existencia", on_delete=models.PROTECT, related_name="alertas")
    generada_en = models.DateTimeField("generada en", default=timezone.now)
    # Fig. 12: nivel_detectado es la cantidad (Decimal) que tenía la existencia al detectar la alerta.
    nivel_detectado = models.DecimalField("nivel detectado", max_digits=10, decimal_places=2)
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    # D-16: quién y cuándo la atendió (IAlertas.marcar_atendida(alerta_id, usuario_id)).
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="alertas_atendidas"
    )
    atendida_en = models.DateTimeField("atendida en", null=True, blank=True)

    class Meta:
        verbose_name = "alerta de inventario"
        verbose_name_plural = "alertas de inventario"
        ordering = ["-generada_en"]
        constraints = [
            # Regla "sin duplicar": como máximo UNA alerta pendiente por existencia.
            models.UniqueConstraint(
                fields=["existencia"], condition=models.Q(estado="pendiente"), name="alerta_pendiente_unica",
            ),
        ]
        permissions = [("marcar_atendida", "Marcar alertas como atendidas")]

    def __str__(self):
        return f"Alerta {self.get_estado_display().lower()}: {self.existencia.producto} en {self.existencia.ubicacion}"

    @property
    def es_agotado(self):
        return self.nivel_detectado == 0

    @property
    def nivel_texto(self):
        return "Agotado" if self.es_agotado else "Bajo"

    @property
    def nivel_css(self):
        return "agotado" if self.es_agotado else "bajo"

    @property
    def nivel_detectado_texto(self):
        return f"{formatear_cantidad(self.nivel_detectado)} {self.existencia.producto.unidad_medida}"

    def notificar(self, notificador=None):
        """Fig. 12: notificar() usa el adaptador de notificación (patrón Adapter)."""
        from .servicios import AlertaInventarioService

        return AlertaInventarioService(notificador).notificar(self.pk)

    def marcar_atendida(self, usuario):
        """UC05 paso 4. Devuelve False si ya estaba atendida."""
        if self.estado == self.Estado.ATENDIDA:
            return False
        self.estado = self.Estado.ATENDIDA
        self.atendida_por = usuario
        self.atendida_en = timezone.now()
        self.save(update_fields=["estado", "atendida_por", "atendida_en"])
        return True
