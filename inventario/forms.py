from decimal import Decimal

from django import forms

from config.ui import FormularioBootstrapMixin
from proveedores.servicios import proveedores_activos
from usuarios.models import Producto

from .models import Sucursal


def _campo_producto():
    # RF-09: solo los productos activos están disponibles en los formularios.
    return forms.ModelChoiceField(
        label="Producto", queryset=Producto.objects.filter(activo=True), empty_label="Seleccionar producto…"
    )


def _campo_cantidad(etiqueta):
    # UC02/UC03 E1: cantidad numérica y positiva.
    return forms.DecimalField(
        label=etiqueta, max_digits=10, decimal_places=2, min_value=Decimal("0.01"),
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0.01", "placeholder": "0.00"}),
    )


class EntradaForm(FormularioBootstrapMixin, forms.Form):  # RF-02, RF-11 (Fig. 15)
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad recibida")
    proveedor = forms.ModelChoiceField(label="Proveedor", queryset=None, empty_label="Seleccionar proveedor…")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor"].queryset = proveedores_activos()


class SalidaForm(FormularioBootstrapMixin, forms.Form):  # RF-03 (Fig. 16)
    sucursal = forms.ModelChoiceField(
        label="Sucursal destino", queryset=Sucursal.objects.all(), empty_label="Seleccionar sucursal…"
    )
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad a enviar")
