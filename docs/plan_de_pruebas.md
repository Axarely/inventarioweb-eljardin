# Plan de Pruebas — InventarioWeb El Jardín

**Curso:** Metodología y Diseño de Sistemas II · **Fase:** 1 (Preparación técnica y Plan de Pruebas)
**Base teórica:** Pressman, 7.ª ed., cap. 14 (conceptos de calidad) y cap. 17 (estrategias de prueba)
**Documento fuente:** [DEDS.pdf](DEDS.pdf), Capítulo 2 (SRS, IEEE 830) y Capítulo 3 (diseño, v1.1)

| Versión | Fecha | Cambios | Autor |
|---|---|---|---|
| 1.0 | 2026-10-11 | Versión inicial: estrategia, herramientas, ambiente, criterios de aceptación de los RF de prioridad Alta. | A. Escobar |

---

## 1. Introducción

### 1.1 Propósito
Este plan define **cómo se verificará y validará** InventarioWeb El Jardín antes de escribir el código de
producción: qué se prueba, en qué nivel, con qué herramientas, en qué ambiente y con qué criterio se
considera aceptado cada requerimiento crítico. Corresponde al Capítulo 1 del IIPD.

### 1.2 Alcance

**Dentro del alcance**
- Los 18 RF del DEDS 2.3. Los **8 de prioridad Alta** (RF-01, 02, 03, 04, 05, 06, 13, 16) tienen
  criterios de aceptación detallados en la sección 5.
- Los 8 RNF del DEDS 2.4, verificados en las pruebas de sistema (sección 2.4).
- Los tres patrones de diseño del DEDS 3.4 (Factory Method, Observer, Adapter), verificados en las
  pruebas de integración.
- Las decisiones de diseño de datos del DEDS 3.2: `Existencia` persistida, herencia
  `Ubicacion → Bodega/Sucursal`, unicidad `(producto, ubicacion)`.

**Fuera del alcance**
- Funciones que el DEDS 2.1.2 excluye: facturación, punto de venta, contabilidad y nómina.
- Recuperación de contraseña (no hay RF; ver [desviaciones.md](desviaciones.md) D-05).
- Envío real de SMS (`AdaptadorSMS` es un stub, D-08).
- Pruebas de carga a gran escala: el volumen del negocio es un bodeguero y dos encargados concurrentes
  (RNF-06). Se prueba concurrencia básica, no estrés.
- La infraestructura interna de Render y de PostgreSQL administrado.

### 1.3 Referencias
- DEDS v1.1 (§2.3 RF, §2.4 RNF, §2.6 casos de uso, §2.10 diagrama de estados, §3.2 componentes,
  §3.4 patrones, §3.5 seguridad).
- Pressman (2010), cap. 17 "Estrategias de prueba de software" y cap. 18–19.
- Documentación de pytest-django: https://pytest-django.readthedocs.io/

---

## 2. Estrategia de prueba (IIPD 1.1)

### 2.1 Enfoque general
Se sigue la estrategia en espiral de Pressman (cap. 17): se prueba **de lo pequeño a lo grande**,
empezando por las unidades (modelos y servicios), siguiendo con su integración entre módulos, después
el sistema completo contra RF y RNF, y por último la validación de aceptación contra los criterios del
DEDS 2.3.

| Nivel | Pregunta que responde | Base de diseño | Cuándo | Responsable |
|---|---|---|---|---|
| Unitaria | ¿Cada clase o método hace lo que dice el diseño? | Fig. 12 (clases de diseño), Fig. 8 (estados) | Sprint 1 y 2, junto con el código | Desarrolladora |
| Integración | ¿Los módulos colaboran como dice la Fig. 11? | Fig. 11 (componentes), §3.4 (patrones), Fig. 5–7 (secuencia) | Sprint 2 (Fase 3) | Desarrolladora |
| Sistema | ¿El sistema completo cumple RF y RNF de punta a punta? | §2.3, §2.4, §3.5 | Fase 4 | Desarrolladora |
| Aceptación | ¿El cliente aceptaría el RF según su criterio? | Columna "Criterio de aceptación" de la Tabla 6 | Fase 4 | Desarrolladora, con un usuario por rol simulado |

Todas las pruebas automatizadas se ejecutan **antes de cada commit** a `main`, como regresión. Una prueba
fallida bloquea el commit hasta corregirla o registrarla en la bitácora de defectos.

### 2.2 Pruebas unitarias
**Objeto:** modelos y servicios de cada app, aislados de las vistas.
**Técnicas:**
- *Caja negra:* partición de equivalencia y **análisis de valores límite** sobre cantidades y umbrales
  (cantidad = 0, negativa, decimal, igual al stock mínimo, igual a la existencia disponible).
