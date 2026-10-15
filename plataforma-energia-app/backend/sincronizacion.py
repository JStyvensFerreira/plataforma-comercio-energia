"""
Plataforma de Comercio de Energía — protocolos de lectura de dispositivos
IoT (patrón Bridge). Consumido por plataforma.py (sincronizar_dispositivo).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
import random

if TYPE_CHECKING:
    from factory_method import DispositivoIoT


# ---------------------------------------------------------------------------
# IMPLEMENTOR — la jerarquía de "cómo se obtiene el dato"
# ---------------------------------------------------------------------------
class ProtocoloLectura(ABC):
    """Implementor: declara la operación que cada protocolo concreto implementa."""

    nombre: str = ""

    @abstractmethod
    def leer(self, dispositivo: "DispositivoIoT", ultima_lectura: Optional[float]) -> float:
        """Devuelve la lectura en kWh, o lanza ConnectionError si falla."""
        raise NotImplementedError


class ProtocoloSimulado(ProtocoloLectura):
    """ConcreteImplementor: un valor aleatorio genérico (el que ya usaba simular_lecturas)."""

    nombre = "simulado"

    def leer(self, dispositivo, ultima_lectura=None) -> float:
        return round(random.uniform(0.5, 4.0), 2)


class ProtocoloHTTP(ProtocoloLectura):
    """
    ConcreteImplementor: simula leer la API propia del fabricante del
    dispositivo. El valor queda dentro de SUS umbrales ya calibrados.
    """

    nombre = "http"
    tasa_falla: float = 0.0  # 0 por defecto: no introduce flakiness salvo que se pida

    def leer(self, dispositivo, ultima_lectura=None) -> float:
        if random.random() < self.tasa_falla:
            raise ConnectionError(f"El fabricante no respondió para '{dispositivo.id}' (HTTP)")
        lo = dispositivo.umbral_min if dispositivo.umbral_min is not None else 0.0
        hi = dispositivo.umbral_max if dispositivo.umbral_max is not None else 4.0
        if lo > hi:
            lo, hi = hi, lo
        return round(random.uniform(lo, hi), 2)


class ProtocoloMQTT(ProtocoloLectura):
    """
    ConcreteImplementor: simula un valor retenido por un broker MQTT, con
    una pequeña variación sobre la última lectura conocida del dispositivo.
    """

    nombre = "mqtt"
    tasa_falla: float = 0.0

    def leer(self, dispositivo, ultima_lectura=None) -> float:
        if random.random() < self.tasa_falla:
            raise ConnectionError(f"Sin mensaje reciente en el tópico de '{dispositivo.id}' (MQTT)")
        base = ultima_lectura if ultima_lectura is not None else 1.0
        return round(base + random.uniform(-0.3, 0.3), 2)


# ---------------------------------------------------------------------------
# ABSTRACTION — la jerarquía de "cómo se sincroniza"
# ---------------------------------------------------------------------------
class SincronizadorDispositivo:
    """Abstraction: el cliente delega la lectura en el protocolo recibido, sin conocerlo."""

    def __init__(self, protocolo: ProtocoloLectura) -> None:
        self._protocolo = protocolo

    @property
    def protocolo(self) -> ProtocoloLectura:
        return self._protocolo

    def sincronizar(self, dispositivo: "DispositivoIoT", ultima_lectura: Optional[float] = None) -> float:
        return self._protocolo.leer(dispositivo, ultima_lectura)


class SincronizadorConReintentos(SincronizadorDispositivo):
    """RefinedAbstraction: reintenta ante fallas de comunicación, sin importar el protocolo."""

    def __init__(self, protocolo: ProtocoloLectura, intentos: int = 3) -> None:
        super().__init__(protocolo)
        self.intentos = intentos
        self.intentos_usados = 0

    def sincronizar(self, dispositivo: "DispositivoIoT", ultima_lectura: Optional[float] = None) -> float:
        self.intentos_usados = 0
        error: Optional[ConnectionError] = None
        for _ in range(self.intentos):
            self.intentos_usados += 1
            try:
                return self._protocolo.leer(dispositivo, ultima_lectura)
            except ConnectionError as e:
                error = e
        raise error


# ---------------------------------------------------------------------------
# Registro de protocolos disponibles
# ---------------------------------------------------------------------------
_PROTOCOLOS: dict[str, type[ProtocoloLectura]] = {
    "simulado": ProtocoloSimulado,
    "http": ProtocoloHTTP,
    "mqtt": ProtocoloMQTT,
}

PROTOCOLOS_DISPONIBLES = tuple(_PROTOCOLOS)


def obtener_protocolo(nombre: str) -> ProtocoloLectura:
    """
    Punto único donde se resuelve el protocolo concreto por nombre. Un
    nombre desconocido lanza `ValueError` con los disponibles.
    """
    try:
        return _PROTOCOLOS[nombre]()
    except KeyError:
        disponibles = ", ".join(_PROTOCOLOS)
        raise ValueError(f"Protocolo de lectura '{nombre}' no soportado. Disponibles: {disponibles}")
