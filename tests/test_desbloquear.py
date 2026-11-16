"""D-51: el administrador ve qué cuentas están bloqueadas por intentos fallidos y puede desbloquearlas."""
import pytest
from django.conf import settings
from django.urls import reverse

from conftest import PASSWORD

pytestmark = pytest.mark.django_db
URL_LOGIN = reverse("autenticacion:login")


def bloquear(client, usuario):
    for _ in range(settings.LOGIN_MAX_INTENTOS):
        client.post(URL_LOGIN, {"username": usuario.correo, "password": "equivocada"})
    usuario.refresh_from_db()
    assert usuario.esta_bloqueado()


def test_login_bloqueado_indica_minutos_y_como_desbloquear(client, bodeguero):
    bloquear(client, bodeguero)
    html = client.post(URL_LOGIN, {"username": bodeguero.correo, "password": PASSWORD}).content.decode()
    assert f"Intente de nuevo en {settings.LOGIN_BLOQUEO_MINUTOS} minutos" in html
    assert "Usuarios → Desbloquear" in html


def test_lista_muestra_bloqueada_y_desbloquea(client, cliente_de, dueno, bodeguero):
    bloquear(client, bodeguero)
    cliente = cliente_de(dueno)
    html = cliente.get(reverse("usuarios:usuarios")).content.decode()
    assert "Bloqueada" in html and reverse("usuarios:usuario_desbloquear", args=[bodeguero.pk]) in html
    respuesta = cliente.post(reverse("usuarios:usuario_desbloquear", args=[bodeguero.pk]), follow=True)
    assert "desbloqueada" in respuesta.content.decode()
    bodeguero.refresh_from_db()
    assert not bodeguero.esta_bloqueado()
    cliente.logout()
    assert client.post(URL_LOGIN, {"username": bodeguero.correo, "password": PASSWORD}).status_code == 302


def test_restablecer_contrasena_desbloquea(client, cliente_de, dueno, bodeguero):
    bloquear(client, bodeguero)
    cliente_de(dueno).post(reverse("usuarios:usuario_password", args=[bodeguero.pk]),
                           {"new_password1": "Otra-Clave-2026", "new_password2": "Otra-Clave-2026"})
    bodeguero.refresh_from_db()
    assert not bodeguero.esta_bloqueado()


def test_solo_quien_administra_usuarios_desbloquea(client, cliente_de, bodeguero, encargado_sc):
    bloquear(client, encargado_sc)
    respuesta = cliente_de(bodeguero).post(reverse("usuarios:usuario_desbloquear", args=[encargado_sc.pk]))
    assert respuesta.status_code == 403
    encargado_sc.refresh_from_db()
    assert encargado_sc.esta_bloqueado()
