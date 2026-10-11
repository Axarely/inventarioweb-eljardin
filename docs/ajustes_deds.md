# Ajustes al DEDS — Correcciones de la retroalimentación de la Fase 3

**Proyecto:** InventarioWeb El Jardín · **Curso:** Metodología y Diseño de Sistemas II · **Fase:** 1

La consigna de MDS2 (Fase 1, "Ajustes al DEDS") pide incorporar, antes de codificar, las correcciones
pendientes señaladas en la retroalimentación de la Fase 3. Las cinco correcciones ya están aplicadas en
[DEDS.pdf](DEDS.pdf), Capítulo 3, **versión 1.1** (Tabla 8, control de versiones del Capítulo 3). Esta tabla
indica dónde quedó cada una, para poder verificarlas.

| # | Corrección solicitada | Qué se cambió | Dónde quedó (sección / figura) | Registro en el DEDS |
|---|---|---|---|---|
| 1 | Quitar la relación «usa» directa de Inventario hacia Alertas | El diagrama de componentes ya no tiene una dependencia directa Inventario → Alertas/Reportes. Alertas y Reportes reciben los cambios de `Existencia` como observadores, con líneas discontinuas «notifica» del patrón Observer, y Inventario no conoce a sus observadores. | §3.2 "Diagrama de componentes", **Fig. 11** (v1.1, corregido) y la nota al pie de la figura; coherente con §3.4 Patrón 2, **Fig. 23** | Tabla 8, v1.1, punto (1); §3.2, párrafo previo a la Fig. 11 |
| 2 | Conectar el Módulo Reportes | El Módulo Reportes expone `IReportes` y queda conectado al componente **Panel de Indicadores (Dueños)**. Se agregó `IReportes.generar_indicadores(filtros)` a la especificación de interfaces. | §3.2, **Fig. 11**; tabla "Especificación de interfaces de los componentes principales" (fila IReportes) | Tabla 8, v1.1, punto (2) |
| 3 | Agregar el Módulo Proveedores | Hay un sexto módulo con el CRUD de proveedores (alta, edición, activar/desactivar), la interfaz `IProveedores` (`crear_proveedor`, `desactivar_proveedor`) que consume Inventario al registrar entradas (RF-11), un wireframe de gestión y una entrada en el sitemap. | §3.2, tabla "Módulos identificados y responsabilidades" (Módulo de Proveedores), **Fig. 11**, tabla de interfaces; §3.3, **Fig. 19** (wireframe Gestionar Proveedores); §3.5, **Fig. 25** (sitemap v1.1) | Tabla 8, v1.1, punto (3); §4.2 (reflexión) |
| 4 | Unificar los métodos de `Existencia` | `Existencia` declara los mismos métodos en el diagrama de clases de diseño y en el del patrón Observer: `agregar_observador(o)`, `notificar_observadores()` y `actualizar_cantidad(delta)`, además de `nivel()` y `esta_bajo_umbral()`. | §3.2 "Diagrama de clases de diseño", **Fig. 12** (v1.1); §3.4 Patrón 2, **Fig. 23** | Tabla 8, v1.1, punto (4); §3.2, párrafo previo a la Fig. 12 |
| 5 | Cerrar las decisiones de hospedaje y canal de notificación | Hospedaje: **Render (plan económico)**, que antes quedaba abierto entre Render y Railway. Notificación: **SMTP (correo)** en la primera versión, con el patrón Adapter (`INotificador`) preparado para agregar SMS. | §3.1 "Decisiones de tecnología" (tabla, filas Hospedaje y Notificaciones); §3.4 Patrón 3, **Fig. 24** | Texto introductorio de "Decisiones de tecnología" ("se cierran las dos decisiones que habían quedado abiertas") |

## Cómo se refleja en el código

| Corrección | Dónde se implementa | Sprint |
|---|---|---|
| 1 | `inventario` no importa `alertas` ni `reportes`. Los observadores se registran en `AppConfig.ready()` de `alertas` y `reportes`. | 2 |
| 2 | App `reportes`: `PanelIndicadoresService` (observador) y el dashboard con Chart.js | 2 |
| 3 | App `proveedores`: modelo `Proveedor`, CRUD y la interfaz que consume `inventario` | 1 |
| 4 | `inventario.models.Existencia` con esos nombres exactos de método | 1 (`nivel`, `esta_bajo_umbral`), 2 (métodos Observer) |
| 5 | `config/settings/prod.py` (Render, HTTPS) y `alertas`: `INotificador`, `AdaptadorCorreoSMTP` | 1 (settings), 2 (Adapter) |

## Inconsistencias detectadas al revisar el DEDS

Se documentan por transparencia. **No se rediseña nada**: se implementa según el texto y las figuras
corregidas, y cuando eso obliga a decidir algo, la decisión queda en [desviaciones.md](desviaciones.md).

| # | Inconsistencia | Ubicación | Tratamiento |
|---|---|---|---|
| I-1 | La portada y la Tabla 1 indican "Versión 1.0 — Final, 10/08/2026", pero la Tabla 8 registra el Capítulo 3 v1.1 con fecha 13/08/2026, posterior a la entrega del documento. | Portada, Tabla 1, Tabla 8 | Pendiente: actualizar la Tabla 1 del DEDS a v1.1 con la fecha real de la corrección. |
| I-2 | La corrección 5 (hospedaje y notificación) no figura en la lista de cambios de la Tabla 8, aunque el texto de §3.1 la declara. | Tabla 8, §3.1 | Pendiente: agregarla como punto (5) en la Tabla 8. |
| I-3 | El prototipo de navegación no incluye "Gestionar proveedores" ni "Exportar reportes" para el Dueño, aunque el sitemap (Fig. 25) sí los incluye. | §3.3, Fig. 20 vs Fig. 25 | Se implementa el menú del Dueño según la Fig. 25, que es la versión corregida. |
| I-4 | Los wireframes del bodeguero y del encargado (Fig. 15, 16, 17) muestran el menú lateral completo del Dueño (Panel de indicadores, Catálogo, Usuarios). | §3.3, Fig. 15–17 | El menú se filtra por rol según §3.5 "Diseño de la navegación" (mínimo privilegio). Los wireframes se toman solo como referencia de contenido. |
| I-5 | El wireframe de login incluye el enlace "¿Olvidó su contraseña?", pero ningún RF lo especifica. | §3.3, Fig. 13 | No se implementa (ver desviaciones D-05). |
