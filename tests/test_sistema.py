"""
Pruebas de sistema (plan de pruebas §2.4): recorridos de punta a punta por rol (SIS-01 a SIS-03) y
verificación de RNF-01, RNF-02, RNF-03 y RNF-08 sobre el sistema completo por HTTP.
RNF-04 (disponibilidad) y RNF-07 (navegadores) son manuales: ver docs/pruebas_sistema.md.
"""
import json
import os
import statistics
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest
from django.contrib.auth.hashers import identify_hasher
from django.core.management import call_command
from django.db import DatabaseError
from django.urls import reverse

from alertas.models import AlertaInventario
from inventario.models import Existencia, MovimientoInventario
from usuarios.models import Categoria, Producto

pytestmark = [pytest.mark.sistema, pytest.mark.django_db]

RAIZ = Path(__file__).resolve().parents[1]


def cantidad(producto, ubicacion):
    fila = Existencia.objects.filter(producto=producto, ubicacion=ubicacion).first()
    return fila.cantidad if fila else Decimal("0")


def login(client, correo, password="Clave-segura-123"):
    respuesta = client.post(reverse("autenticacion:login"), {"username": correo, "password": password})
    assert respuesta.status_code == 302, "no pudo iniciar sesión"
    return respuesta


# --- SIS-01 a SIS-03: recorridos por rol --------------------------------------------------------

def test_sis01_bodeguero(client, bodeguero, bodega, santa_cruz, producto, proveedor):
    """Login -> registrar entrada -> registrar salida a Santa Cruz -> historial -> corregir -> cerrar sesión."""
    login(client, bodeguero.correo)
    assert client.get(reverse("inicio")).status_code == 200
    client.post(reverse("inventario:entrada"), {"producto": producto.pk, "cantidad": "40", "proveedor": proveedor.nombre})
    client.post(reverse("inventario:salida"), {"sucursal": santa_cruz.pk, "producto": producto.pk, "cantidad": "15"})
    assert cantidad(producto, bodega) == Decimal("25") and cantidad(producto, santa_cruz) == Decimal("15")
    historial = list(client.get(reverse("inventario:historial")).context["movimientos"])
    assert [m.tipo for m in historial] == ["salida", "entrada"]
    client.post(reverse("inventario:corregir", args=[historial[0].pk]), {"cantidad": "12", "motivo": "Recuento en bodega"})
    assert cantidad(producto, bodega) == Decimal("28") and cantidad(producto, santa_cruz) == Decimal("12")
    client.post(reverse("autenticacion:logout"))
    assert client.get(reverse("inventario:entrada")).status_code == 302  # RF-18


def test_sis02_encargado(client, encargado_sc, bodeguero, bodega, santa_cruz, producto, proveedor):
    """Login -> existencias (solo su sucursal) -> reportar consumo -> reportar discrepancia -> cerrar sesión."""
    from inventario import servicios

    servicios.registrar_entrada(producto.pk, Decimal("30"), proveedor.pk, bodeguero.pk)
    envio = servicios.registrar_salida(producto.pk, Decimal("20"), santa_cruz.pk, bodeguero.pk)
    login(client, encargado_sc.correo)
    existencias = client.get(reverse("inventario:existencias")).context["existencias"]
    assert {e.ubicacion_id for e in existencias} == {santa_cruz.pk}
    assert client.get(reverse("inventario:existencias"), {"ubicacion": bodega.pk}).status_code == 403
    client.post(reverse("inventario:consumo"), {"producto": producto.pk, "cantidad": "12"})
    assert cantidad(producto, santa_cruz) == Decimal("8")
    assert AlertaInventario.objects.filter(existencia__ubicacion=santa_cruz).exists()  # 8 < 10
    client.post(reverse("inventario:discrepancia"), {"movimiento": envio.pk, "cantidad_recibida": "19"})
    assert envio.discrepancia.diferencia == Decimal("-1")
    client.post(reverse("autenticacion:logout"))
    assert client.get(reverse("inventario:existencias")).status_code == 302


def test_sis03_dueno(client, dueno, encargado_sc, bodeguero, bodega, santa_cruz, producto, proveedor,
                     django_capture_on_commit_callbacks, mailoutbox):
    """Login -> dashboard -> alerta y correo -> atender -> catálogo, usuarios, proveedores -> exportar."""
    from inventario import servicios

    servicios.registrar_entrada(producto.pk, Decimal("10"), proveedor.pk, bodeguero.pk)
    with django_capture_on_commit_callbacks(execute=True):
        servicios.registrar_salida(producto.pk, Decimal("10"), santa_cruz.pk, bodeguero.pk)  # bodega en 0
    assert len(mailoutbox) == 1  # RF-16

    login(client, dueno.correo)
    assert client.get(reverse("inicio"))["Location"] == reverse("reportes:dashboard")
    panel = client.get(reverse("reportes:dashboard")).context["panel"]
    assert panel.alertas_activas == 1
    alerta = AlertaInventario.objects.get(estado="pendiente", existencia__ubicacion=bodega)
    client.post(reverse("alertas:atendida", args=[alerta.pk]))
    client.post(reverse("usuarios:producto_crear"), {
        "nombre": "Harina", "categoria": Categoria.objects.get(nombre="Abarrotes").pk, "unidad_medida": "lb",
        "stock_minimo": "5"})
    client.post(reverse("proveedores:crear"), {"nombre": "Molinos del Valle", "contacto": "9500-0000"})
    assert Producto.objects.filter(nombre="Harina").exists()
    for ruta in ("usuarios:usuarios", "usuarios:roles", "proveedores:lista", "inventario:historial"):
        assert client.get(reverse(ruta)).status_code == 200, ruta
    exportado = client.get(reverse("reportes:exportar", args=["pdf"]), {"tipo": "existencias"})
    assert exportado.status_code == 200 and exportado.content.startswith(b"%PDF")


