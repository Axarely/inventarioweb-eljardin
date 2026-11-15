"""
D-32 (RF-09): categorías de productos. Las 9 fijas siempre existen y no se eliminan; las demás se
agregan (también desde el formulario del producto) y se eliminan si no tienen productos.
"""
import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from conftest import PASSWORD, categoria_fija
from usuarios.models import CATEGORIAS_BASE, Categoria, Producto, Rol

pytestmark = pytest.mark.django_db

URL_CREAR_PRODUCTO = reverse("usuarios:producto_crear")


def producto(**cambios):
    return {"nombre": "Harina", "categoria": "", "unidad_medida": "lb", "stock_minimo": "5", **cambios}


# --- Categorías fijas ---------------------------------------------------------------------------

def test_rf09_categorias_fijas_en_orden():
    fijas = list(Categoria.objects.filter(es_base=True).values_list("nombre", flat=True))
    assert fijas == CATEGORIAS_BASE == [
        "Proteínas", "Lácteos", "Congelados", "Concentrados", "Abarrotes", "Latas y aderezos", "Verduras",
        "Desechables y limpieza", "Varios",
    ]


def test_rf09_categoria_fija_no_se_elimina_ni_por_modelo():
    with pytest.raises(ValidationError, match="fija"):
        categoria_fija("Verduras").delete()
    assert Categoria.objects.filter(nombre="Verduras").exists()


def test_rf09_nombre_unico_sin_distinguir_mayusculas():
    with pytest.raises(IntegrityError), transaction.atomic():
        Categoria.objects.create(nombre="lácteos")


def test_rf09_obtener_o_crear():
    existente, creada = Categoria.obtener_o_crear("  proteínas ")
    assert existente == categoria_fija("Proteínas") and creada is False
    nueva, creada = Categoria.obtener_o_crear("bebidas   calientes")
    assert nueva.nombre == "Bebidas calientes" and creada is True and not nueva.es_base
    with pytest.raises(ValidationError):
        Categoria.obtener_o_crear("   ")


# --- Agregar categoría desde el formulario del producto ------------------------------------------

def test_rf09_producto_con_categoria_nueva(cliente_de, dueno):
    respuesta = cliente_de(dueno).post(URL_CREAR_PRODUCTO, producto(nueva_categoria="Bebidas"), follow=True)
    harina = Producto.objects.get(nombre="Harina")
    assert harina.categoria.nombre == "Bebidas" and not harina.categoria.es_base
    assert "Categoría «Bebidas» agregada." in respuesta.content.decode()


@pytest.mark.parametrize("escrita", ["LÁCTEOS", "lacteos", "Lácteo", "  lacteo "])
def test_d35_categoria_nueva_que_ya_existe_avisa(cliente_de, dueno, escrita):
    """D-35: sin importar mayúsculas, tildes ni singular/plural, se avisa que ya existe y no se duplica."""
    respuesta = cliente_de(dueno).post(URL_CREAR_PRODUCTO, producto(nueva_categoria=escrita))
    assert "La categoría «Lácteos» ya existe" in str(respuesta.context["form"].errors["nueva_categoria"])
    assert not Producto.objects.filter(nombre="Harina").exists()
    assert Categoria.objects.filter(nombre__icontains="cteo").count() == 1


@pytest.mark.parametrize("escrita", ["proteina", "PROTEINAS", "Proteínas", "Desechable y limpiezas", "verdura"])
def test_d35_pagina_categorias_avisa_que_existe_y_es_fija(cliente_de, dueno, escrita):
    total = Categoria.objects.count()
    respuesta = cliente_de(dueno).post(reverse("usuarios:categoria_crear"), {"nombre": escrita})
    assert "ya existe (es una categoría fija)" in respuesta.content.decode()
    assert Categoria.objects.count() == total


def test_d35_categoria_realmente_nueva_se_agrega(cliente_de, dueno):
    cliente_de(dueno).post(reverse("usuarios:categoria_crear"), {"nombre": "panadería"})
    assert Categoria.objects.filter(nombre="Panadería", es_base=False).exists()


def test_rf09_categoria_obligatoria(cliente_de, dueno):
    respuesta = cliente_de(dueno).post(URL_CREAR_PRODUCTO, producto())
    assert "Elija una categoría o escriba una nueva." in str(respuesta.context["form"].errors["categoria"])
    assert not Producto.objects.filter(nombre="Harina").exists()


def test_rf09_categoria_nueva_no_queda_si_el_producto_falla(cliente_de, dueno, otro_producto):
    """El producto (nombre repetido) no se guarda: la categoría escrita tampoco debe quedar creada."""
    respuesta = cliente_de(dueno).post(URL_CREAR_PRODUCTO, producto(nombre="Servilletas", nueva_categoria="Papelería"))
    assert respuesta.status_code == 200 and "nombre" in respuesta.context["form"].errors
    assert not Categoria.objects.filter(nombre="Papelería").exists()


