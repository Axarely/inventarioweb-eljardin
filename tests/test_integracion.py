"""
Pruebas de integración entre módulos (plan de pruebas §2.3, INT-01 a INT-08).
Recorren los flujos completos a través de HTTP (vistas -> servicios -> Factory -> modelos -> Observer
-> Alertas/Reportes -> Adapter de correo) contra PostgreSQL real.
"""
import threading
from decimal import Decimal

import pytest
from django.db import connection
from django.urls import reverse

from alertas.models import AlertaInventario
from inventario import servicios
from inventario.excepciones import ExistenciaInsuficiente
from inventario.models import Existencia, MovimientoInventario
from inventario.observador import IObservadorExistencia
from reportes.models import EstadoIndicadores
from reportes.servicios import Filtros, consumos, estado_indicadores

pytestmark = pytest.mark.integracion


def existencia(producto, ubicacion):
    fila = Existencia.objects.filter(producto=producto, ubicacion=ubicacion).first()
    return fila.cantidad if fila else Decimal("0")


@pytest.mark.django_db
def test_int_entrada_salida_existencia_alerta_correo(
    client, bodeguero, dueno, bodega, santa_cruz, producto, proveedor, mailoutbox, django_capture_on_commit_callbacks
):
    """Flujo completo: entrada -> existencia -> salida que agota la bodega -> alerta -> correo -> panel."""
    client.force_login(bodeguero)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("inventario:entrada"), {"producto": producto.pk, "cantidad": "15", "proveedor": proveedor.pk})
    assert existencia(producto, bodega) == Decimal("15")
    assert not AlertaInventario.objects.exists() and mailoutbox == []

    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("inventario:salida"), {"sucursal": santa_cruz.pk, "producto": producto.pk, "cantidad": "15"})
    assert existencia(producto, bodega) == Decimal("0") and existencia(producto, santa_cruz) == Decimal("15")
    alerta = AlertaInventario.objects.get()
    assert alerta.existencia.ubicacion_id == bodega.pk and alerta.es_agotado
    assert [m.to for m in mailoutbox] == [["duena@eljardin.test"]]
    assert "Pechuga de pollo en Bodega central" in mailoutbox[0].subject

    client.force_login(dueno)
    panel = client.get(reverse("reportes:dashboard")).context["panel"]
    assert panel.alertas_activas == 1
    client.post(reverse("alertas:atendida", args=[alerta.pk]))
    assert client.get(reverse("reportes:dashboard")).context["panel"].alertas_activas == 0


@pytest.mark.django_db
def test_int02_int03_salida_notifica_a_ambos_observadores(
    bodeguero, bodega, santa_cruz, producto, con_existencia, django_capture_on_commit_callbacks
):
    """INT-02 (Alertas) e INT-03 (Reportes) reciben la notificación de la misma salida."""
    con_existencia(producto, bodega, 12)
    version = estado_indicadores().version
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_salida(producto.pk, Decimal("4"), santa_cruz.pk, bodeguero.pk)
    # Bodega 8 < 10 y Santa Cruz 4 < 10: una alerta por cada existencia afectada
    assert set(AlertaInventario.objects.values_list("existencia__ubicacion__nombre", flat=True)) == {
        "Bodega central", "Santa Cruz",
    }
    # Un refresco por existencia cambiada (2): DEF-04, aceptado.
    assert EstadoIndicadores.objects.get(pk=1).version == version + 2


@pytest.mark.django_db
def test_int_anulacion_revierte_existencias_e_indicadores(
    client, bodeguero, dueno, encargado_sc, bodega, santa_cruz, producto, proveedor, django_capture_on_commit_callbacks
):
    """Anular revierte existencias, excluye el consumo de los reportes y refresca los indicadores."""
    servicios.registrar_entrada(producto.pk, Decimal("30"), proveedor.pk, bodeguero.pk)
    servicios.registrar_salida(producto.pk, Decimal("20"), santa_cruz.pk, bodeguero.pk)
    consumo = servicios.registrar_consumo(producto.pk, Decimal("6"), santa_cruz.pk, encargado_sc.pk)
    assert consumos(Filtros()).count() == 1

    client.force_login(dueno)
    version = estado_indicadores().version
    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("inventario:anular", args=[consumo.pk]), {"motivo": "Se reportó dos veces"})
    assert existencia(producto, santa_cruz) == Decimal("20")
    assert consumos(Filtros()).count() == 0
    assert estado_indicadores().version > version
    fila = client.get(reverse("reportes:reportes"), {"tipo": "consumo"}).context["reporte"].filas
    assert fila == []
    # RF-04: invariante después de la anulación
    for e in Existencia.objects.all():
        vigentes = MovimientoInventario.objects.filter(producto=e.producto, anulado=False)
        entra = sum((m.cantidad for m in vigentes.filter(destino=e.ubicacion)), Decimal("0"))
        sale = sum((m.cantidad for m in vigentes.filter(origen=e.ubicacion)), Decimal("0"))
        assert e.cantidad == entra - sale


