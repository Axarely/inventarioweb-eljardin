"""Configuración de desarrollo local."""
from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1"]  # noqa: F405

# WhiteNoise sirve los estáticos desde las apps sin necesidad de collectstatic.
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True

# En desarrollo los correos se imprimen en consola en lugar de enviarse.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
