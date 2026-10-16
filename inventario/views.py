"""
Módulo de Inventario (DEDS 3.2): entradas (RF-02), salidas (RF-03), existencias (RF-04, RF-05)
e historial (RF-12). Las vistas solo delegan en inventario/servicios.py (IInventario).
"""
import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, ListView

from autenticacion.mixins import PermisoRequeridoMixin
from usuarios.models import Categoria, Producto

from . import servicios
from .excepciones import ExistenciaInsuficiente, formatear_cantidad
from .forms import AnulacionForm, ConsumoForm, CorreccionForm, DiscrepanciaForm, EntradaForm, SalidaForm
from .models import Existencia, MovimientoInventario, Ubicacion

logger = logging.getLogger(__name__)

PERM_EXISTENCIAS_TODAS = "inventario.consultar_existencias_todas"
MENSAJE_ERROR_BD = (
    "No se pudo completar la operación por un error de la base de datos. "
    "No se aplicó ningún cambio; intente de nuevo en unos momentos."
)


def error_de_base_de_datos(form):
    """UC02/UC03 E2 (RNF-08): el movimiento se revirtió completo; se informa sin mostrar un error 500."""
    logger.exception("Error de base de datos al registrar un movimiento")
    form.add_error(None, MENSAJE_ERROR_BD)
    return form
PERM_EXISTENCIAS_PROPIAS = "inventario.consultar_existencias_propias"


class EntradaView(PermisoRequeridoMixin, FormView):  # RF-02, RF-11, UC02
    permission_required = "inventario.registrar_entrada"
    template_name = "inventario/entrada.html"
    form_class = EntradaForm

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            entrada = servicios.registrar_entrada(
                datos["producto"].pk, datos["cantidad"], datos["proveedor"].pk, self.request.user.pk
            )
        except ValidationError as error:  # UC02 E1/E2: se informa sin cambios parciales
            form.add_error(None, error)
            return self.form_invalid(form)
        except DatabaseError:  # DEF-09, UC02/UC03 E2: se informa; la transacción ya se revirtió
            return self.form_invalid(error_de_base_de_datos(form))
        existencia = servicios.existencia_en_bodega(entrada.producto_id)
        messages.success(
            self.request,
            f"Entrada registrada: +{formatear_cantidad(entrada.cantidad)} {entrada.producto.unidad_medida} "
            f"de {entrada.producto}. Existencia en bodega: {formatear_cantidad(existencia.cantidad)}.",
        )
        return redirect("inventario:entrada")


class SalidaView(PermisoRequeridoMixin, FormView):  # RF-03, UC03
    permission_required = "inventario.registrar_salida"
    template_name = "inventario/salida.html"
    form_class = SalidaForm
    cantidad_sugerida = None

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["cantidad_sugerida"] = self.cantidad_sugerida
        return contexto

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            salida = servicios.registrar_salida(
                datos["producto"].pk, datos["cantidad"], datos["sucursal"].pk, self.request.user.pk
            )
        except ExistenciaInsuficiente as error:  # UC03 E1 + A1: se sugiere el máximo disponible
            form.add_error("cantidad", error.messages[0])
            self.cantidad_sugerida = error.disponible if error.disponible > 0 else None
            return self.form_invalid(form)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        except DatabaseError:  # DEF-09, UC02/UC03 E2: se informa; la transacción ya se revirtió
            return self.form_invalid(error_de_base_de_datos(form))
        messages.success(
            self.request,
            f"Salida registrada: {formatear_cantidad(salida.cantidad)} {salida.producto.unidad_medida} "
            f"de {salida.producto} hacia {salida.destino}.",
        )
        return redirect("inventario:salida")


