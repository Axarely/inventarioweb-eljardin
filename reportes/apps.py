from django.apps import AppConfig


class ReportesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reportes"
    verbose_name = "Reportes e indicadores"

    def ready(self):
        # Patrón Observer: Reportes se suscribe a Existencia; Inventario no conoce a Reportes.
        from inventario.models import Existencia

        from .servicios import PanelIndicadoresService

        Existencia.agregar_observador(PanelIndicadoresService())
