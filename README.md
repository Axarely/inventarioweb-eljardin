# InventarioWeb El Jardín

Sistema web de control de inventario para la bodega central y las sucursales Santa Cruz y
Peña Blanca del restaurante El Jardín. Proyecto final de Metodología y Diseño de Sistemas II
(UNADECA, 2026). El diseño completo está en [docs/DEDS.pdf](docs/DEDS.pdf).

**Stack (DEDS 3.1):** Python 3.12 · Django 5.2 · PostgreSQL 16 · plantillas Django + Bootstrap 5 +
Chart.js · gunicorn · Render · correo SMTP. **Pruebas:** pytest + pytest-django + coverage.

## Requisitos

- Python 3.12
- PostgreSQL 16, con un usuario que tenga permiso `CREATEDB` (pytest crea la base `test_<nombre>`)
- Git

## Puesta en marcha (Windows / PowerShell)

```powershell
# 1. Entorno virtual y dependencias
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Base de datos (una sola vez, como superusuario postgres)
psql -U postgres -h localhost -c "CREATE ROLE inventarioweb LOGIN CREATEDB PASSWORD 'tu-clave';"
psql -U postgres -h localhost -c "CREATE DATABASE inventarioweb OWNER inventarioweb;"

# 3. Variables de entorno
Copy-Item .env.example .env
#    editar .env: SECRET_KEY y DATABASE_URL=postgres://inventarioweb:tu-clave@localhost:5432/inventarioweb

# 4. Migraciones y usuario administrador
python manage.py migrate
python manage.py createsuperuser

# 5. Servidor de desarrollo -> http://127.0.0.1:8000/
python manage.py runserver
```

En Linux/macOS es igual, salvo que se activa con `source .venv/bin/activate` y se copia con `cp`.

## Pruebas

```powershell
pytest                       # todas las pruebas
pytest -m humo               # solo pruebas de humo del entorno
pytest --cov                 # con cobertura (configuración en .coveragerc)
pytest --cov --cov-report=html   # informe navegable en htmlcov/
```

Los tests se nombran `test_rfXX_...` para trazarlos al requerimiento. La estrategia completa está
en [docs/plan_de_pruebas.md](docs/plan_de_pruebas.md).

## Configuración

| Archivo | Uso |
|---|---|
| `config/settings/base.py` | Común: apps, PostgreSQL por `DATABASE_URL`, auth por correo, sesión por inactividad |
| `config/settings/dev.py` | Desarrollo (`manage.py` lo usa por defecto): DEBUG, correo en consola |
| `config/settings/prod.py` | Producción en Render (`wsgi.py` lo usa): HTTPS, HSTS, cookies seguras, SMTP |

Los secretos van **solo** en variables de entorno (`.env` en local, panel de Render en producción).
`.env` no se versiona.

## Estructura

```
config/          proyecto Django (settings base/dev/prod, urls, wsgi)
autenticacion/   Módulo de Autenticación        RF-01, RF-18
usuarios/        Módulo de Usuarios y Roles      RF-09, RF-10 (usuarios, roles y catálogo de productos)
proveedores/     Módulo de Proveedores           RF-11
inventario/      Módulo de Inventario (sujeto Observer)   RF-02..05, RF-12, RF-13, RF-15
alertas/         Módulo de Alertas (observador)           RF-06, RF-16
reportes/        Módulo de Reportes (observador)          RF-07, RF-08, RF-14, RF-17
templates/       plantillas comunes (base.html)
static/          CSS (guía de estilo, DEDS Fig. 21)
tests/           pruebas transversales (humo)
docs/            DEDS, consigna, plan de pruebas, backlog, ajustes, desviaciones, registro de tiempo
```

## Documentación del proyecto

- [docs/plan_de_pruebas.md](docs/plan_de_pruebas.md): estrategia, herramientas y criterios de aceptación
- [docs/backlog.md](docs/backlog.md): backlog de los Sprints 1 y 2
- [docs/ajustes_deds.md](docs/ajustes_deds.md): correcciones de la Fase 3 incorporadas en el DEDS
- [docs/desviaciones.md](docs/desviaciones.md): ajustes menores respecto al diseño
- [docs/registro_tiempo.md](docs/registro_tiempo.md): horas reales invertidas
