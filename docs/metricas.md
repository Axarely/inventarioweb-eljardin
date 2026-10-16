# Métricas del proyecto: estimado vs. real

**Proyecto:** InventarioWeb El Jardín · **Fase:** 4 · **Corresponde a:** IIPD 5.1 · **Corte:** 2026-10-15

**Fuentes y regla de honestidad.** Lo **estimado** sale del plan de trabajo del DEDS (Tabla 3, Fase 1 del
curso anterior), del calendario de la consigna de MDS2 y de `docs/backlog.md`. Lo **real** sale de
`docs/registro_tiempo.md` (horas), del historial de `git` (fechas y alcance) y de los resultados de pruebas.
**Las horas reales que la estudiante no registró quedan en blanco: no se estiman ni se rellenan.** Al
corte, `registro_tiempo.md` no tiene ninguna entrada.

> Las fechas de git indican **cuándo se confirmó** el trabajo, no cuánto esfuerzo tomó: varios commits se
> hicieron juntos al final de una sesión. Además, el código se desarrolló con apoyo de una herramienta de
> IA (declarado según la consigna §6.3), lo que hace todavía menos comparables las horas estimadas para
> codificación manual con el tiempo real. Por eso este documento no infiere horas a partir de git.

## 1. Plan original del DEDS (MDS1, 8 semanas) vs. lo ocurrido

Datos tomados del propio DEDS: Tabla 3 (plan) y tablas de control de versiones (real).

| Incremento | Plan (Tabla 3) | Real según el control de versiones del DEDS | Desvío |
|---|---|---|---|
| Fase 1: marco del proyecto | Sem. 1–2, entrega 03/07/2026 | Cap. 1 v1.0 el 03/07/2026; corrección v1.1 el 28/07/2026 | A tiempo; corrección +25 días |
| Fase 2: SRS + UML | Sem. 3–5, entrega 17/07/2026 | Cap. 2 v1.0 el 17/07/2026 | A tiempo |
| Fase 3: diseño | Sem. 6–7, entrega 31/07/2026 | Cap. 3 v1.0 el 31/07/2026; **v1.1 el 13/08/2026** | A tiempo; corrección **después** de la entrega final |
| Fase 4: DEDS integrado | Sem. 8, 07–10/08/2026 | DEDS v1.0 "Final" el 10/08/2026 | A tiempo, pero el Cap. 3 se corrigió 3 días después (inconsistencia I-1 en `ajustes_deds.md`) |

## 2. Calendario de MDS2 (consigna) vs. real (git)

| Fase | Entrega según la consigna | Primer commit | Último commit | Desvío |
|---|---|---|---|---|
| Fase 1: preparación y plan de pruebas | vie 18/09/2026 | 11/10/2026 12:09 | 11/10/2026 12:14 | **+23 días** de atraso |
| Fase 2: Sprint 1 (núcleo) | vie 09/10/2026 | 11/10/2026 12:43 | 11/10/2026 15:46 | **+2 días** de atraso |
| Fase 3: Sprint 2 (avanzado) | vie 30/10/2026 | 15/10/2026 | 15/10/2026 | 15 días antes |
| Fase 4: sistema y despliegue | vie 20/11/2026 | 15/10/2026 | en curso | Código y documentos listos; **falta desplegar** en Render y la evidencia manual |
| Fase 5: IIPD + presentación | vie 27/11 y dom 29/11/2026 | — | — | Pendiente |

Commits por día: 14 el 11/10/2026 y 7 el 15/10/2026 (más los de la Fase 4 al cerrar este documento).

## 3. Tiempo: estimado (backlog) vs. real (registro de tiempo)

`registro_tiempo.md` está vacío al corte, así que la columna **Real** queda en blanco. Cuando la estudiante
registre sus horas con el ID de la tarea, se completa la columna y la diferencia (Real − Estimado).

### Sprint 1 — estimado 57 h

