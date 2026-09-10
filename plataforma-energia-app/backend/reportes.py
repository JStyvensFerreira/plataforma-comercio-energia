"""
Plataforma de Comercio de Energía — construcción del reporte energético
(patrón Builder). Este módulo es consumido por plataforma.py / main.py.

Es la versión de la aplicación del patrón documentado en
`Patrones/Semana 4/builder.py`. El reporte energético de un usuario se construye
PASO A PASO con un `ReporteBuilder`, y el mismo proceso de construcción produce
representaciones distintas:

    ReporteResumenBuilder    -> dict plano (lo que consume el FormateadorReporte
                                del patrón Abstract Factory)
    ReporteDetalladoBuilder  -> ReporteEnergetico (objeto con secciones tipadas)
    ReporteTextoBuilder      -> str (reporte ya formateado)

El `DirectorReportes` conoce las recetas (qué pasos y en qué orden); la
plataforma solo le pasa un `DatosReporte` con la materia prima ya calculada.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


# ===========================================================================
# Datos de entrada
# ===========================================================================
@dataclass
class DatosReporte:
    """Materia prima del reporte, ya calculada por la plataforma."""

    usuario: str
    periodo: str
    produccion_kwh: float = 0.0
    consumo_kwh: float = 0.0
    lecturas_por_dispositivo: dict[str, list[float]] = field(default_factory=dict)
    transacciones: list[dict] = field(default_factory=list)
    prediccion_por_dispositivo: dict[str, float | None] = field(default_factory=dict)


# ===========================================================================
# Producto detallado
# ===========================================================================
@dataclass
class SeccionReporte:
    titulo: str
    lineas: list[str] = field(default_factory=list)
    datos: dict = field(default_factory=dict)


@dataclass
class ReporteEnergetico:
    usuario: str = ""
    periodo: str = ""
    generado_en: str = ""
    secciones: list[SeccionReporte] = field(default_factory=list)

    def titulos(self) -> list[str]:
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


# Claves que el FormateadorReporte del patrón Abstract Factory espera recibir.
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
# BUILDER ABSTRACTO
# ===========================================================================
class ReporteBuilder(ABC):
    formato: str = ""

    def __init__(self) -> None:
        self.reiniciar()

    @abstractmethod
    def reiniciar(self) -> None:
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
        raise NotImplementedError


# ===========================================================================
# BUILDER CONCRETO 1 — dict plano (contrato del canal de notificación)
# ===========================================================================
class ReporteResumenBuilder(ReporteBuilder):
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
        return self

    def historial_transacciones(self, transacciones: list[dict]) -> "ReporteBuilder":
        self._r["transacciones"] = len(transacciones)
        return self

    def prediccion_consumo(
        self, prediccion_por_dispositivo: dict[str, float | None]
    ) -> "ReporteBuilder":
        return self

    def obtener_reporte(self) -> dict:
        return dict(self._r)


# ===========================================================================
# BUILDER CONCRETO 2 — objeto con secciones tipadas
# ===========================================================================
class ReporteDetalladoBuilder(ReporteBuilder):
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
# DIRECTOR — conoce las recetas
# ===========================================================================
class DirectorReportes:
    def __init__(self, builder: ReporteBuilder) -> None:
        self._builder = builder

    @property
    def builder(self) -> ReporteBuilder:
        return self._builder

    @builder.setter
    def builder(self, builder: ReporteBuilder) -> None:
        self._builder = builder

    def reporte_ejecutivo(self, datos: DatosReporte):
        b = self._builder
        b.reiniciar()
        b.encabezado(datos.usuario, datos.periodo)
        b.balance_energetico(datos.produccion_kwh, datos.consumo_kwh)
        b.historial_transacciones(datos.transacciones)
        return b.obtener_reporte()

    def reporte_completo(self, datos: DatosReporte):
        b = self._builder
        b.reiniciar()
        b.encabezado(datos.usuario, datos.periodo)
        b.balance_energetico(datos.produccion_kwh, datos.consumo_kwh)
        b.desglose_dispositivos(datos.lecturas_por_dispositivo)
        b.historial_transacciones(datos.transacciones)
        b.prediccion_consumo(datos.prediccion_por_dispositivo)
        return b.obtener_reporte()

    def reporte_para_factura(self, datos: DatosReporte):
        b = self._builder
        b.reiniciar()
        b.encabezado(datos.usuario, datos.periodo)
        b.historial_transacciones(datos.transacciones)
        b.balance_energetico(datos.produccion_kwh, datos.consumo_kwh)
        return b.obtener_reporte()


# ===========================================================================
# Registro de formatos
# ===========================================================================
_BUILDERS: dict[str, type[ReporteBuilder]] = {
    "resumen": ReporteResumenBuilder,
    "detallado": ReporteDetalladoBuilder,
    "texto": ReporteTextoBuilder,
}

FORMATOS_DISPONIBLES = tuple(_BUILDERS)


def crear_builder(formato: str) -> ReporteBuilder:
    try:
        return _BUILDERS[formato]()
    except KeyError:
        disponibles = ", ".join(_BUILDERS)
        raise ValueError(
            f"Formato de reporte '{formato}' no soportado. Disponibles: {disponibles}"
        )
