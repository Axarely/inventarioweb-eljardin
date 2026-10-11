"""
Pruebas de las vistas de Inventario por rol (plan de pruebas §5): RF-02, RF-03, RF-05, RF-12.
"""
from decimal import Decimal

import pytest
from django.urls import reverse

from inventario.models import EntradaInventario, Existencia, MovimientoInventario, SalidaInventario

pytestmark = pytest.mark.django_db

URL_ENTRADA = reverse("inventario:entrada")
URL_SALIDA = reverse("inventario:salida")
URL_EXISTENCIAS = reverse("inventario:existencias")
URL_HISTORIAL = reverse("inventario:historial")
URL_API = reverse("inventario:existencia_bodega")


# --- RF-02 ---------------------------------------------------------------------------------------

def test_rf02_formulario_entrada_registra_movimiento(cliente_de, bodeguero, bodega, producto, proveedor):
    """CP-RF02-03."""
    respuesta = cliente_de(bodeguero).post(
        URL_ENTRADA, {"producto": producto.pk, "cantidad": "12.5", "proveedor": proveedor.pk}, follow=True
    )
    assert respuesta.status_code == 200
    entrada = EntradaInventario.objects.get()
    assert entrada.usuario == bodeguero and entrada.proveedor == proveedor and entrada.destino_id == bodega.pk
    assert Existencia.objects.get(producto=producto, ubicacion=bodega).cantidad == Decimal("12.5")
    assert "Entrada registrada: +12.5 kg de Pechuga de pollo" in respuesta.content.decode()


@pytest.mark.parametrize("cantidad", ["0", "-3", "abc", ""])
def test_rf02_formulario_rechaza_cantidad_invalida(cliente_de, bodeguero, bodega, producto, proveedor, cantidad):
    """CP-RF02-04 a través de la vista."""
    respuesta = cliente_de(bodeguero).post(
        URL_ENTRADA, {"producto": producto.pk, "cantidad": cantidad, "proveedor": proveedor.pk}
    )
    assert respuesta.status_code == 200
    assert respuesta.context["form"].errors["cantidad"]
    assert not MovimientoInventario.objects.exists()


def test_rf02_formulario_no_ofrece_inactivos(cliente_de, bodeguero, bodega, producto, proveedor_inactivo):
    """RF-09 / RF-11: productos y proveedores inactivos no aparecen en el formulario."""
    producto.activo = False
    producto.save()
    form = cliente_de(bodeguero).get(URL_ENTRADA).context["form"]
    assert producto not in form.fields["producto"].queryset
    assert proveedor_inactivo not in form.fields["proveedor"].queryset


def test_rf02_sin_bodega_muestra_error(cliente_de, bodeguero, producto, proveedor):
    respuesta = cliente_de(bodeguero).post(
        URL_ENTRADA, {"producto": producto.pk, "cantidad": "5", "proveedor": proveedor.pk}
    )
    assert "No hay una bodega central registrada." in respuesta.content.decode()


@pytest.mark.parametrize("rol", ["dueno", "encargado_sc"])
def test_rf02_solo_bodeguero_registra_entrada(request, cliente_de, rol, bodega, producto, proveedor):
    """CP-RF02-07."""
    usuario = request.getfixturevalue(rol)
    respuesta = cliente_de(usuario).post(
        URL_ENTRADA, {"producto": producto.pk, "cantidad": "5", "proveedor": proveedor.pk}
    )
    assert respuesta.status_code == 403
    assert not MovimientoInventario.objects.exists()


# --- RF-03 ---------------------------------------------------------------------------------------

def test_rf03_formulario_salida_registra(cliente_de, bodeguero, bodega, santa_cruz, producto, con_existencia):
    con_existencia(producto, bodega, 18)
    respuesta = cliente_de(bodeguero).post(
        URL_SALIDA, {"sucursal": santa_cruz.pk, "producto": producto.pk, "cantidad": "8"}, follow=True
    )
    assert SalidaInventario.objects.count() == 1
    assert Existencia.objects.get(producto=producto, ubicacion=santa_cruz).cantidad == Decimal("8")
    assert "Salida registrada: 8 kg de Pechuga de pollo hacia Santa Cruz." in respuesta.content.decode()


