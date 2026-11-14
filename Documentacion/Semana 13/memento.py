"""
Patrón Memento — versiones de la configuración energética del hogar.

Problema: cada hogar prosumidor ajusta las reglas con las que la plataforma
gestiona su energía: qué porcentaje de batería guardar como reserva, a qué
precio vender el excedente, cuánto pagar como máximo al comprar y si vende
o no. Un cambio mal hecho (por ejemplo, vender a un precio demasiado bajo)
puede costar dinero, así que el usuario necesita DESHACER y REHACER cambios
y ver qué versiones guardó. Si otro objeto copiara los atributos de la
configuración para respaldarla, conocería su estructura interna: cada campo
nuevo obligaría a modificar el respaldo, y nada impediría alterar una copia
guardada.

Solución (Memento):

    - Originator `ConfiguracionHogar`: el único que sabe crear una
      instantánea de su estado (`guardar`) y volver a ella (`restaurar`).
    - Memento `MementoConfiguracion`: instantánea INMUTABLE (dataclass
      congelada). Hacia afuera solo expone metadatos (etiqueta y fecha); el
      estado viaja en un campo privado que solo lee el Originator.
    - Caretaker `HistorialConfiguracion`: guarda los mementos en dos pilas
      (deshacer / rehacer) sin mirar ni modificar su contenido. Respalda
      antes de cada cambio, limita cuántas versiones conserva y descarta
      la pila de rehacer cuando se hace un cambio nuevo.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 13/memento.py"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

CAMPOS = ("reserva_minima_pct", "precio_venta_kwh", "precio_compra_max_kwh", "vender_excedente")


class SinVersiones(LookupError):
    """No hay versión a la cual deshacer o rehacer."""


# ===========================================================================
# MEMENTO — instantánea inmutable; el Caretaker solo ve sus metadatos
# ===========================================================================
@dataclass(frozen=True)
class MementoConfiguracion:
    etiqueta: str
    creado: datetime
    _estado: Mapping[str, Any] = field(repr=False)


# ===========================================================================
# ORIGINATOR — la configuración sabe guardarse y restaurarse
# ===========================================================================
class ConfiguracionHogar:
    def __init__(
        self,
        reserva_minima_pct: float = 20.0,
        precio_venta_kwh: float = 450.0,
        precio_compra_max_kwh: float = 520.0,
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
        """Aplica los cambios; si el resultado no es válido, no cambia nada."""
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


# ===========================================================================
# CARETAKER — administra los mementos sin abrirlos
# ===========================================================================
class HistorialConfiguracion:
    def __init__(self, configuracion: ConfiguracionHogar, limite: int = 10) -> None:
        if limite < 1:
            raise ValueError("El historial debe conservar al menos una versión")
        self._configuracion = configuracion
        self._limite = limite
        self._deshacer: list[MementoConfiguracion] = []
        self._rehacer: list[MementoConfiguracion] = []

    def cambiar(self, etiqueta: str, **cambios: Any) -> None:
        """Respalda la versión actual y aplica el cambio. Un cambio inválido no deja respaldo."""
        respaldo = self._configuracion.guardar(etiqueta)
        self._configuracion.actualizar(**cambios)
        self._deshacer.append(respaldo)
        if len(self._deshacer) > self._limite:
            self._deshacer.pop(0)  # se descarta la versión más antigua
        self._rehacer.clear()  # un cambio nuevo invalida lo que se podía rehacer

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
        """Solo metadatos: el Caretaker nunca expone el estado guardado."""
        return [{"etiqueta": m.etiqueta, "creado": m.creado.isoformat()} for m in self._deshacer]


if __name__ == "__main__":
    config = ConfiguracionHogar()
    historial = HistorialConfiguracion(config)
    print(f"Inicial:              {config.to_dict()}")

    historial.cambiar("subir precio de venta", precio_venta_kwh=490)
    historial.cambiar("reserva para la noche", reserva_minima_pct=40)
    print(f"Tras dos cambios:     {config.to_dict()}")

    try:
        historial.cambiar("error de digitación", precio_venta_kwh=-5)
    except ValueError as exc:
        print(f"Cambio rechazado:     {exc} (la configuración no cambió)")

    print(f"Versiones guardadas:  {[v['etiqueta'] for v in historial.versiones()]}")
    deshecho = historial.deshacer()
    print(f"Deshacer '{deshecho.etiqueta}': {config.to_dict()}")
    historial.deshacer()
    print(f"Deshacer otra vez:    {config.to_dict()}")
    historial.rehacer()
    print(f"Rehacer:              {config.to_dict()}")
