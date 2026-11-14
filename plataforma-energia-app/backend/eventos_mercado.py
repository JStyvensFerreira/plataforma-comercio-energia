"""
Plataforma de Comercio de Energía — eventos del mercado (patrón Observer).
Consumido por plataforma.py (publicar_venta, publicar_compra,
ejecutar_subasta, cancelar_orden).

`MercadoEventos` (Subject) avisa a sus observadores cada vez que se publica,
ejecuta o cancela una orden, sin conocer sus clases concretas:
`EstadisticasMercado` (volumen y precio promedio) siempre está suscrito, y
cada usuario puede suscribir su propia `AlertaPrecio` en tiempo de ejecución.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

ORDEN_PUBLICADA = "orden_publicada"
TRANSACCION_EJECUTADA = "transaccion_ejecutada"
ORDEN_CANCELADA = "orden_cancelada"


@dataclass(frozen=True)
class EventoMercado:
    tipo: str
    datos: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class ObservadorMercado(ABC):
    @abstractmethod
    def actualizar(self, evento: EventoMercado) -> None:
        raise NotImplementedError


class MercadoEventos:
    """Subject: lista de observadores + aviso a todos ante cada evento."""

    def __init__(self) -> None:
        self._observadores: list[ObservadorMercado] = []
        self.errores: list[str] = []

    @property
    def observadores(self) -> tuple[ObservadorMercado, ...]:
        return tuple(self._observadores)

    def suscribir(self, observador: ObservadorMercado) -> None:
        if observador not in self._observadores:
            self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorMercado) -> None:
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar(self, tipo: str, datos: dict) -> None:
        evento = EventoMercado(tipo, datos)
        for observador in list(self._observadores):
            try:
                observador.actualizar(evento)
            except Exception as exc:  # un observador defectuoso no frena la subasta
                self.errores.append(f"{type(observador).__name__}: {exc}")


@dataclass(eq=False)
class AlertaPrecio(ObservadorMercado):
    """
    Avisa a `usuario_id` cuando se publica una venta de OTRO usuario a un
    precio <= `precio_max`. Cómo llega el aviso (bandeja + canal del usuario)
    lo decide quien la crea, a través de `entregar`.
    """

    usuario_id: str
    precio_max: float
    entregar: Callable[[str, dict], None]
    disparos: int = 0

    def actualizar(self, evento: EventoMercado) -> None:
        orden = evento.datos
        if (
            evento.tipo == ORDEN_PUBLICADA
            and orden["tipo"] == "venta"
            and orden["usuario_id"] != self.usuario_id
            and orden["precio_kwh"] <= self.precio_max
        ):
            self.disparos += 1
            self.entregar(self.usuario_id, orden)

    def to_dict(self) -> dict:
        return {"usuario_id": self.usuario_id, "precio_max": self.precio_max, "disparos": self.disparos}


@dataclass(eq=False)
class EstadisticasMercado(ObservadorMercado):
    ordenes_publicadas: int = 0
    ordenes_canceladas: int = 0
    transacciones: int = 0
    volumen_kwh: float = 0.0
    monto_total: float = 0.0
    ultimos_eventos: list[dict] = field(default_factory=list)

    def actualizar(self, evento: EventoMercado) -> None:
        if evento.tipo == ORDEN_PUBLICADA:
            self.ordenes_publicadas += 1
        elif evento.tipo == ORDEN_CANCELADA:
            self.ordenes_canceladas += 1
        elif evento.tipo == TRANSACCION_EJECUTADA:
            self.transacciones += 1
            self.volumen_kwh += evento.datos["cantidad_kwh"]
            self.monto_total += evento.datos["cantidad_kwh"] * evento.datos["precio_kwh"]
        self.ultimos_eventos = (self.ultimos_eventos + [{"tipo": evento.tipo, "timestamp": evento.timestamp}])[-10:]

    @property
    def precio_promedio(self) -> float:
        """Precio promedio ponderado por volumen."""
        if self.volumen_kwh == 0:
            return 0.0
        return round(self.monto_total / self.volumen_kwh, 2)

    def to_dict(self) -> dict:
        return {
            "ordenes_publicadas": self.ordenes_publicadas,
            "ordenes_canceladas": self.ordenes_canceladas,
            "transacciones": self.transacciones,
            "volumen_kwh": round(self.volumen_kwh, 2),
            "precio_promedio": self.precio_promedio,
            "ultimos_eventos": list(self.ultimos_eventos),
        }
