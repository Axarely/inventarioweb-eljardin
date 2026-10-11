from django import forms

from config.ui import FormularioBootstrapMixin

from .models import Proveedor


class ProveedorForm(FormularioBootstrapMixin, forms.ModelForm):  # RF-11
    class Meta:
        model = Proveedor
        fields = ["nombre", "contacto"]
