"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: PROTOTYPE (Prototipo)
---------------------------------------
Cuando se da de alta un dispositivo IoT nuevo (patrón Factory Method,
Semana 3), la fábrica le asigna los UMBRALES POR DEFECTO de su tipo
(`UMBRALES_IOT` en la app real). Eso funciona para el caso general, pero
en una instalación real casi nunca basta:

  - Un instalador CALIBRA un panel solar en campo (ajusta `umbral_min`/
    `umbral_max` según la orientación del techo, la sombra de un edificio
    vecino, etc.) y luego necesita dar de alta OTROS 10 PANELES IDÉNTICOS
    en la misma instalación, con exactamente esos mismos umbrales ya
    ajustados — no los de fábrica.
  - Ese dispositivo "maestro" ya calibrado puede tener, además, notas de
    calibración (una lista mutable) que tampoco se deben perder ni
    compartir por referencia entre las copias.

Si la plataforma solo tuviera Factory Method, la única forma de reproducir
ese ajuste fino sería volver a escribir los mismos parámetros a mano en
cada alta nueva (o modificar la fábrica para aceptar umbrales, con lo que
deja de ser una fábrica "por tipo" y el operador tiene que recordar los
números exactos cada vez).

Con PROTOTYPE, el dispositivo ya calibrado se CLONA: el nuevo objeto nace
con el mismo estado (tipo, umbrales, notas de calibración) sin que el
cliente conozca su clase concreta ni tenga que re-especificar cada campo,
y solo cambia lo que identifica al dispositivo nuevo (`id`, `usuario_id`).
Un `RegistroPlantillas` (prototype registry) además permite guardar
configuraciones ya calibradas con un nombre y clonarlas por catálogo,
igual que `obtener_factory`/`crear_builder`/`obtener_canal` resuelven las
otras fábricas del proyecto.

Diferencia con Factory Method:
  - Factory Method crea un dispositivo A PARTIR DE CERO, con los valores
    por defecto de su tipo; el cliente decide "qué tipo" pero no controla
    el estado fino del objeto.
  - Prototype crea un dispositivo A PARTIR DE OTRO YA CONFIGURADO EN
    TIEMPO DE EJECUCIÓN (incluyendo ajustes que nadie escribió en el
    código); el cliente decide "a partir de cuál" y qué cambiar.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# PROTOTIPO — declara la interfaz de clonado
