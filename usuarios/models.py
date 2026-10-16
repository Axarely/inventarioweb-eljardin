"""
Módulo de Usuarios y Roles (DEDS 3.2, Fig. 12): Usuario, Rol y catálogo de Producto.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Permission, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
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

    def solicitudes_pendientes(self):
        """D-31: cuentas creadas con el autorregistro que ningún dueño aprobó todavía."""
        return self.filter(activo=False, rol__isnull=True, last_login__isnull=True, is_superuser=False)

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
    def es_solicitud_pendiente(self):
        """D-31: misma condición que UsuarioManager.solicitudes_pendientes()."""
        return not self.activo and self.rol_id is None and self.last_login is None and not self.is_superuser

    @property
    def es_encargado(self):
        return self.rol_id is not None and self.rol.codigo == Rol.Codigo.ENCARGADO


# D-32: categorías fijas del restaurante, en este orden. No se pueden eliminar ni renombrar.
CATEGORIAS_BASE = [
    "Proteínas", "Lácteos", "Congelados", "Concentrados", "Abarrotes", "Latas y aderezos", "Verduras",
    "Desechables y limpieza", "Varios",
]


class Categoria(models.Model):
    """D-32 (RF-09): categoría de productos. Las base son fijas; el resto se agrega o elimina."""

    nombre = models.CharField("nombre", max_length=60)
    es_base = models.BooleanField("fija", default=False, editable=False)
    orden = models.PositiveSmallIntegerField(default=100, editable=False)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["orden", "nombre"]
        constraints = [
            # "Lácteos" y "lácteos" son la misma categoría.
            models.UniqueConstraint(Lower("nombre"), name="categoria_nombre_unico_sin_mayusculas"),
        ]

    def __str__(self):
        return self.nombre

    def delete(self, *args, **kwargs):
        if self.es_base:
            raise ValidationError(f"«{self.nombre}» es una categoría fija y no se puede eliminar.")
        return super().delete(*args, **kwargs)

    @classmethod
    def obtener_o_crear(cls, nombre):
        """Busca sin distinguir mayúsculas; si no existe, la crea (agregar categoría desde el producto)."""
        nombre = " ".join((nombre or "").split())
        if not nombre:
            raise ValidationError("Escriba el nombre de la categoría.")
        existente = cls.objects.filter(nombre__iexact=nombre).first()
        if existente:
            return existente, False
        return cls.objects.create(nombre=nombre[:1].upper() + nombre[1:]), True


class Producto(models.Model):
    """RF-09: catálogo de productos."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos", verbose_name="categoría")
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
