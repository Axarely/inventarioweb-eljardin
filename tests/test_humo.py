"""
Pruebas de humo de la Fase 1: verifican que el entorno (Django + PostgreSQL + auth)
está bien configurado. No sustituyen las pruebas por RF de los sprints.
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse

pytestmark = pytest.mark.humo


def test_humo_settings_cargados():
    assert settings.AUTH_USER_MODEL == "usuarios.Usuario"
    assert settings.LANGUAGE_CODE == "es"
    for app in ("autenticacion", "usuarios", "proveedores", "inventario", "alertas", "reportes"):
        assert app in settings.INSTALLED_APPS


@pytest.mark.django_db
def test_humo_base_de_datos_es_postgresql():
    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version")
        assert cursor.fetchone()[0].startswith("16")


@pytest.mark.django_db
def test_rf01_inicio_sin_sesion_redirige_a_login(client):
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert reverse("autenticacion:login") in respuesta["Location"]


@pytest.mark.django_db
def test_rf01_pagina_login_responde(client):
    respuesta = client.get(reverse("autenticacion:login"))
    assert respuesta.status_code == 200
    assert "csrfmiddlewaretoken" in respuesta.content.decode()


@pytest.mark.django_db
def test_rf01_login_por_correo_y_rnf02_password_con_hash(client):
    usuario = get_user_model().objects.create_user(
        correo="bodega@eljardin.test", password="Clave-segura-123", nombre="Bodeguero"
    )
    assert usuario.password != "Clave-segura-123"
    assert usuario.password.startswith("pbkdf2_sha256$")

    respuesta = client.post(
        reverse("autenticacion:login"),
        {"username": "bodega@eljardin.test", "password": "Clave-segura-123"},
        follow=True,
    )
    assert respuesta.status_code == 200
    assert "Bienvenido, Bodeguero" in respuesta.content.decode()


@pytest.mark.django_db
def test_rf01_credenciales_invalidas_rechazadas(client):
    get_user_model().objects.create_user(
        correo="bodega@eljardin.test", password="Clave-segura-123", nombre="Bodeguero"
    )
    respuesta = client.post(
        reverse("autenticacion:login"),
        {"username": "bodega@eljardin.test", "password": "incorrecta"},
    )
    assert respuesta.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_rf01_usuario_inactivo_no_inicia_sesion(client):
    get_user_model().objects.create_user(
        correo="baja@eljardin.test", password="Clave-segura-123", nombre="Baja", activo=False
    )
    client.post(
        reverse("autenticacion:login"),
        {"username": "baja@eljardin.test", "password": "Clave-segura-123"},
    )
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_rf18_logout_invalida_sesion(client):
    usuario = get_user_model().objects.create_user(
        correo="duena@eljardin.test", password="Clave-segura-123", nombre="Dueña"
    )
    client.force_login(usuario)
    client.post(reverse("autenticacion:logout"))
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302
