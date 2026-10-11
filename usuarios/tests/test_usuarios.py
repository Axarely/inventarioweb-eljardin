"""
Pruebas del Módulo de Usuarios y Roles: usuarios y roles (RF-10), catálogo (RF-09), RBAC (RF-01).
"""
from decimal import Decimal

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from conftest import PASSWORD
from usuarios.models import Producto, Rol, Usuario
from usuarios.roles import PERMISOS_POR_ROL, rol_base, sincronizar_roles_base

pytestmark = pytest.mark.django_db


# --- Roles base y RBAC -------------------------------------------------------------------------

@pytest.mark.unitaria
def test_rf01_roles_base_con_permisos_exactos():
    for codigo, nombres in PERMISOS_POR_ROL.items():
        rol = rol_base(codigo)
        actuales = {f"{p.content_type.app_label}.{p.codename}" for p in rol.permisos.all()}
        assert actuales == set(nombres), codigo


@pytest.mark.unitaria
def test_rf01_sincronizar_restaura_permisos_base():
    rol = rol_base(Rol.Codigo.ENCARGADO)
    rol.permisos.add(Permission.objects.get(codename="registrar_entrada"))
    sincronizar_roles_base()
    assert not rol.permisos.filter(codename="registrar_entrada").exists()


@pytest.mark.unitaria
def test_rf01_tiene_permiso_segun_rol(bodeguero, encargado_sc):
    assert bodeguero.tiene_permiso("inventario.registrar_entrada")
    assert not bodeguero.tiene_permiso("usuarios.view_usuario")
    assert encargado_sc.tiene_permiso("inventario.consultar_existencias_propias")
    assert not encargado_sc.tiene_permiso("inventario.consultar_existencias_todas")


@pytest.mark.unitaria
def test_rf01_usuario_inactivo_sin_permisos(bodeguero):
    bodeguero.activo = False
    bodeguero.save()
    bodeguero = Usuario.objects.get(pk=bodeguero.pk)
    assert not bodeguero.tiene_permiso("inventario.registrar_entrada")


@pytest.mark.unitaria
def test_rf01_rol_agregar_permiso(django_user_model):
    rol = Rol.objects.create(nombre="Auditor")
    rol.agregar_permiso(Permission.objects.get(codename="ver_historial"))
    usuario = django_user_model.objects.create_user(correo="aud@eljardin.test", password=PASSWORD, nombre="A", rol=rol)
    assert usuario.tiene_permiso("inventario.ver_historial")
    assert not rol.es_base


# --- Modelo Usuario ----------------------------------------------------------------------------

@pytest.mark.unitaria
def test_rf10_encargado_requiere_sucursal(santa_cruz):
    usuario = Usuario(nombre="X", correo="x@eljardin.test", rol=rol_base(Rol.Codigo.ENCARGADO))
    with pytest.raises(ValidationError) as error:
        usuario.full_clean(exclude=["password"])
    assert "sucursal" in error.value.message_dict


@pytest.mark.unitaria
def test_rf10_solo_encargado_tiene_sucursal(santa_cruz):
    usuario = Usuario(nombre="X", correo="x@eljardin.test", rol=rol_base(Rol.Codigo.BODEGUERO), sucursal=santa_cruz)
    with pytest.raises(ValidationError):
        usuario.full_clean(exclude=["password"])


@pytest.mark.unitaria
def test_rf01_correo_unico_y_en_minusculas(django_user_model):
    usuario = django_user_model.objects.create_user(correo="Ana@ElJardin.TEST", password=PASSWORD, nombre="Ana")
    assert usuario.correo == "ana@eljardin.test"
    with pytest.raises(IntegrityError), transaction.atomic():
        django_user_model.objects.create_user(correo="ana@eljardin.test", password=PASSWORD, nombre="Otra")


@pytest.mark.unitaria
def test_rf01_correo_obligatorio(django_user_model):
    with pytest.raises(ValueError):
        django_user_model.objects.create_user(correo="", password=PASSWORD, nombre="Sin correo")


# --- CRUD de usuarios (RF-10) -------------------------------------------------------------------

def test_rf10_usuario_nuevo_inicia_sesion_con_su_rol(cliente_de, dueno, santa_cruz, client):
    """Criterio RF-10: un usuario nuevo inicia sesión y accede solo a las funciones de su rol."""
    respuesta = cliente_de(dueno).post(reverse("usuarios:usuario_crear"), {
        "nombre": "Nuevo encargado", "correo": "Nuevo@ElJardin.test",
        "rol": rol_base(Rol.Codigo.ENCARGADO).pk, "sucursal": santa_cruz.pk,
        "password1": "Otra-clave-456", "password2": "Otra-clave-456",
    })
    assert respuesta.status_code == 302
    nuevo = Usuario.objects.get(correo="nuevo@eljardin.test")
    assert nuevo.password.startswith("pbkdf2_sha256$")

    client.logout()
    client.post(reverse("autenticacion:login"), {"username": "nuevo@eljardin.test", "password": "Otra-clave-456"})
    assert client.get(reverse("inventario:existencias")).status_code == 200
    assert client.get(reverse("usuarios:usuarios")).status_code == 403