- *Caja blanca:* cobertura de ramas en la lógica de decisión: `nivel()`, la validación de existencia
  suficiente, la decisión de crear o actualizar una alerta.
- *Transición de estados:* las transiciones de la Fig. 8 (Normal → Bajo → Agotado → Normal y Bajo → Bajo).

**Unidades principales y ejemplos:**

| Unidad | Qué se verifica | Ejemplo de caso |
|---|---|---|
| `Existencia.nivel()` | Devuelve `agotado` si cantidad == 0, `bajo` si cantidad < stock_minimo y `normal` en otro caso | stock_minimo = 10: 0 → agotado, 9.99 → bajo, 10 → normal |
| `Existencia.esta_bajo_umbral()` | True solo si cantidad < stock_minimo | Límite exacto: 10 con mínimo 10 → False |
| `Existencia.actualizar_cantidad(delta)` | Suma el delta, rechaza un resultado negativo y llama a `notificar_observadores()` | delta = −5 sobre 3 → error; con un observador simulado, se le notifica una vez |
| `EntradaInventario.aplicar()` | Suma la cantidad a la existencia de la bodega | Ver CP-RF02 |
| `SalidaInventario.aplicar()` | Resta en la bodega y suma en la sucursal | Ver CP-RF03 |
| `MovimientoInventario.anular(motivo)` | Revierte el efecto, marca `anulado`, exige motivo y no borra | Anular una entrada de 20 → existencia −20 y el registro sigue en el historial |
| `MovimientoInventarioFactory.crear(tipo, datos)` | Devuelve la subclase correcta y rechaza un tipo desconocido | `crear("entrada", …)` → `EntradaInventario` |
| `Producto` | `stock_minimo >= 0` y un producto inactivo no aparece en los formularios | stock_minimo = −1 → `ValidationError` |
| `Usuario` | Login por correo, correo único, contraseña con hash | Ya cubierto en `tests/test_humo.py` |

### 2.3 Pruebas de integración
**Estrategia:** incremental **ascendente** (bottom-up). Primero se integran los modelos de `inventario`
con sus servicios; después se conectan los observadores (`alertas`, `reportes`) y el adaptador de
notificación, y al final las vistas. No se usa integración "big bang".

| ID | Integración | Qué se verifica | Patrón / Figura |
|---|---|---|---|
| INT-01 | Vista → Factory → Movimiento | Las vistas de entrada y salida crean movimientos solo a través de `MovimientoInventarioFactory`, sin importar las subclases. | Factory Method, Fig. 22 |
| INT-02 | Inventario → Alertas | Una salida que deja la existencia bajo el umbral crea `AlertaInventario`, aunque `inventario` no importe `alertas`. Los observadores se registran en `AppConfig.ready()`. | Observer, Fig. 11 y 23 |
| INT-03 | Inventario → Reportes | `PanelIndicadoresService.actualizar()` se invoca en cada cambio de existencia y el panel muestra el dato nuevo. | Observer, Fig. 23 |
| INT-04 | Alertas → INotificador → SMTP | Ante "Agotado", `AlertaInventarioService` llama a `INotificador.enviar()` y el correo llega al buzón en memoria (`locmem`) con destinatarios = dueños activos. | Adapter, Fig. 24 |
| INT-05 | Inventario → Proveedores | Una entrada solo acepta proveedores activos, a través de la interfaz `IProveedores`. | Fig. 11 |
| INT-06 | Transaccionalidad | Si falla un paso dentro de `aplicar()`, por ejemplo una excepción simulada en la existencia destino, no queda ningún cambio parcial. | RNF-08, UC02 E2 |
| INT-07 | Concurrencia | Dos salidas simultáneas por el total disponible: solo una se aplica y la existencia nunca queda negativa (`select_for_update`). | RNF-06, RNF-08 |
| INT-08 | Desacoplamiento | Prueba estática: ningún módulo de `inventario/` contiene `import alertas` ni `import reportes`. | Corrección 1 del DEDS v1.1 |

### 2.4 Pruebas de sistema
**Objeto:** el sistema completo, a través de HTTP con el `Client` de Django, de punta a punta y por rol.
Se completan con verificaciones manuales en el ambiente de producción (Render).

**Funcionales de punta a punta:** un recorrido por rol según el prototipo de navegación (Fig. 20) y el
sitemap (Fig. 25):
- SIS-01 **Bodeguero:** login → registrar entrada → registrar salida a Santa Cruz → ver el historial → cerrar sesión.
- SIS-02 **Encargado (Santa Cruz):** login → consultar existencias (solo de Santa Cruz) → reportar consumo → reportar discrepancia → cerrar sesión.
- SIS-03 **Dueño:** login → dashboard → ver alerta generada en SIS-01 → marcarla atendida → CRUD de catálogo, usuarios y proveedores → exportar reporte → cerrar sesión.

