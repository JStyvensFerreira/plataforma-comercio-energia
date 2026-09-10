"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: BUILDER  (Constructor)
---------------------------------------
La plataforma genera un "reporte energético" por usuario a partir de varias
fuentes de datos: el balance de producción y consumo, el desglose por
dispositivo IoT, el historial de operaciones en la subasta y la predicción de
la próxima lectura de cada dispositivo.

Ese reporte no es un objeto simple:

  1. Tiene MUCHAS PARTES OPCIONALES. No siempre se quieren todas: el resumen
     ejecutivo solo lleva balance y número de operaciones; el reporte completo
     lleva además el desglose por dispositivo y la predicción; el reporte para
     factura lleva el historial de operaciones y el balance, pero no la
     predicción.

  2. Debe existir en VARIAS REPRESENTACIONES. El canal de notificación (patrón
     Abstract Factory) necesita un `dict` plano con unas claves concretas; un
     panel web quiere un objeto con secciones tipadas; un correo o un archivo
     de texto quieren una cadena ya formateada.

Si `PlataformaEnergia.generar_reporte()` armara ese objeto "a mano" con
condicionales (`if tipo == "completo": ...`) y además tuviera que saber cómo
serializarlo a `dict`, a texto o a HTML, la lógica de negocio quedaría
mezclada con la de presentación y con la de "qué secciones incluir".

Con BUILDER separamos las tres cosas:

  - El BUILDER (`ReporteBuilder`) declara los PASOS de construcción
    (`encabezado`, `balance_energetico`, `desglose_dispositivos`,
    `historial_transacciones`, `prediccion_consumo`) y un `obtener_reporte()`
    que entrega el producto terminado.

  - Cada BUILDER CONCRETO produce una REPRESENTACIÓN distinta con esos mismos
    pasos:
        ReporteResumenBuilder    -> dict plano (lo que consume el canal de aviso)
        ReporteDetalladoBuilder  -> ReporteEnergetico (objeto con secciones)
        ReporteTextoBuilder      -> str (reporte ya formateado)

  - El DIRECTOR (`DirectorReportes`) conoce las RECETAS: en qué orden y con qué
    pasos se arma un "reporte ejecutivo", uno "completo" o uno "para factura".
    El director no sabe qué representación sale; solo llama los pasos.

El código cliente elige un builder + una receta (o encadena los pasos a mano)
y recibe el reporte listo, sin condicionales de "qué incluir" ni de "cómo
serializar".

Diferencia con las fábricas del proyecto:
  - Factory Method / Abstract Factory crean un producto (o una familia) en UNA
    sola llamada.
  - Builder construye UN objeto complejo PASO A PASO, y el mismo proceso de
    construcción puede producir representaciones diferentes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


# ===========================================================================
# Datos de entrada — lo que la plataforma recolecta antes de construir
# ===========================================================================
@dataclass
class DatosReporte:
    """
    Materia prima del reporte, ya calculada por la plataforma. El builder solo
    da forma a estos datos; no los consulta ni los calcula.
    """

    usuario: str
    periodo: str
    produccion_kwh: float = 0.0
    consumo_kwh: float = 0.0
    # {id_dispositivo: [lecturas_kwh]}  (positivas = producción, negativas = consumo)
    lecturas_por_dispositivo: dict[str, list[float]] = field(default_factory=dict)
    # filas del historial de la subasta: {comprador, vendedor, cantidad_kwh, total, timestamp}
    transacciones: list[dict] = field(default_factory=list)
    # {id_dispositivo: valor_previsto_kwh | None}
    prediccion_por_dispositivo: dict[str, float | None] = field(default_factory=dict)


# ===========================================================================
# Producto detallado — objeto con secciones tipadas
# ===========================================================================
@dataclass
class SeccionReporte:
    """Una sección del reporte: un título, líneas legibles y datos estructurados."""

    titulo: str
    lineas: list[str] = field(default_factory=list)
    datos: dict = field(default_factory=dict)


