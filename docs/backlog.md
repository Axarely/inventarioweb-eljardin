# Backlog de sprints — InventarioWeb El Jardín

**Curso:** MDS2 · **Fase:** 1 · **Modelo de proceso:** incremental con Scrum adaptado (DEDS 1.4, consigna 1.3)

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-10-11 | Backlog inicial de los Sprints 1 y 2 con estimaciones. |

## Cómo se estimó
- **Método:** descomposición de cada RF en tareas técnicas (modelo → servicio → vista/plantilla → pruebas)
  y estimación por juicio experto en **horas ideales**, de una sola desarrolladora.
- Cada tarea incluye sus pruebas unitarias básicas. Las pruebas de integración y la revisión de código
  son tareas aparte.
- Las horas **reales** se anotan en [registro_tiempo.md](registro_tiempo.md) con el mismo ID de tarea,
  para comparar estimado contra real en la Fase 4 (IIPD 5.1).

## Definición de terminado (aplica a toda tarea)
1. El código referencia su RF/RNF (`# RF-XX`) y respeta los nombres del DEDS.
2. Sus pruebas `test_rfXX_...` pasan y la suite completa sigue en verde (`pytest`).
3. Si hay vista: menú y permisos filtrados por rol (mínimo privilegio).
4. Commit pequeño con el formato `feat(RF-XX): ...`. Si la tarea obliga a desviarse del DEDS, se registra
   en [desviaciones.md](desviaciones.md).

---

## Sprint 1 — Núcleo funcional (Fase 2 de la consigna)
**Objetivo:** autenticación con roles, capa de datos y CRUD de las entidades centrales, con entradas y
salidas básicas funcionando de forma transaccional.

