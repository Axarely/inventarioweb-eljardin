# Mapeo de componentes del DEDS a código y evidencia de patrones

**Proyecto:** InventarioWeb El Jardín · **Fase:** 3 (Sprint 2) · **Corresponde a:** IIPD 2.2 y 2.3
Los números de línea corresponden al commit de cierre del Sprint 2 y se obtuvieron con `grep -n`
sobre el código. Si el código cambia, se vuelven a generar.

## 1. Componentes del DEDS (§3.2, Fig. 11) → módulos de código

| Componente del DEDS | Interfaz (DEDS §3.2) | App Django | Archivos principales | RF/RNF |
|---|---|---|---|---|
| Módulo de Autenticación | IAuth | `autenticacion/` | `views.py` (login, logout, inicio), `forms.py` (bloqueo por intentos), `servicios.py`, `backends.py` (RBAC `RolBackend`, l. 5), `mixins.py` (`PermisoRequeridoMixin`), `menu.py` (menú por rol, `OPCIONES_MENU` l. 15) | RF-01, RF-18, RNF-02 |
| Módulo de Usuarios y Roles | IUsuarios | `usuarios/` | `models.py` (`Usuario`, `Rol`, `Producto`), `roles.py` (`PERMISOS_POR_ROL` l. 10), `views.py`, `forms.py` | RF-09, RF-10 |
| Módulo de Proveedores | IProveedores | `proveedores/` | `models.py` (`Proveedor`), `servicios.py` (`crear_proveedor`, `desactivar_proveedor`, `obtener_proveedor_activo` l. 28), `views.py` (Fig. 19) | RF-11 |
| Módulo de Inventario «sujeto Observer» | IInventario | `inventario/` | `models.py` (`Ubicacion`, `Bodega`, `Sucursal`, `Existencia`, `MovimientoInventario`, `EntradaInventario`, `SalidaInventario`, `DiscrepanciaInventario`), `fabrica.py`, `observador.py`, `servicios.py` (`registrar_entrada`, `registrar_salida`, `consultar_existencias`, consumo, anulación, discrepancias), `views.py` | RF-02 a RF-05, RF-12, RF-13, RF-15 |
| Módulo de Alertas «observador» | IAlertas | `alertas/` | `models.py` (`AlertaInventario`), `servicios.py` (`AlertaInventarioService`: `generar_alerta` l. 43, `marcar_atendida`, `notificar`), `notificadores.py` (Adapter), `views.py` (Fig. 18) | RF-06, RF-16 |
| Módulo de Reportes «observador» | IReportes | `reportes/` | `servicios.py` (`PanelIndicadoresService`, `generar_indicadores` l. 118, `consumos` l. 83, reportes), `exportadores.py` (`a_excel` l. 19, `a_pdf` l. 45), `views.py` (Fig. 14) | RF-07, RF-08, RF-14, RF-17 |
| Panel de Indicadores (Dueños) | consume IInventario, IAlertas, IReportes | `reportes/` | `templates/reportes/dashboard.html`, `static/js/dashboard.js` (Chart.js 4.4.1) | RF-08, RF-17 |
| Gestión de Catálogo, Usuarios y Proveedores (UI) | consume IUsuarios, IProveedores | `usuarios/`, `proveedores/` | plantillas `usuario_lista.html`, `rol_lista.html`, `producto_lista.html`, `proveedor_lista.html` | RF-09, RF-10, RF-11 |
| Notificador Externo (correo / SMS) | INotificador | `alertas/` | `notificadores.py`: `AdaptadorCorreoSMTP` (funcional), `AdaptadorSMS` (stub, D-08) | RF-16 |
| UI Web (plantillas + JS) | — | `templates/`, `static/` | `base.html` (menú lateral), `css/estilos.css` (Fig. 21), `js/movimientos.js`, `js/dashboard.js` | RNF-03, RNF-07 |

**Dependencias verificadas (corrección 1 del DEDS v1.1):** `inventario` no importa `alertas` ni `reportes`.
Lo comprueba automáticamente `inventario/tests/test_patrones.py:136` (`test_int08_...`), que recorre el AST
de cada módulo de producción de `inventario/`. Las flechas «notifica» de la Fig. 11 se implementan como
observadores que se registran solos desde las apps observadoras (`alertas/apps.py:15`, `reportes/apps.py:15`).

## 2. Clases de diseño (Fig. 12) → modelos

| Clase (Fig. 12) | Modelo | Métodos del DEDS implementados |
|---|---|---|
| Usuario | `usuarios.models.Usuario` | `check_password()`, `tiene_permiso(p)` |
| Rol | `usuarios.models.Rol` | `agregar_permiso(p)` |
| Producto | `usuarios.models.Producto` | restricción `stock_minimo >= 0` |
| Ubicacion (abstracta) / Bodega / Sucursal | `inventario.models` (herencia multi-tabla) | `existencia_total()` |
| Existencia «sujeto» | `inventario.models.Existencia` | `nivel()`, `esta_bajo_umbral()`, `agregar_observador(o)`, `notificar_observadores()`, `actualizar_cantidad(delta)` |
| MovimientoInventario (abstracta) | `inventario.models.MovimientoInventario` (l. 185) | `aplicar()`, `anular(motivo)` (l. 255) |
| EntradaInventario / SalidaInventario | `inventario.models` (l. 296 / l. 321) | `aplicar()` (l. 307 / l. 333) |
| Proveedor | `proveedores.models.Proveedor` | `actualizar_contacto()`, `desactivar()` |
| AlertaInventario «observador» | `alertas.models.AlertaInventario` | `notificar()`, `marcar_atendida()` |
| DiscrepanciaInventario (D-03) | `inventario.models.DiscrepanciaInventario` (l. 357) | — |