**No funcionales (RNF del DEDS 2.4):**

| RNF | Cómo se verifica | Criterio de aprobación | Tipo |
|---|---|---|---|
| RNF-01 Rendimiento | Con un conjunto de datos representativo (≥ 200 productos × 3 ubicaciones, ≥ 5 000 movimientos), se mide el tiempo de respuesta de "Consultar existencias" y del dashboard, en local con el `Client` y en Render con las herramientas de desarrollo del navegador. Se usa `django_assert_max_num_queries` para detectar consultas N+1. | < 2 s por petición; número de consultas acotado e independiente del número de filas | Automatizada + manual |
| RNF-02 Seguridad | (a) Las contraseñas se guardan con hash `pbkdf2_sha256`. (b) Matriz rol × URL: cada URL protegida devuelve 403 o redirige para los roles no autorizados. (c) CSRF: un POST sin token devuelve 403 (`Client(enforce_csrf_checks=True)`). (d) Bloqueo temporal tras 5 intentos fallidos. (e) La sesión expira por inactividad. (f) En producción, `manage.py check --deploy` no da errores y `http://` redirige a `https://`. (g) No hay secretos en el repositorio. | Todos los puntos se cumplen | Automatizada + manual |
| RNF-03 Usabilidad | Checklist: se cuentan los pasos de "registrar entrada", "registrar salida" y "consultar existencias" desde el menú. | ≤ 3 pasos cada una | Manual |
| RNF-04 Disponibilidad | Monitoreo de la URL pública durante la Fase 4, con un monitor externo gratuito de disponibilidad. | ≥ 95 % del horario operativo medido | Manual (medición) |
| RNF-05 Mantenibilidad | Prueba de integración: se crea una **tercera sucursal** solo con datos (sin tocar código) y se registran salidas, existencias, alertas y su columna en reportes. | Funciona sin cambios de código | Automatizada |
| RNF-06 Escalabilidad | INT-07 (concurrencia), más una sesión manual con 3 navegadores simultáneos (bodeguero y 2 encargados). | Sin errores ni inconsistencias | Automatizada + manual |
| RNF-07 Portabilidad | Checklist de los 3 recorridos SIS en Chrome, Edge y Firefox (versiones actuales), en escritorio y en móvil (vista responsiva). | Sin defectos de presentación ni de función | Manual |
| RNF-08 Confiabilidad | INT-06 (rollback) e INT-07. | Ninguna existencia queda inconsistente | Automatizada |

### 2.5 Pruebas de aceptación
Validación (Pressman cap. 17, "pruebas de validación"): para cada RF se ejecuta su criterio de
aceptación de la Tabla 6 del DEDS y se guarda **evidencia**: captura de pantalla del sistema desplegado,
más la salida de pytest del test automatizado correspondiente. El resultado se registra en un checklist
(`docs/checklist_aceptacion.md`, Fase 4) con las columnas *RF · criterio · caso(s) · resultado
(Cumple / No cumple) · evidencia · fecha*. La aceptación se hace como prueba **alfa**: la desarrolladora
actúa cada rol con usuarios de prueba en Render, siguiendo los recorridos SIS-01 a SIS-03.

### 2.6 Regresión
- Toda la suite automatizada se ejecuta antes de cada commit (`pytest`) y antes de cada despliegue.
- Cada defecto corregido agrega **al menos una prueba** que lo reproduce, con nombre `test_rfXX_...` y una
  referencia al ID de la bitácora en el docstring.

---

## 3. Herramientas y ambiente de pruebas (IIPD 1.2)

### 3.1 Herramientas

| Herramienta | Versión | Uso |
|---|---|---|
| pytest | 9.1.1 | Ejecutor de pruebas, fixtures y marcadores (`humo`, `unitaria`, `integracion`, `sistema`) |
| pytest-django | 4.14.0 | Integración con Django: BD de prueba, `client`, `django_db`, `django_assert_max_num_queries`, `mailoutbox` |
| coverage / pytest-cov | 7.16.2 / 7.1.0 | Cobertura de líneas y ramas (configuración en `.coveragerc`) |
| `django.test.Client` | Django 5.2.18 | Peticiones HTTP simuladas para las pruebas de integración y de sistema |
| Backend de correo `locmem` | Django | Captura de los correos enviados (RF-16) sin un servidor SMTP real |
| `unittest.mock` | Python 3.12 | Dobles de prueba: un observador simulado y un `INotificador` que falla |
| `manage.py check --deploy` | Django | Verificación de la configuración de seguridad de producción |
| Navegadores Chrome / Edge / Firefox | Actuales | Pruebas manuales de sistema y aceptación (RNF-07) |

### 3.2 Ambientes

