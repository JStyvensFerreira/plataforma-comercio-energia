"""
Plataforma de Comercio de Energía — catálogo de tipos de dispositivo IoT
(patrón Flyweight). Consumido por plataforma.py / main.py.

Separa el estado intrínseco (la ficha técnica de un TIPO de dispositivo:
nombre amigable, categoría, unidad, umbrales y descripción) del estado
extrínseco (el id, el dueño y las lecturas de cada dispositivo concreto,
que viven en DispositivoIoT). Los umbrales se reutilizan de
factory_method.UMBRALES_IOT para no duplicar esa fuente de verdad.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

from factory_method import UMBRALES_IOT


@dataclass(frozen=True)
class FichaTipoDispositivo:
    """Ficha técnica compartida por todos los dispositivos de un mismo tipo."""

    tipo: str
    nombre_amigable: str
    categoria: str
    unidad: str
    umbral_min: float
    umbral_max: float
    descripcion: str

    def to_dict(self) -> dict:
        return asdict(self)


_ESPECIFICACIONES: dict[str, dict] = {
    "panel_solar": dict(
        nombre_amigable="Panel solar",
        categoria="generación",
        unidad="kWh",
        descripcion="Produce energía; una lectura fuera de rango suele indicar "
        "sombra, suciedad o una falla del inversor.",
    ),
    "bateria": dict(
        nombre_amigable="Batería inteligente",
        categoria="almacenamiento",
        unidad="kWh",
        descripcion="Produce al descargarse y consume al cargarse; una lectura "
        "fuera de rango puede indicar sobrecarga o descarga profunda.",
    ),
    "medidor": dict(
        nombre_amigable="Medidor de consumo",
        categoria="medición",
        unidad="kWh",
        descripcion="Mide principalmente consumo; una lectura fuera de rango "
        "puede indicar un pico de demanda inusual.",
    ),
}


class FabricaFichasDispositivo:
    """Devuelve siempre la misma instancia de ficha para un mismo tipo."""

    def __init__(self) -> None:
        self._cache: dict[str, FichaTipoDispositivo] = {}

    def obtener_ficha(self, tipo: str) -> FichaTipoDispositivo:
        if tipo not in self._cache:
            try:
                extra = _ESPECIFICACIONES[tipo]
            except KeyError:
                disponibles = ", ".join(_ESPECIFICACIONES)
                raise ValueError(
                    f"Tipo de dispositivo '{tipo}' no soportado. Disponibles: {disponibles}"
                )
            umbral_min, umbral_max = UMBRALES_IOT.get(tipo, (None, None))
            self._cache[tipo] = FichaTipoDispositivo(
                tipo=tipo, umbral_min=umbral_min, umbral_max=umbral_max, **extra
            )
        return self._cache[tipo]

    @property
    def fichas_creadas(self) -> int:
        return len(self._cache)

    @property
    def tipos_disponibles(self) -> tuple[str, ...]:
        return tuple(_ESPECIFICACIONES)


fabrica_fichas = FabricaFichasDispositivo()