@dataclass
class ReporteEnergetico:
    """Representación rica del reporte: se arma agregando secciones en orden."""

    usuario: str = ""
    periodo: str = ""
    generado_en: str = ""
    secciones: list[SeccionReporte] = field(default_factory=list)

    def titulos(self) -> list[str]:
        """Títulos de las secciones, en el orden en que se agregaron."""
        return [s.titulo for s in self.secciones]

    def seccion(self, titulo: str) -> SeccionReporte | None:
        return next((s for s in self.secciones if s.titulo == titulo), None)

    def to_dict(self) -> dict:
        return {
            "usuario": self.usuario,
            "periodo": self.periodo,
            "generado_en": self.generado_en,
            "secciones": [
                {"titulo": s.titulo, "lineas": list(s.lineas), "datos": dict(s.datos)}
                for s in self.secciones
            ],
        }


# ===========================================================================
# Claves del "contrato de notificación": lo que el FormateadorReporte del
# patrón Abstract Factory espera recibir en el `dict` del reporte.
# ===========================================================================
CLAVES_CONTRATO_NOTIFICACION = (
    "usuario",
    "produccion_kwh",
    "consumo_kwh",
    "balance_kwh",
    "transacciones",
)


def _balance(produccion_kwh: float, consumo_kwh: float) -> float:
    return round(produccion_kwh - consumo_kwh, 2)


# ===========================================================================
# BUILDER ABSTRACTO — declara los pasos de construcción
# ===========================================================================
class ReporteBuilder(ABC):
    """
    Constructor abstracto. Cada paso agrega una parte del reporte y devuelve
    `self`, de modo que los pasos se pueden encadenar. `obtener_reporte()`
    entrega el producto terminado en la representación propia de cada builder.
    """

    #: nombre corto del formato que produce este builder
    formato: str = ""

    def __init__(self) -> None:
        self.reiniciar()

    @abstractmethod
    def reiniciar(self) -> None:
        """Deja el builder listo para construir un reporte nuevo desde cero."""
        raise NotImplementedError

    @abstractmethod
    def encabezado(self, usuario: str, periodo: str) -> "ReporteBuilder":
        raise NotImplementedError

    @abstractmethod
    def balance_energetico(self, produccion_kwh: float, consumo_kwh: float) -> "ReporteBuilder":
        raise NotImplementedError

    @abstractmethod
    def desglose_dispositivos(
        self, lecturas_por_dispositivo: dict[str, list[float]]
    ) -> "ReporteBuilder":
        raise NotImplementedError

    @abstractmethod
    def historial_transacciones(self, transacciones: list[dict]) -> "ReporteBuilder":
        raise NotImplementedError

    @abstractmethod
    def prediccion_consumo(
        self, prediccion_por_dispositivo: dict[str, float | None]
    ) -> "ReporteBuilder":
        raise NotImplementedError

    @abstractmethod
    def obtener_reporte(self):
        """Devuelve el producto terminado (dict, objeto o str, según el builder)."""
        raise NotImplementedError


