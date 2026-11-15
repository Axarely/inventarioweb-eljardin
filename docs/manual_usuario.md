# Manual de usuario básico — InventarioWeb El Jardín

**Corresponde a:** IIPD 4.3 · Para: dueños, bodeguero y encargados de sucursal

## Solicitar una cuenta (primera vez)

1. En la pantalla de acceso pulse **Solicitar acceso**.
2. Escriba su nombre completo, su correo y una contraseña (dos veces). Pulse **Enviar solicitud**.
3. Espere a que un **dueño** apruebe su solicitud y le asigne su rol. Hasta entonces no podrá entrar.

## Entrar y salir

1. Abra la dirección del sistema en Chrome, Edge o Firefox (computadora o celular).
2. Escriba su **correo** y su **contraseña** y pulse **Entrar**.
3. A la izquierda verá el **menú** con las opciones de su rol. En el celular, ábralo con el botón ☰.
4. Para salir, pulse **Cerrar sesión** al final del menú.

- Si se equivoca 5 veces seguidas con la contraseña, la cuenta se bloquea **15 minutos**.
- **Cantidades:** se escriben directamente. Para libra y media puede escribir `1.5`, `1,5`, `1 1/2` o
  `1 y media`.
- Si pasan 30 minutos sin usar el sistema, tendrá que volver a entrar.
- ¿Olvidó la contraseña? Pídale a un dueño que la restablezca desde **Usuarios → Contraseña**.

Los estados de existencia se muestran siempre con color **y** texto: **Normal** (verde), **Bajo** (ámbar,
por debajo del stock mínimo) y **Agotado** (rojo).

## Bodeguero

**Registrar una entrada de mercadería**
1. Menú → **Entradas**.
2. Elija el producto. A la derecha verá cuánto hay ahora en bodega.
3. Escriba la cantidad recibida y elija el proveedor. Pulse **Registrar entrada**.
4. Un mensaje verde confirma la entrada y muestra la nueva existencia en bodega.

Si el producto no está en la lista, use el enlace **Crear producto**: al guardarlo vuelve al formulario.
Si tampoco existe su categoría, escríbala en el campo **«¿No existe la categoría? Agréguela aquí»**.

**Proteínas: registrar la merma (dos pasos)**

Las proteínas que se limpian o preparan en producción (alitas, pechuga, tortas de res y de cerdo, camarón,
langosta, filete) se registran en **libras** y en dos pasos:
1. **Cuando llega el proveedor:** Menú → **Entradas**, con el peso que entregó (por ejemplo, 10 lb de alitas).
   El panel le recuerda que el producto controla merma.
2. **Cuando producción termina de limpiar:** Menú → **Entradas**, abajo en **Pendientes de peso real**, escriba
   el **peso real** que quedó (por ejemplo, 8 lb) y pulse **Registrar**. El sistema descuenta la merma (2 lb) de la bodega y muestra
   el rendimiento (80 %).

Los paquetes de res y de cerdo van por **unidad** y en una sola entrada. Si se equivocó con el peso real,
anule la merma en el **Historial** y vuelva a registrarlo.

**Productos que vienen en cajas o paquetes**

Algunos productos se cuentan por **unidad** pero llegan en **cajas o paquetes** (por ejemplo, el queso Sula
viene en paquetes de 16, la leche entera en cajas de 24 y el queso mozzarella rallado en bolsas de 5 lb). Al elegirlos aparece **«Registrar en»**: escoja **Unidades** o **Paquetes**. Si
registra 2 paquetes de queso Sula, el sistema suma 32 unidades. Las existencias muestran las dos cosas:
"32 unidades = 2 paquetes".

**Enviar mercadería a una sucursal**
1. Menú → **Salidas**.
2. Elija la sucursal, el producto y la cantidad. El panel derecho avisa si alcanza o no.
3. Pulse **Registrar salida**. Si no hay suficiente, el sistema indica el máximo disponible; pulse
   **Usar …** para cargar esa cantidad.

**Corregir un error**
Menú → **Historial**, busque el movimiento y elija:
- **Anular**: deshace el movimiento. Hay que escribir el motivo.
- **Corregir**: cambia la cantidad. El original queda anulado con su motivo y se registra uno nuevo.

Los movimientos nunca se borran: quedan en el historial marcados como "Anulado".

## Encargado de sucursal

- **Existencias:** muestra solo los productos de **su** sucursal, con buscador y filtro por categoría.
- **Reportar consumo:** registre lo que la sucursal gastó (producto y cantidad). Se descuenta de su
  existencia.
- **Reportar discrepancia:** si un envío de la bodega llegó incompleto o con más de lo indicado, elija el
  envío y escriba la cantidad que recibió de verdad. Queda registrado para que el dueño lo revise.

## Dueño

- **Dashboard:** consumo de cada sucursal, comparativo Santa Cruz vs. Peña Blanca, alertas activas. Filtre
  por sucursal, producto y fechas. Con un producto elegido verá también el total y la evolución diaria.
  Los datos están siempre al día; no hace falta recargar nada a mano.
- **Alertas:** productos en estado Bajo o Agotado. Cuando gestione la reposición, pulse
  **Marcar atendida**. Si un producto se **agota**, además le llega un **correo**.
- **Existencias:** elija cualquier ubicación (bodega o sucursales).
- **Catálogo:** cree, edite y active o desactive productos. El stock mínimo define cuándo se genera una
  alerta.
- **Presentación (cajas o paquetes):** al editar un producto indique si llega en **caja** o **paquete** y
  **cuántas unidades trae**. Si falta ese número (la lista muestra «Falta definir»), el producto solo se
  puede registrar en unidades.
- **Controla merma:** la casilla solo aparece (y solo se puede activar) en productos de **Proteínas**.
- **Categorías** (botón en Catálogo): hay 9 fijas (Proteínas, Lácteos, Congelados, Concentrados, Abarrotes,
  Latas y aderezos, Verduras, Desechables y limpieza, Varios). Si necesita otra, escríbala en
  **«¿No existe la categoría? Agréguela aquí»** al crear o editar un producto, o en la página Categorías.
  Las categorías agregadas se pueden **eliminar** si ningún producto las usa; las fijas no.
  Si intenta agregar una que ya existe, aunque la escriba sin tilde o en singular ("proteina"), el sistema
  avisa **«La categoría Proteínas ya existe»** y no la duplica.
- **Usuarios:** cree usuarios con su rol; los encargados necesitan una sucursal. Edítelos, desactívelos o
  restablezca su contraseña.
- **Solicitudes de acceso:** el número junto a **Usuarios** indica cuántas personas pidieron una cuenta.
  En Usuarios → **Solicitudes de acceso** pulse **Aprobar**, elija el rol (y la sucursal si es encargado) y
  guarde; o **Rechazar** si no corresponde.
- **Roles:** los tres roles base son fijos. Puede crear roles adicionales eligiendo sus permisos.
- **Proveedores:** alta, edición y activar o desactivar.
- **Reportes:** consumo por sucursal y producto, existencias actuales o **Merma** (control interno de
  proteínas: cuánto entregó cada proveedor, cuánto quedó, la merma y el rendimiento %). Use **Exportar a Excel** o
  **Exportar a PDF**: el archivo contiene lo mismo que la pantalla.
- **Historial:** todos los movimientos, con quién los registró, anulaciones y discrepancias.
