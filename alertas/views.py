"""Pantalla de alertas de bajo inventario (DEDS Fig. 18, UC05) — RF-06."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from autenticacion.mixins import PermisoRequeridoMixin

from .models import AlertaInventario


class AlertaListView(PermisoRequeridoMixin, ListView):  # RF-06
    permission_required = "alertas.view_alertainventario"
    template_name = "alertas/alerta_lista.html"
    context_object_name = "alertas"
    paginate_by = 25

    def get_queryset(self):
        alertas = AlertaInventario.objects.select_related(
            "existencia__producto", "existencia__ubicacion", "atendida_por"
        )
        estado = self.request.GET.get("estado", AlertaInventario.Estado.PENDIENTE)
        if estado in AlertaInventario.Estado.values:
            alertas = alertas.filter(estado=estado)
        return alertas

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["estado"] = self.request.GET.get("estado", AlertaInventario.Estado.PENDIENTE)
        return contexto


class MarcarAtendidaView(PermisoRequeridoMixin, View):  # RF-06, UC05 paso 4
    permission_required = "alertas.marcar_atendida"

    def post(self, request, pk):
        alerta = get_object_or_404(AlertaInventario.objects.select_related("existencia__producto"), pk=pk)
        if alerta.marcar_atendida(request.user):
            messages.success(request, f"Alerta de «{alerta.existencia.producto}» marcada como atendida.")
        else:
            messages.info(request, "La alerta ya estaba atendida.")
        return redirect("alertas:lista")
