from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", login_required(TemplateView.as_view(template_name="inicio.html")), name="inicio"),  # RF-01
    path("", include("autenticacion.urls")),
    path("admin/", admin.site.urls),
]