| ID | Tarea | RF / RNF | Est. (h) | Criterio de terminado |
|---|---|---|---|---|
| S1-01 | Modelo `Rol(nombre, permisos)`, migración de datos con los 3 roles (Dueño, Bodeguero, Encargado de sucursal) y sus permisos | RF-01, RF-10 | 3 | Los 3 roles existen tras `migrate`; prueba unitaria de permisos |
| S1-02 | `Usuario.rol` (FK) y `Usuario.sucursal` opcional (D-01) | RF-10, RF-05 | 1.5 | Migración aplicada; un encargado sin sucursal no es válido |
| S1-03 | RBAC: mixin/decorador `rol_requerido` y menú lateral filtrado por rol (context processor) según CLAUDE.md y Fig. 25 | RF-01, RNF-02 | 4 | CP-RF01-01, 02 y 05 (matriz RBAC) en verde |
| S1-04 | Bloqueo temporal tras 5 intentos fallidos (15 min) | RNF-02 | 3 | CP-RF01-07 en verde |
| S1-05 | Prueba de expiración de sesión por inactividad y logout por POST (ya configurados en la Fase 1) | RNF-02, RF-18 | 1 | CP-RF01-08 y `test_rf18_*` en verde |
| S1-06 | CRUD de usuarios para el Dueño: crear, editar, desactivar, asignar rol y sucursal, restablecer contraseña | RF-10 | 5 | Un usuario creado inicia sesión y ve solo su menú |
| S1-07 | Modelo `Producto(nombre, categoria, unidad_medida, stock_minimo, activo)` y CRUD de catálogo (crear, editar, desactivar) | RF-09 | 4 | Un producto nuevo aparece en los formularios; uno inactivo no; `stock_minimo >= 0` |
| S1-08 | Modelo `Proveedor(nombre, contacto, activo)`, CRUD (Fig. 19) y servicio `IProveedores` (`crear_proveedor`, `desactivar_proveedor`) | RF-11 | 3.5 | CRUD funcionando; un proveedor inactivo no se ofrece en las entradas |
| S1-09 | `Ubicacion(nombre, direccion, tipo)` con herencia multi-tabla `Bodega(capacidad_max)` / `Sucursal(horario)`, y migración semilla: Bodega central, Santa Cruz, Peña Blanca | RF-04, RNF-05 | 3 | Las 3 ubicaciones existen; se puede agregar una 4.ª solo con datos |
| S1-10 | `Existencia(producto, ubicacion, cantidad, actualizado_en)` única por (producto, ubicación), con índices, `nivel()` y `esta_bajo_umbral()` | RF-04, RNF-01 | 3 | CP-RF04-02, 03 y 04 en verde |
| S1-11 | `MovimientoInventario` (tipo, producto, origen, destino, cantidad, usuario, fecha, anulado, motivo_anulacion) con subclases `EntradaInventario(proveedor)` y `SalidaInventario`; `aplicar()` dentro de `transaction.atomic` con `select_for_update` | RF-02, RF-03, RNF-08 | 5 | CP-RF02-01, 02 y 06, y CP-RF03-01…04 y 07 en verde |
| S1-12 | Vista y formulario "Registrar entrada" (Fig. 15), con la existencia actual de la bodega como contexto | RF-02, RF-11, RNF-03 | 3 | CP-RF02-03, 04, 05 y 07 en verde; ≤ 3 pasos |
| S1-13 | Vista "Registrar salida" (Fig. 16): validación de existencia suficiente y sugerencia de la cantidad máxima | RF-03, RNF-03 | 3.5 | CP-RF03-03 y 05 en verde; mensaje E1 como en la Fig. 16 |
| S1-14 | "Consultar existencias": el encargado solo ve la suya, el dueño cualquiera; filtros por nombre y categoría; pills de estado (Fig. 17) | RF-05, RF-04 | 3 | CP-RF05-01…05 en verde |
| S1-15 | Historial de movimientos por producto o ubicación (fecha, tipo, cantidad, usuario) | RF-12 | 2.5 | Lista cronológica correcta; el bodeguero y el dueño acceden |
| S1-16 | Completar las pruebas unitarias del sprint y medir la cobertura | RF-01…05 | 6 | Suite en verde; cobertura medida y reportada tal como salga (meta ≥ 80 % en `inventario` y `usuarios`) |
| S1-17 | Revisión de código formal documentada (`docs/revision_codigo_s1.md`): hallazgos y correcciones aplicadas | Consigna Fase 2 | 3 | Acta con hallazgos, severidad y commit de cada corrección |
| | **Total Sprint 1** | | **57** | |

---

## Sprint 2 — Funcionalidad avanzada (Fase 3 de la consigna)
**Objetivo:** patrones de diseño del DEDS 3.4, alertas y notificaciones, reportes y dashboard, y las
operaciones de excepción (consumo, discrepancias, anulación). Incluye las pruebas de integración entre
módulos.

