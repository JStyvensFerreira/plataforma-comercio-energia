"""
Plataforma de Comercio de Energía — ciclo de vida de una orden (patrón
State). Consumido por plataforma.py (Orden, ejecutar_subasta, cancelar_orden).

La `Orden` delega `ejecutar` y `cancelar` en su estado actual; cada estado
decide qué está permitido y a cuál se pasa:

    abierta ──parcial──▶ parcial ──resto──▶ completada
       │      └──────todo───────────────────▶ completada
       └──cancelar──▶ cancelada ◀──cancelar── parcial

`completada` y `cancelada` son finales: cualquier operación lanza
`TransicionInvalida`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from plataforma import Orden


class TransicionInvalida(ValueError):
    """La operación no está permitida en el estado actual de la orden."""


class EstadoOrden(ABC):
    nombre: str = ""

    @abstractmethod
    def ejecutar(self, orden: "Orden", cantidad_kwh: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def cancelar(self, orden: "Orden") -> None:
        raise NotImplementedError

    def puede_negociar(self) -> bool:
        return False


class _EstadoNegociable(EstadoOrden):
    def ejecutar(self, orden: "Orden", cantidad_kwh: float) -> None:
        if cantidad_kwh <= 0:
            raise ValueError("La cantidad a ejecutar debe ser positiva")
        if cantidad_kwh > orden.cantidad_kwh:
            raise ValueError(
                f"No se pueden ejecutar {cantidad_kwh} kWh: a la orden solo le quedan {orden.cantidad_kwh}"
            )
        orden.cantidad_kwh = round(orden.cantidad_kwh - cantidad_kwh, 6)
        orden.cambiar_estado(COMPLETADA if orden.cantidad_kwh == 0 else PARCIAL)

    def cancelar(self, orden: "Orden") -> None:
        orden.cambiar_estado(CANCELADA)

    def puede_negociar(self) -> bool:
        return True


class Abierta(_EstadoNegociable):
    nombre = "abierta"


class ParcialmenteEjecutada(_EstadoNegociable):
    nombre = "parcial"


class _EstadoFinal(EstadoOrden):
    def ejecutar(self, orden: "Orden", cantidad_kwh: float) -> None:
        raise TransicionInvalida(f"La orden {orden.id} está {self.nombre}: no se puede ejecutar")

    def cancelar(self, orden: "Orden") -> None:
        raise TransicionInvalida(f"La orden {orden.id} está {self.nombre}: no se puede cancelar")


class Completada(_EstadoFinal):
    nombre = "completada"


class Cancelada(_EstadoFinal):
    nombre = "cancelada"


# Los estados no guardan datos (la cantidad pendiente vive en la orden).
ABIERTA = Abierta()
PARCIAL = ParcialmenteEjecutada()
COMPLETADA = Completada()
CANCELADA = Cancelada()
