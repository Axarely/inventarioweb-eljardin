"""
Módulo de Usuarios y Roles (DEDS 3.2): gestión de usuarios y roles (RF-10) y catálogo (RF-09).
Solo el Dueño tiene estos permisos (usuarios/roles.py); el bodeguero puede crear productos (UC02 A1).
"""
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

from autenticacion.mixins import PermisoRequeridoMixin
from config.ui import FormularioMixin, siguiente_seguro

from .forms import (
    CategoriaForm, ProductoForm, RestablecerPasswordForm, RolForm, UsuarioCrearForm, UsuarioEditarForm,
)
from .models import CATEGORIA_CON_MERMA, Categoria, Producto, Rol, Usuario


# --- Usuarios (RF-10) ---------------------------------------------------------------------------

class UsuarioListView(PermisoRequeridoMixin, ListView):  # RF-10
    permission_required = "usuarios.view_usuario"
    template_name = "usuarios/usuario_lista.html"
    paginate_by = 25

    def get_queryset(self):
        if self.request.GET.get("estado") == "pendientes":  # D-31
            usuarios = Usuario.objects.solicitudes_pendientes().select_related("rol", "sucursal")
        else:
            usuarios = Usuario.objects.select_related("rol", "sucursal")
        texto = self.request.GET.get("q", "").strip()
        if texto:
            usuarios = usuarios.filter(Q(nombre__icontains=texto) | Q(correo__icontains=texto))
        return usuarios

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["pendientes"] = Usuario.objects.solicitudes_pendientes().count()
        contexto["solo_pendientes"] = self.request.GET.get("estado") == "pendientes"
        return contexto


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

    def get_initial(self):
        inicial = super().get_initial()
        if self.request.GET.get("aprobar"):  # D-31: aprobar una solicitud = activar y asignar rol
            inicial["activo"] = True
        return inicial

    def get_context_data(self, **kwargs):
        if self.request.GET.get("aprobar"):
            self.titulo = f"Aprobar solicitud de {self.object.nombre}: asigne un rol"
        return super().get_context_data(**kwargs)

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


class UsuarioRechazarView(PermisoRequeridoMixin, View):  # D-31: solo solicitudes nunca aprobadas
    permission_required = "usuarios.change_usuario"

    def post(self, request, pk):
        solicitud = get_object_or_404(Usuario.objects.solicitudes_pendientes(), pk=pk)
        nombre = solicitud.nombre
        solicitud.delete()  # no tiene rol, nunca entró ni registró movimientos
        messages.success(request, f"Solicitud de «{nombre}» rechazada.")
        return redirect(f"{reverse('usuarios:usuarios')}?estado=pendientes")


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
        elif usuario.es_solicitud_pendiente:  # D-31: se aprueba asignando rol, no solo activando
            messages.error(request, f"Para aprobar a «{usuario.nombre}» asígnele un rol con «Aprobar».")
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
        productos = Producto.objects.select_related("categoria")
        texto = self.request.GET.get("q", "").strip()
        categoria = self.request.GET.get("categoria", "")
        if texto:
            productos = productos.filter(nombre__icontains=texto)
        if categoria.isdigit():
            productos = productos.filter(categoria_id=categoria)
        return productos

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["categorias"] = Categoria.objects.all()
        return contexto


class ProductoFormularioMixin:  # D-32
    """Guarda el producto y, si se escribió, la categoría nueva en UNA transacción: si el producto no
    se guarda (por ejemplo, nombre repetido), la categoría tampoco queda creada."""

    template_name = "usuarios/producto_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["puede_crear_categoria"] = self.request.user.has_perm("usuarios.add_categoria")
        return kwargs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        # D-38: la casilla "controla merma" solo se muestra para Proteínas
        proteinas = Categoria.objects.filter(nombre=CATEGORIA_CON_MERMA).first()
        contexto["categoria_merma_id"] = proteinas.pk if proteinas else ""
        return contexto

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            self._guardado = False
            respuesta = super().post(request, *args, **kwargs)
            if not self._guardado:
                transaction.set_rollback(True)
        return respuesta

    def form_valid(self, form):
        self._guardado = True
        if form.categoria_creada:
            messages.info(self.request, f"Categoría «{form.categoria_creada}» agregada.")
        return super().form_valid(form)


