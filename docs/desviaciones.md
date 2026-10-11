# Registro de desviaciones respecto al DEDS

La consigna (§1.2) solo permite ajustes **menores y justificados** respecto al DEDS, y cada uno debe
quedar documentado como desviación. Este registro alimenta el IIPD, §2.1 "Arquitectura final vs.
arquitectura diseñada".

**Tipos:** *Adición* (algo que el DEDS no modela y un RF exige), *Interpretación* (el DEDS es ambiguo o
incompleto), *Tecnología* (cambio de librería o infraestructura), *Omisión* (algo del DEDS que no se
implementa).

| ID | Fecha | Tipo | Qué cambia | Por qué | Impacto | RF/RNF |
|---|---|---|---|---|---|---|
| D-01 | 2026-10-11 | Adición | `Usuario` tiene un campo opcional `sucursal` (FK a `Sucursal`), que no aparece en la Fig. 12. | UC04, paso 2: "el sistema determina la sucursal asociada al usuario", y §3.5 dice que el encargado opera solo sobre su ubicación asignada. Sin esta relación el requisito no se puede cumplir. | Bajo: un campo nullable, obligatorio solo para el rol Encargado. | RF-05, RNF-02 |
| D-02 | 2026-10-11 | Interpretación | El consumo de sucursal se registra como `SalidaInventario` con `origen = sucursal` y `destino = null`. | §1.3 dice que los encargados "reportan el consumo", y RF-07/RF-08 miden el consumo por sucursal, pero ningún caso de uso ni clase modela ese movimiento. Reutilizar `SalidaInventario` evita una clase nueva y mantiene la existencia de la sucursal coherente con RF-04. | Medio: el campo `destino` pasa a ser nullable (la Fig. 12 ya lo marca `null=True`) y los reportes de consumo filtran por `origen` de tipo sucursal. | RF-04, RF-07, RF-08 |
| D-03 | 2026-10-11 | Adición | Nueva clase `DiscrepanciaInventario(movimiento, cantidad_enviada, cantidad_recibida, diferencia, usuario, fecha)`. | RF-13 (prioridad Alta) exige que la discrepancia quede "asociada al movimiento correspondiente", pero la Fig. 12 no tiene ninguna clase que la almacene. | Bajo: una tabla nueva en la app `inventario`, sin cambios en las clases existentes. | RF-13 |
| D-04 | 2026-10-11 | Adición | `MovimientoInventario.motivo_anulacion` (texto). | RF-15 exige justificar la anulación, y la Fig. 12 tiene `anular(motivo)` pero ningún atributo donde guardarlo. | Bajo: un campo nullable. | RF-15 |
| D-05 | 2026-10-11 | Omisión | No se implementa la recuperación de contraseña: se quita el enlace "¿Olvidó su contraseña?" de la Fig. 13. | Ningún RF la pide, y exige un flujo de correo adicional que habría que asegurar. El Dueño restablece las contraseñas desde la gestión de usuarios (RF-10). | Bajo: menos superficie de ataque. | RF-01, RF-10 |
| D-06 | 2026-10-11 | Tecnología | En producción no se usa Nginx: Render termina TLS en su proxy y **WhiteNoise** sirve los estáticos. Gunicorn se mantiene. | Render (decisión cerrada en §3.1) no permite instalar Nginx en su servicio web administrado, y su proxy ya cumple esa función (HTTPS y reenvío). | Bajo: la Fig. 10 se cumple en sus nodos (cliente, servidor de aplicación, BD y servicio externo). Solo cambia el componente proxy. | RNF-02, RNF-04 |
| D-07 | 2026-10-11 | Interpretación | La comunicación entre frontend y backend son peticiones HTTP a vistas MVT que devuelven HTML, no una "API de tipo REST". | §2.5 menciona una API REST, pero §3.1 (posterior y más específico) elige plantillas de Django renderizadas en el servidor "sin la complejidad de mantener una API separada". Se sigue §3.1. | Ninguno funcional; se cumple el HTTPS de §2.5. | RNF-02 |
| D-08 | 2026-10-11 | Interpretación | `AdaptadorSMS` es un *stub* sin integración real. La Fig. 24 lo nombra `AdaptadorSMSTwilio`. | §3.1 fija SMTP para la primera versión. El adaptador SMS existe para demostrar la extensibilidad del patrón Adapter sin contratar un proveedor. | Bajo: solo `AdaptadorCorreoSMTP` envía notificaciones reales. | RF-16 |
| D-09 | 2026-10-11 | Interpretación | El sistema se despliega en producción (Render) con una URL pública. | §2.1.2 del DEDS excluía "el despliegue en un ambiente de producción con usuarios reales", pero la consigna de MDS2 (Fase 4) lo exige. Manda la consigna. | Ninguno sobre el diseño: la Fig. 10 ya modela el despliegue. | RNF-04 |
| D-10 | 2026-10-11 | Adición | `Usuario` tiene además `is_staff` y los campos de `PermissionsMixin` de Django. | Son necesarios para el admin de Django y el sistema de permisos que §3.5 elige para el RBAC. | Ninguno funcional. | RF-01, RF-10 |

### Sprint 1

| ID | Fecha | Tipo | Qué cambia | Por qué | Impacto | RF/RNF |
|---|---|---|---|---|---|---|
| D-11 | 2026-10-11 | Omisión | El formulario de entrada no tiene el campo "Observación (opcional)" del wireframe (Fig. 15). | La clase de diseño `MovimientoInventario` (Fig. 12) no tiene ese atributo: aparece solo en el diagrama de análisis (Fig. 2). Se sigue la Fig. 12, que es el modelo de diseño. | Bajo: ningún RF lo exige. | RF-02 |
| D-12 | 2026-10-11 | Adición | `Usuario.intentos_fallidos` y `Usuario.bloqueado_hasta`. | El DEDS 3.5 exige un "bloqueo temporal tras varios intentos fallidos", y la Fig. 12 no tiene dónde guardarlo. Se persiste en la BD, y no en la caché, para que funcione con varios workers de gunicorn. | Bajo: dos campos no editables. | RNF-02 |
| D-13 | 2026-10-11 | Adición | `Rol.codigo` identifica los 3 roles base (Dueño, Bodeguero, Encargado). Sus permisos los fija el código (`usuarios/roles.py`) y no se editan desde la interfaz; los roles adicionales sí. | Si el dueño pudiera quitar permisos a los roles base, podría romper el mínimo privilegio del DEDS 3.5 o quedarse sin acceso. | Bajo: el CRUD de roles (RF-10) aplica a los roles personalizados. | RF-01, RF-10 |
| D-14 | 2026-10-11 | Interpretación | El rol Bodeguero tiene el permiso `add_producto` (sin opción de menú): puede crear un producto desde el formulario de entrada. | UC02, flujo alternativo A1: "Producto no existe en catálogo: el sistema permite crearlo antes de continuar". El resto del catálogo (listar, editar, desactivar) sigue siendo solo del Dueño. | Bajo. | RF-02, RF-09 |
| D-15 | 2026-10-11 | Interpretación | Las entradas siempre van a la bodega central (`Bodega.central()`). | La interfaz `IInventario.registrar_entrada(producto_id, cantidad, proveedor_id, usuario_id)` no recibe la bodega, y el DEDS 1.1 describe una única bodega central. | Bajo: si en el futuro hubiera más bodegas, se agregaría el parámetro. | RF-02 |

## Plantilla para nuevas desviaciones

```
| D-NN | AAAA-MM-DD | Adición/Interpretación/Tecnología/Omisión | Qué cambia | Por qué (cita al DEDS/RF) | Impacto | RF/RNF |
```