# --- RNF-01: rendimiento con volumen de datos ---------------------------------------------------

PAGINAS_RNF01 = {
    "Existencias (sucursal)": ("inventario:existencias", {}, "encargado"),
    "Existencias (bodega, dueño)": ("inventario:existencias", {"ubicacion": "bodega"}, "dueno"),
    "Dashboard (30 días)": ("reportes:dashboard", {}, "dueno"),
    "Dashboard (60 días, 1 producto)": ("reportes:dashboard", {"desde": "hace60", "producto": "uno"}, "dueno"),
    "Reporte de consumo": ("reportes:reportes", {"tipo": "consumo"}, "dueno"),
    "Historial (página 1)": ("inventario:historial", {}, "dueno"),
    "Exportar Excel (existencias)": ("reportes:exportar", {"tipo": "existencias", "_formato": "excel"}, "dueno"),
}


def test_rnf01_tiempos_con_volumen(client, settings):
    """RNF-01: con 200 productos y 5 000 movimientos, cada consulta responde en menos de 2 s.
    Se toma la mediana de 5 mediciones por página (la primera petición calienta la conexión)."""
    from datetime import timedelta

    from django.utils import timezone

    settings.DEBUG = True
    call_command("seed_demo", verbosity=0)
    call_command("seed_volumen", verbosity=0)
    assert MovimientoInventario.objects.count() >= 5000 and Producto.objects.count() >= 200
    from inventario.models import Bodega
    from usuarios.models import Usuario

    usuarios = {
        "dueno": Usuario.objects.get(correo="duena@eljardin.test"),
        "encargado": Usuario.objects.get(correo="encargado.santacruz@eljardin.test"),
    }
    sustituciones = {
        "bodega": str(Bodega.central().pk),
        "hace60": (timezone.localdate() - timedelta(days=60)).isoformat(),
        "uno": str(Producto.objects.get(nombre="Volumen 001").pk),
    }
    resultados = {}
    for nombre, (ruta, parametros, rol) in PAGINAS_RNF01.items():
        client.force_login(usuarios[rol])
        parametros = {k: sustituciones.get(v, v) for k, v in parametros.items()}
        formato = parametros.pop("_formato", None)
        url = reverse(ruta, args=[formato]) if formato else reverse(ruta)
        client.get(url, parametros)  # calentamiento
        tiempos = []
        for _ in range(5):
            inicio = time.perf_counter()
            respuesta = client.get(url, parametros)
            tiempos.append(time.perf_counter() - inicio)
            assert respuesta.status_code == 200, nombre
        resultados[nombre] = {"mediana_ms": round(statistics.median(tiempos) * 1000), "max_ms": round(max(tiempos) * 1000)}
    salida = os.environ.get("RNF01_RESULTADOS")
    if salida:
        Path(salida).write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nRNF-01 (ms):", json.dumps(resultados, ensure_ascii=False, indent=2))
    lentas = {n: r for n, r in resultados.items() if r["max_ms"] >= 2000}
    assert not lentas, f"Superan 2 s: {lentas}"


# --- RNF-02: seguridad --------------------------------------------------------------------------

def test_rnf02_password_con_hash_fuerte(django_user_model):
    usuario = django_user_model.objects.create_user(correo="h@eljardin.test", password="Clave-segura-123", nombre="H")
    assert identify_hasher(usuario.password).algorithm == "pbkdf2_sha256"
    assert "Clave-segura-123" not in usuario.password


def _ejecutar_con_prod(codigo):
    entorno = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.prod",
               "RENDER_EXTERNAL_HOSTNAME": "inventarioweb-eljardin.onrender.com", "DEBUG": "False"}
    return subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=entorno, capture_output=True, text=True,
                          timeout=120)