def test_rf09_campo_nueva_categoria_segun_permiso(cliente_de, bodeguero, django_user_model):
    """El bodeguero (UC02 A1) puede agregar categorías; un rol solo con add_producto no."""
    assert "nueva_categoria" in cliente_de(bodeguero).get(URL_CREAR_PRODUCTO).context["form"].fields
    rol = Rol.objects.create(nombre="Solo catálogo")
    rol.agregar_permiso(Permission.objects.get(codename="add_producto"))
    usuario = django_user_model.objects.create_user(correo="cat@eljardin.test", password=PASSWORD, nombre="C", rol=rol)
    formulario = cliente_de(usuario).get(URL_CREAR_PRODUCTO).context["form"]
    assert "nueva_categoria" not in formulario.fields
    cliente_de(usuario).post(URL_CREAR_PRODUCTO, producto(nueva_categoria="Intento"))
    assert not Categoria.objects.filter(nombre="Intento").exists()


# --- Página de categorías (dueño) -----------------------------------------------------------------

def test_rf09_pagina_categorias_agregar_y_eliminar(cliente_de, dueno):
    cliente = cliente_de(dueno)
    lista = cliente.get(reverse("usuarios:categorias"))
    assert [c.nombre for c in lista.context["categorias"]][:9] == CATEGORIAS_BASE
    cliente.post(reverse("usuarios:categoria_crear"), {"nombre": "  panadería "})
    panaderia = Categoria.objects.get(nombre="Panadería")
    duplicada = cliente.post(reverse("usuarios:categoria_crear"), {"nombre": "PANADERÍA"})
    assert "ya existe" in duplicada.content.decode()
    respuesta = cliente.post(reverse("usuarios:categoria_eliminar", args=[panaderia.pk]), follow=True)
    assert "Categoría «Panadería» eliminada." in respuesta.content.decode()
    assert not Categoria.objects.filter(pk=panaderia.pk).exists()


def test_rf09_no_elimina_fija_ni_con_productos(cliente_de, dueno, producto):
    cliente = cliente_de(dueno)
    fija = categoria_fija("Varios")
    respuesta = cliente.post(reverse("usuarios:categoria_eliminar", args=[fija.pk]), follow=True)
    assert "es una categoría fija" in respuesta.content.decode() and Categoria.objects.filter(pk=fija.pk).exists()
    agregada = Categoria.objects.create(nombre="Aves")
    producto.categoria = agregada
    producto.save()
    respuesta = cliente.post(reverse("usuarios:categoria_eliminar", args=[agregada.pk]), follow=True)
    assert "tiene 1 producto" in respuesta.content.decode() and Categoria.objects.filter(pk=agregada.pk).exists()


def test_rf09_categorias_solo_dueno(cliente_de, bodeguero, encargado_sc):
    agregada = Categoria.objects.create(nombre="Temporal")
    for usuario in (bodeguero, encargado_sc):
        cliente = cliente_de(usuario)
        assert cliente.get(reverse("usuarios:categorias")).status_code == 403
        assert cliente.post(reverse("usuarios:categoria_eliminar", args=[agregada.pk])).status_code == 403
    assert Categoria.objects.filter(pk=agregada.pk).exists()


def test_rf05_filtro_de_existencias_por_categoria_muestra_nombres(cliente_de, encargado_sc, santa_cruz, producto,
                                                                  con_existencia):
    con_existencia(producto, santa_cruz, 20)
    respuesta = cliente_de(encargado_sc).get(reverse("inventario:existencias"))
    assert [c.nombre for c in respuesta.context["categorias"]] == ["Proteínas"]
    assert "<td>Proteínas</td>" in respuesta.content.decode()


def test_rf09_categorias_fijas_se_restauran_tras_flush():
    """DEF-10: un flush (o cualquier borrado) no deja al sistema sin las categorías fijas."""
    from usuarios.roles import sincronizar_categorias_base

    Producto.objects.all().delete()
    Categoria.objects.all().delete()  # QuerySet.delete no pasa por Categoria.delete()
    Categoria.objects.create(nombre="verduras")  # una homónima sin marcar como fija
    sincronizar_categorias_base()
    assert list(Categoria.objects.filter(es_base=True).values_list("nombre", flat=True)) == CATEGORIAS_BASE
    assert Categoria.objects.filter(nombre__iexact="verduras").count() == 1


@pytest.mark.parametrize("unidad", ["kg", "KG", "kilos", "Kilogramos", "kg."])
def test_d36_no_se_registran_productos_en_kilos(cliente_de, dueno, unidad):
    respuesta = cliente_de(dueno).post(URL_CREAR_PRODUCTO, producto(categoria=categoria_fija("Proteínas").pk,
                                                                     unidad_medida=unidad))
    assert "escriba la unidad en libras" in str(respuesta.context["form"].errors["unidad_medida"])
    assert not Producto.objects.filter(nombre="Harina").exists()


def test_d36_libras_si_se_aceptan(cliente_de, dueno):
    cliente_de(dueno).post(URL_CREAR_PRODUCTO, producto(categoria=categoria_fija("Proteínas").pk, unidad_medida="lb"))
    assert Producto.objects.get(nombre="Harina").unidad_medida == "lb"
