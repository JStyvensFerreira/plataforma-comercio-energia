"""
Plataforma de Comercio de Energía — regla de precio de cierre de la subasta
(patrón Strategy). Consumido por plataforma.py (ejecutar_subasta,
cambiar_estrategia_precio).

Cuando una compra y una venta se cruzan (venta.precio_kwh <= compra.precio_kwh)
la estrategia configurada decide a qué precio por kWh se cierra el trato.
La subasta no sabe qué regla está usando.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


class OrdenConPrecio(Protocol):
    precio_kwh: float


# ---------------------------------------------------------------------------
# STRATEGY
# ---------------------------------------------------------------------------
class EstrategiaPrecio(ABC):
    nombre: str = ""
    descripcion: str = ""

    @abstractmethod
    def precio_cierre(self, compra: OrdenConPrecio, venta: OrdenConPrecio) -> float:
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {"nombre": self.nombre, "descripcion": self.descripcion}


# ---------------------------------------------------------------------------
# CONCRETE STRATEGIES
# ---------------------------------------------------------------------------
class PrecioVendedor(EstrategiaPrecio):
    nombre = "vendedor"
    descripcion = "Se paga lo que pide el vendedor: el ahorro queda para el comprador"

    def precio_cierre(self, compra, venta) -> float:
        return venta.precio_kwh


class PrecioComprador(EstrategiaPrecio):
    nombre = "comprador"
    descripcion = "Se paga lo que ofrece el comprador: la ganancia queda para el vendedor"

    def precio_cierre(self, compra, venta) -> float:
        return compra.precio_kwh


class PrecioPuntoMedio(EstrategiaPrecio):
    nombre = "punto_medio"
    descripcion = "Se reparte la diferencia a partes iguales entre comprador y vendedor"

    def precio_cierre(self, compra, venta) -> float:
        return round((compra.precio_kwh + venta.precio_kwh) / 2, 4)


ESTRATEGIAS_DISPONIBLES: dict[str, type[EstrategiaPrecio]] = {
    e.nombre: e for e in (PrecioVendedor, PrecioComprador, PrecioPuntoMedio)
}


def crear_estrategia(nombre: str) -> EstrategiaPrecio:
    try:
        return ESTRATEGIAS_DISPONIBLES[nombre]()
    except KeyError:
        raise ValueError(
            f"Estrategia '{nombre}' no soportada. Disponibles: {', '.join(ESTRATEGIAS_DISPONIBLES)}"
        ) from None
