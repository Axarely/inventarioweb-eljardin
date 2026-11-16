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
        "bloqueado_manual": "Cuenta bloqueada por el administrador. Pídale que la desbloquee.",
        "bloqueado": "Cuenta bloqueada temporalmente por intentos fallidos. Intente de nuevo en %(minutos)s "
                     "o pida al administrador que la desbloquee (Usuarios → Desbloquear).",
    }

    def clean(self):
        correo = (self.cleaned_data.get("username") or "").lower()
        usuario = get_user_model().objects.filter(correo__iexact=correo).first() if correo else None
        if usuario is not None and usuario.bloqueado_manual:  # D-52
            raise ValidationError(self.error_messages["bloqueado_manual"], code="bloqueado")
        if usuario is not None and usuario.esta_bloqueado():
            # Ni siquiera se comprueba la contraseña mientras dure el bloqueo.
            minutos = usuario.minutos_de_bloqueo()
            raise ValidationError(
                self.error_messages["bloqueado"], code="bloqueado",
                params={"minutos": "1 minuto" if minutos == 1 else f"{minutos} minutos"},
            )
        try:
            datos = super().clean()
        except ValidationError:
            if correo:
                servicios.registrar_intento_fallido(correo)
            raise
        # R-11: con correo inválido o contraseña vacía Django no autentica y get_user() es None.
        if self.get_user() is not None:
            servicios.reiniciar_intentos(self.get_user())
        return datos