# ---------------------------------------------------------------------------
class PrototipoDispositivo(ABC):
    """
    Todo dispositivo clonable implementa `clonar()`. El cliente nunca llama
    al constructor de la clase concreta: siempre clona un objeto existente,
    así que no necesita conocer esa clase para crear uno "igual, pero con
    otro id".
    """

    @abstractmethod
    def clonar(self, nuevo_id: str, nuevo_usuario_id: Optional[str] = None) -> "PrototipoDispositivo":
        """Devuelve una copia INDEPENDIENTE de este objeto con nueva identidad."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# PRODUCTO — dispositivo IoT clonable
# ---------------------------------------------------------------------------
@dataclass
class DispositivoIoT(PrototipoDispositivo):
    """
    Dispositivo IoT de la plataforma. Además de identidad y umbrales, guarda
    `notas_calibracion`: una lista MUTABLE que demuestra por qué Prototype
    necesita copia PROFUNDA (`copy.deepcopy`) y no superficial — con una
    copia superficial, dos dispositivos "clonados" terminarían compartiendo
    la misma lista de notas por referencia.
    """

    id: str
    usuario_id: str
    tipo: str
    umbral_min: Optional[float] = None
    umbral_max: Optional[float] = None
    notas_calibracion: list[str] = field(default_factory=list)
    calibrado_en: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "tipo": self.tipo,
            "umbral_min": self.umbral_min,
            "umbral_max": self.umbral_max,
            "notas_calibracion": list(self.notas_calibracion),
            "calibrado_en": self.calibrado_en,
        }

    def clonar(
        self,
        nuevo_id: str,
        nuevo_usuario_id: Optional[str] = None,
        **cambios,
    ) -> "DispositivoIoT":
        """
        Copia PROFUNDA de este dispositivo (preserva tipo, umbrales y notas
        de calibración) con nueva identidad. `**cambios` permite ajustar
        campos puntuales sin perder el resto de la configuración clonada
        (p. ej. clonar un panel calibrado pero con un `umbral_max` distinto
        por una sombra diferente en el techo nuevo).
        """
        copia = copy.deepcopy(self)
        copia.id = nuevo_id
        if nuevo_usuario_id is not None:
            copia.usuario_id = nuevo_usuario_id
        copia.calibrado_en = datetime.now().isoformat(timespec="seconds")
        for campo, valor in cambios.items():
            if not hasattr(copia, campo):
                raise ValueError(f"'{campo}' no es un campo válido de DispositivoIoT")
            setattr(copia, campo, valor)
        return copia


# ---------------------------------------------------------------------------
# REGISTRO DE PLANTILLAS — prototype registry/manager
# ---------------------------------------------------------------------------
class RegistroPlantillas:
    """
    Guarda dispositivos ya calibrados con un nombre de catálogo y los clona
    bajo demanda. Es el equivalente, para Prototype, de `obtener_factory`
    (Factory Method), `obtener_canal` (Abstract Factory) o `crear_builder`
    (Builder): un punto único donde se resuelve "a partir de cuál plantilla".
    """

    def __init__(self) -> None:
        self._plantillas: dict[str, DispositivoIoT] = {}

    def registrar_plantilla(self, nombre: str, prototipo: DispositivoIoT) -> None:
        """Guarda una COPIA del prototipo, para que ajustes futuros a `prototipo`
        (el objeto original del llamador) no alteren la plantilla guardada."""
        self._plantillas[nombre] = copy.deepcopy(prototipo)

    @property
    def plantillas_disponibles(self) -> tuple[str, ...]:
        return tuple(self._plantillas)

    def crear_desde_plantilla(
        self,
        nombre: str,
        nuevo_id: str,
        nuevo_usuario_id: Optional[str] = None,
        **cambios,
    ) -> DispositivoIoT:
        """
        Punto único donde se resuelve qué plantilla clonar. Una plantilla
        desconocida lanza `ValueError` con las disponibles (mismo contrato
        que `obtener_factory`/`obtener_canal`/`crear_builder`).
        """
        try:
            plantilla = self._plantillas[nombre]
        except KeyError:
            disponibles = ", ".join(self._plantillas) or "(ninguna registrada)"
            raise ValueError(f"Plantilla '{nombre}' no existe. Disponibles: {disponibles}")
        return plantilla.clonar(nuevo_id, nuevo_usuario_id, **cambios)


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Un instalador calibra un panel solar en campo, ajustando el umbral
    # máximo por la sombra parcial de un edificio vecino.
    panel_calibrado = DispositivoIoT(
        id="panel-maestro",
        usuario_id="u1",
        tipo="panel_solar",
        umbral_min=0.0,
        umbral_max=2.8,  # más bajo que el default de fábrica (3.5) por la sombra
        notas_calibracion=["Sombra parcial 14:00-16:00, techo orientado sureste"],
    )

    registro = RegistroPlantillas()
    registro.registrar_plantilla("panel_con_sombra", panel_calibrado)

    print("Plantillas disponibles:", registro.plantillas_disponibles)

    # Se instalan 3 paneles idénticos más en el mismo techo: mismos umbrales
    # y mismas notas, sin volver a escribirlos a mano.
    paneles_nuevos = [
        registro.crear_desde_plantilla("panel_con_sombra", f"panel-0{n}", "u1")
        for n in range(2, 5)
    ]
    for p in paneles_nuevos:
        print(" -", p.to_dict())

    # Las notas son independientes entre clones (copia profunda):
    paneles_nuevos[0].notas_calibracion.append("Panel adicional, misma orientación")
    print("\n¿Las notas se comparten entre clones? ->",
          paneles_nuevos[0].notas_calibracion == paneles_nuevos[1].notas_calibracion)

    # El original tampoco se ve afectado por los cambios en los clones.
    print("Notas del panel maestro (sin cambios):", panel_calibrado.notas_calibracion)

    # Clonar con un ajuste puntual: mismo tipo y notas, pero otro umbral.
    panel_sin_sombra = panel_calibrado.clonar("panel-05", "u2", umbral_max=3.5)
    print("\nClon con override de umbral_max:", panel_sin_sombra.to_dict())

    print("\nPlantilla inexistente:")
    try:
        registro.crear_desde_plantilla("bateria_industrial", "bat-99")
    except ValueError as e:
        print(" ", e)
