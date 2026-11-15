#!/usr/bin/env bash
# Build de Render (docs/manual_despliegue.md). Se ejecuta en cada despliegue.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input   # también sincroniza los roles base (post_migrate)
python manage.py carga_inicial         # D-44: catálogo real del restaurante; solo actúa la primera vez

# El plan gratuito de Render no ofrece consola (Shell), así que la carga inicial se hace aquí,
# solo si se definieron las variables. Ambos comandos son idempotentes.
if [[ -n "${DEMO_PASSWORD:-}" ]]; then
  python manage.py seed_demo
fi
if [[ -n "${DJANGO_SUPERUSER_CORREO:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --no-input || echo "El superusuario ya existe; se omite."
fi