| ID | Tarea | Estimado (h) | Real (h) | Diferencia |
|---|---|---|---|---|
| S1-01 | Rol y roles base | 3 | | |
| S1-02 | Usuario.rol y sucursal | 1.5 | | |
| S1-03 | RBAC y menú por rol | 4 | | |
| S1-04 | Bloqueo por intentos | 3 | | |
| S1-05 | Expiración de sesión y logout | 1 | | |
| S1-06 | CRUD de usuarios | 5 | | |
| S1-07 | Catálogo de productos | 4 | | |
| S1-08 | Proveedores e IProveedores | 3.5 | | |
| S1-09 | Ubicaciones y semilla | 3 | | |
| S1-10 | Existencia | 3 | | |
| S1-11 | Movimientos y aplicar() atómico | 5 | | |
| S1-12 | Vista de entrada | 3 | | |
| S1-13 | Vista de salida | 3.5 | | |
| S1-14 | Consultar existencias | 3 | | |
| S1-15 | Historial | 2.5 | | |
| S1-16 | Pruebas unitarias | 6 | | |
| S1-17 | Revisión de código | 3 | | |
| | **Total Sprint 1** | **57** | | |

### Sprint 2 — estimado 53.5 h

| ID | Tarea | Estimado (h) | Real (h) | Diferencia |
|---|---|---|---|---|
| S2-01 | Factory Method | 3 | | |
| S2-02 | Observer | 4 | | |
| S2-03 | AlertaInventario sin duplicados | 4 | | |
| S2-04 | Pantalla de alertas | 2.5 | | |
| S2-05 | Adapter y correo | 4 | | |
| S2-06 | Consumo de sucursal | 3 | | |
| S2-07 | Discrepancias | 4 | | |
| S2-08 | Anulación | 4 | | |
| S2-09 | Indicadores de consumo | 5 | | |
| S2-10 | Dashboard con Chart.js | 5 | | |
| S2-11 | Exportación PDF/Excel | 4 | | |
| S2-12 | Pruebas de integración | 8 | | |
| S2-13 | Bitácora de defectos | 3 | | |
| | **Total Sprint 2** | **53.5** | | |

### Fases 1, 4 y 5 (no estimadas en el backlog)

| Actividad | Estimado (h) | Real (h) |
|---|---|---|
| Fase 1: entorno, plan de pruebas, backlog, ajustes al DEDS | — | |
| Fase 4: pruebas de sistema, despliegue, manuales, métricas | — | |
| Fase 5: IIPD y presentación | — | |
| **Total del proyecto** | **110.5** (solo sprints) | |

**Lección de estimación:** el backlog solo estimó los dos sprints de codificación; la preparación, el
despliegue y la documentación quedaron sin estimar. Para el IIPD 5.1 conviene reconocerlo como un sesgo
del plan.

## 4. Alcance: planificado vs. entregado

| Concepto | Planificado | Real al 2026-10-15 |
|---|---|---|
| Requerimientos funcionales | 18 (DEDS §2.3) | **18 de 18** implementados y verificados por pruebas automatizadas ([checklist_aceptacion.md](checklist_aceptacion.md)) |
| Requerimientos no funcionales | 8 (DEDS §2.4) | RNF-01, 02, 03, 05, 06 y 08 verificados en local; **RNF-04 y RNF-07 pendientes** (producción y navegadores, manuales) |
| Patrones de diseño | 3 (DEDS §3.4) | 3 implementados, con evidencia de archivo y línea ([mapeo_componentes.md](mapeo_componentes.md)) |
| Casos de prueba del plan | 51 CP de RF Alta + 8 INT + 3 SIS | **293 pruebas automatizadas** (8 en la Fase 1 → 167 en el Sprint 1 → 280 en el Sprint 2 → 293 en la Fase 4) |
| Cobertura | Meta ≥ 80 % en inventario y alertas; ≥ 70 % global | 96 % global (líneas y ramas) |
| Código | — | 2 617 líneas de Python de producción (70 archivos), 1 946 de pruebas (21 archivos), 28 plantillas |
| Despliegue | URL pública en Render | Configuración lista (`render.yaml`, `build.sh`, settings de producción verificados en local); **sin URL pública todavía** |

