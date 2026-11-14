"""
Plataforma de Comercio de Energía — versiones de la configuración del hogar
(patrón Memento). Consumido por plataforma.py (configuracion_hogar,
cambiar_configuracion, deshacer/rehacer) y main.py (/hogar/configuracion).

    - Originator `ConfiguracionHogar`: reglas que usa la central de energía
      (Mediator): reserva mínima de batería, precio de venta del excedente,
      precio máximo de compra y si se vende o no.
    - Memento `MementoConfiguracion`: instantánea inmutable; hacia afuera
      solo muestra etiqueta y fecha.
    - Caretaker `HistorialConfiguracion`: pilas de deshacer/rehacer, con
      límite de versiones, sin abrir nunca los mementos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

CAMPOS = ("reserva_minima_pct", "precio_venta_kwh", "precio_compra_max_kwh", "vender_excedente")


class SinVersiones(LookupError):
    """No hay versión a la cual deshacer o rehacer."""


@dataclass(frozen=True)
class MementoConfiguracion:
    etiqueta: str
    creado: datetime
    _estado: Mapping[str, Any] = field(repr=False)


class ConfiguracionHogar:
    def __init__(
        self,
        reserva_minima_pct: float = 20.0,
        precio_venta_kwh: float = 0.15,
        precio_compra_max_kwh: float = 0.20,
        vender_excedente: bool = True,
    ) -> None:
        self.reserva_minima_pct = reserva_minima_pct
        self.precio_venta_kwh = precio_venta_kwh
        self.precio_compra_max_kwh = precio_compra_max_kwh
        self.vender_excedente = vender_excedente
        self._validar()

    def _validar(self) -> None:
        if not 0 <= self.reserva_minima_pct <= 100:
            raise ValueError("La reserva mínima debe estar entre 0 y 100 %")
        if self.precio_venta_kwh <= 0 or self.precio_compra_max_kwh <= 0:
            raise ValueError("Los precios deben ser positivos")

    def actualizar(self, **cambios: Any) -> None:
        desconocidos = set(cambios) - set(CAMPOS)
        if desconocidos:
            raise ValueError(f"Campos desconocidos: {', '.join(sorted(desconocidos))}")
        anterior = self.guardar("antes de actualizar")
        for campo, valor in cambios.items():
            setattr(self, campo, valor)
        try:
            self._validar()
        except ValueError:
            self.restaurar(anterior)
            raise

    def guardar(self, etiqueta: str) -> MementoConfiguracion:
        estado = MappingProxyType({campo: getattr(self, campo) for campo in CAMPOS})
        return MementoConfiguracion(etiqueta, datetime.now(), estado)

    def restaurar(self, memento: MementoConfiguracion) -> None:
        for campo, valor in memento._estado.items():
            setattr(self, campo, valor)

    def to_dict(self) -> dict:
        return {campo: getattr(self, campo) for campo in CAMPOS}


class HistorialConfiguracion:
    def __init__(self, configuracion: ConfiguracionHogar, limite: int = 10) -> None:
        if limite < 1:
            raise ValueError("El historial debe conservar al menos una versión")
        self._configuracion = configuracion
        self._limite = limite
        self._deshacer: list[MementoConfiguracion] = []
        self._rehacer: list[MementoConfiguracion] = []

    def cambiar(self, etiqueta: str, **cambios: Any) -> None:
        respaldo = self._configuracion.guardar(etiqueta)
        self._configuracion.actualizar(**cambios)
        self._deshacer.append(respaldo)
        if len(self._deshacer) > self._limite:
            self._deshacer.pop(0)
        self._rehacer.clear()

    def deshacer(self) -> MementoConfiguracion:
        if not self._deshacer:
            raise SinVersiones("No hay cambios para deshacer")
        memento = self._deshacer.pop()
        self._rehacer.append(self._configuracion.guardar(memento.etiqueta))
        self._configuracion.restaurar(memento)
        return memento

    def rehacer(self) -> MementoConfiguracion:
        if not self._rehacer:
            raise SinVersiones("No hay cambios para rehacer")
        memento = self._rehacer.pop()
        self._deshacer.append(self._configuracion.guardar(memento.etiqueta))
        self._configuracion.restaurar(memento)
        return memento

    @property
    def puede_deshacer(self) -> bool:
        return bool(self._deshacer)

    @property
    def puede_rehacer(self) -> bool:
        return bool(self._rehacer)

    def versiones(self) -> list[dict]:
        return [{"etiqueta": m.etiqueta, "creado": m.creado.isoformat()} for m in self._deshacer]
