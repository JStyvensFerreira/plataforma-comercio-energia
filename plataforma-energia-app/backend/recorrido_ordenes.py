"""
Plataforma de Comercio de Energía — recorridos del libro de órdenes (patrón
Iterator). Consumido por plataforma.py (libro_ordenes, ejecutar_subasta) y
main.py (GET /ordenes?recorrido=...&usuario=...).

`LibroOrdenes` envuelve las listas de órdenes de la plataforma sin
exponerlas y entrega iteradores con una interfaz común:

    - IteradorLlegada:   orden de publicación.
    - IteradorPrioridad: precio-tiempo (ventas baratas primero, compras
      caras primero; empate por llegada), con un montículo: la subasta solo
      "ordena" lo que consume y se detiene en cuanto los precios no cruzan.
    - IteradorFiltrado:  envuelve otro iterador (por usuario, negociables).

Cada iterador recorre una instantánea tomada al crearlo.
"""

from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Iterable, Optional

if TYPE_CHECKING:
    from plataforma import Orden

VENTA = "venta"
COMPRA = "compra"
RECORRIDOS = ("llegada", "prioridad")


class IteradorOrdenes(ABC):
    @abstractmethod
    def tiene_siguiente(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def siguiente(self) -> "Orden":
        raise NotImplementedError

    @abstractmethod
    def reiniciar(self) -> None:
        raise NotImplementedError

    def __iter__(self) -> "IteradorOrdenes":
        return self

    def __next__(self) -> "Orden":
        return self.siguiente()


class IteradorLlegada(IteradorOrdenes):
    def __init__(self, ordenes: Iterable["Orden"]) -> None:
        self._ordenes = list(ordenes)
        self._posicion = 0

    def tiene_siguiente(self) -> bool:
        return self._posicion < len(self._ordenes)

    def siguiente(self) -> "Orden":
        if not self.tiene_siguiente():
            raise StopIteration
        orden = self._ordenes[self._posicion]
        self._posicion += 1
        return orden

    def reiniciar(self) -> None:
        self._posicion = 0


class IteradorPrioridad(IteradorOrdenes):
    def __init__(self, ordenes: Iterable["Orden"]) -> None:
        self._base = [
            (o.precio_kwh if o.tipo == VENTA else -o.precio_kwh, llegada, o)
            for llegada, o in enumerate(ordenes)
        ]
        self.reiniciar()

    def tiene_siguiente(self) -> bool:
        return bool(self._monticulo)

    def siguiente(self) -> "Orden":
        if not self._monticulo:
            raise StopIteration
        return heapq.heappop(self._monticulo)[2]

    def reiniciar(self) -> None:
        self._monticulo = list(self._base)
        heapq.heapify(self._monticulo)


class IteradorFiltrado(IteradorOrdenes):
    def __init__(self, interno: IteradorOrdenes, criterio: Callable[["Orden"], bool]) -> None:
        self._interno = interno
        self._criterio = criterio
        self._pendiente: Optional["Orden"] = None

    def _avanzar(self) -> None:
        while self._pendiente is None and self._interno.tiene_siguiente():
            candidata = self._interno.siguiente()
            if self._criterio(candidata):
                self._pendiente = candidata

    def tiene_siguiente(self) -> bool:
        self._avanzar()
        return self._pendiente is not None

    def siguiente(self) -> "Orden":
        if not self.tiene_siguiente():
            raise StopIteration
        orden, self._pendiente = self._pendiente, None
        return orden

    def reiniciar(self) -> None:
        self._interno.reiniciar()
        self._pendiente = None


class LibroOrdenes:
    """Aggregate: vista sobre las listas de órdenes activas de la plataforma."""

    def __init__(self, ventas: list["Orden"], compras: list["Orden"]) -> None:
        self._ventas = ventas
        self._compras = compras

    def _seleccion(self, tipo: Optional[str]) -> list["Orden"]:
        if tipo == VENTA:
            return self._ventas
        if tipo == COMPRA:
            return self._compras
        if tipo is None:
            return sorted(self._ventas + self._compras, key=lambda o: o.id)
        raise ValueError(f"Tipo de orden desconocido: {tipo}")

    def crear_iterador(self, recorrido: str = "llegada", tipo: Optional[str] = None) -> IteradorOrdenes:
        ordenes = self._seleccion(tipo)
        if recorrido == "llegada":
            return IteradorLlegada(ordenes)
        if recorrido == "prioridad":
            if tipo is None:
                raise ValueError("La prioridad precio-tiempo exige indicar 'venta' o 'compra'")
            return IteradorPrioridad(ordenes)
        raise ValueError(f"Recorrido '{recorrido}' no soportado. Disponibles: {', '.join(RECORRIDOS)}")

    def recorrer(self, recorrido: str, tipo: str, usuario_id: Optional[str] = None) -> IteradorOrdenes:
        iterador = self.crear_iterador(recorrido, tipo)
        if usuario_id:
            iterador = IteradorFiltrado(iterador, lambda o: o.usuario_id == usuario_id)
        return iterador

    def negociables(self, tipo: str) -> IteradorOrdenes:
        """Lo que usa la subasta: prioridad precio-tiempo, sin órdenes cerradas."""
        return IteradorFiltrado(self.crear_iterador("prioridad", tipo), lambda o: o.puede_negociar())
