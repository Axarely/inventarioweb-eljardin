"""
Módulo de Usuarios y Roles (DEDS 3.2, Fig. 12): Usuario, Rol y catálogo de Producto.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Permission, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Rol(models.Model):
    """RF-01/RF-10: un rol agrupa permisos de Django (RBAC, DEDS 3.5)."""

    class Codigo(models.TextChoices):
        DUENO = "dueno", "Dueño"
        BODEGUERO = "bodeguero", "Bodeguero"
        ENCARGADO = "encargado", "Encargado de sucursal"

    nombre = models.CharField("nombre", max_length=40, unique=True)
    # Solo los tres roles base del DEDS tienen código; sus permisos los fija usuarios/roles.py.
    codigo = models.CharField(max_length=20, choices=Codigo.choices, unique=True, null=True, blank=True, editable=False)
    permisos = models.ManyToManyField(Permission, blank=True, related_name="roles", verbose_name="permisos")

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def es_base(self):
        return self.codigo is not None

    def agregar_permiso(self, permiso):
        self.permisos.add(permiso)


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, correo):
        # RF-01: el correo no distingue mayúsculas al iniciar sesión.
        return self.get(correo__iexact=correo)

    def create_user(self, correo, password=None, **campos):
        if not correo:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(correo=self.normalize_email(correo).lower(), **campos)
        usuario.set_password(password)  # RNF-02: se guarda solo el hash
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, password=None, **campos):
        campos.setdefault("is_staff", True)
        campos.setdefault("is_superuser", True)
        return self.create_user(correo, password, **campos)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """RF-01: el correo es el identificador de inicio de sesión."""

    nombre = models.CharField("nombre", max_length=120)
    correo = models.EmailField("correo", unique=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, null=True, blank=True, related_name="usuarios")
    # D-01: la sucursal del encargado (UC04 paso 2).
    sucursal = models.ForeignKey(
        "inventario.Sucursal", on_delete=models.PROTECT, null=True, blank=True, related_name="encargados"
    )
    activo = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al admin", default=False)
    # RNF-02 (DEDS 3.5): bloqueo temporal tras intentos fallidos (D-12).
    intentos_fallidos = models.PositiveSmallIntegerField(default=0, editable=False)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, editable=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "correo"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["nombre"]

    @property
    def is_active(self):
        # Django consulta is_active al autenticar; en el DEDS el atributo se llama "activo".
        return self.activo

    def __str__(self):
        return f"{self.nombre} <{self.correo}>"

    def clean(self):
        super().clean()
        self.correo = (self.correo or "").lower()
        es_encargado = self.rol_id is not None and self.rol.codigo == Rol.Codigo.ENCARGADO
        if es_encargado and not self.sucursal_id:
            raise ValidationError({"sucursal": "El encargado de sucursal debe tener una sucursal asignada."})
        if self.sucursal_id and not es_encargado:
            raise ValidationError({"sucursal": "Solo los encargados de sucursal tienen sucursal asignada."})

    def tiene_permiso(self, permiso):
        """Fig. 12: tiene_permiso(p). Delega en el RBAC de Django (autenticacion.backends)."""
        return self.has_perm(permiso)

    def esta_bloqueado(self, ahora=None):
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > (ahora or timezone.now())

    @property
    def es_encargado(self):
        return self.rol_id is not None and self.rol.codigo == Rol.Codigo.ENCARGADO


class Producto(models.Model):
    """RF-09: catálogo de productos."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    categoria = models.CharField("categoría", max_length=60)
    unidad_medida = models.CharField("unidad de medida", max_length=20)
    stock_minimo = models.DecimalField(
        "stock mínimo", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(condition=models.Q(stock_minimo__gte=0), name="producto_stock_minimo_no_negativo"),
        ]

    def __str__(self):
        return self.nombre
