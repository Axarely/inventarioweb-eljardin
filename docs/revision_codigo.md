# Revisión técnica formal de código — Sprint 1

**Proyecto:** InventarioWeb El Jardín · **Fase:** 2 (Sprint 1, núcleo funcional) · **Fecha:** 2026-10-11
**Base teórica:** Pressman, cap. 15 "Técnicas de revisión": revisión técnica formal con lista de verificación,
registro de hallazgos y seguimiento de las correcciones.

| Aspecto | Detalle |
|---|---|
| Tipo de revisión | Revisión propia, con apoyo de IA, sobre el código del Sprint 1 antes del commit |
| Revisores | Autora (A. Escobar), asistida por Claude (Anthropic) como herramienta de revisión. Se declara según la consigna §6.3. **Pendiente:** que la autora valide cada hallazgo y su corrección antes de la entrega. |
| Material revisado | `autenticacion/`, `usuarios/`, `proveedores/`, `inventario/` (modelos, servicios, vistas, formularios, plantillas, admin, `seed_demo`), `config/` |
| Tamaño | 1 435 líneas de Python de producción (50 archivos, sin pruebas ni migraciones; cuenta docstrings, no líneas vacías ni comentarios) y 18 plantillas |
| Duración | Las horas reales las registra la autora en [registro_tiempo.md](registro_tiempo.md) (tarea S1-17) |

## 1. Lista de verificación aplicada

| # | Pregunta | Resultado |
|---|---|---|
| C1 | ¿Cada vista y servicio aplica el permiso del rol (mínimo privilegio) y redirige al login sin sesión? | Sí: matriz RBAC automatizada de 33 casos (`test_rf01_matriz_rbac`) |
| C2 | ¿Los movimientos se aplican dentro de una transacción y con bloqueo de fila (RNF-08)? | Sí: `aplicar()` usa `transaction.atomic` y `select_for_update`. Probado con fallos simulados. |
| C3 | ¿Toda entrada del usuario se valida en el servidor (cantidades, IDs, `next`)? | Sí, salvo R-04 (cantidad máxima acumulada), ya corregido |
| C4 | ¿Algún flujo puede terminar en error 500? | Sí: R-01 y R-04 (corregidos) |
| C5 | ¿Los mensajes al usuario son correctos y no confunden? | R-02 y R-07 (corregidos) |
| C6 | ¿El administrador puede dejar el sistema inconsistente o sin acceso? | R-03 y R-05 (corregidos) |
| C7 | ¿Hay secretos en el código? | No. `seed_demo` usa una contraseña de demostración **solo** con `DEBUG=True` y en producción exige `--password`. |
| C8 | ¿Los nombres coinciden con el DEDS (Fig. 12) y el código referencia su RF/RNF? | Sí: `Existencia.nivel()`, `esta_bajo_umbral()`, `actualizar_cantidad(delta)`, `aplicar()`, `tiene_permiso()`, `agregar_permiso()`; comentarios `# RF-XX` |
| C9 | ¿`inventario` importa `alertas` o `reportes` (corrección 1 del DEDS)? | No |
| C10 | ¿Hay consultas N+1 en los listados? | No: `select_related` y `prefetch_related`; `test_rnf01_consulta_existencias_consultas_acotadas` |

## 2. Hallazgos

Severidad según el plan de pruebas §7 (Crítica / Alta / Media / Baja).

