"""
Patrón Iterator — recorridos del libro de órdenes del mercado de energía.

Problema: las órdenes de compra y venta se guardan en listas, pero cada parte
de la plataforma necesita recorrerlas de una forma distinta:

    - La subasta necesita la PRIORIDAD precio-tiempo: las ventas más baratas
      primero y las compras más caras primero; a igual precio, la que llegó
      antes.
    - El libro de órdenes que ve el usuario las muestra en orden de LLEGADA.
    - La vista "mis órdenes" solo recorre las de UN usuario.

Si cada cliente ordenara y filtrara la lista por su cuenta (`sorted(...)`,
`for i in range(len(...))`, `if o.usuario_id == ...`), todos quedarían
acoplados a la estructura interna del libro (listas, campos, criterio de
desempate) y la subasta tendría que reordenar la lista original en sitio,
alterando lo que ven los demás.

Solución (Iterator): `LibroOrdenes` (Aggregate) entrega iteradores que
encapsulan CÓMO se recorre, sin exponer cómo se almacenan las órdenes. Todos
implementan la misma interfaz `IteradorOrdenes` (`tiene_siguiente`,
`siguiente`, `reiniciar` y el protocolo de Python `__iter__`/`__next__`), de
modo que un cliente puede recorrer cualquiera con un `for` sin saber cuál es:

    - IteradorLlegada:   orden de publicación (FIFO).
    - IteradorPrioridad: precio-tiempo, implementado con un montículo
      (heapq): solo ordena lo que realmente se consume, útil cuando la
      subasta se detiene en cuanto los precios dejan de cruzarse.
    - IteradorFiltrado:  envuelve CUALQUIER otro iterador y solo deja pasar
      las órdenes que cumplen un predicado (por usuario, solo negociables).

Cada iterador trabaja sobre una instantánea de la colección tomada al
crearlo: si se publica una orden mientras otro cliente recorre el libro, ese
recorrido no se rompe ni cambia a mitad de camino.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 13/iterator.py"
"""

from __future__ import annotations

import heapq
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

VENTA = "venta"
COMPRA = "compra"


@dataclass
class Orden:
    id: int
    usuario_id: str
    tipo: str  # "venta" | "compra"
    cantidad_kwh: float
    precio_kwh: float
    negociable: bool = True

    def __repr__(self) -> str:
        return f"#{self.id} {self.tipo} {self.usuario_id} {self.cantidad_kwh}kWh@{self.precio_kwh}"


