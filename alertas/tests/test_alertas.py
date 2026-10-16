"""
Módulo de Alertas: RF-06 (alerta sin duplicar), RF-16 (correo a los dueños vía Adapter) y UC05.
El correo usa el backend en memoria de Django (`mailoutbox`). Las notificaciones se envían en
transaction.on_commit, por eso las pruebas ejecutan esos callbacks con django_capture_on_commit_callbacks.
"""
from decimal import Decimal

import pytest
from django.db import transaction
from django.urls import reverse

from alertas.models import AlertaInventario
from alertas.notificadores import AdaptadorCorreoSMTP, AdaptadorSMS, INotificador
from alertas.servicios import AlertaInventarioService
from conftest import PASSWORD
from inventario import servicios
from usuarios.models import Rol
from usuarios.roles import rol_base

pytestmark = pytest.mark.django_db


@pytest.fixture
def stock(producto, bodega, santa_cruz, proveedor, bodeguero):
    """Bodega con 15 de un producto con stock mínimo 10; Santa Cruz con 12."""
    servicios.registrar_entrada(producto.pk, Decimal("27"), proveedor.pk, bodeguero.pk)
    servicios.registrar_salida(producto.pk, Decimal("12"), santa_cruz.pk, bodeguero.pk)
    return producto


def pendientes():
    return AlertaInventario.objects.filter(estado="pendiente")


# --- RF-06: generación sin duplicados ------------------------------------------------------------

def test_rf06_alerta_al_quedar_bajo_umbral(stock, santa_cruz, encargado_sc):
    """CP-RF06-01: en la misma transacción del movimiento."""
    with transaction.atomic():
        servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
        alerta = pendientes().get()
    assert alerta.existencia.ubicacion_id == santa_cruz.pk
    assert alerta.nivel_detectado == Decimal("8") and alerta.nivel_texto == "Bajo"


def test_rf06_alerta_agotado_en_bodega(stock, bodega, pena_blanca, bodeguero):
    """CP-RF06-02."""
    servicios.registrar_salida(stock.pk, Decimal("15"), pena_blanca.pk, bodeguero.pk)
    alerta = pendientes().get(existencia__ubicacion=bodega)
    assert alerta.es_agotado and alerta.nivel_texto == "Agotado"


def test_rf06_no_duplica_alerta_pendiente(stock, santa_cruz, encargado_sc):
    """CP-RF06-03: se actualizan fecha y nivel de la alerta pendiente existente."""
    servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    primera = pendientes().get()
    servicios.registrar_consumo(stock.pk, Decimal("3"), santa_cruz.pk, encargado_sc.pk)
    assert pendientes().count() == 1
    actualizada = pendientes().get()
    assert actualizada.pk == primera.pk
    # DEF-06: >= porque en Windows dos llamadas seguidas a now() pueden devolver el mismo instante.
    assert actualizada.nivel_detectado == Decimal("5") and actualizada.generada_en >= primera.generada_en


def test_rf06_sin_alerta_si_queda_en_minimo(stock, santa_cruz, encargado_sc):
    """CP-RF06-04: límite exacto, 12 - 2 = 10 = stock mínimo."""
    servicios.registrar_consumo(stock.pk, Decimal("2"), santa_cruz.pk, encargado_sc.pk)
    assert not AlertaInventario.objects.exists()


def test_rf06_nueva_alerta_tras_atendida(stock, santa_cruz, encargado_sc, dueno):
    """CP-RF06-05."""
    servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    pendientes().get().marcar_atendida(dueno)
    servicios.registrar_consumo(stock.pk, Decimal("1"), santa_cruz.pk, encargado_sc.pk)
    assert AlertaInventario.objects.count() == 2 and pendientes().count() == 1


def test_rf06_alerta_se_revierte_con_el_movimiento(stock, santa_cruz, encargado_sc):
    """RNF-08: si la transacción del movimiento falla, tampoco queda la alerta."""
    with pytest.raises(RuntimeError), transaction.atomic():
        servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
        raise RuntimeError("falla posterior")
    assert not AlertaInventario.objects.exists()