def test_rf10_crear_usuario_valida_datos(cliente_de, dueno, bodeguero):
    respuesta = cliente_de(dueno).post(reverse("usuarios:usuario_crear"), {
        "nombre": "Repetido", "correo": "BODEGUERO@eljardin.test", "rol": rol_base(Rol.Codigo.ENCARGADO).pk,
        "password1": "123", "password2": "456",
    })
    errores = respuesta.context["form"].errors
    assert "correo" in errores and "password2" in errores and "sucursal" in errores
    assert Usuario.objects.count() == 2


def test_rf10_crear_usuario_password_debil(cliente_de, dueno):
    respuesta = cliente_de(dueno).post(reverse("usuarios:usuario_crear"), {
        "nombre": "Débil", "correo": "debil@eljardin.test", "rol": rol_base(Rol.Codigo.BODEGUERO).pk,
        "password1": "12345678", "password2": "12345678",
    })
    assert "password2" in respuesta.context["form"].errors


def test_rf10_editar_y_desactivar_usuario(cliente_de, dueno, bodeguero):
    cliente = cliente_de(dueno)
    cliente.post(reverse("usuarios:usuario_editar", args=[bodeguero.pk]), {
        "nombre": "Bodeguero Editado", "correo": bodeguero.correo, "rol": bodeguero.rol_id, "activo": "on",
    })
    bodeguero.refresh_from_db()
    assert bodeguero.nombre == "Bodeguero Editado"

    cliente.post(reverse("usuarios:usuario_activar", args=[bodeguero.pk]))
    bodeguero.refresh_from_db()
    assert bodeguero.activo is False


def test_rf10_no_puede_desactivarse_a_si_mismo(cliente_de, dueno):
    cliente = cliente_de(dueno)
    cliente.post(reverse("usuarios:usuario_activar", args=[dueno.pk]))
    respuesta = cliente.post(reverse("usuarios:usuario_editar", args=[dueno.pk]), {
        "nombre": dueno.nombre, "correo": dueno.correo, "rol": dueno.rol_id,
    })
    dueno.refresh_from_db()
    assert dueno.activo is True
    assert "activo" in respuesta.context["form"].errors


def test_rf10_restablecer_password(cliente_de, dueno, bodeguero):
    cliente_de(dueno).post(reverse("usuarios:usuario_password", args=[bodeguero.pk]), {
        "new_password1": "Nueva-clave-789", "new_password2": "Nueva-clave-789",
    })
    bodeguero.refresh_from_db()
    assert bodeguero.check_password("Nueva-clave-789")


def test_rf10_lista_usuarios_busqueda(cliente_de, dueno, bodeguero, encargado_sc):
    lista = cliente_de(dueno).get(reverse("usuarios:usuarios"), {"q": "bodeguero"}).context["object_list"]
    assert list(lista) == [bodeguero]


def test_rf10_formularios_crear_cargan_sin_error(cliente_de, dueno):
    """Regresión R-01: los CreateView con success_url daban 500 al mostrar el formulario."""
    cliente = cliente_de(dueno)
    for nombre in ("usuarios:usuario_crear", "usuarios:rol_crear", "usuarios:producto_crear", "proveedores:crear"):
        respuesta = cliente.get(reverse(nombre))
        assert respuesta.status_code == 200, nombre
        assert respuesta.context["url_cancelar"]


def test_rf10_no_puede_cambiar_su_propio_rol(cliente_de, dueno):
    """Regresión R-03."""
    respuesta = cliente_de(dueno).post(reverse("usuarios:usuario_editar", args=[dueno.pk]), {
        "nombre": dueno.nombre, "correo": dueno.correo, "rol": rol_base(Rol.Codigo.BODEGUERO).pk, "activo": "on",
    })
    dueno.refresh_from_db()
    assert dueno.rol.codigo == Rol.Codigo.DUENO
    assert "rol" in respuesta.context["form"].errors


def test_rf10_rol_obligatorio_en_formulario(cliente_de, dueno):
    """Regresión R-06."""
    respuesta = cliente_de(dueno).post(reverse("usuarios:usuario_crear"), {
        "nombre": "Sin rol", "correo": "sinrol@eljardin.test",
        "password1": "Otra-clave-456", "password2": "Otra-clave-456",
    })
    assert "rol" in respuesta.context["form"].errors
    assert not Usuario.objects.filter(correo="sinrol@eljardin.test").exists()


def test_rf10_admin_no_crea_usuarios_sin_password(admin_client):
    """Regresión R-05."""
    assert admin_client.get("/admin/usuarios/usuario/add/").status_code == 403


