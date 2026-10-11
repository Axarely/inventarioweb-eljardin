"""
Módulo de Usuarios y Roles (DEDS 3.2): gestión de usuarios y roles (RF-10) y catálogo (RF-09).
Solo el Dueño tiene estos permisos (usuarios/roles.py); el bodeguero puede crear productos (UC02 A1).
"""
from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

from autenticacion.mixins import PermisoRequeridoMixin
from config.ui import FormularioMixin, siguiente_seguro

from .forms import ProductoForm, RestablecerPasswordForm, RolForm, UsuarioCrearForm, UsuarioEditarForm
from .models import Producto, Rol, Usuario


# --- Usuarios (RF-10) ---------------------------------------------------------------------------

class UsuarioListView(PermisoRequeridoMixin, ListView):  # RF-10
    permission_required = "usuarios.view_usuario"
    template_name = "usuarios/usuario_lista.html"
    paginate_by = 25

    def get_queryset(self):
        usuarios = Usuario.objects.select_related("rol", "sucursal")
        texto = self.request.GET.get("q", "").strip()
        if texto:
            usuarios = usuarios.filter(Q(nombre__icontains=texto) | Q(correo__icontains=texto))
        return usuarios


class UsuarioCrearView(PermisoRequeridoMixin, FormularioMixin, CreateView):  # RF-10
    permission_required = "usuarios.add_usuario"
    form_class = UsuarioCrearForm
    titulo = "Nuevo usuario"
    success_url = reverse_lazy("usuarios:usuarios")

    def form_valid(self, form):
        messages.success(self.request, f"Usuario «{form.instance.nombre}» creado.")
        return super().form_valid(form)


class UsuarioEditarView(PermisoRequeridoMixin, FormularioMixin, UpdateView):  # RF-10
    permission_required = "usuarios.change_usuario"
    model = Usuario
    form_class = UsuarioEditarForm
    titulo = "Editar usuario"
    success_url = reverse_lazy("usuarios:usuarios")

    def form_valid(self, form):
        if form.instance.pk == self.request.user.pk:
            # R-03: evita que el dueño se deje a sí mismo sin acceso a la administración.
            if not form.cleaned_data["activo"]:
                form.add_error("activo", "No puede desactivar su propia cuenta.")
            if "rol" in form.changed_data:
                form.add_error("rol", "No puede cambiar su propio rol.")
            if form.errors:
                return self.form_invalid(form)
        messages.success(self.request, f"Usuario «{form.instance.nombre}» actualizado.")
        return super().form_valid(form)


class UsuarioPasswordView(PermisoRequeridoMixin, FormularioMixin, FormView):  # RF-10, D-05
    permission_required = "usuarios.change_usuario"
    form_class = RestablecerPasswordForm
    success_url = reverse_lazy("usuarios:usuarios")

    def dispatch(self, request, *args, **kwargs):
        self.usuario = get_object_or_404(Usuario, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.usuario
        return kwargs

    def get_context_data(self, **kwargs):
        self.titulo = f"Restablecer contraseña de {self.usuario.nombre}"
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"Contraseña de «{self.usuario.nombre}» restablecida.")
        return super().form_valid(form)


class UsuarioActivarView(PermisoRequeridoMixin, View):  # RF-10: desactivar en lugar de borrar
    permission_required = "usuarios.change_usuario"

    def post(self, request, pk):
        usuario = get_object_or_404(Usuario, pk=pk)
        if usuario.pk == request.user.pk:
            messages.error(request, "No puede desactivar su propia cuenta.")
        else:
            usuario.activo = not usuario.activo
            usuario.save(update_fields=["activo"])
            estado = "activado" if usuario.activo else "desactivado"
            messages.success(request, f"Usuario «{usuario.nombre}» {estado}.")
        return redirect("usuarios:usuarios")


# --- Roles (RF-10) ------------------------------------------------------------------------------

class RolListView(PermisoRequeridoMixin, ListView):  # RF-10
    permission_required = "usuarios.view_rol"
    template_name = "usuarios/rol_lista.html"

    def get_queryset(self):
        return Rol.objects.prefetch_related("permisos")


class RolCrearView(PermisoRequeridoMixin, FormularioMixin, CreateView):  # RF-10
    permission_required = "usuarios.add_rol"
    form_class = RolForm
    titulo = "Nuevo rol"
    success_url = reverse_lazy("usuarios:roles")


class RolEditarView(PermisoRequeridoMixin, FormularioMixin, UpdateView):  # RF-10
    permission_required = "usuarios.change_rol"
    form_class = RolForm
    titulo = "Editar rol"
    success_url = reverse_lazy("usuarios:roles")

    def get_queryset(self):
        return Rol.objects.filter(codigo__isnull=True)  # D-13: los roles base no se editan


class RolEliminarView(PermisoRequeridoMixin, View):  # RF-10
    permission_required = "usuarios.delete_rol"

    def post(self, request, pk):
        rol = get_object_or_404(Rol, pk=pk, codigo__isnull=True)
        try:
            rol.delete()
            messages.success(request, f"Rol «{rol.nombre}» eliminado.")
        except ProtectedError:
            messages.error(request, f"El rol «{rol.nombre}» tiene usuarios asignados; reasígnelos primero.")
        return redirect("usuarios:roles")


# --- Catálogo de productos (RF-09) --------------------------------------------------------------

class ProductoListView(PermisoRequeridoMixin, ListView):  # RF-09
    permission_required = "usuarios.view_producto"
    template_name = "usuarios/producto_lista.html"
    paginate_by = 25

    def get_queryset(self):
        productos = Producto.objects.all()
        texto = self.request.GET.get("q", "").strip()
        categoria = self.request.GET.get("categoria", "")
        if texto:
            productos = productos.filter(nombre__icontains=texto)
        if categoria:
            productos = productos.filter(categoria=categoria)
        return productos

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["categorias"] = Producto.objects.order_by("categoria").values_list("categoria", flat=True).distinct()
        return contexto


class ProductoCrearView(PermisoRequeridoMixin, FormularioMixin, CreateView):  # RF-09, UC02 A1
    permission_required = "usuarios.add_producto"
    form_class = ProductoForm
    titulo = "Nuevo producto"

    def get_success_url(self):
        return siguiente_seguro(self.request, reverse("usuarios:productos"))

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["siguiente"] = self.request.GET.get("next", "")
        return contexto

    def form_valid(self, form):
        messages.success(self.request, f"Producto «{form.instance.nombre}» creado.")
        return super().form_valid(form)


class ProductoEditarView(PermisoRequeridoMixin, FormularioMixin, UpdateView):  # RF-09
    permission_required = "usuarios.change_producto"
    model = Producto
    form_class = ProductoForm
    titulo = "Editar producto"
    success_url = reverse_lazy("usuarios:productos")

    def form_valid(self, form):
        messages.success(self.request, f"Producto «{form.instance.nombre}» actualizado.")
        return super().form_valid(form)


class ProductoActivarView(PermisoRequeridoMixin, View):  # RF-09: activar/desactivar
    permission_required = "usuarios.change_producto"

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        producto.activo = not producto.activo
        producto.save(update_fields=["activo"])
        estado = "activado" if producto.activo else "desactivado"
        messages.success(request, f"Producto «{producto.nombre}» {estado}.")
        return redirect("usuarios:productos")
