# Pruebas de sistema y de requerimientos no funcionales

**Proyecto:** InventarioWeb El Jardín · **Fase:** 4 · **Corresponde a:** IIPD 3.3
**Fecha de ejecución:** 2026-10-15 · **Ambiente:** local (Windows 11, Intel 4 CPU lógicas, Python 3.12.10,
PostgreSQL 16.15). La parte en producción (Render) queda pendiente del despliegue: ver la sección 6.

Pruebas automatizadas en `tests/test_sistema.py`. Suite completa el 2026-10-15: **293 passed**, 0 fallos,
cobertura 96 %.

## 1. Recorridos de punta a punta por rol (SIS)

| ID | Rol | Recorrido | Prueba | Resultado |
|---|---|---|---|---|
| SIS-01 | Bodeguero | Login → entrada (40) → salida a Santa Cruz (15) → historial → corregir salida a 12 → cerrar sesión → sin acceso | `test_sis01_bodeguero` | PASSED |
| SIS-02 | Encargado | Login → existencias (solo su sucursal; 403 a otra) → consumo (deja alerta) → discrepancia → cerrar sesión | `test_sis02_encargado` | PASSED |
| SIS-03 | Dueño | Agotado → correo → login (va al dashboard) → alerta → atender → catálogo, proveedores, usuarios, roles, historial → exportar PDF | `test_sis03_dueno` | PASSED |

Además se hizo un recorrido HTTP real contra `runserver` con los datos de `seed_demo`. Cada rol ve
exactamente su menú, cada pantalla responde 200 a su rol y 403 a los demás, y el log del servidor no
registró ninguna respuesta 500.

## 2. RNF-01 — Rendimiento (< 2 s)

**Volumen:** BD aparte `inventarioweb_volumen`, cargada con `seed_demo` + `seed_volumen`:
**206 productos, 5 031 movimientos** en 60 días y **618 existencias**.

### 2.1 Medición HTTP real (`runserver`, 10 peticiones por página tras 1 de calentamiento)

| Página | Tamaño | Mediana | Máximo | < 2 s |
|---|---|---|---|---|
| Existencias (sucursal Santa Cruz) | 39 KB | 90.8 ms | 92.4 ms | Sí |
| Existencias (bodega, 206 productos) | 41 KB | 89.2 ms | 92.2 ms | Sí |
| Dashboard (30 días, todo) | 23 KB | 98.0 ms | 116.8 ms | Sí |
| Dashboard (60 días, 1 producto) | 17 KB | 104.8 ms | 213.7 ms | Sí |
| Reporte de consumo (30 días) | 55 KB | 146.0 ms | 257.0 ms | Sí |
| Reporte de existencias | 91 KB | 172.0 ms | 286.6 ms | Sí |
| Historial (página 1) | 30 KB | 126.4 ms | 210.5 ms | Sí |
| Exportar Excel (existencias) | 25 KB | 165.0 ms | 305.8 ms | Sí |
| Exportar PDF (consumo) | 32 KB | 151.8 ms | 252.9 ms | Sí |

### 2.2 Prueba automatizada (`test_rnf01_tiempos_con_volumen`, cliente de pruebas, mediana de 5)

| Página | Mediana | Máximo |
|---|---|---|
| Existencias (sucursal) | 23 ms | 25 ms |
| Existencias (bodega, dueño) | 24 ms | 36 ms |
| Dashboard (30 días) | 41 ms | 82 ms |
| Dashboard (60 días, 1 producto) | 42 ms | 49 ms |
| Reporte de consumo | 86 ms | 146 ms |
| Historial (página 1) | 53 ms | 54 ms |
| Exportar Excel (existencias) | 103 ms | 178 ms |

**Conclusión local:** se cumple RNF-01 con amplio margen; el peor caso fue 306 ms. **Limitación:** son
mediciones en la máquina de desarrollo. En Render (plan gratuito, CPU compartida) hay que repetirlas
(sección 6), y la **primera** petición después de 15 min sin tráfico puede tardar unos 50 s por el
arranque en frío del plan gratuito (D-28). Esa demora no la causa la aplicación, pero un usuario la
percibe.

## 3. RNF-02 — Seguridad

| Verificación | Cómo | Resultado |
|---|---|---|
| Contraseñas con hash | `test_rnf02_password_con_hash_fuerte`: el algoritmo es `pbkdf2_sha256` y la contraseña no aparece en texto plano | PASSED |
| Acceso por rol (RBAC), 403 | `test_rf01_matriz_rbac`: 17 rutas × 3 roles = **51 casos**, más los 403 de cada módulo | PASSED |
| Sin sesión → login | `test_rf01_sin_sesion_redirige_a_login` (17 rutas) | PASSED |
| CSRF obligatorio | `test_rnf02_csrf_obligatorio_en_login` (POST sin token → 403) | PASSED |
| Bloqueo tras 5 intentos fallidos | `test_rf01_bloqueo_tras_intentos_fallidos`, `test_rf01_bloqueo_expira` | PASSED |
| Sesión expira por inactividad | `test_rnf02_sesion_expira_por_inactividad`, `test_rnf02_actividad_renueva_expiracion` | PASSED |
| Configuración de producción | `test_rnf02_configuracion_de_produccion_segura`: `DEBUG=False`, `SECURE_SSL_REDIRECT`, cookies `Secure` (sesión y CSRF), `HttpOnly`, HSTS ≥ 30 días, proxy HTTPS de Render | PASSED |
| `check --deploy` sin errores | `test_rnf02_check_deploy_sin_errores` (queda solo la advertencia W021, HSTS preload, aceptada) | PASSED |
| Secretos fuera del repositorio | `test_rnf02_secretos_fuera_del_repositorio` (`.env` no versionado) | PASSED |
| Comportamiento real en modo producción (local) | Script con `config.settings.prod`: HTTP → **301** a HTTPS; HSTS presente; `csrftoken` y `sessionid` con `Secure`; `sessionid` `HttpOnly`; 404 sin traza; host no permitido → **400** | Verificado |
| HTTPS real en Render | Pendiente del despliegue (sección 6) | Pendiente |