def test_rf03_formulario_insuficiente_sugiere_maximo(cliente_de, bodeguero, bodega, santa_cruz, producto, con_existencia):
    """CP-RF03-03 en la interfaz (Fig. 16): mensaje E1 y botón con la cantidad máxima (A1)."""
    con_existencia(producto, bodega, 12)
    respuesta = cliente_de(bodeguero).post(
        URL_SALIDA, {"sucursal": santa_cruz.pk, "producto": producto.pk, "cantidad": "15"}
    )
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert respuesta.context["cantidad_sugerida"] == Decimal("12")
    assert "Solo hay 12 kg disponibles en Bodega central" in html
    assert 'data-cantidad="12"' in html
    assert not MovimientoInventario.objects.exists()


def test_rf03_formulario_sin_existencia_no_sugiere(cliente_de, bodeguero, bodega, santa_cruz, producto):
    respuesta = cliente_de(bodeguero).post(
        URL_SALIDA, {"sucursal": santa_cruz.pk, "producto": producto.pk, "cantidad": "1"}
    )
    assert respuesta.context["cantidad_sugerida"] is None
    assert "Solo hay 0 kg disponibles" in respuesta.content.decode()


def test_rf03_solo_cambia_sucursal_destino(cliente_de, bodeguero, bodega, santa_cruz, pena_blanca, producto, con_existencia):
    """CP-RF03-05."""
    con_existencia(producto, bodega, 20)
    con_existencia(producto, santa_cruz, 3)
    cliente_de(bodeguero).post(URL_SALIDA, {"sucursal": pena_blanca.pk, "producto": producto.pk, "cantidad": "5"})
    assert Existencia.objects.get(producto=producto, ubicacion=santa_cruz).cantidad == Decimal("3")
    assert Existencia.objects.get(producto=producto, ubicacion=pena_blanca).cantidad == Decimal("5")


def test_rf03_encargado_no_registra_salida(cliente_de, encargado_sc):
    assert cliente_de(encargado_sc).get(URL_SALIDA).status_code == 403


# --- Panel de existencia en bodega (Fig. 15/16) ----------------------------------------------------

def test_rf02_api_existencia_bodega(cliente_de, bodeguero, bodega, producto, con_existencia):
    con_existencia(producto, bodega, "8.5")
    datos = cliente_de(bodeguero).get(URL_API, {"producto": producto.pk}).json()
    assert datos == {"cantidad": "8.5", "unidad": "kg", "stock_minimo": "10", "nivel": "bajo", "nivel_texto": "Bajo"}


def test_rf02_api_existencia_sin_registro_es_agotado(cliente_de, bodeguero, bodega, producto):
    datos = cliente_de(bodeguero).get(URL_API, {"producto": producto.pk}).json()
    assert datos["cantidad"] == "0" and datos["nivel"] == "agotado"


def test_rf01_api_existencia_restringida(cliente_de, encargado_sc, bodeguero, producto):
    assert cliente_de(encargado_sc).get(URL_API, {"producto": producto.pk}).status_code == 403
    assert cliente_de(bodeguero).get(URL_API, {"producto": "x"}).status_code == 404


# --- RF-05 ---------------------------------------------------------------------------------------

def test_rf05_encargado_ve_solo_su_sucursal(
    cliente_de, encargado_sc, bodega, santa_cruz, pena_blanca, producto, otro_producto, con_existencia
):
    """CP-RF05-01: lista de Santa Cruz con pill de estado (color y texto)."""
    con_existencia(producto, santa_cruz, 8)
    con_existencia(otro_producto, pena_blanca, 40)
    con_existencia(otro_producto, bodega, 99)
    respuesta = cliente_de(encargado_sc).get(URL_EXISTENCIAS)
    html = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert [e.ubicacion_id for e in respuesta.context["existencias"]] == [santa_cruz.pk]
    assert "Existencias — Sucursal Santa Cruz" in html
    assert '<span class="pill pill-bajo">Bajo</span>' in html
    assert "Servilletas" not in html


def test_rf05_encargado_no_ve_otra_ubicacion(cliente_de, encargado_sc, bodega, pena_blanca):
    """CP-RF05-02: manipular el parámetro devuelve 403."""
    cliente = cliente_de(encargado_sc)
    assert cliente.get(URL_EXISTENCIAS, {"ubicacion": pena_blanca.pk}).status_code == 403
    assert cliente.get(URL_EXISTENCIAS, {"ubicacion": bodega.pk}).status_code == 403


