"""
Módulo de Usuarios y Roles (DEDS 3.2, Fig. 12): Usuario, Rol y catálogo de Producto.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Permission, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
import unicodedata
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


CATEGORIA_CON_MERMA = "Proteínas"  # D-38: única categoría con control de merma


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

    @staticmethod
    def clave(nombre):
        """
        D-35: forma comparable de un nombre, para no duplicar categorías. Ignora mayúsculas, tildes,
        espacios de más y singular/plural: "proteina", "Proteínas" y "PROTEINAS" dan la misma clave.
        """
        sin_tildes = "".join(
            c for c in unicodedata.normalize("NFD", (nombre or "").lower()) if unicodedata.category(c) != "Mn"
        )
        palabras = []
        for palabra in sin_tildes.split():
            if len(palabra) > 3 and palabra.endswith("s"):
                palabra = palabra[:-1]  # plural simple: "proteinas" -> "proteina", "desechables" -> "desechable"
            palabras.append(palabra)
        return " ".join(palabras)

    @classmethod
    def buscar_equivalente(cls, nombre, excluir_pk=None):
        """Devuelve la categoría que ya existe con un nombre equivalente, o None."""
        clave = cls.clave(nombre)
        for categoria in cls.objects.exclude(pk=excluir_pk):
            if cls.clave(categoria.nombre) == clave:
                return categoria
        return None

    @classmethod
    def obtener_o_crear(cls, nombre):
        """Busca una categoría equivalente (D-35); si no existe, la crea."""
        nombre = " ".join((nombre or "").split())
        if not nombre:
            raise ValidationError("Escriba el nombre de la categoría.")
        existente = cls.buscar_equivalente(nombre)
        if existente:
            return existente, False
        return cls.objects.create(nombre=nombre[:1].upper() + nombre[1:]), True


class Producto(models.Model):
    """RF-09: catálogo de productos."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos", verbose_name="categoría")
    unidad_medida = models.CharField("unidad de medida", max_length=20)
    # D-33: entrada en dos pasos (peso bruto del proveedor -> peso real tras limpieza; la diferencia es merma)
    controla_merma = models.BooleanField(
        "controla merma", default=False,
        help_text="Proteínas que se limpian o preparan en producción: se registra el peso del proveedor y luego "
                  "el peso real; la diferencia queda como merma.",
    )
    stock_minimo = models.DecimalField(
        "stock mínimo", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    activo = models.BooleanField("activo", default=True)

    # D-37: presentación de compra. La existencia se lleva en `unidad_medida` (p. ej. "unidad"), pero el
    # producto llega en cajas o paquetes que traen varias unidades (p. ej. paquete de 6).
    class Presentacion(models.TextChoices):
        CAJA = "caja", "Caja"
        PAQUETE = "paquete", "Paquete"
        BOLSA = "bolsa", "Bolsa"  # D-39: p. ej. queso mozzarella rallado, bolsa de 5 lb

    PLURAL_PRESENTACION = {"caja": "cajas", "paquete": "paquetes", "bolsa": "bolsas"}

    presentacion = models.CharField(
        "presentación", max_length=10, choices=Presentacion.choices, blank=True,
        help_text="Si el producto se compra en cajas, paquetes o bolsas.",
    )
    unidades_por_presentacion = models.PositiveIntegerField(
        "cantidad por presentación", null=True, blank=True,
        help_text="Cuánto trae cada caja, paquete o bolsa, en la unidad de medida del producto "
                  "(por ejemplo, 24 unidades o 5 lb).",
    )

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(condition=models.Q(stock_minimo__gte=0), name="producto_stock_minimo_no_negativo"),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        # D-38: la merma (entrada en dos pasos) es exclusiva de la categoría Proteínas.
        if self.controla_merma and self.categoria_id and self.categoria.nombre != CATEGORIA_CON_MERMA:
            raise ValidationError({"controla_merma": "La merma solo aplica a productos de la categoría Proteínas."})
        if self.unidades_por_presentacion and not self.presentacion:
            raise ValidationError({"presentacion": "Indique la presentación: caja, paquete o bolsa."})
        if self.unidades_por_presentacion is not None and self.unidades_por_presentacion < 1:
            raise ValidationError({"unidades_por_presentacion": "Debe ser al menos 1."})

    @property
    def usa_presentacion(self):
        """D-37: se puede registrar por caja o paquete solo si se sabe cuántas unidades trae."""
        return bool(self.presentacion and self.unidades_por_presentacion)

    def unidad_en(self, cantidad):
        """"unidad" en plural cuando corresponde (6 unidades); las abreviaturas (lb, paq.) no cambian."""
        return "unidades" if self.unidad_medida == "unidad" and cantidad != 1 else self.unidad_medida

    def nombre_presentacion(self, cantidad=2):
        if not self.presentacion:
            return ""
        return self.get_presentacion_display().lower() if cantidad == 1 else self.PLURAL_PRESENTACION[self.presentacion]

    def descripcion_presentacion(self):
        """"Paquete de 16 unidades", "Bolsa de 5 lb"; solo "Caja" si aún no se sabe cuánto trae; o ""."""
        if not self.presentacion:
            return ""
        if not self.unidades_por_presentacion:
            return self.get_presentacion_display()  # nombre corto, a pedido de la clienta
        return f"{self.get_presentacion_display()} de {self.unidades_por_presentacion} {self.unidad_en(self.unidades_por_presentacion)}"

    def en_presentaciones(self, cantidad):
        """D-37: 20 unidades con paquete de 6 -> "3 paquetes + 2 unidad". Vacío si no aplica."""
        if not self.usa_presentacion or cantidad is None:
            return ""
        enteros, resto = divmod(cantidad, self.unidades_por_presentacion)
        partes = []
        if enteros:
            enteros = int(enteros)
            partes.append(f"{enteros} {self.nombre_presentacion(enteros)}")
        if resto:
            texto = f"{resto:.2f}".rstrip("0").rstrip(".")
            partes.append(f"{texto} {self.unidad_en(resto)}")
        return " + ".join(partes) or f"0 {self.nombre_presentacion(0)}"
