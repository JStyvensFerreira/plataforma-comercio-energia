"""
Plataforma de Comercio de Energía — central de energía del hogar (patrón
Mediator). Consumido por plataforma.py (coordinar_hogar) y main.py
(POST /hogar/coordinar).

Panel solar, medidor, batería y punto de mercado no se conocen entre sí:
cada uno solo avisa a `CentralEnergiaHogar`, que aplica la regla de balance
de cada intervalo:

    excedente = generación - consumo
    > 0  →  cargar la batería; lo que no quepa se vende (o se vierte).
    < 0  →  descargar la batería sin romper la reserva; el resto se compra.

Las reglas (reserva, precios, vender o no) las lee de la configuración del
hogar, que se versiona con el patrón Memento (configuracion_hogar.py). El
punto de mercado no publica órdenes por su cuenta: recibe las funciones de
la plataforma (`publicar_venta` / `publicar_compra`), así las órdenes que
decide la central entran al mismo libro, con su estado y sus eventos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

GENERACION = "generacion"
CONSUMO = "consumo"
CAPACIDAD_POR_BATERIA_KWH = 10.0


def _r(valor: float) -> float:
    return round(valor, 6)


class MediadorEnergia(ABC):
    @abstractmethod
    def notificar(self, emisor: "Componente", evento: str, valor: float) -> None:
        raise NotImplementedError


class Componente:
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.mediador: Optional[MediadorEnergia] = None

    def _avisar(self, evento: str, valor: float) -> None:
        if self.mediador is None:
            raise RuntimeError(f"{self.nombre} no está conectado a ninguna central")
        self.mediador.notificar(self, evento, valor)


class PanelSolar(Componente):
    def reportar_generacion(self, kwh: float) -> None:
        if kwh < 0:
            raise ValueError("La generación no puede ser negativa")
        self._avisar(GENERACION, kwh)


class Medidor(Componente):
    def reportar_consumo(self, kwh: float) -> None:
        if kwh < 0:
            raise ValueError("El consumo no puede ser negativo")
        self._avisar(CONSUMO, kwh)


class Bateria(Componente):
    def __init__(self, nombre: str, capacidad_kwh: float, carga_kwh: float = 0.0) -> None:
        super().__init__(nombre)
        self.capacidad_kwh = capacidad_kwh
        self.carga_kwh = min(carga_kwh, capacidad_kwh)

    @property
    def nivel_pct(self) -> float:
        return round(100 * self.carga_kwh / self.capacidad_kwh, 2) if self.capacidad_kwh else 0.0

    def ajustar_capacidad(self, capacidad_kwh: float) -> None:
        """Cambia al conectar/clonar baterías; la carga no puede superar la capacidad."""
        self.capacidad_kwh = capacidad_kwh
        self.carga_kwh = min(self.carga_kwh, capacidad_kwh)

    def cargar(self, kwh: float) -> float:
        aceptado = _r(min(kwh, self.capacidad_kwh - self.carga_kwh))
        self.carga_kwh = _r(self.carga_kwh + aceptado)
        return aceptado

    def descargar(self, kwh: float, reserva_kwh: float = 0.0) -> float:
        entregado = _r(max(0.0, min(kwh, self.carga_kwh - reserva_kwh)))
        self.carga_kwh = _r(self.carga_kwh - entregado)
        return entregado

    def to_dict(self) -> dict:
        return {"capacidad_kwh": self.capacidad_kwh, "carga_kwh": self.carga_kwh, "nivel_pct": self.nivel_pct}


class PuntoMercado(Componente):
    def __init__(
        self,
        publicar_venta: Callable[[float, float], Any],
        publicar_compra: Callable[[float, float], Any],
        nombre: str = "mercado",
    ) -> None:
        super().__init__(nombre)
        self._publicar_venta = publicar_venta
        self._publicar_compra = publicar_compra
        self.ordenes: list[Any] = []

    def vender(self, kwh: float, precio_kwh: float) -> None:
        self.ordenes.append(self._publicar_venta(kwh, precio_kwh))

    def comprar(self, kwh: float, precio_kwh: float) -> None:
        self.ordenes.append(self._publicar_compra(kwh, precio_kwh))


class CentralEnergiaHogar(MediadorEnergia):
    """
    `reglas` es cualquier objeto con reserva_minima_pct, precio_venta_kwh,
    precio_compra_max_kwh y vender_excedente (en la app, la
    ConfiguracionHogar versionada con Memento).
    """

    def __init__(self, panel: PanelSolar, medidor: Medidor, bateria: Bateria, mercado: PuntoMercado, reglas) -> None:
        self.panel, self.medidor, self.bateria, self.mercado = panel, medidor, bateria, mercado
        self.reglas = reglas
        for componente in (panel, medidor, bateria, mercado):
            componente.mediador = self
        self._generacion: Optional[float] = None
        self._consumo: Optional[float] = None
        self.registro: list[str] = []

    def notificar(self, emisor: Componente, evento: str, valor: float) -> None:
        if emisor is self.panel and evento == GENERACION:
            self._generacion = valor
        elif emisor is self.medidor and evento == CONSUMO:
            self._consumo = valor
        else:
            raise ValueError(f"Evento '{evento}' de {emisor.nombre} no reconocido")
        self.registro.append(f"{emisor.nombre} reporta {evento}: {valor} kWh")
        if self._generacion is not None and self._consumo is not None:
            self._balancear(self._generacion, self._consumo)
            self._generacion = self._consumo = None

    def _balancear(self, generacion: float, consumo: float) -> None:
        excedente = _r(generacion - consumo)
        if excedente > 0:
            self._repartir_excedente(excedente)
        elif excedente < 0:
            self._cubrir_deficit(-excedente)
        else:
            self.registro.append("Generación y consumo empatan: no se mueve energía")

    def _repartir_excedente(self, excedente: float) -> None:
        cargado = self.bateria.cargar(excedente)
        if cargado:
            self.registro.append(f"{self.bateria.nombre} carga {cargado} kWh ({self.bateria.nivel_pct}%)")
        resto = _r(excedente - cargado)
        if resto <= 0:
            return
        if self.reglas.vender_excedente:
            self.mercado.vender(resto, self.reglas.precio_venta_kwh)
            self.registro.append(f"Se publica venta de {resto} kWh a {self.reglas.precio_venta_kwh} $/kWh")
        else:
            self.registro.append(f"Se vierten {resto} kWh a la red sin vender")

    def _cubrir_deficit(self, deficit: float) -> None:
        reserva = self.bateria.capacidad_kwh * self.reglas.reserva_minima_pct / 100
        entregado = self.bateria.descargar(deficit, reserva)
        if entregado:
            self.registro.append(f"{self.bateria.nombre} entrega {entregado} kWh ({self.bateria.nivel_pct}%)")
        faltante = _r(deficit - entregado)
        if faltante > 0:
            self.mercado.comprar(faltante, self.reglas.precio_compra_max_kwh)
            self.registro.append(
                f"Se publica compra de {faltante} kWh hasta {self.reglas.precio_compra_max_kwh} $/kWh"
            )