def test_rf05_dueno_consulta_cualquier_ubicacion(cliente_de, dueno, bodega, pena_blanca, producto, con_existencia):
    """CP-RF05-03."""
    con_existencia(producto, pena_blanca, 0)
    respuesta = cliente_de(dueno).get(URL_EXISTENCIAS, {"ubicacion": pena_blanca.pk})
    assert respuesta.status_code == 200
    assert respuesta.context["ubicacion"].pk == pena_blanca.pk
    assert '<span class="pill pill-agotado">Agotado</span>' in respuesta.content.decode()


def test_rf05_filtros_nombre_y_categoria(cliente_de, dueno, santa_cruz, producto, otro_producto, con_existencia):
    """CP-RF05-04."""
    con_existencia(producto, santa_cruz, 20)
    con_existencia(otro_producto, santa_cruz, 20)
    cliente = cliente_de(dueno)
    por_nombre = cliente.get(URL_EXISTENCIAS, {"ubicacion": santa_cruz.pk, "q": "pollo"}).context["existencias"]
    por_categoria = cliente.get(
        URL_EXISTENCIAS, {"ubicacion": santa_cruz.pk, "categoria": "Desechables"}
    ).context["existencias"]
    assert [e.producto for e in por_nombre] == [producto]
    assert [e.producto for e in por_categoria] == [otro_producto]


def test_rf05_encargado_sin_sucursal(cliente_de, encargado_sc):
    """CP-RF05-05: error controlado, no excepción."""
    type(encargado_sc).objects.filter(pk=encargado_sc.pk).update(sucursal=None)
    respuesta = cliente_de(encargado_sc).get(URL_EXISTENCIAS)
    assert respuesta.status_code == 200
    assert "no tiene una sucursal asignada" in respuesta.content.decode()


def test_rf05_dueno_sin_ubicaciones_mensaje_correcto(cliente_de, dueno):
    """Regresión R-07."""
    html = cliente_de(dueno).get(URL_EXISTENCIAS).content.decode()
    assert "Todavía no hay ubicaciones registradas." in html
    assert "no tiene una sucursal asignada" not in html


def test_rf05_bodeguero_sin_permiso_de_existencias(cliente_de, bodeguero):
    assert cliente_de(bodeguero).get(URL_EXISTENCIAS).status_code == 403


def test_rf05_producto_inactivo_no_se_lista(cliente_de, encargado_sc, santa_cruz, producto, con_existencia):
    con_existencia(producto, santa_cruz, 5)
    producto.activo = False
    producto.save()
    assert not cliente_de(encargado_sc).get(URL_EXISTENCIAS).context["existencias"]


def test_rnf01_consulta_existencias_consultas_acotadas(
    cliente_de, encargado_sc, santa_cruz, django_assert_max_num_queries, con_existencia
):
    """CP-RF05-06 (parcial): el número de consultas no crece con las filas (sin N+1)."""
    from usuarios.models import Producto

    for i in range(30):
        p = Producto.objects.create(nombre=f"Producto {i}", categoria="X", unidad_medida="u.", stock_minimo=5)
        con_existencia(p, santa_cruz, i)
    cliente = cliente_de(encargado_sc)
    with django_assert_max_num_queries(12):
        assert cliente.get(URL_EXISTENCIAS).status_code == 200


# --- RF-12 ---------------------------------------------------------------------------------------

def test_rf12_historial_cronologico_con_filtros(
    cliente_de, bodeguero, dueno, bodega, santa_cruz, producto, otro_producto, proveedor
):
    from inventario import servicios

    servicios.registrar_entrada(producto.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    servicios.registrar_entrada(otro_producto.pk, Decimal("4"), proveedor.pk, bodeguero.pk)
    servicios.registrar_salida(producto.pk, Decimal("3"), santa_cruz.pk, bodeguero.pk)

    respuesta = cliente_de(dueno).get(URL_HISTORIAL)
    movimientos = list(respuesta.context["movimientos"])
    assert [m.tipo for m in movimientos] == ["salida", "entrada", "entrada"]  # más reciente primero
    assert "Avícola El Progreso" in respuesta.content.decode()

    por_producto = cliente_de(dueno).get(URL_HISTORIAL, {"producto": otro_producto.pk}).context["movimientos"]
    assert [m.producto_id for m in por_producto] == [otro_producto.pk]
    por_ubicacion = cliente_de(dueno).get(URL_HISTORIAL, {"ubicacion": santa_cruz.pk}).context["movimientos"]
    assert [m.tipo for m in por_ubicacion] == ["salida"]


def test_rf12_encargado_sin_historial(cliente_de, encargado_sc):
    assert cliente_de(encargado_sc).get(URL_HISTORIAL).status_code == 403