@pytest.mark.django_db
def test_int05_entrada_solo_con_proveedor_activo_via_iproveedores(
    client, bodeguero, dueno, bodega, producto, proveedor
):
    """INT-05: el dueño desactiva un proveedor (Módulo Proveedores) y deja de ofrecerse en Inventario."""
    client.force_login(dueno)
    client.post(reverse("proveedores:activar", args=[proveedor.pk]))
    client.force_login(bodeguero)
    respuesta = client.post(reverse("inventario:entrada"), {"producto": producto.pk, "cantidad": "5", "proveedor": proveedor.pk})
    assert respuesta.context["form"].errors["proveedor"]
    assert not MovimientoInventario.objects.exists()


class ObservadorQueFalla(IObservadorExistencia):
    def actualizar(self, existencia):
        raise RuntimeError("falla de un observador")


@pytest.mark.django_db
def test_int06_falla_de_observador_revierte_el_movimiento(bodeguero, bodega, santa_cruz, producto, con_existencia):
    """INT-06 / RNF-08: los observadores corren dentro de la transacción; si uno falla, nada queda a medias."""
    con_existencia(producto, bodega, 20)
    observador = ObservadorQueFalla()
    Existencia.agregar_observador(observador)
    try:
        with pytest.raises(RuntimeError):
            servicios.registrar_salida(producto.pk, Decimal("5"), santa_cruz.pk, bodeguero.pk)
    finally:
        Existencia.quitar_observador(observador)
    assert existencia(producto, bodega) == Decimal("20") and existencia(producto, santa_cruz) == Decimal("0")
    assert not MovimientoInventario.objects.exists() and not AlertaInventario.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_int07_salidas_concurrentes_no_sobregiran(bodeguero, bodega, santa_cruz, pena_blanca, producto, proveedor):
    """INT-07 / RNF-06: dos salidas simultáneas por el total disponible: solo una se aplica."""
    servicios.registrar_entrada(producto.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    barrera = threading.Barrier(2)
    resultados = []

    def enviar(sucursal):
        try:
            barrera.wait(timeout=10)
            servicios.registrar_salida(producto.pk, Decimal("10"), sucursal.pk, bodeguero.pk)
            resultados.append("aplicada")
        except ExistenciaInsuficiente:
            resultados.append("rechazada")
        finally:
            connection.close()  # cada hilo usa su propia conexión a PostgreSQL

    hilos = [threading.Thread(target=enviar, args=(s,)) for s in (santa_cruz, pena_blanca)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)
    assert sorted(resultados) == ["aplicada", "rechazada"]
    assert existencia(producto, bodega) == Decimal("0")
    assert existencia(producto, santa_cruz) + existencia(producto, pena_blanca) == Decimal("10")
    assert MovimientoInventario.objects.filter(tipo="salida").count() == 1


@pytest.mark.django_db(transaction=True)
def test_int07_salida_y_anulacion_concurrentes_sin_deadlock(
    bodeguero, bodega, santa_cruz, producto, proveedor
):
    """Bloqueo en orden fijo (bloquear_varias): una salida y la anulación de otra no se bloquean mutuamente."""
    servicios.registrar_entrada(producto.pk, Decimal("50"), proveedor.pk, bodeguero.pk)
    previa = servicios.registrar_salida(producto.pk, Decimal("10"), santa_cruz.pk, bodeguero.pk)
    barrera = threading.Barrier(2)
    errores = []

    def tarea(funcion):
        try:
            barrera.wait(timeout=10)
            funcion()
        except Exception as error:  # se registra cualquier error, incluido un deadlock de PostgreSQL
            errores.append(repr(error))
        finally:
            connection.close()

    hilos = [
        threading.Thread(target=tarea, args=(lambda: servicios.registrar_salida(
            producto.pk, Decimal("5"), santa_cruz.pk, bodeguero.pk),)),
        threading.Thread(target=tarea, args=(lambda: servicios.anular_movimiento(
            previa.pk, "Anulación concurrente", bodeguero),)),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)
    assert errores == []
    assert existencia(producto, bodega) == Decimal("45") and existencia(producto, santa_cruz) == Decimal("5")
