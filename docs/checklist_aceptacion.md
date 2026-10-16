# Checklist de aceptación por requerimiento funcional

**Proyecto:** InventarioWeb El Jardín · **Fase:** 4 · **Corresponde a:** IIPD 3.3 · Plan de pruebas §2.5

- **Criterio del DEDS:** texto literal de la Tabla 6 (§2.3).
- **Automatizado:** resultado real de la suite el **2026-10-15** (`pytest`: 293 passed, 0 fallos). El número
  indica cuántas pruebas llevan el RF en su nombre (`test_rfXX_...`).
- **Prueba manual para la evidencia:** qué hacer en el sistema desplegado (alfa, con los usuarios de `seed_demo`)
  para tomar la captura.
- **Resultado manual** y **Evidencia:** los completa la estudiante (Cumple / No cumple, nombre de la captura,
  fecha).

Usuarios de demostración: `duena@`, `bodeguero@`, `encargado.santacruz@` y `encargada.penablanca@eljardin.test`.

| RF | Prior. | Criterio de aceptación (DEDS) | Automatizado | Prueba manual para la evidencia | Resultado manual | Evidencia (captura) |
|---|---|---|---|---|---|---|
| RF-01 | Alta | Un usuario con credenciales válidas accede únicamente a las funciones permitidas para su rol; con credenciales inválidas, el acceso es rechazado. | **Cumple** (97 pruebas: menú por rol, matriz RBAC de 51 casos, bloqueo, CSRF) | Entrar con cada rol y capturar su menú. Escribir mal la contraseña y capturar el rechazo. Abrir `/usuarios/` como bodeguero y capturar el 403. | | |
| RF-02 | Alta | Tras registrar una entrada válida, la existencia de la bodega aumenta exactamente en la cantidad ingresada. | **Cumple** (24) | Bodeguero: anotar la existencia del panel lateral, registrar una entrada de 12.5 y capturar el mensaje con la existencia nueva. | | |
| RF-03 | Alta | Tras registrar una salida válida, la existencia de la bodega disminuye y la de la sucursal destino aumenta en la cantidad enviada. | **Cumple** (13) | Registrar una salida a Santa Cruz y capturar la existencia de la bodega y luego la de Santa Cruz. Intentar enviar más de lo disponible y capturar el aviso con "Usar máximo". | | |
| RF-04 | Alta | En todo momento, la existencia mostrada para una ubicación refleja la suma de sus movimientos de entrada y salida registrados. | **Cumple** (16, con la invariante en secuencias, anulaciones, `seed_demo` y concurrencia) | Dueño: capturar Historial filtrado por un producto y una ubicación junto a Existencias de esa ubicación y comprobar la suma. | | |
| RF-05 | Alta | El encargado de una sucursal visualiza únicamente las existencias correspondientes a su sucursal. | **Cumple** (8) | Encargado de Santa Cruz: capturar Existencias. Cambiar la URL a `?ubicacion=<id de Peña Blanca>` y capturar el 403. | | |
| RF-06 | Alta | Al registrarse un movimiento que deja la existencia bajo el umbral, se crea una alerta visible para los dueños en un plazo no mayor a la actualización inmediata de la existencia. | **Cumple** (17, sin duplicados y en la misma transacción) | Encargado: reportar un consumo que deje un producto bajo el mínimo. Dueño: capturar Alertas de inmediato y luego "Marcar atendida". | | |
| RF-07 | Media | El usuario puede filtrar por sucursal, producto y rango de fechas, y obtener el consumo total correspondiente. | **Cumple** (12) | Dueño: Reportes → Consumo con los tres filtros; capturar la tabla y el KPI del Dashboard con el mismo producto. | | |
| RF-08 | Media | El panel muestra, para un mismo período, el consumo de Santa Cruz y de Peña Blanca lado a lado. | **Cumple** (2) | Dueño: capturar el gráfico "Comparativo de consumo por producto entre sucursales". | | |
| RF-09 | Media | Un producto creado o editado queda disponible para su uso inmediato en los formularios de entrada y salida. | **Cumple** (6) | Dueño: crear el producto "Harina". Bodeguero: capturar el desplegable de Entradas con "Harina". Desactivarlo y capturar que ya no aparece. | | |
| RF-10 | Media | Un usuario nuevo puede iniciar sesión y acceder únicamente a las funciones de su rol asignado. | **Cumple** (16) | Dueño: crear un encargado de Peña Blanca. Iniciar sesión con él y capturar su menú. | | |
| RF-11 | Media | Todo registro de entrada exitoso queda vinculado a un proveedor existente en el sistema. | **Cumple** (7) | Capturar Historial con la columna Proveedor. Desactivar un proveedor y capturar que no aparece en Entradas. | | |
| RF-12 | Media | El usuario obtiene una lista cronológica de movimientos con fecha, tipo, cantidad y usuario que los registró. | **Cumple** (2, más los recorridos SIS) | Capturar Historial, del más reciente al más antiguo, con los filtros. | | |
| RF-13 | Alta | Una discrepancia reportada queda registrada y asociada al movimiento correspondiente para su trazabilidad. | **Cumple** (8) | Encargado: Reportar discrepancia de un envío. Dueño: capturar en Historial la etiqueta "Discrepancia" en ese envío. | | |
| RF-14 | Baja | El archivo exportado contiene la misma información mostrada en pantalla al momento de la exportación. | **Cumple** (7; el Excel se compara celda por celda con la tabla) | Reportes → Exportar a Excel y a PDF; capturar la pantalla y el archivo abierto, uno al lado del otro. | | |
| RF-15 | Media | Un movimiento anulado revierte su efecto sobre las existencias afectadas y queda marcado como anulado en el historial, sin eliminarse. | **Cumple** (15: anular y corregir, motivo obligatorio, sin cambios parciales) | Bodeguero: anular una salida con motivo; capturar Historial ("Anulado" con el motivo) y las existencias restauradas. | | |
| RF-16 | Alta | Ante una existencia en estado "Agotado", los dueños reciben una notificación además de la alerta visible en el panel. | **Cumple** (10, con el backend de correo en memoria) | **En Render con SMTP real:** agotar un producto y capturar el correo recibido en el buzón del dueño, más la alerta en el panel. | | |
| RF-17 | Media | Los indicadores mostrados reflejan los movimientos registrados hasta el momento de la consulta, sin necesidad de actualización manual. | **Cumple** (3: el observador invalida los indicadores) | Capturar el Dashboard, registrar un consumo en otra pestaña y recargar el Dashboard: la cifra cambia. | | |
| RF-18 | Baja | Tras cerrar sesión, el usuario no puede acceder a funciones protegidas sin autenticarse nuevamente. | **Cumple** (1, más los recorridos SIS-01 y SIS-02) | Cerrar sesión, pegar la URL de `/inventario/entradas/` y capturar la redirección al login. | | |

## Resumen

| | Cantidad |
|---|---|
| RF con criterio verificado automáticamente | **18 de 18** |
| RF de prioridad Alta (01, 02, 03, 04, 05, 06, 13, 16) | 8 de 8 automatizados; **RF-16 necesita además la prueba con SMTP real en producción** |
| RF con evidencia manual (captura) completada | ___ de 18 (lo completa la estudiante) |

Los RNF se verifican en [pruebas_sistema.md](pruebas_sistema.md).