| Ambiente | Dónde | Base de datos | Correo | Uso |
|---|---|---|---|---|
| Desarrollo | Laptop Windows 11, Python 3.12.10 | PostgreSQL 16.15 local, base `inventarioweb` | Consola | Programación y pruebas manuales rápidas |
| Pruebas automatizadas | La misma máquina | PostgreSQL 16 local, base `test_inventarioweb`, que pytest-django crea y destruye en cada ejecución | `locmem` | Unitarias, integración y sistema automatizadas |
| Producción | Render (plan económico) | PostgreSQL 16 de Render | SMTP real | Pruebas de sistema manuales, aceptación, RNF-01/02/04/07 |

Las pruebas usan **el mismo motor (PostgreSQL 16)** que producción, no SQLite, para que
`select_for_update`, las restricciones de unicidad y las agregaciones se comporten igual (RNF-08).

### 3.3 Datos de prueba
Se definen fixtures de pytest en `conftest.py`, reutilizables y creados por cada prueba (sin datos
compartidos entre pruebas):
- **Ubicaciones:** "Bodega central" (Bodega), "Santa Cruz" y "Peña Blanca" (Sucursal).
- **Roles y usuarios:** un usuario por rol (dueño, bodeguero, encargado de Santa Cruz y de Peña Blanca).
- **Productos** tomados de los wireframes (Fig. 17): Aceite vegetal 1L, Pechuga de pollo (kg),
  Servilletas (paq.), etc., con un `stock_minimo` conocido.
- **Proveedores:** uno activo y uno inactivo.

### 3.4 Convenciones de trazabilidad
- Nombre de la prueba: `test_rfXX_<comportamiento>` o `test_rnfXX_<comportamiento>`, por ejemplo
  `test_rf03_salida_resta_bodega_y_suma_sucursal`.
- Las vistas y servicios llevan un comentario `# RF-XX`.
- Cada caso de la sección 5 tiene un ID `CP-RFXX-NN`, que se cita en el docstring de su prueba.

### 3.5 Ejecución
```powershell
pytest                         # suite completa
pytest -m unitaria             # solo un nivel
pytest -k rf03                 # solo un requerimiento
pytest --cov --cov-report=html # cobertura (htmlcov/index.html)
```

---

## 4. Criterios de entrada, salida y suspensión

| Criterio | Definición |
|---|---|
| **Entrada a un sprint** | El backlog del sprint está estimado y trazado ([backlog.md](backlog.md)); el ambiente pasa las pruebas de humo (`pytest -m humo`). |
| **Salida de pruebas unitarias (Sprint 1)** | 100 % de las pruebas pasan. **Meta** de cobertura: ≥ 80 % de líneas en `inventario` y `usuarios`. |
| **Salida de pruebas de integración (Sprint 2)** | INT-01 a INT-08 pasan. **Meta** de cobertura: ≥ 80 % de líneas en `inventario` y `alertas`, ≥ 70 % global. |
| **Salida de pruebas de sistema y aceptación (Fase 4)** | Todos los RF de prioridad Alta "Cumple". Ningún defecto Crítico o Alto abierto. Los RNF-01, 02, 03, 07 y 08 verificados. |
| **Suspensión** | Se suspende la ejecución si el ambiente falla (por ejemplo, la BD de pruebas no se crea) o si un defecto Crítico bloquea más del 30 % de los casos. Se reanuda cuando se corrige. |

Las metas de cobertura son **objetivos**. El valor real se mide con `pytest --cov` en cada fase y se
reporta en el IIPD tal como salga.

---

## 5. Criterios de aceptación por requerimiento crítico (IIPD 1.3)

Para cada RF de prioridad Alta se transcribe el criterio del DEDS 2.3 (Tabla 6) y se derivan casos de
prueba verificables. Columnas: **ID** · **Nivel** (U = unitaria, I = integración, S = sistema) · **Escenario
(Dado / Cuando / Entonces)** · **Tipo** (+ positivo / − negativo / L límite) · **Prueba prevista**.

