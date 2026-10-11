"""
Configuración común de InventarioWeb El Jardín (DEDS 3.1).

Los secretos y la conexión a PostgreSQL se leen SIEMPRE de variables de entorno
(o de un archivo .env en desarrollo). Ver .env.example.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Módulos del DEDS 3.2 (una app por módulo)
    "autenticacion",
    "usuarios",
    "proveedores",
    "inventario",
    "alertas",
    "reportes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",  # RNF-02: protección CSRF
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "autenticacion.menu.menu",  # RF-01: menú filtrado por rol
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL 16 (DEDS 3.1). Formato: postgres://usuario:clave@host:5432/bd
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = False  # las transacciones se declaran en los servicios (RNF-08)

# RF-01 / RNF-02: usuario propio, login por correo, contraseñas con hash (PBKDF2 por defecto)
AUTH_USER_MODEL = "usuarios.Usuario"
AUTHENTICATION_BACKENDS = ["autenticacion.backends.RolBackend"]  # RBAC: permisos del Rol
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "autenticacion:login"
LOGIN_REDIRECT_URL = "inicio"
LOGOUT_REDIRECT_URL = "autenticacion:login"

# RNF-02 (DEDS 3.5): bloqueo temporal tras intentos fallidos consecutivos
LOGIN_MAX_INTENTOS = env.int("LOGIN_MAX_INTENTOS", default=5)
LOGIN_BLOQUEO_MINUTOS = env.int("LOGIN_BLOQUEO_MINUTOS", default=15)

from django.contrib.messages import constants as mensajes  # noqa: E402

MESSAGE_TAGS = {mensajes.ERROR: "danger"}

# RNF-02 (DEDS 3.5): sesión con expiración por inactividad. Cada petición renueva el plazo.
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=30 * 60)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Tegucigalpa"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Notificaciones por correo SMTP (DEDS 3.1, RF-16). Credenciales solo por entorno.
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="InventarioWeb El Jardín <no-reply@localhost>")
