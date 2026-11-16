"""
RNF-02 (DEDS 3.5): bloqueo temporal tras varios intentos fallidos consecutivos de inicio de sesión.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone


def registrar_intento_fallido(correo):
    """Suma un intento fallido; al llegar al máximo bloquea la cuenta durante LOGIN_BLOQUEO_MINUTOS."""
    Usuario = get_user_model()
    with transaction.atomic():
        usuario = Usuario.objects.select_for_update().filter(correo__iexact=correo).first()
        if usuario is None:
            return None
        usuario.intentos_fallidos += 1
        if usuario.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
            usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.LOGIN_BLOQUEO_MINUTOS)
            usuario.intentos_fallidos = 0
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        return usuario


def reiniciar_intentos(usuario):
    if usuario.intentos_fallidos or usuario.bloqueado_hasta:
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])


def bloquear(usuario):
    """D-52: bloqueo manual; la persona no puede entrar hasta que la desbloqueen."""
    usuario.bloqueado_manual = True
    usuario.save(update_fields=["bloqueado_manual"])


def desbloquear(usuario):
    """D-51/D-52: quita el bloqueo manual y el temporal por intentos fallidos."""
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.bloqueado_manual = False
    usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta", "bloqueado_manual"])
