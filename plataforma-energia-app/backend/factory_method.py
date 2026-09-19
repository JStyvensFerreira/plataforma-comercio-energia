"""
Plataforma de Comercio de Energía — dispositivos IoT domésticos (patrón
Factory Method). Consumido por plataforma.py (conectar_dispositivo).
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional

# Rango "normal" de lectura por tipo de dispositivo. Una lectura fuera de este
# rango dispara una alerta IoT (patrón Abstract Factory: se notifica por el
# canal que el dueño del dispositivo tenga configurado).
UMBRALES_IOT: dict[str, tuple[float, float]] = {
    "panel_solar": (0.0, 3.5),
    "bateria": (-2.0, 2.0),
    "medidor": (-2.5, 0.5),
}


@dataclass
class DispositivoIoT:
    """Producto: dispositivo IoT conectado a la plataforma."""

    id: str
    usuario_id: str
    tipo: str
    umbral_min: Optional[float] = None
    umbral_max: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    def fuera_de_rango(self, lectura: float) -> Optional[float]:
        """Devuelve el umbral cruzado (o None si la lectura es normal)."""
        if self.umbral_min is not None and lectura < self.umbral_min:
            return self.umbral_min
        if self.umbral_max is not None and lectura > self.umbral_max:
            return self.umbral_max
        return None


class DispositivoIoTFactory(ABC):
    """
    Creador abstracto. Declara el Factory Method `crear_dispositivo` y una
    lógica común (`registrar`) que aplica los umbrales por defecto del tipo
    sin que el resto de la plataforma tenga que conocerlos ni decidir con
    un if/elif qué clase de dispositivo instanciar.
    """

    tipo: str = ""

    @abstractmethod
    def crear_dispositivo(
        self,
        id_dispositivo: str,
        usuario_id: str,
        umbral_min: Optional[float],
        umbral_max: Optional[float],
    ) -> DispositivoIoT:
        """Factory Method: cada subclase decide cómo construir su producto."""
        raise NotImplementedError

    def registrar(
        self,
        id_dispositivo: str,
        usuario_id: str,
        umbral_min: Optional[float] = None,
        umbral_max: Optional[float] = None,
    ) -> DispositivoIoT:
        """
        Lógica común a todas las fábricas: si no se indican umbrales propios
        (p. ej. de una calibración manual), aplica los umbrales por defecto
        del tipo antes de delegar la construcción al Factory Method.
        """
        if umbral_min is None and umbral_max is None:
            umbral_min, umbral_max = UMBRALES_IOT.get(self.tipo, (None, None))
        return self.crear_dispositivo(id_dispositivo, usuario_id, umbral_min, umbral_max)


class PanelSolarFactory(DispositivoIoTFactory):
    tipo = "panel_solar"

    def crear_dispositivo(self, id_dispositivo, usuario_id, umbral_min, umbral_max):
        return DispositivoIoT(id_dispositivo, usuario_id, self.tipo, umbral_min, umbral_max)


class BateriaFactory(DispositivoIoTFactory):
    tipo = "bateria"

    def crear_dispositivo(self, id_dispositivo, usuario_id, umbral_min, umbral_max):
        return DispositivoIoT(id_dispositivo, usuario_id, self.tipo, umbral_min, umbral_max)


class MedidorFactory(DispositivoIoTFactory):
    tipo = "medidor"

    def crear_dispositivo(self, id_dispositivo, usuario_id, umbral_min, umbral_max):
        return DispositivoIoT(id_dispositivo, usuario_id, self.tipo, umbral_min, umbral_max)


# ---------------------------------------------------------------------------
# Registro de fábricas disponibles
# ---------------------------------------------------------------------------
_FACTORIES: dict[str, DispositivoIoTFactory] = {
    "panel_solar": PanelSolarFactory(),
    "bateria": BateriaFactory(),
    "medidor": MedidorFactory(),
}

TIPOS_DISPONIBLES = tuple(_FACTORIES)


def obtener_factory(tipo: str) -> DispositivoIoTFactory:
    """
    Punto único donde se resuelve qué fábrica concreta usar según el tipo
    solicitado. Agregar un nuevo tipo de dispositivo solo requiere registrar
    su fábrica aquí, sin modificar el resto de la plataforma.
    """
    try:
        return _FACTORIES[tipo]
    except KeyError:
        disponibles = ", ".join(_FACTORIES)
        raise ValueError(f"Tipo de dispositivo '{tipo}' no soportado. Disponibles: {disponibles}")


def crear_dispositivo(
    tipo: str,
    id_dispositivo: str,
    usuario_id: str,
    umbral_min: Optional[float] = None,
    umbral_max: Optional[float] = None,
) -> DispositivoIoT:
    """Función de conveniencia usada por la plataforma para registrar dispositivos."""
    return obtener_factory(tipo).registrar(id_dispositivo, usuario_id, umbral_min, umbral_max)
