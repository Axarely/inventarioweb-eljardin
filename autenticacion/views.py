"""
Módulo de Autenticación (DEDS 3.2) — RF-01, RF-18, RNF-02.
"""
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from .forms import IniciarSesionForm


class IniciarSesionView(auth_views.LoginView):  # RF-01
    template_name = "autenticacion/login.html"
    authentication_form = IniciarSesionForm
    redirect_authenticated_user = True


class CerrarSesionView(auth_views.LogoutView):  # RF-18: solo por POST, invalida la sesión
    pass


class InicioView(LoginRequiredMixin, TemplateView):  # RF-01: página de inicio según el rol
    template_name = "inicio.html"

    def get(self, request, *args, **kwargs):
        # Fig. 20: el Dueño entra directamente a su Panel de indicadores.
        if request.user.has_perm("reportes.ver_dashboard"):
            return redirect("reportes:dashboard")
        return super().get(request, *args, **kwargs)
