"""Utilidades de presentación compartidas por las apps (guía de estilo, DEDS Fig. 21)."""
from decimal import ROUND_HALF_UP, Decimal

from django import forms
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe


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


# De la frase más larga a la más corta: "tres cuartos" debe reemplazarse antes que "cuarto".
_FRACCIONES_EN_PALABRAS = {"tres cuartos": "3/4", "media": "1/2", "medio": "1/2", "cuarto": "1/4"}


def interpretar_cantidad(texto):
    """
    Cantidad escrita a mano (D-35): "1.5", "1,5", "1 1/2", "1 y 1/2", "1 y media", "1/2", "media".
    Devuelve un Decimal con 2 decimales o lanza ValueError.
    """
    limpio = " ".join(str(texto).strip().lower().replace(",", ".").split())
    for palabras, fraccion in _FRACCIONES_EN_PALABRAS.items():
        limpio = limpio.replace(palabras, fraccion)
    limpio = limpio.replace(" y ", " ")
    if not limpio:
        raise ValueError("vacío")
    total = Decimal("0")
    partes = limpio.split(" ")
    if len(partes) > 2:
        raise ValueError(texto)
    for parte in partes:
        if "/" in parte:
            numerador, _, denominador = parte.partition("/")
            if not denominador or Decimal(denominador) == 0:
                raise ValueError(texto)
            total += Decimal(numerador) / Decimal(denominador)
        else:
            total += Decimal(parte)
    if len(partes) == 2 and "/" not in partes[1]:
        raise ValueError(texto)  # "1 5" no es una cantidad válida
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CampoCantidad(forms.DecimalField):
    """
    D-35: cantidad que se ESCRIBE (sin flechas de subir y bajar). Acepta decimales con punto o coma y
    fracciones: libra y media = "1.5", "1,5", "1 1/2" o "1 y media".
    """

    AYUDA = "Escriba la cantidad: por ejemplo 1.5, 1,5 o 1 1/2 (libra y media)."

    def __init__(self, *args, placeholder="Ej.: 1.5 o 1 1/2", **kwargs):
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("decimal_places", 2)
        kwargs.setdefault("help_text", self.AYUDA)
        kwargs["widget"] = forms.TextInput(attrs={
            "inputmode": "decimal", "autocomplete": "off", "placeholder": placeholder, "data-cantidad": "1",
        })
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return interpretar_cantidad(value)
        except (ValueError, ArithmeticError):
            raise forms.ValidationError(
                "Escriba una cantidad válida, por ejemplo 1.5, 1,5 o 1 1/2.", code="invalid"
            )

    def widget_attrs(self, widget):
        # Sin min/max/step: el campo es de texto, no un control de subir y bajar.
        return {}


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


class TextoConSugerencias(forms.TextInput):
    """Campo de texto libre con sugerencias (<datalist>): se puede elegir una o escribir otra (D-45, D-46)."""

    def __init__(self, sugerencias=(), attrs=None):
        super().__init__(attrs)
        self.sugerencias = list(sugerencias)

    def render(self, name, value, attrs=None, renderer=None):
        lista = f"lista-{name}"
        attrs = {**(attrs or {}), "list": lista, "autocomplete": "off"}
        html = super().render(name, value, attrs, renderer)
        opciones = "".join(format_html('<option value="{}">', s) for s in self.sugerencias)
        return mark_safe(f'{html}<datalist id="{lista}">{opciones}</datalist>')
