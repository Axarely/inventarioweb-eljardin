# Bitácora de defectos (SQA)

**Proyecto:** InventarioWeb El Jardín · **Fase:** 3 (Sprint 2) · **Base:** Pressman, cap. 16 (SQA)

Esta bitácora registra **solo defectos reales encontrados al ejecutar pruebas**: automatizadas, manuales
en el navegador, o la ejecución real de comandos y del servidor. Los problemas detectados leyendo el código
antes de ejecutarlo están en el acta de revisión ([revision_codigo.md](revision_codigo.md)), no aquí.

**Severidad** (plan de pruebas §7): Crítica / Alta / Media / Baja.
**Tipo:** *Producto* (defecto del sistema) o *Prueba* (defecto en el código de la prueba, que daba un
resultado falso).
**Estado:** Abierto → Corregido → Verificado (con prueba de regresión en verde) → Cerrado. También
*Aceptado* (se decide no corregir, con justificación).

| ID | Fecha | Sprint | Tipo | RF/RNF | Severidad | Descripción | Cómo se detectó | Causa raíz | Resolución | Prueba de regresión | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DEF-01 | 2026-10-11 | 1 | Producto | RF-10, RF-11 | **Alta** | Los formularios para crear usuario, rol y proveedor daban **error 500** al abrirse. | Prueba automatizada: matriz RBAC (2 casos fallidos) | `FormularioMixin` llamaba a `CreateView.get_success_url()`, que usa `self.object`, todavía `None` antes de guardar. | Nuevo `get_url_cancelar()` en `config/ui.py`. Revisión R-01. | `test_rf10_formularios_crear_cargan_sin_error` | Cerrado |
| DEF-02 | 2026-10-11 | 1 | Producto | RNF-02 | Media | El usuario bloqueado por intentos fallidos nunca veía el mensaje de bloqueo. | Prueba automatizada `test_rf01_bloqueo_tras_intentos_fallidos` | La plantilla de login mostraba un texto fijo en lugar de los errores del formulario. | La plantilla muestra `form.non_field_errors`. Revisión R-02. | La misma prueba | Cerrado |
| DEF-03 | 2026-10-11 | 1 | Producto | RF-01 | **Alta** | **Error 500** al enviar el login con la contraseña vacía o un correo inválido. | **Prueba manual** en el navegador (traza en el log de `runserver`) | Se llamaba a `reiniciar_intentos(None)` cuando Django no llegaba a autenticar. | Solo se reinicia el contador si hay un usuario autenticado. Revisión R-11. | `test_rf01_login_datos_incompletos_no_da_500` (4 casos) | Cerrado |
| DEF-04 | 2026-10-15 | 2 | Producto | RF-17 | Baja | Cada salida refresca **dos veces** los indicadores del panel (un UPDATE de más tras el commit). El resultado es correcto. | Prueba de integración INT-03: esperaba 1 refresco y hubo 2 | Una salida cambia dos existencias (bodega y sucursal) y cada cambio notifica a `PanelIndicadoresService`, que programa su propio refresco. | **Aceptado.** Se intentó dejar un solo refresco por transacción revisando `connection.run_on_commit`, que es una API interna de Django. Esa corrección **rompió 2 pruebas** (`test_rf17_indicadores_reflejan_movimiento_nuevo` y `test_int_anulacion_revierte_existencias_e_indicadores`), porque se comporta distinto dentro de las pruebas que en producción. Se revirtió: el costo del refresco doble es despreciable y depender de una API interna es un riesgo mayor. | INT-03 documenta el comportamiento (versión +2) | Aceptado |
| DEF-05 | 2026-10-15 | 2 | Producto | RF-17, RNF-01 | Baja | La clave de caché del panel tenía espacios y comillas (`CacheKeyWarning`). Con memcached habría fallado. | Advertencia de la suite de pruebas | La clave se armaba con `repr()` de los filtros. | La clave es un hash SHA-256 de los filtros (`reportes/servicios.py`). | La suite corre sin advertencias | Cerrado |
| DEF-06 | 2026-10-15 | 2 | Prueba | RF-06 | Baja | `test_rf06_no_duplica_alerta_pendiente` fallaba de forma intermitente. | Ejecución de la suite | En Windows, dos llamadas seguidas a `timezone.now()` pueden devolver el mismo instante (resolución de unos 15 ms). La prueba exigía `>` cuando lo correcto es `>=`. El sistema sí actualiza la fecha. | La prueba usa `>=` y sigue verificando que se actualiza el nivel detectado. | La misma prueba | Cerrado |
| DEF-07 | 2026-10-15 | 2 | Prueba | RF-06 | Baja | `test_rf06_alerta_visible_y_atendible_por_dueno` daba un **falso fallo**: decía que la alerta atendida seguía en la lista. | Ejecución de la suite | La prueba buscaba el nombre del producto en todo el HTML, y el mensaje de confirmación "Alerta de «Pechuga de pollo» marcada como atendida" también lo contiene. | La prueba revisa la lista de alertas del contexto, no el HTML. | La misma prueba | Cerrado |
| DEF-08 | 2026-10-15 | 2 | Producto | RF-16 | Baja | El correo de producto agotado mostraba "Stock mínimo configurado: **8.00** kg", con un formato distinto al resto del sistema ("8 kg"). | Ejecución real de `seed_demo` (correo impreso en la consola) | Se interpolaba el `Decimal` directamente, sin `formatear_cantidad`. | Se usa `formatear_cantidad`. | `test_rf16_correo_a_duenos_al_agotarse` verifica "Stock mínimo configurado: 10 kg." | Cerrado |

## Resumen

| Métrica | Valor |
|---|---|
| Defectos registrados | 8 (6 de producto, 2 de prueba) |
| Por severidad (producto) | Crítica 0 · Alta 2 · Media 1 · Baja 3 |
| Cerrados / aceptados / abiertos | 7 / 1 / 0 |
| Detectados por pruebas automatizadas | 5 (DEF-01, 02, 04, 06, 07) |
| Detectados por advertencias de la suite | 1 (DEF-05) |
| Detectados por ejecución o prueba manual | 2 (DEF-03, DEF-08) |
| Críticos o Altos abiertos | **0** (criterio de salida del plan de pruebas §4) |

**Observación (DEF-04):** es el único caso en que una corrección introdujo una regresión, y la detectó la
suite automatizada antes del commit. Es una evidencia directa del valor de las pruebas de regresión
(plan de pruebas §2.6).