def test_rf06_unicidad_de_pendiente_en_bd(stock, santa_cruz, encargado_sc):
    from django.db import IntegrityError

    servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    existente = pendientes().get()
    with pytest.raises(IntegrityError), transaction.atomic():
        AlertaInventario.objects.create(existencia=existente.existencia, nivel_detectado=1)


# --- UC05: pantalla y marcar atendida ------------------------------------------------------------

def test_rf06_alerta_visible_y_atendible_por_dueno(cliente_de, stock, santa_cruz, encargado_sc, dueno):
    """CP-RF06-06."""
    servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    alerta = pendientes().get()
    cliente = cliente_de(dueno)
    html = cliente.get(reverse("alertas:lista")).content.decode()
    assert "Pechuga de pollo" in html and '<span class="pill pill-bajo">Bajo</span>' in html
    cliente.post(reverse("alertas:atendida", args=[alerta.pk]))
    alerta.refresh_from_db()
    assert alerta.estado == "atendida" and alerta.atendida_por == dueno and alerta.atendida_en
    # DEF-07: se revisa la lista, no el HTML (el mensaje de confirmación también nombra el producto).
    assert list(cliente.get(reverse("alertas:lista")).context["alertas"]) == []
    assert "Atendida por Dueña" in cliente.get(reverse("alertas:lista"), {"estado": "atendida"}).content.decode()
    respuesta = cliente.post(reverse("alertas:atendida", args=[alerta.pk]), follow=True)
    assert "ya estaba atendida" in respuesta.content.decode()


@pytest.mark.parametrize("rol", ["bodeguero", "encargado_sc"])
def test_rf06_otros_roles_no_acceden_a_alertas(request, cliente_de, rol, stock, santa_cruz, encargado_sc):
    servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    cliente = cliente_de(request.getfixturevalue(rol))
    assert cliente.get(reverse("alertas:lista")).status_code == 403
    assert cliente.post(reverse("alertas:atendida", args=[pendientes().get().pk])).status_code == 403


def test_rf06_servicio_marcar_atendida(stock, santa_cruz, encargado_sc, dueno):
    servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    alerta = pendientes().get()
    assert AlertaInventarioService().marcar_atendida(alerta.pk, dueno.pk) is True
    assert AlertaInventarioService().marcar_atendida(alerta.pk, dueno.pk) is False


# --- RF-16: notificación por correo (Adapter) ----------------------------------------------------

@pytest.fixture
def dos_duenos(dueno, django_user_model):
    otra = django_user_model.objects.create_user(
        correo="socio@eljardin.test", password=PASSWORD, nombre="Socio", rol=rol_base(Rol.Codigo.DUENO)
    )
    django_user_model.objects.create_user(
        correo="exsocio@eljardin.test", password=PASSWORD, nombre="Ex socio", rol=rol_base(Rol.Codigo.DUENO),
        activo=False,
    )
    return [dueno, otra]


def test_rf16_correo_a_duenos_al_agotarse(
    stock, santa_cruz, encargado_sc, dos_duenos, mailoutbox, django_capture_on_commit_callbacks
):
    """CP-RF16-01: un correo a cada dueño ACTIVO, con producto y ubicación."""
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_consumo(stock.pk, Decimal("12"), santa_cruz.pk, encargado_sc.pk)
    assert sorted(m.to[0] for m in mailoutbox) == ["duena@eljardin.test", "socio@eljardin.test"]
    correo = mailoutbox[0]
    assert correo.subject == "[InventarioWeb El Jardín] Producto agotado: Pechuga de pollo en Santa Cruz"
    assert "quedó AGOTADO en Santa Cruz (0 kg)" in correo.body
    assert "Stock mínimo configurado: 10 kg." in correo.body


def test_rf16_sin_correo_si_solo_bajo(stock, santa_cruz, encargado_sc, dueno, mailoutbox, django_capture_on_commit_callbacks):
    """CP-RF16-02."""
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
    assert pendientes().count() == 1 and mailoutbox == []


