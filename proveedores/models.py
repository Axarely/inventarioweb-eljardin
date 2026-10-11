"""Módulo de Proveedores (DEDS 3.2, Fig. 12 y 19) — RF-11."""
from django.db import models


class Proveedor(models.Model):
    nombre = models.CharField("nombre", max_length=120, unique=True)
    contacto = models.CharField("contacto", max_length=80, blank=True)
    activo = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def actualizar_contacto(self, contacto):
        self.contacto = contacto
        self.save(update_fields=["contacto"])

    def desactivar(self):
        self.activo = False
        self.save(update_fields=["activo"])
