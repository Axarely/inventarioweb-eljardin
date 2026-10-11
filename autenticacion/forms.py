from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from . import servicios


class IniciarSesionForm(AuthenticationForm):  # RF-01, RNF-02
    username = forms.EmailField(label="Correo electrónico")

    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Correo o contraseña incorrectos.",
        "bloqueado": "Cuenta bloqueada temporalmente por intentos fallidos. Intente de nuevo más tarde.",
    }

    def clean(self):
        correo = (self.cleaned_data.get("username") or "").lower()
        usuario = get_user_model().objects.filter(correo__iexact=correo).first() if correo else None
        if usuario is not None and usuario.esta_bloqueado():
            # Ni siquiera se comprueba la contraseña mientras dure el bloqueo.
            raise ValidationError(self.error_messages["bloqueado"], code="bloqueado")
        try:
            datos = super().clean()
        except ValidationError:
            if correo:
                servicios.registrar_intento_fallido(correo)
            raise
        servicios.reiniciar_intentos(self.get_user())
        return datos