### RF-01 — Autenticación y acceso por rol
> **DEDS:** "Un usuario con credenciales válidas accede únicamente a las funciones permitidas para su rol;
> con credenciales inválidas, el acceso es rechazado."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF01-01 | S | Dado un bodeguero activo, cuando inicia sesión con correo y contraseña válidos, entonces entra y su menú muestra solo Inicio, Entradas, Salidas, Historial y Cerrar sesión. | + | `test_rf01_bodeguero_ve_solo_su_menu` |
| CP-RF01-02 | S | Ídem para el encargado (Inicio, Existencias, Reportar consumo, Reportar discrepancia, Cerrar sesión) y para el dueño (Dashboard, Alertas, Catálogo, Usuarios, Proveedores, Reportes, existencias e historial). | + | `test_rf01_menu_por_rol` (parametrizado) |
| CP-RF01-03 | S | Dado un usuario registrado, cuando envía una contraseña incorrecta, entonces no se crea sesión y se muestra un mensaje genérico, sin revelar si el correo existe. | − | `test_rf01_credenciales_invalidas_rechazadas` ✔ (humo) |
| CP-RF01-04 | S | Dado un usuario con `activo = False`, cuando envía credenciales correctas, entonces el acceso es rechazado. | − | `test_rf01_usuario_inactivo_no_inicia_sesion` ✔ (humo) |
| CP-RF01-05 | S | Dado un bodeguero autenticado, cuando solicita una URL del dueño (`/usuarios/`, `/alertas/`), entonces recibe 403. Se repite para cada par rol × URL no permitida (matriz RBAC). | − | `test_rf01_matriz_rbac` (parametrizado) |
| CP-RF01-06 | S | Dado un visitante sin sesión, cuando solicita cualquier URL protegida, entonces es redirigido al login. | − | `test_rf01_inicio_sin_sesion_redirige_a_login` ✔ (humo) |
| CP-RF01-07 | S | Dado un usuario, cuando falla 5 veces seguidas, entonces el 6.º intento, incluso con la contraseña correcta, se rechaza durante 15 minutos (DEDS 3.5). | − L | `test_rf01_bloqueo_tras_intentos_fallidos` |
| CP-RF01-08 | S | Dado un usuario autenticado, cuando pasan más de `SESSION_COOKIE_AGE` segundos sin actividad, entonces la siguiente petición lo envía al login. | − | `test_rnf02_sesion_expira_por_inactividad` |

### RF-02 — Registrar entrada a bodega
> **DEDS:** "Tras registrar una entrada válida, la existencia de la bodega aumenta exactamente en la
> cantidad ingresada."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF02-01 | U | Dada una existencia en bodega de 128 kg, cuando se aplica una entrada de 12.5 kg, entonces la existencia queda en 140.5 kg exactos (Decimal). | + | `test_rf02_entrada_suma_cantidad_exacta` |
| CP-RF02-02 | U | Dado un producto sin existencia previa en bodega, cuando se registra una entrada de 10, entonces se crea la `Existencia` con 10. | + | `test_rf02_entrada_crea_existencia_si_no_existe` |
| CP-RF02-03 | I | Cuando el bodeguero envía el formulario con producto, cantidad y proveedor activo, entonces se crea un `EntradaInventario` (por la Factory) con usuario y fecha, ligado al proveedor (RF-11), y aparece en el historial. | + | `test_rf02_formulario_entrada_registra_movimiento` |
| CP-RF02-04 | U | Cuando la cantidad es 0, negativa o no numérica, entonces el registro se rechaza y la existencia no cambia (UC02 E1). | − L | `test_rf02_cantidad_invalida_rechazada` (parametrizado: 0, −1, "abc") |
| CP-RF02-05 | I | Cuando el proveedor está inactivo o no se indica, entonces se rechaza (RF-11). | − | `test_rf02_requiere_proveedor_activo` |
| CP-RF02-06 | I | Cuando ocurre un error de BD después de crear el movimiento, entonces no queda ni movimiento ni cambio de existencia (UC02 E2, RNF-08). | − | `test_rf02_falla_no_deja_cambios_parciales` |
| CP-RF02-07 | S | Cuando un encargado o un dueño hace POST a la URL de entradas, entonces recibe 403. | − | `test_rf02_solo_bodeguero_registra_entrada` |

### RF-03 — Registrar salida de bodega a sucursal
> **DEDS:** "Tras registrar una salida válida, la existencia de la bodega disminuye y la de la sucursal
> destino aumenta en la cantidad enviada."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF03-01 | U | Dada una bodega con 18 kg y Santa Cruz con 5 kg, cuando se aplica una salida de 8 kg a Santa Cruz, entonces la bodega queda en 10 y Santa Cruz en 13. | + | `test_rf03_salida_resta_bodega_y_suma_sucursal` |
| CP-RF03-02 | U | Dada una sucursal sin existencia del producto, cuando recibe una salida, entonces se crea su `Existencia`. | + | `test_rf03_salida_crea_existencia_en_sucursal` |
| CP-RF03-03 | U | Dada una bodega con 12 kg, cuando se intenta enviar 15 kg, entonces se rechaza con el mensaje "Solo hay 12 … disponibles" (cantidad máxima sugerida, A1) y nada cambia (E1). | − | `test_rf03_existencia_insuficiente_rechaza_y_sugiere_maximo` |
| CP-RF03-04 | U | Dada una bodega con 12 kg, cuando se envían exactamente 12 kg, entonces la bodega queda en 0 (Agotado). | L | `test_rf03_salida_por_el_total_deja_agotado` |
| CP-RF03-05 | S | Dadas existencias en Santa Cruz y Peña Blanca, cuando se envía una salida a Peña Blanca, entonces solo cambia Peña Blanca y Santa Cruz queda igual (independencia, RF-04). | + | `test_rf03_solo_cambia_sucursal_destino` |
| CP-RF03-06 | I | Cuando dos salidas simultáneas piden el total disponible, entonces solo una se aplica y la existencia nunca es negativa. | − | `test_rf03_concurrencia_no_sobregira` (INT-07) |
| CP-RF03-07 | U | Cuando el destino no es una Sucursal o el origen no es la Bodega, entonces se rechaza. | − | `test_rf03_origen_bodega_destino_sucursal` |