## 4. RNF-03 — Usabilidad: tareas frecuentes en ≤ 3 pasos

Paso = una acción del usuario: (1) elegir la opción en el menú lateral visible al entrar, (2) completar y
enviar **un** formulario, (3) ver la confirmación. Lo verifica `test_rnf03_tareas_frecuentes_en_tres_pasos`.

| Tarea | Rol | Paso 1 | Paso 2 | Paso 3 | Pasos | Resultado |
|---|---|---|---|---|---|---|
| Registrar entrada | Bodeguero | Menú → Entradas | Producto, cantidad, proveedor → Registrar | Mensaje "Entrada registrada…" con la existencia nueva | 3 | PASSED |
| Registrar salida | Bodeguero | Menú → Salidas | Sucursal, producto, cantidad → Registrar | Mensaje "Salida registrada…" | 3 | PASSED |
| Consultar existencias | Encargado | Menú → Existencias | — (la lista de su sucursal se muestra de inmediato) | — | 1 | PASSED |

## 5. RNF-08 — Confiabilidad transaccional

| Escenario | Prueba | Resultado |
|---|---|---|
| Falla de BD **a mitad** de una salida (después de descontar la bodega, antes de sumar a la sucursal), por HTTP | `test_rnf08_falla_de_bd_a_mitad_de_una_salida`: la bodega sigue en 20, la sucursal en 0, no hay movimiento y el usuario ve "No se aplicó ningún cambio" | PASSED (antes fallaba: **DEF-09**, corregido) |
| Falla de BD en una entrada, por HTTP | `test_rnf08_falla_de_bd_en_entrada` | PASSED |
| Un observador falla dentro de la transacción | `test_int06_falla_de_observador_revierte_el_movimiento` | PASSED |
| Corrección fallida (anulación + nuevo movimiento) | `test_rf15_corregir_fallida_no_deja_cambios` | PASSED |
| Concurrencia: dos salidas por el total disponible | `test_int07_salidas_concurrentes_no_sobregiran` | PASSED |
| Concurrencia: salida y anulación sin deadlock | `test_int07_salida_y_anulacion_concurrentes_sin_deadlock` | PASSED |
| Invariante RF-04 (existencia = suma de movimientos) | `test_rf04_existencia_igual_suma_de_movimientos`, `test_int_anulacion_...`, `test_rf04_seed_demo_...` | PASSED |

## 6. Pendiente en producción (Render)

Se completa después de seguir `docs/manual_despliegue.md`. Anote los valores reales:

| Verificación | Resultado | Fecha | Evidencia |
|---|---|---|---|
| URL pública responde por HTTPS | | | |
| `http://` redirige a `https://` | | | |
| RNF-01: tiempos de existencias, dashboard y reporte (con el servicio ya activo) | | | |
| RNF-01: tiempo de la primera petición tras inactividad (arranque en frío) | | | |
| RNF-02: cookie `sessionid` con `Secure` (herramientas del navegador → Aplicación → Cookies) | | | |
| RF-16: el correo de "Agotado" llega por SMTP real al buzón del dueño | | | |
| RNF-04: disponibilidad medida con un monitor externo durante la Fase 4 (≥ 95 %) | | | |

## 7. RNF-07 — Checklist manual de navegadores

Ejecutar los recorridos SIS-01 a SIS-03 en cada navegador (versión actual) y marcar ✔ o ✘. Si algo falla,
registrarlo como defecto en la bitácora.

| Verificación | Chrome escritorio | Edge escritorio | Firefox escritorio | Chrome móvil (o vista responsiva) |
|---|---|---|---|---|
| Versión del navegador | | | | |
| Login, menú del rol y cerrar sesión | | | | |
| Registrar entrada: el panel lateral muestra la existencia en bodega | | | | |
| Registrar salida: el aviso de "Insuficiente" y el botón "Usar máximo" funcionan | | | | |
| Existencias: filtros y pills de color con texto | | | | |
| Dashboard: los gráficos de Chart.js se dibujan | | | | |
| Alertas: "Marcar atendida" | | | | |
| Exportar Excel y PDF: los archivos abren | | | | |
| El menú se pliega con el botón ☰ en pantalla angosta | | | | |
| Fecha / responsable | | | | |

## 8. Otros RNF

| RNF | Estado | Evidencia |
|---|---|---|
| RNF-04 Disponibilidad | Pendiente: se mide en producción (sección 6) | — |
| RNF-05 Mantenibilidad | Una sucursal o un producto nuevo se agregan solo con datos: `seed_volumen` y las pruebas crean productos sin tocar código, y el panel itera sobre las sucursales existentes | `test_rf08_comparativo_sucursales_lado_a_lado` (las series se generan por sucursal) |
| RNF-06 Escalabilidad (concurrencia) | Verificada con hilos contra PostgreSQL real | `test_int07_*` |
