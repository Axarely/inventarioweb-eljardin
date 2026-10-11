"""
Pruebas del Módulo de Autenticación (plan de pruebas §5, RF-01): menú por rol, matriz RBAC,
bloqueo tras intentos fallidos y expiración de sesión (RNF-02).
"""
from datetime import timedelta

import pytest
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone

from autenticacion.menu import opciones_para
from conftest import PASSWORD

pytestmark = pytest.mark.django_db

URL_LOGIN = reverse("autenticacion:login")


def _login(client, correo, password=PASSWORD):
    return client.post(URL_LOGIN, {"username": correo, "password": password})


# --- Menú filtrado por rol (CP-RF01-01/02) ----------------------------------------------------

@pytest.mark.parametrize(
    "rol, esperado",
    [
        ("bodeguero", ["Inicio", "Entradas", "Salidas", "Historial"]),
        ("encargado_sc", ["Inicio", "Existencias"]),
        ("dueno", ["Inicio", "Catálogo", "Usuarios", "Roles", "Proveedores", "Existencias", "Historial"]),
    ],
)
def test_rf01_menu_por_rol(request, cliente_de, rol, esperado):
    usuario = request.getfixturevalue(rol)
    assert [etiqueta for etiqueta, _ in opciones_para(usuario)] == esperado
    respuesta = cliente_de(usuario).get(reverse("inicio"))
    assert [item["etiqueta"] for item in respuesta.context["menu"]] == esperado
    assert "Cerrar sesión" in respuesta.content.decode()


def test_rf01_usuario_sin_rol_solo_ve_inicio(cliente_de, django_user_model):
    usuario = django_user_model.objects.create_user(correo="sinrol@eljardin.test", password=PASSWORD, nombre="Sin rol")
    respuesta = cliente_de(usuario).get(reverse("inicio"))
    assert [item["etiqueta"] for item in respuesta.context["menu"]] == ["Inicio"]
    assert "no tiene un rol asignado" in respuesta.content.decode()


# --- Matriz RBAC (CP-RF01-05) -----------------------------------------------------------------

RUTAS = {
    "entrada": reverse("inventario:entrada"),
    "salida": reverse("inventario:salida"),
    "existencias": reverse("inventario:existencias"),
    "historial": reverse("inventario:historial"),
    "usuarios": reverse("usuarios:usuarios"),
    "usuario_crear": reverse("usuarios:usuario_crear"),
    "roles": reverse("usuarios:roles"),
    "catalogo": reverse("usuarios:productos"),
    "producto_crear": reverse("usuarios:producto_crear"),
    "proveedores": reverse("proveedores:lista"),
    "proveedor_crear": reverse("proveedores:crear"),
}

PERMITIDAS = {
    "bodeguero": {"entrada", "salida", "historial", "producto_crear"},
    "encargado_sc": {"existencias"},
    "dueno": {"existencias", "historial", "usuarios", "usuario_crear", "roles", "catalogo",
              "producto_crear", "proveedores", "proveedor_crear"},
}


@pytest.mark.parametrize("rol", list(PERMITIDAS))
@pytest.mark.parametrize("ruta", list(RUTAS))
def test_rf01_matriz_rbac(request, cliente_de, bodega, rol, ruta):
    usuario = request.getfixturevalue(rol)
    codigo = cliente_de(usuario).get(RUTAS[ruta]).status_code
    assert codigo == (200 if ruta in PERMITIDAS[rol] else 403), f"{rol} -> {ruta}: {codigo}"


@pytest.mark.parametrize("ruta", list(RUTAS))
def test_rf01_sin_sesion_redirige_a_login(client, ruta):
    """CP-RF01-06."""
    respuesta = client.get(RUTAS[ruta])
    assert respuesta.status_code == 302
    assert respuesta["Location"].startswith(URL_LOGIN)


def test_rf01_403_muestra_pagina_propia(cliente_de, encargado_sc):
    respuesta = cliente_de(encargado_sc).get(RUTAS["usuarios"])
    assert respuesta.status_code == 403
    assert "Acceso denegado" in respuesta.content.decode()


def test_rf01_superusuario_ve_todo(cliente_de, django_user_model):
    admin = django_user_model.objects.create_superuser(correo="admin@eljardin.test", password=PASSWORD, nombre="Admin")
    assert len(opciones_para(admin)) == 9
    assert admin.tiene_permiso("inventario.registrar_entrada")


# --- Login por correo (RF-01) -----------------------------------------------------------------

def test_rf01_login_correo_sin_distinguir_mayusculas(client, bodeguero):
    respuesta = _login(client, "BODEGUERO@ElJardin.test")
    assert respuesta.status_code == 302
    assert client.session["_auth_user_id"] == str(bodeguero.pk)


def test_rf01_mensaje_generico_en_fallo(client, bodeguero):
    respuesta = _login(client, "bodeguero@eljardin.test", "mal")
    assert "Correo o contraseña incorrectos." in respuesta.content.decode()
    respuesta = _login(client, "noexiste@eljardin.test", "mal")
    assert "Correo o contraseña incorrectos." in respuesta.content.decode()


# --- Bloqueo tras intentos fallidos (CP-RF01-07, RNF-02) --------------------------------------

def test_rf01_bloqueo_tras_intentos_fallidos(client, bodeguero, settings):
    settings.LOGIN_MAX_INTENTOS = 5
    for _ in range(5):
        _login(client, bodeguero.correo, "incorrecta")
    bodeguero.refresh_from_db()
    assert bodeguero.esta_bloqueado()

    respuesta = _login(client, bodeguero.correo)  # contraseña correcta, pero bloqueada
    assert "_auth_user_id" not in client.session
    assert "bloqueada temporalmente" in respuesta.content.decode()


def test_rf01_bloqueo_expira(client, bodeguero):
    bodeguero.bloqueado_hasta = timezone.now() - timedelta(seconds=1)
    bodeguero.save()
    assert _login(client, bodeguero.correo).status_code == 302
    bodeguero.refresh_from_db()
    assert bodeguero.bloqueado_hasta is None and bodeguero.intentos_fallidos == 0


def test_rf01_login_exitoso_reinicia_contador(client, bodeguero):
    for _ in range(3):
        _login(client, bodeguero.correo, "incorrecta")
    bodeguero.refresh_from_db()
    assert bodeguero.intentos_fallidos == 3
    _login(client, bodeguero.correo)
    bodeguero.refresh_from_db()
    assert bodeguero.intentos_fallidos == 0


# --- Expiración de sesión por inactividad (CP-RF01-08) ----------------------------------------

def test_rnf02_sesion_expira_por_inactividad(client, bodeguero, settings):
    assert settings.SESSION_SAVE_EVERY_REQUEST is True
    assert settings.SESSION_COOKIE_AGE <= 60 * 60
    _login(client, bodeguero.correo)
    assert client.get(reverse("inicio")).status_code == 200
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))  # simula inactividad
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302 and respuesta["Location"].startswith(URL_LOGIN)


def test_rnf02_actividad_renueva_expiracion(client, bodeguero):
    _login(client, bodeguero.correo)
    antes = Session.objects.get().expire_date
    Session.objects.update(expire_date=antes - timedelta(minutes=10))
    client.get(reverse("inicio"))
    assert Session.objects.get().expire_date > antes - timedelta(minutes=10)


def test_rnf02_csrf_obligatorio_en_login(bodeguero):
    from django.test import Client

    cliente = Client(enforce_csrf_checks=True)
    respuesta = cliente.post(URL_LOGIN, {"username": bodeguero.correo, "password": PASSWORD})
    assert respuesta.status_code == 403
