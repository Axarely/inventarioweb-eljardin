"""Módulo de Proveedores (DEDS 3.2, Fig. 19): CRUD básico para el Dueño — RF-11."""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from autenticacion.mixins import PermisoRequeridoMixin
from config.ui import FormularioMixin

from . import servicios
from .forms import ProveedorForm
from .models import Proveedor


class ProveedorListView(PermisoRequeridoMixin, ListView):  # RF-11
    permission_required = "proveedores.view_proveedor"
    template_name = "proveedores/proveedor_lista.html"
    paginate_by = 25

    def get_queryset(self):
        proveedores = Proveedor.objects.all()
        texto = self.request.GET.get("q", "").strip()
        if texto:
            proveedores = proveedores.filter(Q(nombre__icontains=texto) | Q(contacto__icontains=texto))
        return proveedores


class ProveedorCrearView(PermisoRequeridoMixin, FormularioMixin, CreateView):  # RF-11
    permission_required = "proveedores.add_proveedor"
    form_class = ProveedorForm
    titulo = "Nuevo proveedor"
    success_url = reverse_lazy("proveedores:lista")

    def form_valid(self, form):
        messages.success(self.request, f"Proveedor «{form.instance.nombre}» creado.")
        return super().form_valid(form)


class ProveedorEditarView(PermisoRequeridoMixin, FormularioMixin, UpdateView):  # RF-11
    permission_required = "proveedores.change_proveedor"
    model = Proveedor
    form_class = ProveedorForm
    titulo = "Editar proveedor"
    success_url = reverse_lazy("proveedores:lista")

    def form_valid(self, form):
        messages.success(self.request, f"Proveedor «{form.instance.nombre}» actualizado.")
        return super().form_valid(form)


class ProveedorActivarView(PermisoRequeridoMixin, View):  # RF-11: activar/desactivar
    permission_required = "proveedores.change_proveedor"

    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk)
        if proveedor.activo:
            servicios.desactivar_proveedor(pk)
            messages.success(request, f"Proveedor «{proveedor.nombre}» desactivado.")
        else:
            servicios.activar_proveedor(pk)
            messages.success(request, f"Proveedor «{proveedor.nombre}» activado.")
        return redirect("proveedores:lista")
