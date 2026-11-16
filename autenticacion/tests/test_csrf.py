"""
DEF-14: el doble clic en "Entrar" mostraba la página técnica 403 de CSRF. La protección se mantiene
(RNF-02: la petición con token inválido NO se procesa), pero el usuario recibe una respuesta comprensible.
"""
import pytest
from django.test import Client
from django.urls import reverse

from conftest import PASSWORD

pytestmark = pytest.mark.django_db

URL_LOGIN = reverse("autenticacion:login")


def cliente_csrf():
    return Client(enforce_csrf_checks=True)


def test_rnf02_doble_envio_de_login_no_muestra_error_tecnico(bodeguero):
    """Simula el doble clic: el primer POST inicia sesión (rota el token); el segundo llega con el viejo."""
    cliente = cliente_csrf()
    cliente.get(URL_LOGIN)
    token_viejo = cliente.cookies["csrftoken"].value
    datos = {"username": bodeguero.correo, "password": PASSWORD, "csrfmiddlewaretoken": token_viejo}
    primero = cliente.post(URL_LOGIN, datos)
    assert primero.status_code == 302 and "_auth_user_id" in cliente.session
    segundo = cliente.post(URL_LOGIN, datos)  # token ya rotado
    assert segundo.status_code == 302 and segundo["Location"] == reverse("inicio")


def test_rnf02_token_invalido_sin_sesion_vuelve_al_login_con_aviso(bodeguero):
    cliente = cliente_csrf()
    cliente.get(URL_LOGIN)
    respuesta = cliente.post(URL_LOGIN, {"username": bodeguero.correo, "password": PASSWORD,
                                         "csrfmiddlewaretoken": "x" * 64}, follow=True)
    assert "_auth_user_id" not in cliente.session  # RNF-02: no se procesó
    assert "La página había vencido. Vuelva a intentarlo." in respuesta.content.decode()


def test_rnf02_token_invalido_en_otro_formulario_muestra_pagina_amable(bodeguero, producto, proveedor, bodega):
    from inventario.models import MovimientoInventario

    cliente = cliente_csrf()
    cliente.force_login(bodeguero)
    cliente.logout()  # sin sesión: el aviso debe ser la página propia, no la técnica de Django
    respuesta = cliente.post(reverse("inventario:entrada"), {"producto": producto.pk, "cantidad": "5",
                                                             "proveedor": proveedor.nombre}, HTTP_REFERER="http://evil.example/")
    html = respuesta.content.decode()
    assert respuesta.status_code == 403 and "La página había vencido" in html
    assert "evil.example" not in html and "Reason given for failure" not in html
    assert not MovimientoInventario.objects.exists()