### RF-04 — Existencias independientes por ubicación
> **DEDS:** "En todo momento, la existencia mostrada para una ubicación refleja la suma de sus
> movimientos de entrada y salida registrados."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF04-01 | I | Dada una secuencia aleatoria de entradas, salidas, consumos y anulaciones, cuando se compara cada `Existencia.cantidad` con la suma de los movimientos no anulados de esa ubicación, entonces coinciden. Es la invariante principal del sistema. | + | `test_rf04_existencia_igual_suma_de_movimientos` |
| CP-RF04-02 | U | Dados el mismo producto en las 3 ubicaciones, cuando cambia una, entonces las otras dos no cambian. | + | `test_rf04_ubicaciones_independientes` |
| CP-RF04-03 | U | Cuando se intenta crear una segunda `Existencia` para el mismo (producto, ubicación), entonces la BD lo rechaza (restricción de unicidad). | − | `test_rf04_existencia_unica_por_producto_ubicacion` |
| CP-RF04-04 | U | `nivel()` con stock_minimo = 10: cantidad 0 → agotado, 9.99 → bajo, 10 → normal, 50 → normal (Fig. 8). | L | `test_rf04_nivel_valores_limite` (parametrizado) |
| CP-RF04-05 | U | Cuando se anula un movimiento, entonces su efecto se revierte y la invariante CP-RF04-01 se mantiene (RF-15). | + | `test_rf04_anulacion_mantiene_invariante` |

### RF-05 — Consultar existencias de una sucursal
> **DEDS:** "El encargado de una sucursal visualiza únicamente las existencias correspondientes a su
> sucursal."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF05-01 | S | Dado un encargado de Santa Cruz, cuando abre "Existencias", entonces ve solo los productos de Santa Cruz, con cantidad y una pill de estado (color y texto). | + | `test_rf05_encargado_ve_solo_su_sucursal` |
| CP-RF05-02 | S | Dado un encargado de Santa Cruz, cuando manipula la URL o los parámetros para pedir Peña Blanca o la Bodega, entonces recibe 403 o 404 y nunca datos ajenos. | − | `test_rf05_encargado_no_ve_otra_ubicacion` |
| CP-RF05-03 | S | Dado un dueño, cuando consulta existencias, entonces puede elegir cualquier ubicación. | + | `test_rf05_dueno_consulta_cualquier_ubicacion` |
| CP-RF05-04 | S | Cuando se filtra por nombre o categoría, entonces solo aparecen los productos que coinciden (Fig. 17). | + | `test_rf05_filtros_nombre_y_categoria` |
| CP-RF05-05 | S | Dado un encargado sin sucursal asignada, cuando abre "Existencias", entonces ve un mensaje de error controlado, no una excepción (D-01). | − | `test_rf05_encargado_sin_sucursal` |
| CP-RF05-06 | S | Con el conjunto de datos de RNF-01, la página responde en < 2 s con un número de consultas acotado. | L | `test_rnf01_consulta_existencias_rapida` |

### RF-06 — Alerta automática bajo el stock mínimo
> **DEDS:** "Al registrarse un movimiento que deja la existencia bajo el umbral, se crea una alerta visible
> para los dueños en un plazo no mayor a la actualización inmediata de la existencia."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF06-01 | I | Dada Santa Cruz con 12 (mínimo 10), cuando un consumo la deja en 8, entonces en la **misma transacción** se crea una `AlertaInventario` *pendiente* con `nivel_detectado = bajo`. | + | `test_rf06_alerta_al_quedar_bajo_umbral` |
| CP-RF06-02 | I | Dada la bodega con 15 (mínimo 10), cuando una salida la deja en 0, entonces se crea una alerta con `nivel_detectado = agotado`. | + | `test_rf06_alerta_agotado_en_bodega` |
| CP-RF06-03 | I | Dada una alerta *pendiente* para esa existencia, cuando otro movimiento la baja más, entonces **no** se crea una segunda alerta: se actualizan `generada_en` y `nivel_detectado`. | − | `test_rf06_no_duplica_alerta_pendiente` |
| CP-RF06-04 | I | Cuando un movimiento deja la existencia ≥ stock mínimo, entonces no se crea alerta. | − L | `test_rf06_sin_alerta_si_queda_en_minimo` (cantidad final = 10) |
| CP-RF06-05 | I | Dada una alerta *atendida*, cuando la existencia vuelve a caer bajo el umbral, entonces se crea una alerta nueva. | + | `test_rf06_nueva_alerta_tras_atendida` |
| CP-RF06-06 | S | Dado un dueño, cuando abre "Alertas" después del movimiento, entonces la alerta aparece de inmediato y puede marcarla como atendida (UC05, paso 4). Bodeguero y encargado no acceden. | + − | `test_rf06_alerta_visible_y_atendible_por_dueno` |
| CP-RF06-07 | I | La alerta la crea `AlertaInventarioService` como observador: `inventario` no la crea directamente (INT-02, INT-08). | + | `test_rf06_alerta_generada_via_observer` |

