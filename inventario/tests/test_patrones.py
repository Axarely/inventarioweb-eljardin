"""
Pruebas de los patrones de diseño del DEDS 3.4 en el Módulo de Inventario: Factory Method y Observer.
"""
import ast
import pathlib
from decimal import Decimal

import pytest

from inventario.excepciones import MovimientoInvalido
from inventario.fabrica import MovimientoInventarioFactory
from inventario.models import EntradaInventario, Existencia, SalidaInventario
from inventario.observador import IObservadorExistencia

pytestmark = pytest.mark.unitaria


# --- Factory Method (Fig. 22) -------------------------------------------------------------------

@pytest.mark.django_db
def test_rf02_factory_crea_entrada(producto, bodega, proveedor, bodeguero):
    entrada = MovimientoInventarioFactory.crear("entrada", {
        "producto": producto, "cantidad": Decimal("5"), "proveedor": proveedor, "destino": bodega,
        "usuario_id": bodeguero.pk,
    })
    assert type(entrada) is EntradaInventario
    assert entrada.pk is None  # la fábrica no guarda: quien la usa llama a aplicar()


@pytest.mark.django_db
def test_rf03_factory_crea_salida(producto, bodega, santa_cruz, bodeguero):
    salida = MovimientoInventarioFactory.crear("salida", {
        "producto": producto, "cantidad": Decimal("5"), "origen": bodega, "destino": santa_cruz,
        "usuario": bodeguero,
    })
    assert type(salida) is SalidaInventario


def test_rf02_factory_rechaza_tipo_desconocido():
    with pytest.raises(MovimientoInvalido, match="desconocido"):
        MovimientoInventarioFactory.crear("traslado", {})


def test_rf02_factory_rechaza_datos_que_no_son_campos():
    with pytest.raises(MovimientoInvalido, match="proveedor"):
        MovimientoInventarioFactory.crear("salida", {"proveedor": None})


def test_rf02_factory_extensible():
    class Ajuste(SalidaInventario):
        class Meta:
            proxy = True
            app_label = "inventario"

    MovimientoInventarioFactory.registrar("ajuste", Ajuste)
    try:
        assert type(MovimientoInventarioFactory.crear("ajuste", {})) is Ajuste
    finally:
        MovimientoInventarioFactory._tipos.pop("ajuste")


def _modulos_produccion(app):
    raiz = pathlib.Path(__file__).resolve().parents[2] / app
    return [p for p in raiz.rglob("*.py") if "tests" not in p.parts and "migrations" not in p.parts]


def test_int01_vistas_y_servicios_no_instancian_subclases():
    """INT-01: solo la fábrica (y los modelos) conocen EntradaInventario/SalidaInventario."""
    raiz = pathlib.Path(__file__).resolve().parents[1]
    for nombre in ("views.py", "servicios.py"):
        arbol = ast.parse((raiz / nombre).read_text(encoding="utf-8"))
        llamadas = {
            nodo.func.id for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
        }
        assert not llamadas & {"EntradaInventario", "SalidaInventario"}, nombre


# --- Observer (Fig. 23) -------------------------------------------------------------------------

class ObservadorEspia(IObservadorExistencia):
    def __init__(self):
        self.recibidos = []

    def actualizar(self, existencia):
        self.recibidos.append((existencia.cantidad, existencia.delta, existencia.nivel_anterior))


@pytest.fixture
def espia():
    observador = ObservadorEspia()
    Existencia.agregar_observador(observador)
    yield observador
    Existencia.quitar_observador(observador)


def test_rf06_observadores_registrados_en_ready():
    """Alertas y Reportes se suscriben desde sus AppConfig.ready()."""
    nombres = {type(o).__name__ for o in Existencia._observadores}
    assert {"AlertaInventarioService", "PanelIndicadoresService"} <= nombres


def test_rf06_agregar_observador_exige_la_interfaz():
    with pytest.raises(TypeError):
        Existencia.agregar_observador(object())


def test_rf06_agregar_observador_no_duplica(espia):
    antes = len(Existencia._observadores)
    Existencia.agregar_observador(ObservadorEspia())
    assert len(Existencia._observadores) == antes


@pytest.mark.django_db
def test_rf06_actualizar_cantidad_notifica_con_delta_y_nivel_anterior(espia, producto, bodega, con_existencia):
    existencia = con_existencia(producto, bodega, 12)
    existencia.actualizar_cantidad(Decimal("-4"))
    assert espia.recibidos == [(Decimal("8"), Decimal("-4"), Existencia.Nivel.NORMAL)]


@pytest.mark.django_db
def test_rf06_salida_notifica_origen_y_destino(espia, producto, bodega, santa_cruz, bodeguero, con_existencia):
    con_existencia(producto, bodega, 20)
    SalidaInventario(producto=producto, origen=bodega, destino=santa_cruz, usuario=bodeguero, cantidad=5).aplicar()
    assert [delta for _, delta, _ in espia.recibidos] == [Decimal("-5"), Decimal("5")]


@pytest.mark.django_db
def test_rf06_sin_cambio_valido_no_hay_notificacion(espia, producto, bodega, con_existencia):
    existencia = con_existencia(producto, bodega, 3)
    with pytest.raises(MovimientoInvalido):
        existencia.actualizar_cantidad(Decimal("-5"))
    assert espia.recibidos == []


def test_int08_inventario_no_importa_alertas_ni_reportes():
    """INT-08 / corrección 1 del DEDS v1.1: Inventario no depende de sus observadores."""
    for archivo in _modulos_produccion("inventario"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                modulos = [nodo.module or ""]
            else:
                continue
            for modulo in modulos:
                assert modulo.split(".")[0] not in {"alertas", "reportes"}, f"{archivo.name} importa {modulo}"
