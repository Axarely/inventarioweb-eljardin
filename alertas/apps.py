from django.apps import AppConfig


class AlertasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "alertas"
    verbose_name = "Alertas de inventario"

    def ready(self):
        # Patrón Observer: Alertas se suscribe a Existencia; Inventario no conoce a Alertas.
        from inventario.models import Existencia

        from .servicios import AlertaInventarioService

        Existencia.agregar_observador(AlertaInventarioService())
