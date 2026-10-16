"""Configuración de producción (Render, DEDS 3.1 y Fig. 10)."""
import os

from .base import *  # noqa: F401,F403
from .base import ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DATABASES, env

DEBUG = False

# Render publica el dominio del servicio en RENDER_EXTERNAL_HOSTNAME (p. ej. inventarioweb.onrender.com).
_dominio_render = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _dominio_render:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _dominio_render]
    CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, f"https://{_dominio_render}"]

# Conexiones persistentes a PostgreSQL (menos latencia por petición, RNF-01).
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)

# RNF-02: toda comunicación por HTTPS. Render termina TLS en su proxy (sustituye a Nginx, D-06)
# y reenvía el esquema original en este encabezado.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# WhiteNoise sirve los estáticos comprimidos y con hash en el nombre (sustituye a Nginx, D-06).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": "WARNING"},
    "loggers": {
        "django.request": {"handlers": ["consola"], "level": "ERROR", "propagate": False},
        "alertas": {"handlers": ["consola"], "level": "INFO", "propagate": False},
    },
}
