from decimal import Decimal

from django import forms

from config.ui import CampoCantidad, FormularioBootstrapMixin
from proveedores.models import Proveedor
from proveedores.servicios import proveedores_activos
from usuarios.models import Producto

from .excepciones import formatear_cantidad
from .models import Sucursal


class CampoProducto(forms.ModelChoiceField):
    """D-53: cada opción muestra la categoría ("Azúcar · Abarrotes") para distinguir nombres parecidos."""

    def label_from_instance(self, producto):
        return f"{producto.nombre} · {producto.categoria}" if producto.categoria_id else producto.nombre


def _campo_producto():
    # RF-09: solo los productos activos están disponibles en los formularios.
    # D-53: el navegador lo convierte en un buscador (escribir y elegir), ver base.html.
    return CampoProducto(
        label="Producto", queryset=Producto.objects.filter(activo=True).select_related("categoria").order_by("nombre"),
        empty_label="Escriba o elija un producto…",
        widget=forms.Select(attrs={"class": "buscador-producto"}),
    )


class PresentacionMixin:
    """
    D-37: permite registrar la cantidad en unidades o en cajas/paquetes. Si se elige caja o paquete, la
    cantidad se convierte a unidades (3 paquetes x 6 = 18) antes de llegar a los servicios.
    """

    MEDIDAS = [("unidad", "Unidad de medida"), ("presentacion", "Cajas, paquetes o bolsas")]
    cantidad_original = None

    def _agregar_medida(self):
        self.fields["medida"] = forms.ChoiceField(
            label="Registrar en", choices=self.MEDIDAS, initial="unidad", required=False,
            widget=forms.Select(attrs={"class": "form-select"}),
        )

    def clean(self):
        datos = super().clean()
        producto, cantidad = datos.get("producto"), datos.get("cantidad")
        if datos.get("medida") == "presentacion" and producto is not None and cantidad is not None:
            if not producto.usa_presentacion:
                self.add_error(
                    "medida",
                    f"{producto} no tiene configurado cuánto trae cada caja, paquete o bolsa: regístrelo en "
                    "unidades o configúrelo en Catálogo.",
                )
            else:
                self.cantidad_original = cantidad
                datos["cantidad"] = cantidad * producto.unidades_por_presentacion
        return datos

    def descripcion_conversion(self):
        producto = self.cleaned_data.get("producto")
        if self.cantidad_original is None or producto is None:
            return ""
        n = self.cantidad_original
        texto = f"{n:.2f}".rstrip("0").rstrip(".")
        return f" ({texto} {producto.nombre_presentacion(n)} de {producto.unidades_por_presentacion})"


def _campo_cantidad(etiqueta):
    # UC02/UC03 E1: cantidad numérica y positiva. D-35: se escribe (1.5, 1,5, 1 1/2), sin flechas.
    return CampoCantidad(label=etiqueta, min_value=Decimal("0.01"))


class EntradaForm(PresentacionMixin, FormularioBootstrapMixin, forms.Form):  # RF-02, RF-11 (Fig. 15)
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad recibida")
    # D-45: opcional y escrito; sugiere los proveedores activos (datalist) y crea el que no exista.
    proveedor = forms.CharField(
        label="Proveedor (opcional)", required=False, max_length=120,
        widget=forms.TextInput(attrs={"list": "lista-proveedores", "autocomplete": "off",
                                      "placeholder": "Escriba el proveedor o déjelo en blanco"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.proveedores_sugeridos = proveedores_activos()
        self._agregar_medida()

    def clean_proveedor(self):
        nombre = " ".join(self.cleaned_data["proveedor"].split())
        if nombre:
            existente = Proveedor.objects.filter(nombre__iexact=nombre).first()
            if existente is not None and not existente.activo:
                raise forms.ValidationError(
                    f"El proveedor «{existente}» está desactivado. Actívelo en Proveedores o escriba otro."
                )
        return nombre


class PesoRealForm(FormularioBootstrapMixin, forms.Form):  # D-33: segunda entrada de proteínas
    control = forms.IntegerField(widget=forms.HiddenInput)
    peso_real = CampoCantidad(label="Peso real", min_value=Decimal("0"))


class ConsumoForm(PresentacionMixin, FormularioBootstrapMixin, forms.Form):  # RF-07 (D-02)
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad consumida")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agregar_medida()


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


class SalidaForm(PresentacionMixin, FormularioBootstrapMixin, forms.Form):  # RF-03 (Fig. 16)
    sucursal = forms.ModelChoiceField(
        label="Sucursal destino", queryset=Sucursal.objects.all(), empty_label="Seleccionar sucursal…"
    )
    producto = _campo_producto()
    cantidad = _campo_cantidad("Cantidad a enviar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agregar_medida()
