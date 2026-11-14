"""
Patrón Mediator — central de energía del hogar.

Problema: en un hogar prosumidor conviven varios componentes que dependen
unos de otros: el panel solar produce, el medidor registra el consumo, la
batería guarda energía y el punto de conexión con el mercado vende o compra
excedentes. Si cada componente hablara directamente con los demás (el panel
le pide a la batería que se cargue; si está llena le pide al mercado que
venda; el medidor le pide a la batería que se descargue y, si no alcanza,
le pide al mercado que compre...), se formaría una red de referencias
cruzadas: cambiar la regla "primero la batería, luego el mercado" obligaría
a tocar varias clases, y no se podría reutilizar la batería sin arrastrar
el panel y el mercado.

Solución (Mediator): `CentralEnergiaHogar` concentra la coordinación. Cada
componente (Colleague) solo conoce a la central y le avisa con
`notificar(emisor, evento, valor)`; la central decide qué hacer y da las
órdenes a los demás componentes:

    PanelSolar ──"generacion"──▶                 ┌──▶ Bateria.cargar / descargar
                               CentralEnergiaHogar
    Medidor    ──"consumo"────▶                 └──▶ PuntoMercado.vender / comprar

Regla de balance de cada intervalo (cuando la central ya tiene la lectura
del panel Y la del medidor):

    excedente = generación - consumo
    > 0  →  cargar la batería hasta su capacidad; el resto se vende en el
            mercado (o se vierte a la red si el hogar no quiere vender).
    < 0  →  descargar la batería sin bajar de la reserva mínima; lo que
            falte se compra en el mercado al precio máximo configurado.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 13/mediator.py"
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

GENERACION = "generacion"
CONSUMO = "consumo"


def _r(valor: float) -> float:
    """Redondeo para que los kWh no arrastren residuos de coma flotante."""
    return round(valor, 6)


# ===========================================================================
# MEDIATOR — interfaz con la que hablan los componentes
# ===========================================================================
class MediadorEnergia(ABC):
    @abstractmethod
    def notificar(self, emisor: "Componente", evento: str, valor: float) -> None:
        raise NotImplementedError


# ===========================================================================
# COLLEAGUES — solo conocen al mediador, nunca a otro componente
# ===========================================================================
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
        if capacidad_kwh < 0 or not 0 <= carga_kwh <= capacidad_kwh:
            raise ValueError("La carga debe estar entre 0 y la capacidad de la batería")
        self.capacidad_kwh = capacidad_kwh
        self.carga_kwh = carga_kwh

    @property
    def nivel_pct(self) -> float:
        return round(100 * self.carga_kwh / self.capacidad_kwh, 2) if self.capacidad_kwh else 0.0

    def cargar(self, kwh: float) -> float:
        """Guarda lo que quepa y devuelve cuánto aceptó."""
        aceptado = _r(min(kwh, self.capacidad_kwh - self.carga_kwh))
        self.carga_kwh = _r(self.carga_kwh + aceptado)
        return aceptado

    def descargar(self, kwh: float, reserva_kwh: float = 0.0) -> float:
        """Entrega lo que pueda sin bajar de la reserva y devuelve cuánto entregó."""
        entregado = _r(max(0.0, min(kwh, self.carga_kwh - reserva_kwh)))
        self.carga_kwh = _r(self.carga_kwh - entregado)
        return entregado


class PuntoMercado(Componente):
    """Conexión del hogar con el mercado: publica órdenes de venta y compra."""

    def __init__(self, nombre: str = "mercado") -> None:
        super().__init__(nombre)
        self.ordenes: list[dict] = []

    def vender(self, kwh: float, precio_kwh: float) -> dict:
        orden = {"tipo": "venta", "cantidad_kwh": kwh, "precio_kwh": precio_kwh}
        self.ordenes.append(orden)
        return orden

    def comprar(self, kwh: float, precio_kwh: float) -> dict:
        orden = {"tipo": "compra", "cantidad_kwh": kwh, "precio_kwh": precio_kwh}
        self.ordenes.append(orden)
        return orden


# ===========================================================================
# CONCRETE MEDIATOR — toda la coordinación vive aquí
# ===========================================================================
@dataclass
class ReglasHogar:
    reserva_minima_pct: float = 20.0
    precio_venta_kwh: float = 450.0
    precio_compra_max_kwh: float = 520.0
    vender_excedente: bool = True


class CentralEnergiaHogar(MediadorEnergia):
    def __init__(
        self,
        panel: PanelSolar,
        medidor: Medidor,
        bateria: Bateria,
        mercado: PuntoMercado,
        reglas: Optional[ReglasHogar] = None,
    ) -> None:
        self.panel, self.medidor, self.bateria, self.mercado = panel, medidor, bateria, mercado
        self.reglas = reglas or ReglasHogar()
        for componente in (panel, medidor, bateria, mercado):
            componente.mediador = self
        self._generacion: Optional[float] = None
        self._consumo: Optional[float] = None
        self.registro: list[str] = []

    # --- lo único que ven los componentes ---
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
            self._generacion = self._consumo = None  # empieza un intervalo nuevo

    # --- reglas de coordinación ---
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
            self.registro.append(f"Se venden {resto} kWh a {self.reglas.precio_venta_kwh} $/kWh")
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
            self.registro.append(f"Se compran {faltante} kWh hasta {self.reglas.precio_compra_max_kwh} $/kWh")


if __name__ == "__main__":
    panel, medidor = PanelSolar("panel"), Medidor("medidor")
    bateria, mercado = Bateria("bateria", capacidad_kwh=10, carga_kwh=6), PuntoMercado()
    central = CentralEnergiaHogar(panel, medidor, bateria, mercado, ReglasHogar(reserva_minima_pct=20))

    for titulo, generacion, consumo in (
        ("Mediodía: mucho sol, poco consumo", 9, 2),
        ("Noche: sin sol, consumo alto", 0, 11),
    ):
        print(titulo)
        desde = len(central.registro)
        panel.reportar_generacion(generacion)
        medidor.reportar_consumo(consumo)
        for linea in central.registro[desde:]:
            print("  ", linea)
    print(f"\nÓrdenes que la central envió al mercado: {mercado.ordenes}")
    print(f"Batería al final: {bateria.carga_kwh} kWh ({bateria.nivel_pct}%) — nunca bajó de la reserva del 20%")
