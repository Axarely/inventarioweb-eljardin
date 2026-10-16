"""
Interfaz IAlertas (DEDS 3.2) y observador AlertaInventarioService (DEDS 3.4, Fig. 23 y 24).
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from inventario.excepciones import formatear_cantidad
from inventario.models import Existencia
from inventario.observador import IObservadorExistencia
from usuarios.models import Rol, Usuario

from .models import AlertaInventario

logger = logging.getLogger(__name__)

NIVELES_DE_ALERTA = (Existencia.Nivel.BAJO, Existencia.Nivel.AGOTADO)


def notificador_configurado():
    return import_string(settings.NOTIFICADOR)()


class AlertaInventarioService(IObservadorExistencia):
    def __init__(self, notificador=None):
        self._notificador = notificador

    @property
    def notificador(self):
        # Se resuelve al usarlo, para que las pruebas puedan cambiar settings.NOTIFICADOR.
        return self._notificador or notificador_configurado()

    # --- Observer -----------------------------------------------------------------------------
    def actualizar(self, existencia):  # RF-06, UC05
        """Cada movimiento que deja la existencia bajo el umbral genera (o actualiza) su alerta."""
        if existencia.nivel() in NIVELES_DE_ALERTA:
            self.generar_alerta(existencia)

    # --- IAlertas -----------------------------------------------------------------------------
    def generar_alerta(self, existencia):  # RF-06
        """
        Sin duplicar: si ya hay una alerta pendiente para esta existencia se actualizan su fecha y su
        nivel; si no, se crea. Si la existencia quedó Agotada y la alerta no lo estaba ya, se notifica a
        los dueños por correo (RF-16) DESPUÉS del commit: si la transacción se revierte no se envía nada
        y si el correo falla el movimiento no se revierte.
        """
        pendiente = (
            AlertaInventario.objects.select_for_update()
            .filter(existencia=existencia, estado=AlertaInventario.Estado.PENDIENTE)
            .first()
        )
        ya_estaba_agotada = pendiente is not None and pendiente.es_agotado
        if pendiente is None:
            alerta = AlertaInventario.objects.create(existencia=existencia, nivel_detectado=existencia.cantidad)
        else:
            alerta = pendiente
            alerta.generada_en = timezone.now()
            alerta.nivel_detectado = existencia.cantidad
            alerta.save(update_fields=["generada_en", "nivel_detectado"])
        if existencia.nivel() == Existencia.Nivel.AGOTADO and not ya_estaba_agotada:
            alerta_id = alerta.pk
            transaction.on_commit(lambda: self.notificar(alerta_id))
        return alerta

    def marcar_atendida(self, alerta_id, usuario_id):
        alerta = AlertaInventario.objects.get(pk=alerta_id)
        return alerta.marcar_atendida(Usuario.objects.get(pk=usuario_id))

    def notificar(self, alerta_id):  # RF-16
        """Envía la notificación a cada dueño activo. Devuelve cuántos envíos aceptó el canal."""
        alerta = AlertaInventario.objects.select_related("existencia__producto", "existencia__ubicacion").get(
            pk=alerta_id
        )
        mensaje = self.redactar_mensaje(alerta)
        enviados = 0
        for correo in duenos_a_notificar():
            try:
                enviados += bool(self.notificador.enviar(correo, mensaje))
            except Exception:  # un fallo del canal no debe afectar la operación de inventario
                logger.exception("No se pudo notificar la alerta %s a %s", alerta_id, correo)
        return enviados

    @staticmethod
    def redactar_mensaje(alerta):
        existencia = alerta.existencia
        fecha = timezone.localtime(alerta.generada_en).strftime("%d/%m/%Y %H:%M")
        return (
            f"Producto agotado: {existencia.producto} en {existencia.ubicacion}\n\n"
            f"El producto «{existencia.producto}» quedó AGOTADO en {existencia.ubicacion} "
            f"({alerta.nivel_detectado_texto}) el {fecha}.\n"
            f"Stock mínimo configurado: {formatear_cantidad(existencia.producto.stock_minimo)} "
            f"{existencia.producto.unidad_medida}.\n\n"
            "Revise la pantalla de Alertas de InventarioWeb El Jardín para gestionar la reposición."
        )


def duenos_a_notificar():
    return list(
        Usuario.objects.filter(rol__codigo=Rol.Codigo.DUENO, activo=True)
        .exclude(correo="")
        .values_list("correo", flat=True)
    )


def alertas_pendientes():
    return AlertaInventario.objects.filter(estado=AlertaInventario.Estado.PENDIENTE).select_related(
        "existencia__producto", "existencia__ubicacion"
    )
