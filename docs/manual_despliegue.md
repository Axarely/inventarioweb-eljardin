# Manual de despliegue en Render

**Proyecto:** InventarioWeb El Jardín · **Corresponde a:** IIPD 4.1 y 4.2 · **Diagrama:** DEDS Fig. 10

## 1. Arquitectura desplegada

```
Navegador ──HTTPS──▶ Proxy de Render (TLS) ──HTTP──▶ Gunicorn (2 workers) ──▶ Django (config.settings.prod)
                                                                              ├─▶ PostgreSQL 16 (Render)
                                                                              └─▶ Servidor SMTP (correo, RF-16)
Estáticos: WhiteNoise, dentro del mismo proceso.
```

Respecto a la Fig. 10, el proxy de Render y WhiteNoise **reemplazan a Nginx** (desviación D-06). Los nodos
del diagrama se mantienen: cliente, servidor de aplicación, base de datos y servicio externo de correo.

| Archivo | Para qué sirve |
|---|---|
| `render.yaml` | Blueprint: crea el servicio web y la BD PostgreSQL 16, y declara las variables de entorno. |
| `build.sh` | Se ejecuta en cada despliegue: instala dependencias, `collectstatic`, `migrate` (que crea los roles base) y, opcionalmente, la carga inicial. |
| `config/settings/prod.py` | `DEBUG=False`, HTTPS obligatorio, cookies `Secure`, HSTS, dominio de Render en `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`, conexiones persistentes, WhiteNoise. |
| `requirements.txt` | Versiones fijas, entre ellas `gunicorn`, `whitenoise` y `dj-database-url`. |

## 2. Requisitos previos

1. El repositorio actualizado en GitHub (`git push`), incluidos `render.yaml` y `build.sh`.
2. Una cuenta en https://render.com, conectada a GitHub (puede iniciar sesión con GitHub).
3. Para el correo (RF-16), una cuenta SMTP. Con Gmail: activar la verificación en dos pasos y crear una
   **contraseña de aplicación** en https://myaccount.google.com/apppasswords. **No** se usa la contraseña
   normal de la cuenta.

## 3. Crear los servicios con el Blueprint

1. En Render: **New → Blueprint**.
2. Elegir el repositorio `inventarioweb-eljardin`, rama `main`. Render detecta `render.yaml` y muestra dos
   recursos: `inventarioweb-db` (PostgreSQL 16) e `inventarioweb-eljardin` (servicio web).
3. Render pide las variables marcadas `sync: false`. Complételas:

| Variable | Valor | Obligatoria |
|---|---|---|
| `EMAIL_HOST` | `smtp.gmail.com` (o el de su proveedor) | Para RF-16 |
| `EMAIL_HOST_USER` | la cuenta de correo que envía | Para RF-16 |
| `EMAIL_HOST_PASSWORD` | la contraseña de aplicación | Para RF-16 |
| `DEFAULT_FROM_EMAIL` | `InventarioWeb El Jardín <la-cuenta@gmail.com>` | Para RF-16 |
| `DEMO_PASSWORD` | **Para uso real del restaurante, déjela VACÍA.** Si se define, crea usuarios, proveedores y movimientos de demostración que se mezclarían con los datos reales. | No |
| `DJANGO_SUPERUSER_CORREO` | **correo real de quien administrará el sistema** (dueño). Es la primera cuenta: con ella se aprueban los registros de los demás usuarios. | Sí, para uso real |
| `DJANGO_SUPERUSER_PASSWORD` | contraseña robusta del administrador | Solo si hay correo |

   `SECRET_KEY` la genera Render, y `DATABASE_URL` la conecta Render a la BD. **No** las escriba a mano.
4. Pulse **Apply**. Render crea la BD, ejecuta `./build.sh` y arranca
   `gunicorn config.wsgi:application --workers 2 --timeout 60`.
5. En **Logs** del servicio web, al final del build deben aparecer:
   - `XXX static files copied ... post-processed`
   - `Applying ... OK` (la primera vez)
   - `Carga inicial lista: 3 ubicaciones y NN productos.` (solo la primera vez, D-44: bodega, sucursales y
     catálogo real de `inventario/datos/catalogo_inicial.json`, con existencias en 0)
   - si definió `DEMO_PASSWORD`: `Datos demo listos: ...`
   - `Your service is live 🎉`
