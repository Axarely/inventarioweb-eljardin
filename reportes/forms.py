from datetime import timedelta

from django import forms
from django.utils import timezone

from config.ui import FormularioBootstrapMixin
from inventario.models import Sucursal
from usuarios.models import Producto

from .servicios import Filtros

DIAS_POR_DEFECTO = 30


class FiltrosForm(FormularioBootstrapMixin, forms.Form):  # RF-07: sucursal, producto y rango de fechas
    sucursal = forms.ModelChoiceField(queryset=Sucursal.objects.order_by("nombre"), required=False, empty_label="Todas")
    producto = forms.ModelChoiceField(queryset=Producto.objects.all(), required=False, empty_label="Todos")
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, datos=None, **kwargs):
        # Siempre ligado: sin fechas en la URL se usan los últimos 30 días.
        datos = dict(datos.items()) if datos is not None else {}
        if "desde" not in datos and "hasta" not in datos:
            hoy = timezone.localdate()
            datos["desde"] = (hoy - timedelta(days=DIAS_POR_DEFECTO)).isoformat()
            datos["hasta"] = hoy.isoformat()
        super().__init__(datos, **kwargs)

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta and desde > hasta:
            raise forms.ValidationError("La fecha «desde» no puede ser posterior a «hasta».")
        return datos

    def filtros(self):
        if not self.is_valid():
            return None
        return Filtros(**self.cleaned_data)
