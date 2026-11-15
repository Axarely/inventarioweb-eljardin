from decimal import Decimal

from django import forms

from config.ui import CampoCantidad, FormularioBootstrapMixin
from proveedores.servicios import proveedores_activos
from usuarios.models import Producto

from .excepciones import formatear_cantidad
from .models import Sucursal


def _campo_producto():
    # RF-09: solo los productos activos están disponibles en los formularios.
    return forms.ModelChoiceField(
        label="Producto", queryset=Producto.objects.filter(activo=True), empty_label="Seleccionar producto…"
    )


def _campo_cantidad(etiqueta):
    # UC02/UC03 E1: cantidad numérica y positiva. D-35: se escribe (1.5, 1,5, 1 1/2), sin flechas.
    return CampoCantidad(label=etiqueta, min_value=Decimal("0.01"))


class EntradaForm(FormularioBootstrapMixin, forms.Form):  # RF-02, RF-11 (Fig. 15)
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad recibida")
    proveedor = forms.ModelChoiceField(label="Proveedor", queryset=None, empty_label="Seleccionar proveedor…")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor"].queryset = proveedores_activos()


class PesoRealForm(FormularioBootstrapMixin, forms.Form):  # D-33: segunda entrada de proteínas
    control = forms.IntegerField(widget=forms.HiddenInput)
    peso_real = CampoCantidad(label="Peso real", min_value=Decimal("0"))


class ConsumoForm(FormularioBootstrapMixin, forms.Form):  # RF-07 (D-02): consumo de la sucursal
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad consumida")


class DiscrepanciaForm(FormularioBootstrapMixin, forms.Form):  # RF-13
    movimiento = forms.ModelChoiceField(label="Envío recibido", queryset=None, empty_label="Seleccionar envío…")
    cantidad_recibida = CampoCantidad(label="Cantidad realmente recibida", min_value=Decimal("0"))

    def __init__(self, *args, envios=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["movimiento"].queryset = envios
        self.fields["movimiento"].label_from_instance = lambda m: (
            f"{m.fecha:%d/%m/%Y %H:%M} · {m.producto} · enviado {formatear_cantidad(m.cantidad)} {m.producto.unidad_medida}"
        )


class AnulacionForm(FormularioBootstrapMixin, forms.Form):  # RF-15
    motivo = forms.CharField(
        label="Motivo de la anulación", min_length=5, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Obligatorio. Quedará registrado en el historial junto con su usuario.",
    )


class CorreccionForm(FormularioBootstrapMixin, forms.Form):  # RF-15 "editar"
    cantidad = _campo_cantidad("Cantidad correcta")
    motivo = forms.CharField(
        label="Motivo de la corrección", min_length=5, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="El movimiento original queda anulado con este motivo y se registra uno nuevo que lo reemplaza.",
    )


class SalidaForm(FormularioBootstrapMixin, forms.Form):  # RF-03 (Fig. 16)
    sucursal = forms.ModelChoiceField(
        label="Sucursal destino", queryset=Sucursal.objects.all(), empty_label="Seleccionar sucursal…"
    )
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad a enviar")