6. La URL pública aparece arriba, a la izquierda, por ejemplo `https://inventarioweb-eljardin.onrender.com`.
   **Anótela en el IIPD 4.1.** El dominio se agrega solo a `ALLOWED_HOSTS` mediante `RENDER_EXTERNAL_HOSTNAME`.

## 4. Verificación después del despliegue

| # | Comprobación | Resultado esperado |
|---|---|---|
| 1 | Abrir la URL con `http://` | Redirige a `https://` (RNF-02) |
| 2 | Iniciar sesión con `DJANGO_SUPERUSER_CORREO` y su contraseña | Entra al Dashboard; el Catálogo trae los productos reales y Existencias está vacío |
| 3 | F12 → Aplicación → Cookies | `sessionid` y `csrftoken` con la marca **Secure** |
| 4 | Con `encargado.santacruz@…`, reportar un consumo que agote un producto | Llega el correo "Producto agotado…" al buzón de `duena@eljardin.test`. **Ese buzón no existe:** para recibirlo de verdad, cree un dueño con su correo real desde Usuarios. |
| 5 | Medir tiempos (F12 → Red) en Existencias, Dashboard y Reportes | < 2 s con el servicio ya activo (RNF-01) |

Anote los resultados en `docs/pruebas_sistema.md`, sección 6.

## 5. Actualizar la aplicación

Cada `git push` a `main` vuelve a desplegar automáticamente (Auto-Deploy). `build.sh` aplica las
migraciones nuevas. Para desplegar a mano: servicio web → **Manual Deploy → Deploy latest commit**.

## 6. Reproducir el entorno local (desarrollo)

Ver el [README](../README.md): Python 3.12, PostgreSQL 16, `pip install -r requirements.txt`, `.env` a partir
de `.env.example`, `migrate`, `seed_demo`, `runserver`. Para revisar el modo producción en local:

```powershell
$env:DJANGO_SETTINGS_MODULE = "config.settings.prod"
python manage.py check --deploy          # solo debe quedar la advertencia W021 (HSTS preload)
python manage.py collectstatic --no-input
Remove-Item Env:DJANGO_SETTINGS_MODULE
```

Gunicorn no funciona en Windows; se prueba en Render, que corre en Linux.

## 7. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `Permission denied: ./build.sh` | `build.sh` perdió el permiso de ejecución | `git update-index --chmod=+x build.sh`, commit y push |
| `ImproperlyConfigured: Defina DATABASE_URL` | La BD no está enlazada | Revise que `DATABASE_URL` venga de `inventarioweb-db` (`fromDatabase`) |
| `Bad Request (400)` | El dominio no está en `ALLOWED_HOSTS` (dominio propio) | Agregue la variable `ALLOWED_HOSTS=sudominio.com` y `CSRF_TRUSTED_ORIGINS=https://sudominio.com` |
| `CSRF verification failed` al iniciar sesión | Igual que la anterior, con dominio propio | Ídem |
| No llegan correos | Credenciales SMTP o contraseña de aplicación incorrectas | Revise el log del servicio: `No se pudo notificar la alerta …`. El movimiento sí se guarda (D-22). |
| La primera carga tarda unos 50 s | Arranque en frío del plan gratuito | Esperado (sección 8) |

## 8. Riesgos del plan gratuito (D-28)

> Revise las condiciones vigentes en https://render.com/pricing antes de desplegar: pueden cambiar.

- **El servicio web se suspende** tras unos 15 minutos sin tráfico. La siguiente petición lo despierta en
  unos 50 s. **Antes de la demostración del 29/11**, abra la URL unos minutos antes.
- **La BD PostgreSQL gratuita vence a los 30 días** de creada; después se borra. Si despliega hoy, vencería
  **antes de la presentación final**. Opciones:
  1. Crear el Blueprint a mediados de noviembre (después del 30/10), o
  2. Cambiar la BD a un plan pago (Basic) durante el período de evaluación, o
  3. Recrearla a tiempo: `build.sh` vuelve a migrar y cargar la demostración.
- Para uso real del restaurante: servicio web **Starter** y BD **Basic** (sin suspensión, con respaldos).