# ===========================================================================
# BUILDER CONCRETO 1 — dict plano (contrato del canal de notificación)
# ===========================================================================
class ReporteResumenBuilder(ReporteBuilder):
    """
    Representación compacta: un `dict` plano con las claves que consume el
    `FormateadorReporte` del patrón Abstract Factory. El desglose por
    dispositivo y la predicción no forman parte de este formato.
    """

    formato = "resumen"

    def reiniciar(self) -> None:
        self._r: dict = {
            "usuario": "",
            "periodo": "",
            "produccion_kwh": 0.0,
            "consumo_kwh": 0.0,
            "balance_kwh": 0.0,
            "transacciones": 0,
        }

    def encabezado(self, usuario: str, periodo: str) -> "ReporteBuilder":
        self._r["usuario"] = usuario
        self._r["periodo"] = periodo
        return self

    def balance_energetico(self, produccion_kwh: float, consumo_kwh: float) -> "ReporteBuilder":
        self._r["produccion_kwh"] = round(produccion_kwh, 2)
        self._r["consumo_kwh"] = round(consumo_kwh, 2)
        self._r["balance_kwh"] = _balance(produccion_kwh, consumo_kwh)
        return self

    def desglose_dispositivos(
        self, lecturas_por_dispositivo: dict[str, list[float]]
    ) -> "ReporteBuilder":
        # El formato resumen no incluye el desglose por dispositivo.
        return self

    def historial_transacciones(self, transacciones: list[dict]) -> "ReporteBuilder":
        self._r["transacciones"] = len(transacciones)
        return self

    def prediccion_consumo(
        self, prediccion_por_dispositivo: dict[str, float | None]
    ) -> "ReporteBuilder":
        # El formato resumen no incluye la predicción detallada.
        return self

    def obtener_reporte(self) -> dict:
        return dict(self._r)


# ===========================================================================
# BUILDER CONCRETO 2 — objeto con secciones tipadas
# ===========================================================================
class ReporteDetalladoBuilder(ReporteBuilder):
    """Representación rica: un `ReporteEnergetico` con una sección por paso."""

    formato = "detallado"

    def reiniciar(self) -> None:
        self._reporte = ReporteEnergetico(
            generado_en=datetime.now().isoformat(timespec="seconds")
        )

    def encabezado(self, usuario: str, periodo: str) -> "ReporteBuilder":
        self._reporte.usuario = usuario
        self._reporte.periodo = periodo
        return self

    def balance_energetico(self, produccion_kwh: float, consumo_kwh: float) -> "ReporteBuilder":
        balance = _balance(produccion_kwh, consumo_kwh)
        self._reporte.secciones.append(
            SeccionReporte(
                "Balance energético",
                lineas=[
                    f"Producción: {round(produccion_kwh, 2)} kWh",
                    f"Consumo: {round(consumo_kwh, 2)} kWh",
                    f"Balance: {balance} kWh",
                ],
                datos={
                    "produccion_kwh": round(produccion_kwh, 2),
                    "consumo_kwh": round(consumo_kwh, 2),
                    "balance_kwh": balance,
                },
            )
        )
        return self

    def desglose_dispositivos(
        self, lecturas_por_dispositivo: dict[str, list[float]]
    ) -> "ReporteBuilder":
        lineas: list[str] = []
        datos: dict = {}
        for disp_id, lecturas in lecturas_por_dispositivo.items():
            producido = round(sum(x for x in lecturas if x > 0), 2)
            consumido = round(-sum(x for x in lecturas if x < 0), 2)
            lineas.append(
                f"{disp_id}: produjo {producido} kWh, consumió {consumido} kWh "
                f"({len(lecturas)} lecturas)"
            )
            datos[disp_id] = {
                "producido_kwh": producido,
                "consumido_kwh": consumido,
                "lecturas": len(lecturas),
            }
        self._reporte.secciones.append(
            SeccionReporte(
                "Desglose por dispositivo",
                lineas or ["Sin dispositivos con lecturas en el período."],
                datos,
            )
        )
        return self

    def historial_transacciones(self, transacciones: list[dict]) -> "ReporteBuilder":
        lineas = [
            f"{t.get('timestamp', '?')}: {t.get('cantidad_kwh', '?')} kWh por "
            f"${t.get('total', '?')} ({t.get('vendedor', '?')} -> {t.get('comprador', '?')})"
            for t in transacciones
        ]
        self._reporte.secciones.append(
            SeccionReporte(
                "Historial de transacciones",
                lineas or ["Sin operaciones en el período."],
                {"total_operaciones": len(transacciones)},
            )
        )
        return self

    def prediccion_consumo(
        self, prediccion_por_dispositivo: dict[str, float | None]
    ) -> "ReporteBuilder":
        lineas = [
            f"{disp_id}: {valor} kWh" if valor is not None else f"{disp_id}: sin datos"
            for disp_id, valor in prediccion_por_dispositivo.items()
        ]
        self._reporte.secciones.append(
            SeccionReporte(
                "Predicción de la próxima lectura",
                lineas or ["Sin dispositivos para predecir."],
                dict(prediccion_por_dispositivo),
            )
        )
        return self

    def obtener_reporte(self) -> ReporteEnergetico:
        return self._reporte


