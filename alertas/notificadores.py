"""
Patrón Adapter (DEDS 3.4, Fig. 24): interfaz común INotificador y un adaptador por canal.
AlertaInventarioService solo conoce INotificador; cambiar de canal es cambiar de adaptador
(settings.NOTIFICADOR), sin tocar el Módulo de Alertas.
"""
import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class INotificador(ABC):
    @abstractmethod
    def enviar(self, destinatario, mensaje):
        """Envía `mensaje` a `destinatario`. Devuelve True si el canal aceptó el envío."""


class AdaptadorCorreoSMTP(INotificador):
    """Adaptador funcional de la v1 (DEDS 3.1): correo por SMTP mediante el backend de Django.
    En pruebas Django usa el backend en memoria (locmem); en desarrollo, la consola."""

    PREFIJO_ASUNTO = "[InventarioWeb El Jardín] "

    def enviar(self, destinatario, mensaje):
        asunto, _, _ = mensaje.partition("\n")
        enviados = send_mail(
            subject=self.PREFIJO_ASUNTO + asunto,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[destinatario],
            fail_silently=False,
        )
        return enviados == 1


class AdaptadorSMS(INotificador):
    """Stub (D-08): demuestra la extensibilidad del Adapter; la v1 no contrata proveedor de SMS."""

    def enviar(self, destinatario, mensaje):
        logger.info("AdaptadorSMS (stub): no se envía SMS a %s.", destinatario)
        return False