### RF-13 — Reportar discrepancias
> **DEDS:** "Una discrepancia reportada queda registrada y asociada al movimiento correspondiente para su
> trazabilidad."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF13-01 | S | Dada una salida de 20 kg a Santa Cruz, cuando su encargado reporta haber recibido 18 kg, entonces se crea una `DiscrepanciaInventario` ligada a ese movimiento, con enviada = 20, recibida = 18, diferencia = −2, usuario y fecha. | + | `test_rf13_discrepancia_ligada_al_movimiento` |
| CP-RF13-02 | S | Cuando el encargado de Peña Blanca intenta reportar sobre una salida a Santa Cruz, entonces se rechaza (403). | − | `test_rf13_solo_movimientos_de_su_sucursal` |
| CP-RF13-03 | U | Cuando la cantidad recibida es negativa o no numérica, entonces se rechaza. Si recibida = enviada, también se rechaza, porque no hay discrepancia. | − L | `test_rf13_cantidad_recibida_valida` |
| CP-RF13-04 | U | Cuando se reporta sobre una entrada o un movimiento anulado, entonces se rechaza: solo aplica a salidas vigentes. | − | `test_rf13_solo_salidas_vigentes` |
| CP-RF13-05 | S | Dado un dueño, cuando consulta el historial del movimiento, entonces ve la discrepancia asociada. | + | `test_rf13_discrepancia_visible_en_historial` |
| CP-RF13-06 | U | Registrar la discrepancia **no** modifica existencias por sí solo: el DEDS solo exige trazabilidad. El ajuste, si corresponde, se hace con una anulación (RF-15). | + | `test_rf13_no_altera_existencias` |

### RF-16 — Notificar a los dueños ante un nivel crítico
> **DEDS:** "Ante una existencia en estado 'Agotado', los dueños reciben una notificación además de la
> alerta visible en el panel."

| ID | Nivel | Escenario | Tipo | Prueba prevista |
|---|---|---|---|---|
| CP-RF16-01 | I | Dados 2 dueños activos y 1 inactivo, cuando una existencia pasa a Agotado, entonces se envía 1 correo (`mailoutbox`) a los 2 dueños activos, con el producto, la ubicación y la fecha en el cuerpo. | + | `test_rf16_correo_a_duenos_al_agotarse` |
| CP-RF16-02 | I | Cuando la existencia pasa solo a "Bajo", entonces se crea la alerta (RF-06) pero **no** se envía correo. | − | `test_rf16_sin_correo_si_solo_bajo` |
| CP-RF16-03 | I | Dada una alerta *agotado* ya pendiente, cuando ocurre otro movimiento sobre esa existencia (sigue en 0), entonces no se envía un segundo correo. | − | `test_rf16_no_reenvia_si_alerta_pendiente` |
| CP-RF16-04 | I | Cuando el servidor SMTP falla (`INotificador` simulado que lanza una excepción), entonces el movimiento y la alerta **sí** se guardan y el error queda en el log: la notificación no revierte la operación. | − | `test_rf16_fallo_smtp_no_revierte_movimiento` |
| CP-RF16-05 | U | `AlertaInventarioService` depende solo de `INotificador`: con `AdaptadorSMS` (stub) en lugar del de correo, el servicio funciona sin modificarse (Adapter, Fig. 24). | + | `test_rf16_notificador_intercambiable` |
| CP-RF16-06 | Manual | En Render, con SMTP real, provocar un Agotado y comprobar que el correo llega al buzón de un dueño de prueba. Se guarda una captura como evidencia. | + | Checklist de aceptación |

Los ✔ marcan pruebas que **ya existen** en `tests/test_humo.py` y pasan desde la Fase 1.

### 5.1 RF de prioridad Media y Baja
Para RF-07 a RF-12, RF-14, RF-15, RF-17 y RF-18 se usa directamente el criterio de la Tabla 6 del DEDS
como caso de aceptación, con al menos un caso positivo y uno negativo automatizados por RF. Se detallan en
el backlog del sprint correspondiente. RF-18 ya tiene `test_rf18_logout_invalida_sesion` ✔.

