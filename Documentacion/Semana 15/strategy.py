"""
Patrón Strategy — regla de precio de cierre de la subasta de energía.

Problema: cuando una orden de compra y una de venta se cruzan (el comprador
ofrece pagar al menos lo que pide el vendedor) hay que decidir a qué precio
se cierra el trato. Hay varias reglas válidas y cada comunidad energética
prefiere una distinta: pagar lo que pide el vendedor (favorece al
comprador), lo que ofrece el comprador (favorece al vendedor) o repartir la
diferencia a partes iguales. Si el motor de subasta resolviera esto con un
if/elif, cada regla nueva obligaría a modificar y volver a probar el motor,
y no se podría cambiar la regla mientras la plataforma está en marcha.

Solución (Strategy):

    - Strategy `EstrategiaPrecio`: interfaz común `precio_cierre(compra, venta)`.
    - Concrete Strategies `PrecioVendedor`, `PrecioComprador` y
      `PrecioPuntoMedio`: cada una encapsula UNA regla.
    - Context `MotorSubasta`: empareja órdenes por prioridad de precio y
      delega en la estrategia que tenga configurada el precio de cada
      cierre. La estrategia se inyecta al crearlo y se puede reemplazar en
      tiempo de ejecución (`motor.estrategia = ...`).

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 15/strategy.py"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Orden:
    usuario: str
    tipo: str  # "compra" | "venta"
    cantidad_kwh: float
    precio_kwh: float

    def __post_init__(self) -> None:
        if self.tipo not in ("compra", "venta"):
            raise ValueError("El tipo debe ser 'compra' o 'venta'")
        if self.cantidad_kwh <= 0 or self.precio_kwh <= 0:
            raise ValueError("Cantidad y precio deben ser positivos")


@dataclass(frozen=True)
class Transaccion:
    comprador: str
    vendedor: str
    cantidad_kwh: float
    precio_kwh: float
    estrategia: str

    @property
    def total(self) -> float:
        return round(self.cantidad_kwh * self.precio_kwh, 2)


# ===========================================================================
# STRATEGY — interfaz común de las reglas de precio
# ===========================================================================
class EstrategiaPrecio(ABC):
    nombre: str = ""
    descripcion: str = ""

    @abstractmethod
    def precio_cierre(self, compra: Orden, venta: Orden) -> float:
        """Precio por kWh al que se cierra el cruce (venta.precio <= compra.precio)."""


# ===========================================================================
# CONCRETE STRATEGIES — una regla por clase
# ===========================================================================
class PrecioVendedor(EstrategiaPrecio):
    nombre = "vendedor"
    descripcion = "Se paga lo que pide el vendedor (pay-as-ask): el ahorro queda para el comprador"

    def precio_cierre(self, compra: Orden, venta: Orden) -> float:
        return venta.precio_kwh


class PrecioComprador(EstrategiaPrecio):
    nombre = "comprador"
    descripcion = "Se paga lo que ofrece el comprador (pay-as-bid): la ganancia queda para el vendedor"

    def precio_cierre(self, compra: Orden, venta: Orden) -> float:
        return compra.precio_kwh


class PrecioPuntoMedio(EstrategiaPrecio):
    nombre = "punto_medio"
    descripcion = "Se reparte la diferencia a partes iguales entre comprador y vendedor"

    def precio_cierre(self, compra: Orden, venta: Orden) -> float:
        return round((compra.precio_kwh + venta.precio_kwh) / 2, 2)


ESTRATEGIAS: dict[str, type[EstrategiaPrecio]] = {
    e.nombre: e for e in (PrecioVendedor, PrecioComprador, PrecioPuntoMedio)
}


def crear_estrategia(nombre: str) -> EstrategiaPrecio:
    try:
        return ESTRATEGIAS[nombre]()
    except KeyError:
        raise ValueError(
            f"Estrategia '{nombre}' no soportada. Disponibles: {', '.join(ESTRATEGIAS)}"
        ) from None


# ===========================================================================
# CONTEXT — el motor de subasta no sabe qué regla de precio usa
# ===========================================================================
class MotorSubasta:
    def __init__(self, estrategia: EstrategiaPrecio) -> None:
        self.estrategia = estrategia

    @property
    def estrategia(self) -> EstrategiaPrecio:
        return self._estrategia

    @estrategia.setter
    def estrategia(self, estrategia: EstrategiaPrecio) -> None:
        if not isinstance(estrategia, EstrategiaPrecio):
            raise TypeError("La estrategia debe implementar EstrategiaPrecio")
        self._estrategia = estrategia

    def ejecutar(self, ordenes: list[Orden]) -> list[Transaccion]:
        """Cruza compras caras con ventas baratas; el precio lo pone la estrategia."""
        compras = sorted((o for o in ordenes if o.tipo == "compra"), key=lambda o: -o.precio_kwh)
        ventas = sorted((o for o in ordenes if o.tipo == "venta"), key=lambda o: o.precio_kwh)
        transacciones = []
        for compra in compras:
            for venta in ventas:
                if venta.precio_kwh > compra.precio_kwh or compra.cantidad_kwh == 0:
                    break
                if venta.cantidad_kwh == 0:
                    continue
                cantidad = round(min(compra.cantidad_kwh, venta.cantidad_kwh), 6)
                precio = self._estrategia.precio_cierre(compra, venta)
                compra.cantidad_kwh = round(compra.cantidad_kwh - cantidad, 6)
                venta.cantidad_kwh = round(venta.cantidad_kwh - cantidad, 6)
                transacciones.append(
                    Transaccion(compra.usuario, venta.usuario, cantidad, precio, self._estrategia.nombre)
                )
        return transacciones


if __name__ == "__main__":
    def libro() -> list[Orden]:
        return [
            Orden("ana", "venta", 5, 440),
            Orden("luis", "venta", 3, 470),
            Orden("marta", "compra", 6, 500),
        ]

    motor = MotorSubasta(PrecioVendedor())
    for nombre in ESTRATEGIAS:
        motor.estrategia = crear_estrategia(nombre)  # se cambia en caliente
        print(f"\nEstrategia '{nombre}': {motor.estrategia.descripcion}")
        for tx in motor.ejecutar(libro()):
            print(f"  {tx.vendedor} -> {tx.comprador}: {tx.cantidad_kwh} kWh a {tx.precio_kwh} = {tx.total}")
