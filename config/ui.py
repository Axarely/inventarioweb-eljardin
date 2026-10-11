"""Utilidades de presentación compartidas por las apps (guía de estilo, DEDS Fig. 21)."""
from django import forms
from django.utils.http import url_has_allowed_host_and_scheme


class FormularioBootstrapMixin:
    """Aplica las clases de Bootstrap 5 a los widgets del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                continue
            if isinstance(widget, forms.CheckboxInput):
                clase = "form-check-input"
            elif isinstance(widget, forms.Select):
                clase = "form-select"
            else:
                clase = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {clase}".strip()


class FormularioMixin:
    """Contexto común de la plantilla genérica templates/formulario.html."""

    template_name = "formulario.html"
    titulo = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["titulo"] = self.titulo
        contexto["url_cancelar"] = self.get_url_cancelar()
        return contexto

    def get_url_cancelar(self):
        # En un CreateView sin guardar, get_success_url() falla porque self.object es None.
        if getattr(self, "success_url", None):
            return str(self.success_url)
        return self.get_success_url()


def siguiente_seguro(request, por_defecto):
    """Devuelve el parámetro `next` solo si apunta a este mismo sitio (evita redirecciones abiertas)."""
    destino = request.POST.get("next") or request.GET.get("next")
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return destino
    return por_defecto