# ===========================================================================
# ITERATOR — interfaz común de todos los recorridos
# ===========================================================================
class IteradorOrdenes(ABC):
    @abstractmethod
    def tiene_siguiente(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def siguiente(self) -> Orden:
        """Devuelve la próxima orden; lanza StopIteration si no quedan."""
        raise NotImplementedError

    @abstractmethod
    def reiniciar(self) -> None:
        raise NotImplementedError

    # Protocolo de Python: permite usar cualquier iterador en un `for`.
    def __iter__(self) -> "IteradorOrdenes":
        return self

    def __next__(self) -> Orden:
        return self.siguiente()


# ===========================================================================
# CONCRETE ITERATORS
# ===========================================================================
class IteradorLlegada(IteradorOrdenes):
    """Recorre las órdenes en el orden en que se publicaron."""

    def __init__(self, ordenes: list[Orden]) -> None:
        self._ordenes = list(ordenes)  # instantánea
        self._posicion = 0

    def tiene_siguiente(self) -> bool:
        return self._posicion < len(self._ordenes)

    def siguiente(self) -> Orden:
        if not self.tiene_siguiente():
            raise StopIteration
        orden = self._ordenes[self._posicion]
        self._posicion += 1
        return orden

    def reiniciar(self) -> None:
        self._posicion = 0


class IteradorPrioridad(IteradorOrdenes):
    """
    Prioridad precio-tiempo: ventas de menor a mayor precio, compras de
    mayor a menor; a igual precio gana la que llegó antes (menor posición).
    Usa un montículo: cada `siguiente()` cuesta O(log n) y no hace falta
    ordenar todo el libro si el recorrido se corta antes.
    """

    def __init__(self, ordenes: list[Orden]) -> None:
        self._base = [(self._clave(o), llegada, o) for llegada, o in enumerate(ordenes)]
        self.reiniciar()

    @staticmethod
    def _clave(orden: Orden) -> float:
        return orden.precio_kwh if orden.tipo == VENTA else -orden.precio_kwh

    def tiene_siguiente(self) -> bool:
        return bool(self._monticulo)

    def siguiente(self) -> Orden:
        if not self._monticulo:
            raise StopIteration
        return heapq.heappop(self._monticulo)[2]

    def reiniciar(self) -> None:
        self._monticulo = list(self._base)
        heapq.heapify(self._monticulo)


class IteradorFiltrado(IteradorOrdenes):
    """Decora otro iterador: solo entrega las órdenes que cumplen `criterio`."""

    def __init__(self, interno: IteradorOrdenes, criterio: Callable[[Orden], bool]) -> None:
        self._interno = interno
        self._criterio = criterio
        self._pendiente: Optional[Orden] = None

    def _avanzar(self) -> None:
        while self._pendiente is None and self._interno.tiene_siguiente():
            candidata = self._interno.siguiente()
            if self._criterio(candidata):
                self._pendiente = candidata

    def tiene_siguiente(self) -> bool:
        self._avanzar()
        return self._pendiente is not None

    def siguiente(self) -> Orden:
        if not self.tiene_siguiente():
            raise StopIteration
        orden, self._pendiente = self._pendiente, None
        return orden

    def reiniciar(self) -> None:
        self._interno.reiniciar()
        self._pendiente = None


# ===========================================================================
# AGGREGATE — el libro de órdenes crea sus iteradores
# ===========================================================================
class ColeccionOrdenes(ABC):
    @abstractmethod
    def crear_iterador(self, recorrido: str = "llegada", tipo: Optional[str] = None) -> IteradorOrdenes:
        raise NotImplementedError


RECORRIDOS = ("llegada", "prioridad")


class LibroOrdenes(ColeccionOrdenes):
    def __init__(self) -> None:
        self._ventas: list[Orden] = []
        self._compras: list[Orden] = []

    def agregar(self, orden: Orden) -> None:
        if orden.tipo not in (VENTA, COMPRA):
            raise ValueError(f"Tipo de orden desconocido: {orden.tipo}")
        (self._ventas if orden.tipo == VENTA else self._compras).append(orden)

    def __len__(self) -> int:
        return len(self._ventas) + len(self._compras)

    def _seleccion(self, tipo: Optional[str]) -> list[Orden]:
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

    def ordenes_de(self, usuario_id: str) -> IteradorOrdenes:
        return IteradorFiltrado(self.crear_iterador(), lambda o: o.usuario_id == usuario_id)

    def negociables(self, tipo: str) -> IteradorOrdenes:
        """Lo que usa la subasta: prioridad precio-tiempo, sin órdenes cerradas."""
        return IteradorFiltrado(self.crear_iterador("prioridad", tipo), lambda o: o.negociable)

    # La colección también es iterable directamente (recorrido por defecto).
    def __iter__(self) -> Iterator[Orden]:
        return self.crear_iterador()


if __name__ == "__main__":
    libro = LibroOrdenes()
    for orden in (
        Orden(1, "ana", VENTA, 5, 480),
        Orden(2, "luis", COMPRA, 3, 500),
        Orden(3, "marta", VENTA, 2, 450),
        Orden(4, "ana", COMPRA, 4, 520),
        Orden(5, "pedro", VENTA, 6, 450),
        Orden(6, "luis", VENTA, 1, 470, negociable=False),
    ):
        libro.agregar(orden)

    print("Libro por llegada:")
    for orden in libro:
        print("  ", orden)

    print("\nVentas por prioridad (más baratas primero; empate -> llegó antes):")
    for orden in libro.crear_iterador("prioridad", VENTA):
        print("  ", orden)

    print("\nCompras por prioridad (más caras primero):")
    for orden in libro.crear_iterador("prioridad", COMPRA):
        print("  ", orden)

    print("\nVentas que la subasta puede negociar (filtro sobre la prioridad):")
    for orden in libro.negociables(VENTA):
        print("  ", orden)

    print("\nÓrdenes de ana:")
    it = libro.ordenes_de("ana")
    while it.tiene_siguiente():
        print("  ", it.siguiente())