# --- CRUD de roles (RF-10) ----------------------------------------------------------------------

def test_rf10_crud_rol_personalizado(cliente_de, dueno):
    cliente = cliente_de(dueno)
    permiso = Permission.objects.get(codename="ver_historial")
    cliente.post(reverse("usuarios:rol_crear"), {"nombre": "Auditor", "permisos": [permiso.pk]})
    rol = Rol.objects.get(nombre="Auditor")
    assert list(rol.permisos.all()) == [permiso]

    cliente.post(reverse("usuarios:rol_editar", args=[rol.pk]), {"nombre": "Auditor externo", "permisos": []})
    rol.refresh_from_db()
    assert rol.nombre == "Auditor externo" and not rol.permisos.exists()

    cliente.post(reverse("usuarios:rol_eliminar", args=[rol.pk]))
    assert not Rol.objects.filter(pk=rol.pk).exists()


def test_rf10_roles_base_no_editables(cliente_de, dueno):
    rol = rol_base(Rol.Codigo.BODEGUERO)
    cliente = cliente_de(dueno)
    assert cliente.get(reverse("usuarios:rol_editar", args=[rol.pk])).status_code == 404
    assert cliente.post(reverse("usuarios:rol_eliminar", args=[rol.pk])).status_code == 404


def test_rf10_no_elimina_rol_con_usuarios(cliente_de, dueno, django_user_model):
    rol = Rol.objects.create(nombre="Temporal")
    django_user_model.objects.create_user(correo="t@eljardin.test", password=PASSWORD, nombre="T", rol=rol)
    respuesta = cliente_de(dueno).post(reverse("usuarios:rol_eliminar", args=[rol.pk]), follow=True)
    assert Rol.objects.filter(pk=rol.pk).exists()
    assert "tiene usuarios asignados" in respuesta.content.decode()


# --- Catálogo de productos (RF-09) --------------------------------------------------------------

@pytest.mark.unitaria
def test_rf09_stock_minimo_no_negativo():
    producto = Producto(nombre="X", categoria="Y", unidad_medida="u.", stock_minimo=Decimal("-1"))
    with pytest.raises(ValidationError):
        producto.full_clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        producto.save()


def test_rf09_producto_creado_disponible_en_formularios(cliente_de, dueno, bodeguero):
    """Criterio RF-09: un producto creado queda disponible de inmediato en entradas y salidas."""
    cliente_de(dueno).post(reverse("usuarios:producto_crear"), {
        "nombre": "Queso mozzarella", "categoria": "Lácteos", "unidad_medida": "kg", "stock_minimo": "8",
    })
    producto = Producto.objects.get(nombre="Queso mozzarella")
    cliente = cliente_de(bodeguero)
    assert producto in cliente.get(reverse("inventario:entrada")).context["form"].fields["producto"].queryset
    assert producto in cliente.get(reverse("inventario:salida")).context["form"].fields["producto"].queryset


def test_rf09_editar_y_desactivar_producto(cliente_de, dueno, bodeguero, producto):
    cliente = cliente_de(dueno)
    cliente.post(reverse("usuarios:producto_editar", args=[producto.pk]), {
        "nombre": producto.nombre, "categoria": "Aves", "unidad_medida": "kg", "stock_minimo": "12",
    })
    cliente.post(reverse("usuarios:producto_activar", args=[producto.pk]))
    producto.refresh_from_db()
    assert producto.categoria == "Aves" and producto.stock_minimo == Decimal("12") and not producto.activo
    queryset = cliente_de(bodeguero).get(reverse("inventario:entrada")).context["form"].fields["producto"].queryset
    assert producto not in queryset


def test_rf09_filtros_catalogo(cliente_de, dueno, producto, otro_producto):
    lista = cliente_de(dueno).get(reverse("usuarios:productos"), {"categoria": "Desechables"}).context["object_list"]
    assert list(lista) == [otro_producto]


def test_rf09_bodeguero_crea_producto_y_vuelve(cliente_de, bodeguero):
    """UC02 A1: el bodeguero crea el producto y regresa al formulario de entrada."""
    destino = reverse("inventario:entrada")
    respuesta = cliente_de(bodeguero).post(
        reverse("usuarios:producto_crear") + f"?next={destino}",
        {"nombre": "Harina", "categoria": "Abarrotes", "unidad_medida": "kg", "stock_minimo": "5", "next": destino},
    )
    assert respuesta.status_code == 302 and respuesta["Location"] == destino
    assert Producto.objects.filter(nombre="Harina").exists()


def test_rf09_next_externo_se_ignora(cliente_de, dueno):
    respuesta = cliente_de(dueno).post(reverse("usuarios:producto_crear"), {
        "nombre": "Sal", "categoria": "Abarrotes", "unidad_medida": "kg", "stock_minimo": "1",
        "next": "https://malicioso.example.com/",
    })
    assert respuesta["Location"] == reverse("usuarios:productos")
