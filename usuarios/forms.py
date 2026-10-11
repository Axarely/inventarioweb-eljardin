from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import Permission

from config.ui import FormularioBootstrapMixin

from .models import Producto, Rol, Usuario
from .roles import APPS_CON_PERMISOS


class UsuarioBaseForm(FormularioBootstrapMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rol"].required = True  # R-06: todo usuario creado desde la interfaz tiene rol

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


class ProductoForm(FormularioBootstrapMixin, forms.ModelForm):  # RF-09
    class Meta:
        model = Producto
        fields = ["nombre", "categoria", "unidad_medida", "stock_minimo"]
        widgets = {"stock_minimo": forms.NumberInput(attrs={"step": "0.01", "min": "0"})}
