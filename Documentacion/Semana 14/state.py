"""
Patrón State — ciclo de vida de una orden del mercado de energía.

Problema: una orden de compra o venta no se comporta igual durante toda su
vida. Recién publicada se puede ejecutar o cancelar; cuando la subasta la
ejecuta en parte sigue negociable por lo que le falta; cuando se completa ya
no se puede tocar; y una orden cancelada no puede volver al mercado. Si cada
operación de la orden decidiera con if/elif sobre un campo `estado` (texto),
esas reglas quedarían repartidas por toda la plataforma, y agregar un estado
nuevo (por ejemplo "suspendida") obligaría a revisar cada condicional.

Solución (State): la orden (Context) delega `ejecutar` y `cancelar` en su
objeto estado actual. Cada estado concreto decide qué está permitido y a qué
estado se pasa:

    Abierta ──ejecutar parcial──▶ ParcialmenteEjecutada ──ejecutar resto──▶ Completada
       │  └────────ejecutar todo───────────────────────────────────────────▶ Completada
       │                               │
       └──cancelar──▶ Cancelada ◀──cancelar──┘

`Completada` y `Cancelada` son estados finales: cualquier operación lanza
`TransicionInvalida`. Los estados no guardan datos (la cantidad pendiente
vive en la orden), por eso se comparten como instancias únicas.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 14/state.py"
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TransicionInvalida(ValueError):
    """La operación no está permitida en el estado actual de la orden."""


# ===========================================================================
# STATE — interfaz común de los estados de una orden
# ===========================================================================
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

    def __repr__(self) -> str:
        return self.nombre


# ===========================================================================
# CONCRETE STATES
# ===========================================================================
class _EstadoNegociable(EstadoOrden):
    """Comportamiento compartido por Abierta y ParcialmenteEjecutada."""

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


# Los estados no tienen datos propios: una sola instancia de cada uno basta.
ABIERTA = Abierta()
PARCIAL = ParcialmenteEjecutada()
COMPLETADA = Completada()
CANCELADA = Cancelada()


# ===========================================================================
# CONTEXT — la orden delega su comportamiento en el estado actual
# ===========================================================================
class Orden:
    def __init__(self, id_: int, usuario_id: str, tipo: str, cantidad_kwh: float, precio_kwh: float) -> None:
        self.id = id_
        self.usuario_id = usuario_id
        self.tipo = tipo
        self.cantidad_inicial = cantidad_kwh
        self.cantidad_kwh = cantidad_kwh  # pendiente por ejecutar
        self.precio_kwh = precio_kwh
        self._estado: EstadoOrden = ABIERTA
        self.historial_estados: list[str] = [ABIERTA.nombre]

    @property
    def estado(self) -> EstadoOrden:
        return self._estado

    def cambiar_estado(self, nuevo: EstadoOrden) -> None:
        """Solo lo invocan los estados: la orden no decide sus transiciones."""
        self._estado = nuevo
        self.historial_estados.append(nuevo.nombre)

    def ejecutar(self, cantidad_kwh: float) -> None:
        self._estado.ejecutar(self, cantidad_kwh)

    def cancelar(self) -> None:
        self._estado.cancelar(self)

    def puede_negociar(self) -> bool:
        return self._estado.puede_negociar()


if __name__ == "__main__":
    orden = Orden(1, "ana", "venta", 10, 450)
    print(f"Orden publicada: estado={orden.estado}, pendiente={orden.cantidad_kwh} kWh")

    orden.ejecutar(4)
    print(f"La subasta ejecuta 4 kWh: estado={orden.estado}, pendiente={orden.cantidad_kwh} kWh")

    orden.ejecutar(6)
    print(f"La subasta ejecuta 6 kWh: estado={orden.estado}, pendiente={orden.cantidad_kwh} kWh")

    try:
        orden.cancelar()
    except TransicionInvalida as exc:
        print(f"Intento de cancelar: rechazado -> {exc}")

    otra = Orden(2, "luis", "compra", 5, 500)
    otra.cancelar()
    print(f"\nOrden 2 cancelada antes de negociar: estado={otra.estado}, ¿negociable? {otra.puede_negociar()}")
    print(f"Historial orden 1: {' -> '.join(orden.historial_estados)}")
