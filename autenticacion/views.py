"""
Módulo de Autenticación (DEDS 3.2) — RF-01, RF-18, RNF-02.
"""
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from usuarios.forms import RegistroForm

from .forms import IniciarSesionForm


class IniciarSesionView(auth_views.LoginView):  # RF-01
    template_name = "autenticacion/login.html"
    authentication_form = IniciarSesionForm
    redirect_authenticated_user = True


class CerrarSesionView(auth_views.LogoutView):  # RF-18: solo por POST, invalida la sesión
    """La sesión solo se cierra por POST (protección CSRF). DEF-16: si el navegador ABRE /logout/ (recargar,
    «Atrás», historial), en vez del error 405 se muestra la confirmación o, sin sesión, el inicio de sesión."""

    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("autenticacion:login")
        return render(request, "autenticacion/cerrar_sesion.html")


class RegistroView(CreateView):  # D-31: solicitud de cuenta, pendiente de aprobación de un dueño
    template_name = "autenticacion/registro.html"
    form_class = RegistroForm
    success_url = reverse_lazy("autenticacion:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("inicio")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(
            self.request,
            "Solicitud enviada. Un dueño debe aprobar su cuenta y asignarle un rol antes de que pueda entrar.",
        )
        return respuesta


class InicioView(LoginRequiredMixin, TemplateView):  # RF-01: página de inicio según el rol
    template_name = "inicio.html"

    def get(self, request, *args, **kwargs):
        # Fig. 20: el Dueño entra directamente a su Panel de indicadores.
        if request.user.has_perm("reportes.ver_dashboard"):
            return redirect("reportes:dashboard")
        return super().get(request, *args, **kwargs)