# ===========================================================================
# BUILDER CONCRETO 3 — cadena de texto ya formateada
# ===========================================================================
class ReporteTextoBuilder(ReporteBuilder):
    """Representación plana: un `str` listo para un correo o un archivo `.txt`."""

    formato = "texto"

    def reiniciar(self) -> None:
        self._lineas: list[str] = []

    def encabezado(self, usuario: str, periodo: str) -> "ReporteBuilder":
        self._lineas = [
            f"REPORTE ENERGÉTICO — {usuario}",
            f"Período: {periodo}",
            "=" * 44,
        ]
        return self

    def balance_energetico(self, produccion_kwh: float, consumo_kwh: float) -> "ReporteBuilder":
        self._lineas += [
            "",
            "BALANCE",
            f"  Producción: {round(produccion_kwh, 2)} kWh",
            f"  Consumo:    {round(consumo_kwh, 2)} kWh",
            f"  Balance:    {_balance(produccion_kwh, consumo_kwh)} kWh",
        ]
        return self

    def desglose_dispositivos(
        self, lecturas_por_dispositivo: dict[str, list[float]]
    ) -> "ReporteBuilder":
        self._lineas += ["", "DISPOSITIVOS"]
        if not lecturas_por_dispositivo:
            self._lineas.append("  (sin lecturas en el período)")
        for disp_id, lecturas in lecturas_por_dispositivo.items():
            producido = round(sum(x for x in lecturas if x > 0), 2)
            consumido = round(-sum(x for x in lecturas if x < 0), 2)
            self._lineas.append(f"  {disp_id}: produjo {producido} kWh, consumió {consumido} kWh")
        return self

    def historial_transacciones(self, transacciones: list[dict]) -> "ReporteBuilder":
        self._lineas += ["", f"OPERACIONES EN SUBASTA: {len(transacciones)}"]
        return self

    def prediccion_consumo(
        self, prediccion_por_dispositivo: dict[str, float | None]
    ) -> "ReporteBuilder":
        self._lineas += ["", "PREDICCIÓN"]
        if not prediccion_por_dispositivo:
            self._lineas.append("  (sin dispositivos)")
        for disp_id, valor in prediccion_por_dispositivo.items():
            self._lineas.append(f"  {disp_id}: {valor if valor is not None else 's/d'} kWh")
        return self

    def obtener_reporte(self) -> str:
        return "\n".join(self._lineas)


