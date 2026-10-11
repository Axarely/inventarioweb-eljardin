"""
Módulo de Autenticación (DEDS 3.2) — RF-01, RF-18.

Fase 1: login y logout de Django con plantillas propias. El RBAC por rol, el menú
filtrado y el bloqueo por intentos fallidos se implementan en el Sprint 1.
"""
from django.contrib.auth import views as auth_views


class IniciarSesionView(auth_views.LoginView):  # RF-01
    template_name = "autenticacion/login.html"
    redirect_authenticated_user = True


class CerrarSesionView(auth_views.LogoutView):  # RF-18: solo por POST, invalida la sesión
    pass