def test_rf16_correo_al_pasar_de_bajo_a_agotado(
    stock, santa_cruz, encargado_sc, dueno, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_consumo(stock.pk, Decimal("4"), santa_cruz.pk, encargado_sc.pk)
        servicios.registrar_consumo(stock.pk, Decimal("8"), santa_cruz.pk, encargado_sc.pk)
    assert len(mailoutbox) == 1 and pendientes().count() == 1


def test_rf16_no_reenvia_si_alerta_pendiente(
    stock, santa_cruz, encargado_sc, dueno, mailoutbox, django_capture_on_commit_callbacks
):
    """CP-RF16-03: la existencia SIGUE en 0 y la alerta pendiente ya era de agotado: no hay segundo correo."""
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_consumo(stock.pk, Decimal("12"), santa_cruz.pk, encargado_sc.pk)
    existencia = pendientes().get().existencia
    with django_capture_on_commit_callbacks(execute=True):
        existencia.notificar_observadores()  # nueva notificación con la existencia aún en 0
    assert len(mailoutbox) == 1 and pendientes().count() == 1


def test_rf16_reenvia_si_vuelve_a_agotarse(
    stock, santa_cruz, bodeguero, encargado_sc, dueno, mailoutbox, django_capture_on_commit_callbacks
):
    """Si se repone parcialmente (Bajo) y vuelve a 0, es un nuevo paso a Agotado (Fig. 8): se notifica."""
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_consumo(stock.pk, Decimal("12"), santa_cruz.pk, encargado_sc.pk)
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_salida(stock.pk, Decimal("2"), santa_cruz.pk, bodeguero.pk)  # sube a 2: Bajo
        servicios.registrar_consumo(stock.pk, Decimal("2"), santa_cruz.pk, encargado_sc.pk)  # vuelve a 0
    assert len(mailoutbox) == 2 and pendientes().count() == 1


def test_rf16_no_envia_si_la_transaccion_se_revierte(
    stock, santa_cruz, encargado_sc, dueno, mailoutbox, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(RuntimeError), transaction.atomic():
            servicios.registrar_consumo(stock.pk, Decimal("12"), santa_cruz.pk, encargado_sc.pk)
            raise RuntimeError("falla posterior")
    assert mailoutbox == []


class NotificadorQueFalla(INotificador):
    def enviar(self, destinatario, mensaje):
        raise ConnectionError("SMTP caído")


def test_rf16_fallo_smtp_no_revierte_movimiento(
    settings, stock, santa_cruz, encargado_sc, dueno, django_capture_on_commit_callbacks, caplog
):
    """CP-RF16-04: el movimiento y la alerta se guardan; el error queda en el log."""
    settings.NOTIFICADOR = "alertas.tests.test_alertas.NotificadorQueFalla"
    with django_capture_on_commit_callbacks(execute=True):
        consumo = servicios.registrar_consumo(stock.pk, Decimal("12"), santa_cruz.pk, encargado_sc.pk)
    assert consumo.pk and pendientes().get().es_agotado
    assert "No se pudo notificar la alerta" in caplog.text


class NotificadorEspia(INotificador):
    def __init__(self):
        self.enviados = []

    def enviar(self, destinatario, mensaje):
        self.enviados.append(destinatario)
        return True


def test_rf16_notificador_intercambiable(stock, santa_cruz, encargado_sc, dueno):
    """CP-RF16-05: el servicio depende solo de INotificador (Adapter, Fig. 24)."""
    servicios.registrar_consumo(stock.pk, Decimal("12"), santa_cruz.pk, encargado_sc.pk)
    alerta = pendientes().get()
    espia = NotificadorEspia()
    assert alerta.notificar(espia) == 1 and espia.enviados == ["duena@eljardin.test"]
    assert alerta.notificar(AdaptadorSMS()) == 0  # el stub no envía nada


def test_rf16_adaptador_correo_smtp(mailoutbox):
    assert AdaptadorCorreoSMTP().enviar("a@eljardin.test", "Asunto\n\nCuerpo") is True
    assert mailoutbox[0].subject == "[InventarioWeb El Jardín] Asunto"
    assert mailoutbox[0].body == "Asunto\n\nCuerpo"


def test_rf16_interfaz_no_instanciable():
    with pytest.raises(TypeError):
        INotificador()
