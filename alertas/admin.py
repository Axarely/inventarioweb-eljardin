from django.contrib import admin

from .models import AlertaInventario


@admin.register(AlertaInventario)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ("existencia", "nivel_detectado", "estado", "generada_en", "atendida_por")
    list_filter = ("estado",)

    def has_add_permission(self, request):
        return False  # las alertas solo las genera el observador (RF-06)
