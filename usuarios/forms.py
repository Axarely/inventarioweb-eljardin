from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Permission

from config.ui import CampoCantidad, FormularioBootstrapMixin

from .models import Categoria, Producto, Rol, Usuario
from .roles import APPS_CON_PERMISOS


class UsuarioBaseForm(FormularioBootstrapMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "rol" in self.fields:
            self.fields["rol"].required = True  # R-06: todo usuario creado por un dueño tiene rol

    def clean_correo(self):
        correo = self.cleaned_data["correo"].lower()
        repetido = Usuario.objects.filter(correo__iexact=correo).exclude(pk=self.instance.pk).exists()
        if repetido:
            raise forms.ValidationError("Ya existe un usuario con ese correo.")
        return correo


class UsuarioCrearForm(UsuarioBaseForm):  # RF-10
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, strip=False)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput, strip=False)

    class Meta:
        model = Usuario
        fields = ["nombre", "correo", "rol", "sucursal"]

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        return datos

    def _post_clean(self):
        super()._post_clean()
        password = self.cleaned_data.get("password2")
        if password:
            try:
                password_validation.validate_password(password, self.instance)
            except forms.ValidationError as error:
                self.add_error("password2", error)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])  # RNF-02: hash
        if commit:
            usuario.save()
        return usuario


class RegistroForm(UsuarioCrearForm):  # D-31: solicitud de cuenta (sin rol, inactiva)
    class Meta:
        model = Usuario
        fields = ["nombre", "correo"]
        labels = {"nombre": "Nombre completo", "correo": "Correo electrónico"}

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.activo = False  # mínimo privilegio: no entra hasta que un dueño apruebe y asigne el rol
        usuario.rol = None
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(UsuarioBaseForm):  # RF-10
    class Meta:
        model = Usuario
        fields = ["nombre", "correo", "rol", "sucursal", "activo"]


class RestablecerPasswordForm(FormularioBootstrapMixin, SetPasswordForm):
    """El dueño restablece la contraseña (sustituye la recuperación por correo, D-05)."""


class RolForm(FormularioBootstrapMixin, forms.ModelForm):  # RF-10: roles personalizados
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.filter(content_type__app_label__in=APPS_CON_PERMISOS)
        .select_related("content_type")
        .order_by("content_type__app_label", "codename"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Rol
        fields = ["nombre", "permisos"]


class ProductoForm(FormularioBootstrapMixin, forms.ModelForm):  # RF-09, D-32
    stock_minimo = CampoCantidad(label="Stock mínimo", min_value=0)  # D-35: se escribe, sin flechas
    nueva_categoria = forms.CharField(
        label="¿No existe la categoría? Agréguela aquí", required=False, max_length=60,
        help_text="Si escribe una categoría nueva, se crea y se asigna a este producto.",
    )

    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "nueva_categoria", "unidad_medida", "controla_merma", "stock_minimo"]


    def __init__(self, *args, puede_crear_categoria=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].required = False  # se exige en clean(): elegida o nueva
        self.fields["categoria"].empty_label = "Seleccionar categoría…"
        if not puede_crear_categoria:
            del self.fields["nueva_categoria"]
        self.categoria_creada = None

    def clean(self):
        datos = super().clean()
        nueva = " ".join((datos.get("nueva_categoria") or "").split())
        if nueva:
            # D-35: si ya existe (sin importar mayúsculas, tildes ni singular/plural) se avisa y no se duplica.
            existente = Categoria.buscar_equivalente(nueva)
            if existente is not None:
                self.add_error(
                    "nueva_categoria",
                    f"La categoría «{existente}» ya existe. Selecciónela en la lista «Categoría».",
                )
                return datos
            # Quien guarda el formulario lo hace en una transacción: si el producto no se guarda, la
            # categoría tampoco queda creada.
            datos["categoria"], creada = Categoria.obtener_o_crear(nueva)
            self.instance.categoria = datos["categoria"]
            self.categoria_creada = datos["categoria"] if creada else None
        elif not datos.get("categoria"):
            self.add_error("categoria", "Elija una categoría o escriba una nueva.")
        return datos


class CategoriaForm(FormularioBootstrapMixin, forms.ModelForm):  # D-32
    class Meta:
        model = Categoria
        fields = ["nombre"]
        labels = {"nombre": "Nueva categoría"}

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split())
        existente = Categoria.buscar_equivalente(nombre)  # D-35: tildes y singular/plural incluidos
        if existente is not None:
            fija = " (es una categoría fija)" if existente.es_base else ""
            raise forms.ValidationError(f"La categoría «{existente}» ya existe{fija}.")
        return nombre[:1].upper() + nombre[1:]
