"""
D-31: solicitud de cuenta desde la pantalla de acceso, con aprobación del dueño (RF-10, RF-01, RNF-02).
Quien se registra NO obtiene acceso ni permisos hasta que un dueño le asigna un rol.
"""
import pytest
from django.urls import reverse

from conftest import PASSWORD
from usuarios.models import Rol, Usuario
from usuarios.roles import rol_base

pytestmark = pytest.mark.django_db

URL_REGISTRO = reverse("autenticacion:registro")
DATOS = {"nombre": "Ana Pérez", "correo": "Ana.Perez@ElJardin.test", "password1": "Otra-clave-456", "password2": "Otra-clave-456"}


def registrar(client, **cambios):
    return client.post(URL_REGISTRO, {**DATOS, **cambios})


def test_rf10_registro_crea_solicitud_inactiva_sin_rol(client):
    respuesta = registrar(client)
    assert respuesta.status_code == 302 and respuesta["Location"] == reverse("autenticacion:login")
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    assert solicitud.activo is False and solicitud.rol is None and not solicitud.is_staff
    assert solicitud.es_solicitud_pendiente
    assert solicitud.password.startswith("pbkdf2_sha256$")  # RNF-02
    assert list(Usuario.objects.solicitudes_pendientes()) == [solicitud]


def test_rf01_solicitud_no_puede_entrar_ni_tiene_permisos(client):
    registrar(client)
    mensaje = client.get(reverse("autenticacion:login")).content.decode()
    assert "Un dueño debe aprobar su cuenta" in mensaje
    respuesta = client.post(reverse("autenticacion:login"), {"username": DATOS["correo"], "password": DATOS["password1"]})
    assert "_auth_user_id" not in client.session
    assert "Correo o contraseña incorrectos." in respuesta.content.decode()
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    assert solicitud.get_all_permissions() == set()


@pytest.mark.parametrize("cambios, campo", [
    ({"correo": "no-es-correo"}, "correo"),
    ({"password2": "distinta-789"}, "password2"),
    ({"password1": "12345678", "password2": "12345678"}, "password2"),
    ({"nombre": ""}, "nombre"),
])
def test_rf10_registro_valida_datos(client, cambios, campo):
    respuesta = registrar(client, **cambios)
    assert respuesta.status_code == 200 and campo in respuesta.context["form"].errors
    assert not Usuario.objects.exists()


def test_rf10_registro_rechaza_correo_existente(client, bodeguero):
    respuesta = registrar(client, correo="BODEGUERO@eljardin.test")
    assert "Ya existe un usuario con ese correo." in respuesta.content.decode()


def test_rf10_registro_ignora_campos_de_privilegio(client):
    """Mínimo privilegio: aunque se envíen, rol/activo/is_staff no se toman del formulario público."""
    registrar(client, rol=rol_base(Rol.Codigo.DUENO).pk, activo="on", is_staff="on", is_superuser="on")
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    assert solicitud.rol is None and not solicitud.activo and not solicitud.is_staff and not solicitud.is_superuser


def test_rf10_usuario_con_sesion_no_ve_registro(cliente_de, bodeguero):
    respuesta = cliente_de(bodeguero).get(URL_REGISTRO)
    assert respuesta.status_code == 302 and respuesta["Location"] == reverse("inicio")


def test_rf10_paginas_de_acceso_muestran_identidad(client):
    login = client.get(reverse("autenticacion:login")).content.decode()
    registro = client.get(URL_REGISTRO).content.decode()
    for html in (login, registro):
        assert "El Jardín" in html and "acceso-tarjeta" in html and "csrfmiddlewaretoken" in html
    assert reverse("autenticacion:registro") in login and reverse("autenticacion:login") in registro


# --- Aprobación por el dueño ---------------------------------------------------------------------

def test_rf10_dueno_ve_y_aprueba_solicitud(client, cliente_de, dueno, santa_cruz):
    registrar(client)
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    duena = cliente_de(dueno)
    inicio = duena.get(reverse("reportes:dashboard"))
    usuarios = next(i for i in inicio.context["menu"] if i["etiqueta"] == "Usuarios")
    assert usuarios["insignia"] == 1
    lista = duena.get(reverse("usuarios:usuarios"), {"estado": "pendientes"})
    assert list(lista.context["object_list"]) == [solicitud] and "Aprobar" in lista.content.decode()

    formulario = duena.get(reverse("usuarios:usuario_editar", args=[solicitud.pk]), {"aprobar": 1})
    assert formulario.context["form"].initial["activo"] is True
    duena.post(reverse("usuarios:usuario_editar", args=[solicitud.pk]), {
        "nombre": solicitud.nombre, "correo": solicitud.correo, "rol": rol_base(Rol.Codigo.ENCARGADO).pk,
        "sucursal": santa_cruz.pk, "activo": "on",
    })
    solicitud.refresh_from_db()
    assert solicitud.activo and solicitud.rol.codigo == "encargado" and not solicitud.es_solicitud_pendiente
    assert "insignia" not in next(
        i for i in duena.get(reverse("reportes:dashboard")).context["menu"] if i["etiqueta"] == "Usuarios")

    duena.post(reverse("autenticacion:logout"))
    client.post(reverse("autenticacion:login"), {"username": DATOS["correo"], "password": DATOS["password1"]})
    assert client.get(reverse("inventario:existencias")).status_code == 200  # ya entra, con su rol


def test_rf10_aprobar_exige_rol(cliente_de, client, dueno):
    registrar(client)
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    respuesta = cliente_de(dueno).post(reverse("usuarios:usuario_editar", args=[solicitud.pk]), {
        "nombre": solicitud.nombre, "correo": solicitud.correo, "activo": "on",
    })
    assert "rol" in respuesta.context["form"].errors
    solicitud.refresh_from_db()
    assert not solicitud.activo


def test_rf10_activar_sin_rol_no_aprueba(cliente_de, client, dueno):
    registrar(client)
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    respuesta = cliente_de(dueno).post(reverse("usuarios:usuario_activar", args=[solicitud.pk]), follow=True)
    solicitud.refresh_from_db()
    assert not solicitud.activo and "asígnele un rol" in respuesta.content.decode()


def test_rf10_rechazar_solicitud(cliente_de, client, dueno, bodeguero):
    registrar(client)
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    cliente = cliente_de(dueno)
    cliente.post(reverse("usuarios:usuario_rechazar", args=[solicitud.pk]))
    assert not Usuario.objects.filter(pk=solicitud.pk).exists()
    # un usuario normal (con rol) nunca se puede "rechazar" ni borrar por esta vía
    assert cliente.post(reverse("usuarios:usuario_rechazar", args=[bodeguero.pk])).status_code == 404
    assert Usuario.objects.filter(pk=bodeguero.pk).exists()


def test_rf10_solo_el_dueno_aprueba_o_rechaza(cliente_de, client, bodeguero):
    registrar(client)
    solicitud = Usuario.objects.get(correo="ana.perez@eljardin.test")
    cliente = cliente_de(bodeguero)
    assert cliente.post(reverse("usuarios:usuario_rechazar", args=[solicitud.pk])).status_code == 403
    assert cliente.get(reverse("usuarios:usuarios"), {"estado": "pendientes"}).status_code == 403