# ===========================================================================
# DIRECTOR — conoce las recetas (qué pasos y en qué orden)
# ===========================================================================
class DirectorReportes:
    """
    Encapsula las secuencias de construcción más comunes. El director llama
    los pasos del builder que tenga configurado; nunca sabe qué representación
    produce ese builder.
    """

    def __init__(self, builder: ReporteBuilder) -> None:
        self._builder = builder

    @property
    def builder(self) -> ReporteBuilder:
        return self._builder

    @builder.setter
    def builder(self, builder: ReporteBuilder) -> None:
        self._builder = builder

    def reporte_ejecutivo(self, datos: DatosReporte):
        """Resumen breve: encabezado + balance + número de operaciones."""
        b = self._builder
        b.reiniciar()
        b.encabezado(datos.usuario, datos.periodo)
        b.balance_energetico(datos.produccion_kwh, datos.consumo_kwh)
        b.historial_transacciones(datos.transacciones)
        return b.obtener_reporte()

    def reporte_completo(self, datos: DatosReporte):
        """Todas las secciones: balance, desglose, historial y predicción."""
        b = self._builder
        b.reiniciar()
        b.encabezado(datos.usuario, datos.periodo)
        b.balance_energetico(datos.produccion_kwh, datos.consumo_kwh)
        b.desglose_dispositivos(datos.lecturas_por_dispositivo)
        b.historial_transacciones(datos.transacciones)
        b.prediccion_consumo(datos.prediccion_por_dispositivo)
        return b.obtener_reporte()

    def reporte_para_factura(self, datos: DatosReporte):
        """Para adjuntar a una factura: encabezado + historial + balance."""
        b = self._builder
        b.reiniciar()
        b.encabezado(datos.usuario, datos.periodo)
        b.historial_transacciones(datos.transacciones)
        b.balance_energetico(datos.produccion_kwh, datos.consumo_kwh)
        return b.obtener_reporte()


# ===========================================================================
# Registro de formatos disponibles
# ===========================================================================
_BUILDERS: dict[str, type[ReporteBuilder]] = {
    "resumen": ReporteResumenBuilder,
    "detallado": ReporteDetalladoBuilder,
    "texto": ReporteTextoBuilder,
}

FORMATOS_DISPONIBLES = tuple(_BUILDERS)


def crear_builder(formato: str) -> ReporteBuilder:
    """
    Punto único donde se resuelve qué builder concreto usar según el formato
    pedido. Agregar un formato nuevo solo requiere registrar su builder aquí.
    """
    try:
        return _BUILDERS[formato]()
    except KeyError:
        disponibles = ", ".join(_BUILDERS)
        raise ValueError(
            f"Formato de reporte '{formato}' no soportado. Disponibles: {disponibles}"
        )


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    datos = DatosReporte(
        usuario="u1",
        periodo="2026-09",
        produccion_kwh=18.4,
        consumo_kwh=12.1,
        lecturas_por_dispositivo={
            "panel-01": [3.1, 2.8, 3.4, 2.2],
            "bat-01": [1.2, -0.8, -1.4, 0.9],
        },
        transacciones=[
            {
                "comprador": "u2",
                "vendedor": "u1",
                "cantidad_kwh": 6,
                "total": 0.9,
                "timestamp": "2026-09-07T10:30:00",
            }
        ],
        prediccion_por_dispositivo={"panel-01": 2.9, "bat-01": None},
    )

    print("Mismo proceso de construcción, distinta representación:\n")

    for formato in FORMATOS_DISPONIBLES:
        director = DirectorReportes(crear_builder(formato))
        reporte = director.reporte_completo(datos)
        print("=" * 70)
        print(f"FORMATO: {formato}  ->  {type(reporte).__name__}")
        print("-" * 70)
        if isinstance(reporte, str):
            print(reporte)
        elif isinstance(reporte, dict):
            print(reporte)
        else:
            print("secciones:", reporte.titulos())
            for s in reporte.secciones:
                print(f"  [{s.titulo}]")
                for linea in s.lineas:
                    print(f"     {linea}")
        print()

    # La receta cambia lo que se incluye, no la representación.
    ejecutivo = DirectorReportes(crear_builder("detallado")).reporte_ejecutivo(datos)
    print("=" * 70)
    print("Reporte EJECUTIVO (detallado): secciones =", ejecutivo.titulos())

    # Uso fluido, sin director.
    a_mano = (
        crear_builder("texto")
        .encabezado("u1", "2026-09")
        .balance_energetico(18.4, 12.1)
        .historial_transacciones(datos.transacciones)
        .obtener_reporte()
    )
    print("\nEncadenado a mano (sin Director):\n")
    print(a_mano)

    print("\nFormato no soportado:")
    try:
        crear_builder("pdf")
    except ValueError as e:
        print(" ", e)
