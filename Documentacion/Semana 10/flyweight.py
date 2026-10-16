"""
Patrón Flyweight — Catálogo de tipos de dispositivo IoT.

Problema: la plataforma puede tener miles de dispositivos IoT conectados
(paneles solares, baterías, medidores). Cada tipo de dispositivo comparte una
"ficha técnica" idéntica para todos los dispositivos de ese tipo: nombre
amigable, categoría, unidad de medida, rango normal de lectura y una
descripción. Si esa ficha se guardara copiada dentro de cada dispositivo,
miles de dispositivos del mismo tipo duplicarían exactamente la misma
información en memoria.

Solución (Flyweight): separar el estado en dos partes.
    - Intrínseco (compartido, inmutable): la ficha técnica del TIPO de
      dispositivo. Se calcula una sola vez por tipo y se reutiliza.
    - Extrínseco (único por objeto): el id del dispositivo, su dueño y sus
      lecturas, que sí varían de un dispositivo a otro y viven fuera del
      Flyweight.

La `FabricaFichasDispositivo` (Flyweight Factory) garantiza que, para un
mismo tipo, siempre se devuelva la MISMA instancia de `FichaTipoDispositivo`
(se verifica con `is`, no solo con `==`), sin importar cuántos dispositivos
la consulten.

Ejecutar este archivo directamente corre una demo por consola:
    python "Documentacion/Semana 10/flyweight.py"
"""

from __future__ import annotations

from dataclasses import dataclass


# ===========================================================================
# FLYWEIGHT — estado intrínseco, compartido e inmutable
# ===========================================================================
@dataclass(frozen=True)
class FichaTipoDispositivo:
    """Ficha técnica compartida por TODOS los dispositivos de un mismo tipo."""

    tipo: str
    nombre_amigable: str
    categoria: str
    unidad: str
    umbral_min: float
    umbral_max: float
    descripcion: str

    def to_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "nombre_amigable": self.nombre_amigable,
            "categoria": self.categoria,
            "unidad": self.unidad,
            "umbral_min": self.umbral_min,
            "umbral_max": self.umbral_max,
            "descripcion": self.descripcion,
        }


# Datos "de fábrica" por tipo de dispositivo (equivalentes a una hoja de
# especificaciones del fabricante): no cambian de un dispositivo a otro.
_ESPECIFICACIONES: dict[str, dict] = {
    "panel_solar": dict(
        nombre_amigable="Panel solar",
        categoria="generación",
        unidad="kWh",
        umbral_min=0.0,
        umbral_max=3.5,
        descripcion="Produce energía; una lectura fuera de rango suele indicar "
        "sombra, suciedad o una falla del inversor.",
    ),
    "bateria": dict(
        nombre_amigable="Batería inteligente",
        categoria="almacenamiento",
        unidad="kWh",
        umbral_min=-2.0,
        umbral_max=2.0,
        descripcion="Produce al descargarse y consume al cargarse; una lectura "
        "fuera de rango puede indicar sobrecarga o descarga profunda.",
    ),
    "medidor": dict(
        nombre_amigable="Medidor de consumo",
        categoria="medición",
        unidad="kWh",
        umbral_min=-2.5,
        umbral_max=0.5,
        descripcion="Mide principalmente consumo; una lectura fuera de rango "
        "puede indicar un pico de demanda inusual.",
    ),
}


# ===========================================================================
# FLYWEIGHT FACTORY
# ===========================================================================
class FabricaFichasDispositivo:
    """
    Punto único de acceso a las fichas técnicas. Cachea una ficha por tipo y
    devuelve siempre la MISMA instancia para el mismo tipo, sin importar
    cuántos dispositivos (o cuántas veces) la soliciten.
    """

    def __init__(self) -> None:
        self._cache: dict[str, FichaTipoDispositivo] = {}

    def obtener_ficha(self, tipo: str) -> FichaTipoDispositivo:
        if tipo not in self._cache:
            try:
                datos = _ESPECIFICACIONES[tipo]
            except KeyError:
                disponibles = ", ".join(_ESPECIFICACIONES)
                raise ValueError(
                    f"Tipo de dispositivo '{tipo}' no soportado. Disponibles: {disponibles}"
                )
            self._cache[tipo] = FichaTipoDispositivo(tipo=tipo, **datos)
        return self._cache[tipo]

    @property
    def fichas_creadas(self) -> int:
        """Cuántos objetos Flyweight distintos se han creado hasta ahora."""
        return len(self._cache)

    @property
    def tipos_disponibles(self) -> tuple[str, ...]:
        return tuple(_ESPECIFICACIONES)


if __name__ == "__main__":
    fabrica = FabricaFichasDispositivo()

    # "Extrínseco": muchos dispositivos, cada uno con su propio id y tipo.
    dispositivos = [
        ("panel-01", "panel_solar"),
        ("panel-02", "panel_solar"),
        ("panel-03", "panel_solar"),
        ("bateria-01", "bateria"),
        ("bateria-02", "bateria"),
        ("medidor-01", "medidor"),
    ]

    print("Consultando la ficha técnica de cada dispositivo...")
    fichas_por_dispositivo = {}
    for id_dispositivo, tipo in dispositivos:
        ficha = fabrica.obtener_ficha(tipo)
        fichas_por_dispositivo[id_dispositivo] = ficha
        print(f"  {id_dispositivo} ({tipo}) -> {ficha.nombre_amigable}")

    print(f"\nDispositivos consultados: {len(dispositivos)}")
    print(f"Fichas (Flyweight) creadas realmente: {fabrica.fichas_creadas}")

    # Misma ficha, misma instancia en memoria: identidad real, no solo igualdad.
    misma_instancia = (
        fichas_por_dispositivo["panel-01"] is fichas_por_dispositivo["panel-02"]
        is fichas_por_dispositivo["panel-03"]
    )
    print(f"Los 3 paneles comparten la MISMA instancia de ficha: {misma_instancia}")

    print("\nCatálogo completo de tipos disponibles:")
    for tipo in fabrica.tipos_disponibles:
        print(" -", fabrica.obtener_ficha(tipo).to_dict())
