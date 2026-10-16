"""
Panel de indicadores (Fig. 14, UC07: RF-07, RF-08, RF-17) y reportes exportables (RF-07, RF-14).
"""
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from autenticacion.mixins import PermisoRequeridoMixin

from . import exportadores, servicios
from .forms import FiltrosForm


class DashboardView(PermisoRequeridoMixin, TemplateView):  # RF-07, RF-08, RF-17
    permission_required = "reportes.ver_dashboard"
    template_name = "reportes/dashboard.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        form = FiltrosForm(self.request.GET)
        filtros = form.filtros()
        contexto["form"] = form
        if filtros is not None:
            panel = servicios.generar_indicadores(filtros)
            contexto["panel"] = panel
            contexto["graficos"] = {"comparativo": panel.comparativo, "diaria": panel.serie_diaria}
        return contexto


class ReportesView(PermisoRequeridoMixin, TemplateView):  # RF-07, RF-14
    permission_required = "reportes.ver_reportes"
    template_name = "reportes/reportes.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        tipo = self.request.GET.get("tipo", "consumo")
        if tipo not in servicios.REPORTES:
            raise Http404
        form = FiltrosForm(self.request.GET)
        filtros = form.filtros()
        contexto.update(form=form, tipo=tipo, tipos=[("consumo", "Consumo"), ("existencias", "Existencias")])
        if filtros is not None:
            contexto["reporte"] = servicios.REPORTES[tipo](filtros)
        return contexto


class ExportarView(PermisoRequeridoMixin, View):  # RF-14: mismo reporte que en pantalla
    permission_required = "reportes.exportar_reportes"
    FORMATOS = {
        "excel": (exportadores.a_excel, "xlsx",
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        "pdf": (exportadores.a_pdf, "pdf", "application/pdf"),
    }

    def get(self, request, formato):
        tipo = request.GET.get("tipo", "consumo")
        if formato not in self.FORMATOS or tipo not in servicios.REPORTES:
            raise Http404
        filtros = FiltrosForm(request.GET).filtros()
        if filtros is None:
            raise Http404("Filtros inválidos")
        exportar, extension, tipo_mime = self.FORMATOS[formato]
        contenido = exportar(servicios.REPORTES[tipo](filtros))
        respuesta = HttpResponse(contenido, content_type=tipo_mime)
        nombre = f"reporte_{tipo}_{timezone.localdate():%Y%m%d}.{extension}"
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return respuesta
