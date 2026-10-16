"""
Patrón Observer (DEDS 3.4, Fig. 23): interfaz que implementan los módulos interesados en los
cambios de una Existencia. Inventario solo conoce esta interfaz, nunca a Alertas ni a Reportes
(corrección 1 del DEDS v1.1); los observadores se registran desde sus propios AppConfig.ready().
"""
from abc import ABC, abstractmethod


class IObservadorExistencia(ABC):
    @abstractmethod
    def actualizar(self, existencia):
        """Se invoca después de cada cambio de cantidad, dentro de la misma transacción.

        La existencia trae dos atributos transitorios: `delta` (cambio aplicado) y
        `nivel_anterior` (nivel antes del cambio, Fig. 8).
        """