class SucursalPropiaMixin:
    """El encargado opera solo sobre la sucursal asociada a su usuario (DEDS 3.5, mínimo privilegio)."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.sucursal_id is None and self.has_permission():
            messages.error(request, "Su usuario no tiene una sucursal asignada. Solicite a un dueño que la asigne.")
            return redirect("inicio")
        return super().dispatch(request, *args, **kwargs)


class ConsumoView(PermisoRequeridoMixin, SucursalPropiaMixin, FormView):  # RF-07 (D-02), Fase 1 "reportan el consumo"
    permission_required = "inventario.reportar_consumo"
    template_name = "inventario/consumo.html"
    form_class = ConsumoForm

    def form_valid(self, form):
        datos = form.cleaned_data
        sucursal = self.request.user.sucursal
        try:
            consumo = servicios.registrar_consumo(datos["producto"].pk, datos["cantidad"], sucursal.pk, self.request.user.pk)
        except ExistenciaInsuficiente as error:
            form.add_error("cantidad", error.messages[0].replace(" Ajuste la cantidad o cancele el envío.", ""))
            return self.form_invalid(form)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        except DatabaseError:  # DEF-09, UC02/UC03 E2: se informa; la transacción ya se revirtió
            return self.form_invalid(error_de_base_de_datos(form))
        messages.success(
            self.request,
            f"Consumo registrado: {formatear_cantidad(consumo.cantidad)} {consumo.producto.unidad_medida} "
            f"de {consumo.producto} en {sucursal}.",
        )
        return redirect("inventario:consumo")


class DiscrepanciaView(PermisoRequeridoMixin, SucursalPropiaMixin, FormView):  # RF-13
    permission_required = "inventario.add_discrepanciainventario"
    template_name = "inventario/discrepancia.html"
    form_class = DiscrepanciaForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["envios"] = servicios.envios_sin_discrepancia(self.request.user.sucursal_id)
        return kwargs

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            discrepancia = servicios.reportar_discrepancia(
                datos["movimiento"].pk, datos["cantidad_recibida"], self.request.user
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        except DatabaseError:  # DEF-09, UC02/UC03 E2: se informa; la transacción ya se revirtió
            return self.form_invalid(error_de_base_de_datos(form))
        messages.success(
            self.request,
            f"Discrepancia registrada para el envío de {discrepancia.movimiento.producto}: "
            f"diferencia de {formatear_cantidad(discrepancia.diferencia)} {discrepancia.movimiento.producto.unidad_medida}.",
        )
        return redirect("inventario:discrepancia")


class MovimientoAccionMixin(PermisoRequeridoMixin):  # RF-15
    permission_required = "inventario.anular_movimiento"

    def dispatch(self, request, *args, **kwargs):
        self.movimiento = get_object_or_404(
            MovimientoInventario.objects.select_related("producto", "origen", "destino", "usuario"), pk=kwargs["pk"]
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["movimiento"] = self.movimiento
        return contexto

    def get(self, request, *args, **kwargs):
        if self.movimiento.anulado:
            messages.info(request, "El movimiento ya está anulado.")
            return redirect("inventario:historial")
        return super().get(request, *args, **kwargs)


class AnularView(MovimientoAccionMixin, FormView):  # RF-15
    template_name = "inventario/anular.html"
    form_class = AnulacionForm

    def form_valid(self, form):
        try:
            servicios.anular_movimiento(self.movimiento.pk, form.cleaned_data["motivo"], self.request.user)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        except DatabaseError:  # DEF-09, UC02/UC03 E2: se informa; la transacción ya se revirtió
            return self.form_invalid(error_de_base_de_datos(form))
        messages.success(self.request, f"Movimiento #{self.movimiento.pk} anulado; las existencias fueron revertidas.")
        return redirect("inventario:historial")


class CorregirView(MovimientoAccionMixin, FormView):  # RF-15 "editar" (D-18)
    template_name = "inventario/corregir.html"
    form_class = CorreccionForm

    def get_initial(self):
        return {"cantidad": self.movimiento.cantidad}

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            nuevo = servicios.corregir_movimiento(self.movimiento.pk, datos["cantidad"], datos["motivo"], self.request.user)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        except DatabaseError:  # DEF-09, UC02/UC03 E2: se informa; la transacción ya se revirtió
            return self.form_invalid(error_de_base_de_datos(form))
        messages.success(
            self.request,
            f"Movimiento #{self.movimiento.pk} corregido: queda anulado y lo reemplaza el #{nuevo.pk} "
            f"con {formatear_cantidad(nuevo.cantidad)} {nuevo.producto.unidad_medida}.",
        )
        return redirect("inventario:historial")


@login_required
def existencia_bodega(request):
    """JSON con la existencia de un producto en bodega, para el panel lateral de las Fig. 15 y 16."""
    usuario = request.user
    if not (usuario.has_perm("inventario.registrar_entrada") or usuario.has_perm("inventario.registrar_salida")):
        raise PermissionDenied
    producto_id = request.GET.get("producto", "")
    if not producto_id.isdigit():
        raise Http404
    producto = get_object_or_404(Producto, pk=producto_id, activo=True)
    existencia = servicios.existencia_en_bodega(producto.pk) or Existencia(producto=producto, cantidad=Decimal("0"))
    nivel = existencia.nivel()
    return JsonResponse({
        "cantidad": formatear_cantidad(existencia.cantidad),
        "unidad": producto.unidad_medida,
        "stock_minimo": formatear_cantidad(producto.stock_minimo),
        "nivel": nivel.value,
        "nivel_texto": nivel.label,
    })


class ExistenciasView(LoginRequiredMixin, ListView):  # RF-04, RF-05, UC04
    template_name = "inventario/existencias.html"
    context_object_name = "existencias"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.puede_todas = request.user.has_perm(PERM_EXISTENCIAS_TODAS)
        if not (self.puede_todas or request.user.has_perm(PERM_EXISTENCIAS_PROPIAS)):
            raise PermissionDenied("Su rol no tiene acceso a esta función.")
        self.ubicacion = self._resolver_ubicacion(request)
        return super().dispatch(request, *args, **kwargs)

    def _resolver_ubicacion(self, request):
        pedida = request.GET.get("ubicacion", "")
        if self.puede_todas:
            if pedida.isdigit():
                return get_object_or_404(Ubicacion, pk=pedida)
            return Ubicacion.objects.order_by("tipo", "nombre").first()
        # UC04 paso 2: el encargado solo ve la sucursal asociada a su usuario (mínimo privilegio).
        propia = request.user.sucursal
        if pedida and (propia is None or pedida != str(propia.pk)):
            raise PermissionDenied("Solo puede consultar las existencias de su sucursal.")
        return propia

    def get_queryset(self):
        if self.ubicacion is None:
            return Existencia.objects.none()
        filtros = {
            "texto": self.request.GET.get("q", "").strip(),
            "categoria": self.request.GET.get("categoria", ""),
        }
        return servicios.consultar_existencias(self.ubicacion.pk, filtros)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["ubicacion"] = self.ubicacion
        contexto["puede_todas"] = self.puede_todas
        contexto["ubicaciones"] = Ubicacion.objects.order_by("tipo", "nombre") if self.puede_todas else []
        contexto["categorias"] = Categoria.objects.filter(productos__activo=True).distinct()
        return contexto


class HistorialView(PermisoRequeridoMixin, ListView):  # RF-12
    permission_required = "inventario.ver_historial"
    template_name = "inventario/historial.html"
    context_object_name = "movimientos"
    paginate_by = 25

    def get_queryset(self):
        producto = self.request.GET.get("producto", "")
        ubicacion = self.request.GET.get("ubicacion", "")
        return servicios.historial(
            producto_id=int(producto) if producto.isdigit() else None,
            ubicacion_id=int(ubicacion) if ubicacion.isdigit() else None,
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["productos"] = Producto.objects.all()
        contexto["ubicaciones"] = Ubicacion.objects.order_by("tipo", "nombre")
        return contexto