class ProductoCrearView(PermisoRequeridoMixin, ProductoFormularioMixin, FormularioMixin, CreateView):  # RF-09, UC02 A1
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


class ProductoEditarView(PermisoRequeridoMixin, ProductoFormularioMixin, FormularioMixin, UpdateView):  # RF-09
    permission_required = "usuarios.change_producto"
    model = Producto
    form_class = ProductoForm
    titulo = "Editar producto"
    success_url = reverse_lazy("usuarios:productos")

    def form_valid(self, form):
        messages.success(self.request, f"Producto «{form.instance.nombre}» actualizado.")
        return super().form_valid(form)


# --- Categorías (D-32) --------------------------------------------------------------------------

class CategoriaListView(PermisoRequeridoMixin, ListView):  # D-32, RF-09
    permission_required = "usuarios.view_categoria"
    template_name = "usuarios/categoria_lista.html"
    context_object_name = "categorias"

    def get_queryset(self):
        # DEF-11: en consultas agrupadas (annotate + Count) Django ignora Meta.ordering: orden explícito.
        return Categoria.objects.annotate(total_productos=Count("productos")).order_by("orden", "nombre")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["form"] = kwargs.get("form") or CategoriaForm()
        return contexto


class CategoriaCrearView(PermisoRequeridoMixin, View):  # D-32
    permission_required = "usuarios.add_categoria"

    def post(self, request):
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, f"Categoría «{categoria}» agregada.")
            return redirect("usuarios:categorias")
        vista = CategoriaListView()
        vista.setup(request)
        vista.object_list = vista.get_queryset()
        return render(request, vista.template_name, vista.get_context_data(form=form))


class CategoriaEliminarView(PermisoRequeridoMixin, View):  # D-32: solo agregadas y sin productos
    permission_required = "usuarios.delete_categoria"

    def post(self, request, pk):
        categoria = get_object_or_404(Categoria, pk=pk)
        if categoria.es_base:
            messages.error(request, f"«{categoria}» es una categoría fija y no se puede eliminar.")
        elif categoria.productos.exists():
            total = categoria.productos.count()
            messages.error(
                request,
                f"«{categoria}» tiene {total} producto{'s' if total != 1 else ''}. "
                "Cámbielos de categoría antes de eliminarla.",
            )
        else:
            categoria.delete()
            messages.success(request, f"Categoría «{categoria}» eliminada.")
        return redirect("usuarios:categorias")


class ProductoEliminarView(PermisoRequeridoMixin, View):  # D-49
    """Elimina un producto solo si nunca tuvo movimientos: si los tiene, borrarlo rompería el historial y
    los reportes (RF-06, RF-15), así que se pide desactivarlo."""
    permission_required = "usuarios.delete_producto"

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        if producto.movimientos.exists():
            messages.error(
                request,
                f"«{producto.nombre}» tiene movimientos registrados y no se puede eliminar sin perder el historial. "
                "Desactívelo para que deje de aparecer en las entradas y salidas.",
            )
            return redirect("usuarios:productos")
        try:
            with transaction.atomic():
                producto.existencias.all().delete()  # sin movimientos solo puede haber registros en 0
                producto.delete()
        except ProtectedError:
            messages.error(request, f"«{producto.nombre}» tiene datos asociados y no se puede eliminar. Desactívelo.")
            return redirect("usuarios:productos")
        messages.success(request, f"Producto «{producto.nombre}» eliminado.")
        return redirect("usuarios:productos")


class ProductoActivarView(PermisoRequeridoMixin, View):  # RF-09: activar/desactivar
    permission_required = "usuarios.change_producto"

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        producto.activo = not producto.activo
        producto.save(update_fields=["activo"])
        estado = "activado" if producto.activo else "desactivado"
        messages.success(request, f"Producto «{producto.nombre}» {estado}.")
        return redirect("usuarios:productos")