---

## 6. Matriz de trazabilidad

| RF/RNF | Prioridad | Módulo (app) | Casos | Niveles | Sprint |
|---|---|---|---|---|---|
| RF-01 | Alta | autenticacion, usuarios | CP-RF01-01…08 | S | 1 |
| RF-02 | Alta | inventario, proveedores | CP-RF02-01…07, INT-01, INT-05 | U, I, S | 1 (básico), 2 (Factory) |
| RF-03 | Alta | inventario | CP-RF03-01…07, INT-07 | U, I, S | 1 (básico), 2 (Factory) |
| RF-04 | Alta | inventario | CP-RF04-01…05 | U, I | 1 |
| RF-05 | Alta | inventario | CP-RF05-01…06 | S | 1 |
| RF-06 | Alta | alertas | CP-RF06-01…07, INT-02 | I, S | 2 |
| RF-13 | Alta | inventario | CP-RF13-01…06 | U, S | 2 |
| RF-16 | Alta | alertas | CP-RF16-01…06, INT-04 | U, I, manual | 2 |
| RNF-01 | — | inventario, reportes | CP-RF05-06, sistema | S | 2 / Fase 4 |
| RNF-02 | — | autenticacion, config | CP-RF01-05…08, sistema | S | 1 / Fase 4 |
| RNF-05 | — | todas | sistema (3.ª sucursal) | I | Fase 4 |
| RNF-06 / 08 | — | inventario | INT-06, INT-07 | I | 2 |

---

## 7. Gestión de defectos

Los defectos encontrados desde el Sprint 2 se registran en `docs/bitacora_defectos.md` (Fase 3) con:
*ID · fecha · RF/RNF · descripción · pasos para reproducir · severidad · causa raíz · corrección (commit)
· prueba de regresión · estado*.

| Severidad | Definición | Ejemplo en este sistema | Plazo de cierre |
|---|---|---|---|
| **Crítica** | Corrompe o pierde datos de inventario, rompe la seguridad o deja el sistema inaccesible | La existencia queda negativa; un encargado ve otra sucursal; login caído | Antes de continuar con cualquier otra tarea |
| **Alta** | Un RF de prioridad Alta no cumple su criterio y no hay alternativa | No se genera la alerta al quedar bajo el umbral; no llega el correo de Agotado | Dentro del sprint |
| **Media** | Un RF Media/Baja falla, o un RF Alta falla con alternativa | Filtro de reportes por fecha incorrecto; exportación con columnas desordenadas | Antes de la Fase 4 |
| **Baja** | Cosmético o de usabilidad sin efecto funcional | Texto mal alineado; pill sin el color de la guía | Si hay tiempo |

Estados: *Abierto → En corrección → Corregido (con prueba de regresión) → Verificado → Cerrado*.

---

## 8. Riesgos del proceso de prueba

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Diferencias de comportamiento entre la BD local y la de Render | Medio | Mismo motor y versión mayor (PostgreSQL 16) en todos los ambientes; nunca SQLite. |
| Las pruebas de concurrencia son intermitentes (*flaky*) | Medio | `transactional_db` y sincronización explícita con `threading.Barrier`. Si aun así fallan de forma intermitente, se registra como defecto y se verifica de forma manual. |
| Rendimiento de Render en plan económico (arranque en frío) | Medio | Medir RNF-01 con el servicio "caliente" y documentar aparte el tiempo de arranque. |
| Una sola persona prueba su propio código (sesgo) | Medio | Casos derivados del DEDS **antes** de codificar (este plan) y la revisión de código formal de la Fase 2. |
| El tiempo del calendario se reduce y las pruebas manuales quedan al final | Alto | Se automatiza todo lo posible desde el Sprint 1 y se deja solo RNF-03/04/07 y CP-RF16-06 como manuales. |

---

## 9. Cronograma de pruebas

| Fase de la consigna | Actividad de prueba | Entregable |
|---|---|---|
| Fase 1 | Este plan; ambiente funcionando y pruebas de humo | `plan_de_pruebas.md`, `tests/test_humo.py` |
| Fase 2 — Sprint 1 | Unitarias de RF-01…05; matriz RBAC; revisión de código formal | Pruebas `test_rf0X_*`, informe de cobertura, acta de revisión |
| Fase 3 — Sprint 2 | Integración INT-01…08; RF-06, 13, 16; bitácora de defectos | Pruebas de integración, `bitacora_defectos.md` |
| Fase 4 | Sistema SIS-01…03, RNF, aceptación con evidencia en Render | `checklist_aceptacion.md`, capturas, registro de pytest |