def test_rnf02_configuracion_de_produccion_segura():
    """Cookies seguras, HTTPS obligatorio, HSTS y DEBUG apagado en config.settings.prod."""
    codigo = (
        "import django, json; django.setup(); from django.conf import settings as s; print(json.dumps({"
        "'debug': s.DEBUG, 'ssl': s.SECURE_SSL_REDIRECT, 'cookie_sesion': s.SESSION_COOKIE_SECURE, "
        "'cookie_csrf': s.CSRF_COOKIE_SECURE, 'httponly': s.SESSION_COOKIE_HTTPONLY, 'hsts': s.SECURE_HSTS_SECONDS, "
        "'proxy': list(s.SECURE_PROXY_SSL_HEADER), 'hosts': s.ALLOWED_HOSTS}))"
    )
    resultado = _ejecutar_con_prod(codigo)
    assert resultado.returncode == 0, resultado.stderr
    valores = json.loads(resultado.stdout.strip().splitlines()[-1])
    assert valores["debug"] is False and valores["ssl"] is True
    assert valores["cookie_sesion"] and valores["cookie_csrf"] and valores["httponly"]
    assert valores["hsts"] >= 60 * 60 * 24 * 30
    assert valores["proxy"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert "inventarioweb-eljardin.onrender.com" in valores["hosts"]


def test_rnf02_check_deploy_sin_errores():
    resultado = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "ERROR", "--settings=config.settings.prod"],
        cwd=RAIZ, env={**os.environ, "DEBUG": "False", "RENDER_EXTERNAL_HOSTNAME": "x.onrender.com"},
        capture_output=True, text=True, timeout=120,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr


def test_rnf02_secretos_fuera_del_repositorio():
    versionados = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True).stdout.split()
    assert ".env" not in versionados and ".env.example" in versionados


# --- RNF-03: tareas frecuentes en máximo 3 pasos ------------------------------------------------

@pytest.mark.parametrize("rol, opcion, ruta, datos", [
    ("bodeguero", "Entradas", "inventario:entrada", "entrada"),
    ("bodeguero", "Salidas", "inventario:salida", "salida"),
    ("encargado_sc", "Existencias", "inventario:existencias", None),
])
def test_rnf03_tareas_frecuentes_en_tres_pasos(request, client, rol, opcion, ruta, datos, bodega, santa_cruz,
                                                producto, proveedor, con_existencia):
    """Paso 1: elegir la opción en el menú visible al entrar. Paso 2: completar y enviar UN formulario.
    Paso 3: ver la confirmación. Consultar existencias termina en el paso 1."""
    con_existencia(producto, bodega, 50)
    client.force_login(request.getfixturevalue(rol))
    inicio = client.get(reverse("inicio"))
    menu = {item["etiqueta"]: item["url"] for item in inicio.context["menu"]}
    assert menu[opcion] == reverse(ruta)  # paso 1: la opción está en el menú desde el inicio
    pagina = client.get(menu[opcion])
    assert pagina.status_code == 200
    if datos is None:
        assert pagina.context["existencias"] is not None  # la consulta ya se ve
        return
    formulario = {"producto": producto.pk, "cantidad": "5"}
    formulario.update({"proveedor": proveedor.nombre} if datos == "entrada" else {"sucursal": santa_cruz.pk})
    respuesta = client.post(menu[opcion], formulario, follow=True)  # paso 2: un solo formulario
    mensajes = [str(m) for m in respuesta.context["messages"]]
    assert any(m.startswith(("Entrada registrada", "Salida registrada")) for m in mensajes)  # paso 3


# --- RNF-08: atomicidad ante una falla a mitad del proceso ---------------------------------------

def test_rnf08_falla_de_bd_a_mitad_de_una_salida(client, bodeguero, bodega, santa_cruz, producto, con_existencia):
    """UC02/UC03 E2: si la BD falla después de descontar la bodega y antes de sumar a la sucursal, el
    sistema informa el error y no deja cambios parciales."""
    con_existencia(producto, bodega, 20)
    original = Existencia.actualizar_cantidad
    llamadas = []

    def falla_en_la_segunda(self, delta):
        llamadas.append(delta)
        if len(llamadas) == 2:
            raise DatabaseError("conexión perdida")
        return original(self, delta)

    client.force_login(bodeguero)
    with mock.patch.object(Existencia, "actualizar_cantidad", falla_en_la_segunda):
        respuesta = client.post(
            reverse("inventario:salida"), {"sucursal": santa_cruz.pk, "producto": producto.pk, "cantidad": "8"}
        )
    assert respuesta.status_code == 200
    assert "No se aplicó ningún cambio" in respuesta.content.decode()
    assert cantidad(producto, bodega) == Decimal("20") and cantidad(producto, santa_cruz) == Decimal("0")
    assert not MovimientoInventario.objects.exists()


def test_rnf08_falla_de_bd_en_entrada(client, bodeguero, bodega, producto, proveedor):
    client.force_login(bodeguero)
    with mock.patch.object(Existencia, "actualizar_cantidad", side_effect=DatabaseError("conexión perdida")):
        respuesta = client.post(reverse("inventario:entrada"),
                                {"producto": producto.pk, "cantidad": "5", "proveedor": proveedor.nombre})
    assert respuesta.status_code == 200 and "No se aplicó ningún cambio" in respuesta.content.decode()
    assert not MovimientoInventario.objects.exists()
