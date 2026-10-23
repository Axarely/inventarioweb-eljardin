"""
DEF-14: respuesta amable cuando falla la verificación CSRF (RNF-02 sigue intacto: la petición se rechaza).

Caso típico: doble clic en "Entrar". El primer envío inicia sesión y Django rota el token CSRF; el segundo
llega con el token viejo. En lugar de la página técnica de Django:
- si el usuario ya tiene sesión, se lo lleva al inicio (el primer envío sí funcionó);
- si no, se vuelve a mostrar el formulario con un aviso para reintentar.
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


def fallo_csrf(request, reason=""):
    if request.user.is_authenticated:
        return redirect("inicio")
    if request.method == "POST" and request.path in ("/login/", "/registro/"):
        messages.warning(request, "La página había vencido. Vuelva a intentarlo.")
        return redirect(request.path)
    destino = request.META.get("HTTP_REFERER", "")
    if not url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        destino = "/"
    return render(request, "403_csrf.html", {"volver_a": destino}, status=403)
