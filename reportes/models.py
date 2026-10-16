"""Módulo de Reportes (DEDS 3.2) — RF-07, RF-08, RF-14, RF-17."""
from django.db import models


class EstadoIndicadores(models.Model):
    """
    Registro único que PanelIndicadoresService (observador de Existencia) actualiza en cada cambio.
    Su `version` invalida los indicadores calculados, también entre varios workers de gunicorn (D-21).
    """

    version = models.PositiveBigIntegerField(default=0)
    actualizado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "estado de los indicadores"
        verbose_name_plural = "estado de los indicadores"
        default_permissions = ()
        permissions = [
            ("ver_dashboard", "Ver el panel de indicadores"),
            ("ver_reportes", "Consultar reportes de inventario"),
            ("exportar_reportes", "Exportar reportes a PDF o Excel"),
        ]