## 5. Defectos

Detalle en [bitacora_defectos.md](bitacora_defectos.md) y [revision_codigo.md](revision_codigo.md).

| Métrica | Valor |
|---|---|
| Defectos de producto registrados en la bitácora | 7 (Alta 2, Media 2, Baja 3) |
| Hallazgos de la revisión formal del Sprint 1 | 11 (9 defectos corregidos) |
| Defectos Críticos o Altos abiertos | **0** |
| Densidad (revisión del Sprint 1) | ≈ 6.3 defectos por KLOC |
| Correcciones que causaron una regresión | 1 (DEF-04, detectada por la suite antes del commit y revertida) |

## 6. Riesgos: previstos (DEDS Tabla 4) vs. materializados

| Riesgo | Impacto previsto | ¿Se materializó? | Evidencia y efecto |
|---|---|---|---|
| Resistencia al cambio del bodeguero y los encargados | Alto | **No evaluable todavía** | No hubo usuarios reales en este período. Mitigación aplicada: tareas frecuentes en ≤ 3 pasos (RNF-03 verificado) y manual de usuario. |
| Datos históricos de Excel incompletos o inconsistentes | Medio | **No se materializó en esta fase** | No se migraron datos históricos (no hay RF para eso). Queda abierto si el restaurante quiere cargar su Excel. |
| Disponibilidad limitada del personal para la elicitación | Medio | No aplica en MDS2 | No hubo elicitación nueva; se trabajó sobre el DEDS. |
| Alcance mal definido del modelo de datos por sucursal | Alto | **Sí, parcialmente** | Hubo que agregar elementos que el modelo no tenía: sucursal del usuario (D-01), consumo de sucursal (D-02), discrepancia (D-03), motivo y trazabilidad de anulación (D-04, D-19). |
| *(No previsto)* Ambiente de desarrollo sin herramientas | — | **Sí** | La máquina no tenía Python, Git ni PostgreSQL. Se instalaron el mismo día (Fase 1). |
| *(No previsto)* Atraso respecto al calendario de la consigna | — | **Sí** | Fase 1 con +23 días y Fase 2 con +2 días (sección 2). |
| *(No previsto)* Inconsistencias en el propio DEDS | — | **Sí** | 5 inconsistencias (I-1 a I-5, `ajustes_deds.md`): versión del documento, la Fig. 20 sin Proveedores, wireframes con el menú del dueño, etc. |
| *(No previsto)* Vencimiento de la BD gratuita de Render | — | **Identificado, no materializado** | Vence a los 30 días; si se despliega antes del 30/10 vence antes de la presentación (D-28, `manual_despliegue.md` §8). |

## 7. Desviaciones respecto al diseño

29 desviaciones registradas en [desviaciones.md](desviaciones.md), todas menores y justificadas. Ninguna
cambia la arquitectura en capas, los módulos ni los patrones del DEDS.

| Tipo | Cantidad | Ejemplos |
|---|---|---|
| Adición (algo que el DEDS no modelaba y un RF exigía) | 10 | Sucursal del usuario, `DiscrepanciaInventario`, campos de bloqueo y de anulación, `EstadoIndicadores` |
| Interpretación (el DEDS era ambiguo o incompleto) | 14 | Consumo = salida desde la sucursal, "editar" = anular + reemplazar, correo después del commit, plan gratuito de Render |
| Tecnología | 3 | **Render en lugar de Nginx** (D-06), openpyxl/ReportLab (D-20), dj-database-url (D-26) |
| Omisión | 2 | Sin recuperación de contraseña (D-05), sin campo "Observación" (D-11) |

## 8. Pendiente para cerrar estas métricas

1. Registrar las horas reales en `registro_tiempo.md` (ID de tarea, fecha y horas) y completar la sección 3.
2. Desplegar en Render y completar `pruebas_sistema.md` §6 y el checklist de navegadores (§7).
3. Agregar las capturas de `checklist_aceptacion.md`.
4. Actualizar la sección 2 con las fechas reales de las entregas de las Fases 4 y 5.
