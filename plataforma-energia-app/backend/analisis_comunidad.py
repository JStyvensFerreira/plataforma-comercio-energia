"""
Plataforma de Comercio de Energía — análisis sobre el árbol energético
(patrón Visitor). Consumido por plataforma.py (analizar_comunidad).

Cada análisis es un visitante que recorre el árbol del Composite
(jerarquia.py) sin agregarle métodos: los nodos solo implementan
`aceptar(visitante)` y despachan a `visitar_dispositivo` o `visitar_grupo`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from jerarquia import DispositivoHoja, GrupoEnergetico, NodoEnergetico

# Factor de emisión de referencia de la red (kg CO₂ por kWh), ilustrativo.
FACTOR_EMISION_KG_KWH = 0.126


class VisitanteEnergetico(ABC):
    @abstractmethod
    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        raise NotImplementedError

    @abstractmethod
    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        raise NotImplementedError

    @abstractmethod
    def resultado(self):
        raise NotImplementedError


class VisitanteHuellaCarbono(VisitanteEnergetico):
    """kg de CO₂ que la red habría emitido para producir lo que produjo cada hogar."""

    def __init__(self, factor_kg_kwh: float = FACTOR_EMISION_KG_KWH) -> None:
        self.factor = factor_kg_kwh
        self.total_kg = 0.0
        self.por_hogar: dict[str, float] = {}
        self._hogar_actual: str | None = None

    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        kg = dispositivo.produccion_kwh() * self.factor
        self.total_kg += kg
        if self._hogar_actual is not None:
            self.por_hogar[self._hogar_actual] = round(self.por_hogar.get(self._hogar_actual, 0.0) + kg, 3)

    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        anterior = self._hogar_actual
        if grupo.nivel == "hogar":
            self._hogar_actual = grupo.nombre
            self.por_hogar.setdefault(grupo.nombre, 0.0)
        for hijo in grupo.hijos:
            hijo.aceptar(self)
        self._hogar_actual = anterior

    def resultado(self) -> dict:
        return {"total_kg_co2": round(self.total_kg, 3), "por_hogar": self.por_hogar, "factor_kg_kwh": self.factor}


class VisitanteDiagnostico(VisitanteEnergetico):
    """Hogares en déficit (balance < 0) y dispositivos que nunca reportaron lecturas."""

    def __init__(self) -> None:
        self.hogares_en_deficit: list[dict] = []
        self.dispositivos_sin_lecturas: list[str] = []

    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        if not dispositivo.lecturas:
            self.dispositivos_sin_lecturas.append(dispositivo.nombre)

    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        if grupo.nivel == "hogar" and grupo.balance_kwh() < 0:
            self.hogares_en_deficit.append({"hogar": grupo.nombre, "balance_kwh": grupo.balance_kwh()})
        for hijo in grupo.hijos:
            hijo.aceptar(self)

    def resultado(self) -> dict:
        return {
            "hogares_en_deficit": self.hogares_en_deficit,
            "dispositivos_sin_lecturas": self.dispositivos_sin_lecturas,
        }


class VisitanteExportarCSV(VisitanteEnergetico):
    """Una fila por nodo; la columna `ruta` conserva la posición en el árbol."""

    ENCABEZADO = "ruta;nivel;tipo;produccion_kwh;consumo_kwh;balance_kwh"

    def __init__(self) -> None:
        self.filas: list[str] = [self.ENCABEZADO]
        self._ruta: list[str] = []

    def _fila(self, nodo: NodoEnergetico, nivel: str, tipo: str) -> None:
        ruta = "/".join(self._ruta + [nodo.nombre])
        self.filas.append(
            f"{ruta};{nivel};{tipo};{nodo.produccion_kwh()};{nodo.consumo_kwh()};{nodo.balance_kwh()}"
        )

    def visitar_dispositivo(self, dispositivo: DispositivoHoja) -> None:
        self._fila(dispositivo, "dispositivo", dispositivo.tipo)

    def visitar_grupo(self, grupo: GrupoEnergetico) -> None:
        self._fila(grupo, grupo.nivel, "")
        self._ruta.append(grupo.nombre)
        for hijo in grupo.hijos:
            hijo.aceptar(self)
        self._ruta.pop()

    def resultado(self) -> dict:
        return {"csv": "\n".join(self.filas)}


_VISITANTES = {
    "huella_carbono": VisitanteHuellaCarbono,
    "diagnostico": VisitanteDiagnostico,
    "exportar_csv": VisitanteExportarCSV,
}

VISITANTES_DISPONIBLES = tuple(_VISITANTES)


def crear_visitante(nombre: str) -> VisitanteEnergetico:
    if nombre not in _VISITANTES:
        raise ValueError(f"Análisis '{nombre}' no soportado. Disponibles: {', '.join(VISITANTES_DISPONIBLES)}")
    return _VISITANTES[nombre]()