| ID | Severidad | Ubicación | Hallazgo | Cómo se detectó | Corrección aplicada | Prueba de regresión | Estado |
|---|---|---|---|---|---|---|---|
| R-01 | **Alta** | `config/ui.py`, `FormularioMixin.get_context_data` | Los formularios de alta (usuario, rol, proveedor) daban **error 500** al abrirse: el enlace "Cancelar" llamaba a `CreateView.get_success_url()`, que formatea `success_url` con `self.object` y este es `None` antes de guardar. Impedía crear usuarios y proveedores (RF-10, RF-11). | Matriz RBAC automatizada (2 casos fallidos) | Nuevo `get_url_cancelar()`: usa `success_url` directamente y solo recurre a `get_success_url()` si no está definida | `test_rf10_formularios_crear_cargan_sin_error` | Cerrado |
| R-02 | Media | `autenticacion/templates/autenticacion/login.html` | La plantilla mostraba el texto fijo "Correo o contraseña incorrectos." para cualquier error, así que el usuario bloqueado (RNF-02) nunca veía que su cuenta estaba bloqueada temporalmente. | `test_rf01_bloqueo_tras_intentos_fallidos` | La plantilla muestra `form.non_field_errors` y los errores del campo correo | `test_rf01_bloqueo_tras_intentos_fallidos` | Cerrado |
| R-03 | Media | `usuarios/views.py`, `UsuarioEditarView` | El dueño podía cambiar su **propio** rol y perder el acceso a la gestión. Si era el único dueño, nadie podía administrar el sistema sin el admin de Django. | Revisión manual (C6) | Se rechaza cambiar el propio rol, igual que ya se rechazaba desactivarse a sí mismo | `test_rf10_no_puede_cambiar_su_propio_rol` | Cerrado |
| R-04 | Baja | `inventario/models.py`, `Existencia.actualizar_cantidad` | Una entrada que lleve la existencia por encima de `numeric(10,2)` (99 999 999.99) provocaba un `DataError` de PostgreSQL (error 500) en lugar de un mensaje. | Revisión manual (C3, valores límite) | Se valida contra `Existencia.CANTIDAD_MAXIMA` y se lanza `MovimientoInvalido` | `test_rf02_existencia_maxima_controlada` | Cerrado |
| R-05 | Baja | `usuarios/admin.py` | El alta de usuarios desde el admin excluye la contraseña y crea cuentas que nunca pueden iniciar sesión. | Revisión manual (C6) | Se deshabilita "añadir" en el admin: el alta se hace en Usuarios (RF-10) o con `createsuperuser` | `test_rf10_admin_no_crea_usuarios_sin_password` | Cerrado |
| R-06 | Baja | `usuarios/forms.py` | El rol era opcional en los formularios, así que se podían crear usuarios sin rol, que entran a un sistema vacío. | Revisión manual | `rol` es obligatorio en los formularios de crear y editar (el modelo lo deja nulo solo para `createsuperuser`) | `test_rf10_rol_obligatorio_en_formulario` | Cerrado |
| R-07 | Baja | `inventario/templates/inventario/existencias.html` | Si no hay ubicaciones, un dueño veía "Su usuario no tiene una sucursal asignada", que es falso para su rol. | Revisión manual (C5) | Mensaje distinto según el permiso | `test_rf05_dueno_sin_ubicaciones_mensaje_correcto` | Cerrado |
| R-08 | Baja | `.coveragerc` | `conftest.py` (código de prueba) se contaba en la cobertura y la inflaba. | Lectura del informe de cobertura | Se omite en `.coveragerc` | — (configuración) | Cerrado |
| R-09 | Baja | `autenticacion/forms.py` | **Riesgo aceptado.** El mensaje de bloqueo solo aparece para correos registrados (permite saber si un correo existe), y un atacante puede bloquear a un usuario a propósito durante 15 minutos. | Revisión manual (C1) | No se corrige: es inherente al bloqueo que pide el DEDS 3.5. Mitigación: el bloqueo es temporal y los límites se configuran (`LOGIN_MAX_INTENTOS`, `LOGIN_BLOQUEO_MINUTOS`). Se reevalúa en las pruebas de seguridad de la Fase 4. | `test_rf01_bloqueo_expira` | Aceptado |
| R-10 | Info | `inventario/servicios.py` | Los servicios crean `EntradaInventario` y `SalidaInventario` directamente: todavía no existe `MovimientoInventarioFactory`. | Revisión contra el DEDS 3.4 | Planificado para S2-01 (backlog del Sprint 2). No es un defecto del Sprint 1. | INT-01 (Sprint 2) | Abierto (planificado) |

## 3. Métricas de la revisión

| Métrica | Valor |
|---|---|
| Hallazgos totales | 10 (8 defectos corregidos, 1 riesgo aceptado, 1 informativo) |
| Por severidad (defectos) | Crítica 0 · Alta 1 · Media 2 · Baja 5 |
| Detectados por pruebas automatizadas | 2 (R-01, R-02) |
| Detectados por inspección manual | 6 (R-03 a R-08) |
| Densidad de defectos | 8 / 1.435 KLOC ≈ **5.6 defectos por KLOC** (antes de la entrega) |
| Pruebas antes → después de las correcciones | 157 pasan, 5 fallan → **163 pasan, 0 fallan** (se agregaron 6 pruebas de regresión) |

## 4. Evidencia

- Ejecución inicial (antes de corregir): `5 failed, 152 passed`. Los fallos eran R-01 (4 pruebas) y R-02 (1 prueba).
- Ejecución final: `163 passed`, con cobertura total de 97 % (líneas y ramas, según `.coveragerc`).
- Recorrido HTTP real contra `runserver` con los datos de `seed_demo`: cada rol ve exactamente su menú,
  los accesos no permitidos devuelven 403 y el log del servidor no tiene ninguna respuesta 500.
