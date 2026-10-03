"""
Plataforma de Comercio de Energía — ajustes al precio de una transacción
(patrón Decorator). Consumido por plataforma.py (_calcular_costo, cotizar).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


# ---------------------------------------------------------------------------
# COMPONENT — interfaz común del costo y de sus decoradores
# ---------------------------------------------------------------------------
class CostoEnergia(ABC):
    """Component: cualquier cosa que tenga un total y un desglose."""

    @abstractmethod
    def total(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def desglose(self) -> list[dict]:
        """Líneas `{concepto, valor, acumulado}` en el orden en que se aplicaron."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# CONCRETE COMPONENT — el objeto base al que se le añaden capas
# ---------------------------------------------------------------------------
class CostoBase(CostoEnergia):
    """ConcreteComponent: energía transada, sin ningún ajuste."""

    def __init__(self, cantidad_kwh: float, precio_kwh: float) -> None:
        self.cantidad_kwh = cantidad_kwh
        self.precio_kwh = precio_kwh

    def total(self) -> float:
        return round(self.cantidad_kwh * self.precio_kwh, 2)

    def desglose(self) -> list[dict]:
        total = self.total()
        return [
            {
                "concepto": f"Energía {self.cantidad_kwh} kWh x ${self.precio_kwh}",
                "valor": total,
                "acumulado": total,
            }
        ]


# ---------------------------------------------------------------------------
# DECORATOR — mantiene la referencia al componente y delega en él
# ---------------------------------------------------------------------------
class AjusteCosto(CostoEnergia):
    """
    Decorator: envuelve a otro `CostoEnergia` (base u otro ajuste) y por
    defecto solo delega. Cada ajuste concreto redefine `_valor_ajuste`
    para añadir su capa encima del total del componente envuelto.
    """

    nombre: str = ""
    etiqueta: str = "Ajuste"

    def __init__(self, componente: CostoEnergia) -> None:
        self._componente = componente

    @property
    def componente(self) -> CostoEnergia:
        return self._componente

    def _valor_ajuste(self, subtotal: float) -> float:
        return 0.0

    def total(self) -> float:
        subtotal = self._componente.total()  # 1) delega
        return round(subtotal + self._valor_ajuste(subtotal), 2)  # 2) añade su capa

    def desglose(self) -> list[dict]:
        lineas = self._componente.desglose()
        subtotal = self._componente.total()
        lineas.append(
            {
                "concepto": self.etiqueta,
                "valor": round(self._valor_ajuste(subtotal), 2),
                "acumulado": self.total(),
            }
        )
        return lineas


class AjustePorcentual(AjusteCosto):
    """Decorador intermedio: ajuste proporcional al subtotal acumulado."""

    porcentaje: float = 0.0

    def _valor_ajuste(self, subtotal: float) -> float:
        return round(subtotal * self.porcentaje, 2)


# ---------------------------------------------------------------------------
# CONCRETE DECORATORS — una capa cada uno
# ---------------------------------------------------------------------------
class DescuentoEnergiaRenovable(AjustePorcentual):
    nombre = "renovable"
    etiqueta = "Descuento energía renovable (-10%)"
    porcentaje = -0.10


class DescuentoCompradorFrecuente(AjustePorcentual):
    nombre = "frecuente"
    etiqueta = "Descuento comprador frecuente (-5%)"
    porcentaje = -0.05


class RecargoHoraPico(AjustePorcentual):
    nombre = "hora_pico"
    etiqueta = "Recargo hora pico (+15%)"
    porcentaje = 0.15


class ComisionPlataforma(AjustePorcentual):
    nombre = "comision"
    etiqueta = "Comisión de la plataforma (+5%)"
    porcentaje = 0.05


class CargoUsoRed(AjusteCosto):
    """Ajuste de valor fijo: no depende del subtotal."""

    nombre = "uso_red"
    etiqueta = "Cargo fijo por uso de la red (+$0.20)"
    valor_fijo = 0.20

    def _valor_ajuste(self, subtotal: float) -> float:
        return self.valor_fijo


# ---------------------------------------------------------------------------
# Registro de ajustes disponibles
# ---------------------------------------------------------------------------
_AJUSTES: dict[str, type[AjusteCosto]] = {
    clase.nombre: clase
    for clase in (
        DescuentoEnergiaRenovable,
        DescuentoCompradorFrecuente,
        RecargoHoraPico,
        CargoUsoRed,
        ComisionPlataforma,
    )
}

AJUSTES_DISPONIBLES = tuple(_AJUSTES)


def obtener_ajuste(nombre: str) -> type[AjusteCosto]:
    """
    Punto único donde se resuelve la clase decoradora por nombre. Un ajuste
    desconocido lanza `ValueError` con los disponibles, igual que las demás
    fábricas/registros del proyecto.
    """
    try:
        return _AJUSTES[nombre]
    except KeyError:
        disponibles = ", ".join(_AJUSTES)
        raise ValueError(f"Ajuste de precio '{nombre}' no soportado. Disponibles: {disponibles}")


def aplicar_ajustes(costo: CostoEnergia, nombres: Iterable[str]) -> CostoEnergia:
    """Envuelve `costo` con cada ajuste, en el orden recibido (el primero queda más adentro)."""
    for nombre in nombres:
        costo = obtener_ajuste(nombre)(costo)
    return costo
