from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "correo", "activo", "is_staff")
    search_fields = ("nombre", "correo")
    exclude = ("password",)