| ID | Tarea | RF / RNF | Est. (h) | Criterio de terminado |
|---|---|---|---|---|
| S2-01 | **Factory Method:** `MovimientoInventarioFactory.crear(tipo, datos)` → `EntradaInventario` o `SalidaInventario`; las vistas pasan a usarla | RF-02, RF-03 | 3 | INT-01 en verde; las vistas no importan las subclases |
| S2-02 | **Observer:** `IObservadorExistencia.actualizar(existencia)` y `Existencia.agregar_observador`, `notificar_observadores` y `actualizar_cantidad(delta)`; registro de los observadores en `AppConfig.ready()` | RF-06, RF-17 | 4 | INT-08 en verde (`inventario` no importa `alertas` ni `reportes`) |
| S2-03 | `AlertaInventario(existencia, generada_en, nivel_detectado, estado)` y `AlertaInventarioService` (observador): sin duplicados, actualiza la fecha si ya hay una pendiente | RF-06 | 4 | CP-RF06-01…05 y 07, e INT-02, en verde |
| S2-04 | Pantalla "Alertas" (Fig. 18) con "Marcar atendida" (`marcar_atendida`), solo para el Dueño | RF-06 | 2.5 | CP-RF06-06 en verde |
| S2-05 | **Adapter:** `INotificador.enviar(destinatario, mensaje)`, `AdaptadorCorreoSMTP` funcional y `AdaptadorSMS` stub; correo a los dueños activos cuando el nivel es "Agotado" | RF-16 | 4 | CP-RF16-01…05 e INT-04 en verde |
| S2-06 | Reportar consumo de sucursal: `SalidaInventario` con origen = sucursal y destino = null (D-02) | RF-04, RF-07 | 3 | La existencia de la sucursal baja; CP-RF04-01 sigue en verde |
| S2-07 | `DiscrepanciaInventario` (D-03) y pantalla "Reportar discrepancia" del encargado | RF-13 | 4 | CP-RF13-01…06 en verde |
| S2-08 | Anulación de movimientos con motivo obligatorio: revierte el efecto y no borra (`anular(motivo)`, D-04) | RF-15 | 4 | CP-RF04-05 en verde; el movimiento queda "anulado" en el historial |
| S2-09 | `PanelIndicadoresService` (observador) e indicadores de consumo con filtros por sucursal, producto y rango de fechas, agregados en la BD | RF-07, RNF-01 | 5 | INT-03 en verde; el consumo total coincide con los movimientos |
| S2-10 | Dashboard de dueños (Fig. 14) con Chart.js: comparativo Santa Cruz vs. Peña Blanca, KPIs y alertas recientes | RF-08, RF-17 | 5 | El panel refleja los movimientos hasta el momento de la consulta |
| S2-11 | Exportación de reportes a Excel y PDF con la misma información de la pantalla (las librerías se eligen en esta tarea y se registran en desviaciones) | RF-14 | 4 | El archivo coincide con la tabla en pantalla |
| S2-12 | Pruebas de integración INT-01…08, incluida la concurrencia (INT-07) | RNF-06, RNF-08 | 8 | Todas en verde; resultados documentados para el IIPD 3.2 |
| S2-13 | Bitácora de defectos (`docs/bitacora_defectos.md`) con severidad, causa y resolución, y corrección de los críticos y altos | Consigna Fase 3 | 3 | Bitácora al día; ningún defecto Crítico abierto |
| | **Total Sprint 2** | | **53.5** | |

---

## Resumen

| Sprint | Tareas | Horas estimadas | Entrega según la consigna |
|---|---|---|---|
| Sprint 1 — Núcleo | 17 | 57 | vie 9 oct 2026 |
| Sprint 2 — Avanzado | 13 | 53.5 | vie 30 oct 2026 |
| **Total** | **30** | **110.5** | |

**Fuera de estos sprints (Fase 4):** despliegue en Render, pruebas de sistema SIS-01…03, verificación de los
RNF y checklist de aceptación con evidencia (ver [plan_de_pruebas.md](plan_de_pruebas.md), secciones 2.4 y 2.5).

## Cobertura de RF en el backlog
| RF | Tareas | RF | Tareas |
|---|---|---|---|
| RF-01 | S1-01, S1-03, S1-04 | RF-10 | S1-01, S1-02, S1-06 |
| RF-02 | S1-11, S1-12, S2-01 | RF-11 | S1-08, S1-12 |
| RF-03 | S1-11, S1-13, S2-01 | RF-12 | S1-15 |
| RF-04 | S1-09, S1-10, S1-14, S2-06 | RF-13 | S2-07 |
| RF-05 | S1-02, S1-14 | RF-14 | S2-11 |
| RF-06 | S2-02, S2-03, S2-04 | RF-15 | S2-08 |
| RF-07 | S2-06, S2-09 | RF-16 | S2-05 |
| RF-08 | S2-10 | RF-17 | S2-02, S2-10 |
| RF-09 | S1-07 | RF-18 | S1-05 (base hecha en la Fase 1) |