## 3. Evidencia de los patrones de diseño (DEDS §3.4)

### 3.1 Factory Method (creacional, Fig. 22)

| Elemento del patrón | Archivo:línea |
|---|---|
| Creador `MovimientoInventarioFactory` | `inventario/fabrica.py:10` |
| Método fábrica `crear(tipo, datos)` | `inventario/fabrica.py:17` |
| Registro de tipos concretos (extensible con `registrar`) | `inventario/fabrica.py:11` |
| Producto abstracto `MovimientoInventario.aplicar()` | `inventario/models.py:185`, `:252` |
| Productos concretos `EntradaInventario` / `SalidaInventario` | `inventario/models.py:296`, `:321` |
| Clientes que usan la fábrica | `inventario/servicios.py:24` (entrada), `:35` (salida), `:47` (consumo), `:85` (corrección) |

**Extensión real del patrón (D-33):** el tipo **Merma** (`MermaInventario`) se agregó al registro de la
fábrica (`inventario/fabrica.py`) sin modificar a ningún cliente; `registrar_peso_real` lo crea con
`MovimientoInventarioFactory.crear("merma", ...)` (`inventario/servicios.py`).

**Pruebas:**
- `inventario/tests/test_patrones.py`: crea cada tipo, rechaza un tipo desconocido, se puede extender.
- `inventario/tests/test_merma.py::test_d33_factory_crea_merma`.
- `test_int01_vistas_y_servicios_no_instancian_subclases` (l. 67): comprueba con el AST que vistas y servicios nunca llaman a `EntradaInventario(...)` ni a `SalidaInventario(...)`.

### 3.2 Observer (conductual, Fig. 23)

| Elemento del patrón | Archivo:línea |
|---|---|
| Interfaz `IObservadorExistencia.actualizar(existencia)` | `inventario/observador.py:9` |
| Sujeto: lista de observadores | `inventario/models.py:134` |
| `agregar_observador(o)` | `inventario/models.py:137` |
| `notificar_observadores()` | `inventario/models.py:148` |
| `actualizar_cantidad(delta)`, que notifica | `inventario/models.py:152` (la notificación está en `:164`) |
| Observador `AlertaInventarioService.actualizar` | `alertas/servicios.py:27`, `:37` |
| Observador `PanelIndicadoresService.actualizar` | `reportes/servicios.py:28`, `:31` |
| Registro en `AppConfig.ready()` | `alertas/apps.py:15`, `reportes/apps.py:15` |

**Pruebas:**
- `test_patrones.py`:
  - Ambos observadores quedan registrados.
  - La notificación lleva el delta y el nivel anterior.
  - Una salida notifica tanto el origen como el destino.
- `tests/test_integracion.py:56`: INT-02 e INT-03.
- `tests/test_integracion.py:118`: INT-06. Si un observador falla, el movimiento se revierte.

### 3.3 Adapter (estructural, Fig. 24)

| Elemento del patrón | Archivo:línea |
|---|---|
| Interfaz objetivo `INotificador.enviar(destinatario, mensaje)` | `alertas/notificadores.py:15`, `:17` |
| Adaptador `AdaptadorCorreoSMTP` (funcional, adapta `django.core.mail.send_mail`) | `alertas/notificadores.py:21`, `:27` |
| Adaptador `AdaptadorSMS` (stub, D-08) | `alertas/notificadores.py:39`, `:42` |
| Cliente `AlertaInventarioService` (solo conoce `INotificador`) | `alertas/servicios.py:81` |
| Selección del adaptador por configuración | `config/settings/base.py:123` (`NOTIFICADOR`), `alertas/servicios.py:23` |

**Pruebas:** `alertas/tests/test_alertas.py`:
- `test_rf16_notificador_intercambiable`: el servicio funciona con un espía y con el stub de SMS.
- `test_rf16_fallo_smtp_no_revierte_movimiento`: se cambia el adaptador desde `settings`.
- `test_rf16_adaptador_correo_smtp`: usa el backend de correo en memoria de Django.

## 4. Pruebas de integración (plan de pruebas §2.3)

| ID | Prueba | Archivo:línea |
|---|---|---|
| Flujo completo | Entrada → existencia → salida que agota → alerta → correo → panel → atender | `tests/test_integracion.py:30` |
| INT-01 | Vistas y servicios solo crean movimientos por la Factory | `inventario/tests/test_patrones.py:67` |
| INT-02 / INT-03 | Una salida notifica a Alertas y a Reportes | `tests/test_integracion.py:56` |
| Anulación | Revierte existencias, saca el consumo de los reportes y refresca los indicadores | `tests/test_integracion.py:73` |
| INT-04 | Alertas → INotificador → correo (`mailoutbox`) | `tests/test_integracion.py:30` y `alertas/tests/test_alertas.py` |
| INT-05 | Proveedor desactivado en su módulo → rechazado en Inventario | `tests/test_integracion.py:100` |
| INT-06 | Un observador que falla revierte el movimiento completo | `tests/test_integracion.py:118` |
| INT-07 | Dos salidas concurrentes no sobregiran; salida y anulación concurrentes sin deadlock | `tests/test_integracion.py:133`, `:161` |
| INT-08 | `inventario` no importa `alertas` ni `reportes` | `inventario/tests/test_patrones.py:136` |
