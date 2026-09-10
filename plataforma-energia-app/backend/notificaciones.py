"""
Plataforma de Comercio de Energía — canales de notificación (patrón Abstract Factory).
Este módulo es consumido por plataforma.py / main.py (API FastAPI).

Es la versión de la aplicación del patrón documentado en
`Patrones/Semana 4/abstract_factory.py`. Cada canal (email, SMS, push)
es una FÁBRICA ABSTRACTA que crea la familia completa de notificadores de ese
canal, todos coherentes entre sí:

    crear_notificador_transaccion()  -> NotificadorTransaccion
    crear_notificador_alerta_iot()   -> NotificadorAlertaIoT
    crear_formateador_reporte()      -> FormateadorReporte

El cliente (`ServicioNotificaciones`, usado dentro de `PlataformaEnergia`) elige
UNA fábrica según la preferencia del usuario y a partir de ahí todos los avisos
salen por el mismo canal, sin conocer una sola clase concreta.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

LIMITE_SMS = 160
LIMITE_TITULO_PUSH = 40
LIMITE_CUERPO_PUSH = 120


@dataclass(frozen=True)
class Mensaje:
    """Resultado uniforme de cualquier notificador, sin importar el canal."""

    canal: str
    cuerpo: str
    asunto: str = ""
    datos: dict = field(default_factory=dict)
    destino: str = ""  # correo, teléfono o token push del destinatario

    def to_dict(self) -> dict:
        return asdict(self)


def _recortar(texto: str, limite: int) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rstrip() + "…"


# ===========================================================================
# PRODUCTOS ABSTRACTOS — la familia de notificadores
# ===========================================================================
class NotificadorTransaccion(ABC):
    @abstractmethod
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        raise NotImplementedError


class NotificadorAlertaIoT(ABC):
    @abstractmethod
    def alertar(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        raise NotImplementedError


class FormateadorReporte(ABC):
    @abstractmethod
    def formatear(self, resumen: dict) -> Mensaje:
        raise NotImplementedError


# ===========================================================================
# FÁBRICA ABSTRACTA
# ===========================================================================
class CanalNotificacionFactory(ABC):
    @property
    @abstractmethod
    def canal(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def crear_notificador_transaccion(self) -> NotificadorTransaccion:
        raise NotImplementedError

    @abstractmethod
    def crear_notificador_alerta_iot(self) -> NotificadorAlertaIoT:
        raise NotImplementedError

    @abstractmethod
    def crear_formateador_reporte(self) -> FormateadorReporte:
        raise NotImplementedError


# ===========================================================================
# FAMILIA 1 — EMAIL
# ===========================================================================
class _TransaccionEmail(NotificadorTransaccion):
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        contraparte = (
            transaccion["vendedor"] if rol == "comprador" else transaccion["comprador"]
        )
        verbo = "compraste" if rol == "comprador" else "vendiste"
        cuerpo = (
            f"Hola {destinatario},\n\n"
            f"La subasta cerró una operación: {verbo} {transaccion['cantidad_kwh']} kWh "
            f"a ${transaccion['precio_kwh']}/kWh (total ${transaccion['total']}) "
            f"con el usuario {contraparte}.\n\n"
            f"Fecha: {transaccion['timestamp']}\n\n"
            f"— Plataforma de Comercio de Energía"
        )
        return Mensaje("email", cuerpo, asunto="Operación cerrada en la subasta")


class _AlertaEmail(NotificadorAlertaIoT):
    def alertar(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        cuerpo = (
            f"Hola,\n\n"
            f"El dispositivo {dispositivo_id} ({tipo_dispositivo}) reportó una lectura de "
            f"{lectura} kWh, fuera del umbral configurado ({umbral} kWh).\n\n"
            f"Revisa el estado del equipo desde el panel.\n\n"
            f"— Plataforma de Comercio de Energía"
        )
        return Mensaje("email", cuerpo, asunto=f"Alerta IoT: {dispositivo_id}")


class _ReporteEmail(FormateadorReporte):
    def formatear(self, resumen: dict) -> Mensaje:
        cuerpo = (
            f"Hola {resumen['usuario']},\n\n"
            f"Resumen energético del período:\n"
            f"  • Producción: {resumen['produccion_kwh']} kWh\n"
            f"  • Consumo:    {resumen['consumo_kwh']} kWh\n"
            f"  • Balance:    {resumen['balance_kwh']} kWh\n"
            f"  • Operaciones en subasta: {resumen['transacciones']}\n\n"
            f"— Plataforma de Comercio de Energía"
        )
        return Mensaje("email", cuerpo, asunto="Tu reporte energético del período")


class CanalEmail(CanalNotificacionFactory):
    @property
    def canal(self) -> str:
        return "email"

    def crear_notificador_transaccion(self) -> NotificadorTransaccion:
        return _TransaccionEmail()

    def crear_notificador_alerta_iot(self) -> NotificadorAlertaIoT:
        return _AlertaEmail()

    def crear_formateador_reporte(self) -> FormateadorReporte:
        return _ReporteEmail()


# ===========================================================================
# FAMILIA 2 — SMS  (sin asunto, cuerpo <= 160)
# ===========================================================================
class _TransaccionSMS(NotificadorTransaccion):
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        verbo = "Compra" if rol == "comprador" else "Venta"
        cuerpo = _recortar(
            f"{verbo} confirmada: {transaccion['cantidad_kwh']} kWh a "
            f"${transaccion['precio_kwh']}/kWh (total ${transaccion['total']}).",
            LIMITE_SMS,
        )
        return Mensaje("sms", cuerpo)


class _AlertaSMS(NotificadorAlertaIoT):
    def alertar(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        cuerpo = _recortar(
            f"Alerta IoT {dispositivo_id}: lectura {lectura} kWh fuera de umbral "
            f"({umbral} kWh). Revisa el equipo.",
            LIMITE_SMS,
        )
        return Mensaje("sms", cuerpo)


class _ReporteSMS(FormateadorReporte):
    def formatear(self, resumen: dict) -> Mensaje:
        cuerpo = _recortar(
            f"Reporte {resumen['usuario']}: prod {resumen['produccion_kwh']} kWh, "
            f"cons {resumen['consumo_kwh']} kWh, balance {resumen['balance_kwh']} kWh, "
            f"{resumen['transacciones']} operaciones.",
            LIMITE_SMS,
        )
        return Mensaje("sms", cuerpo)


class CanalSMS(CanalNotificacionFactory):
    @property
    def canal(self) -> str:
        return "sms"

    def crear_notificador_transaccion(self) -> NotificadorTransaccion:
        return _TransaccionSMS()

    def crear_notificador_alerta_iot(self) -> NotificadorAlertaIoT:
        return _AlertaSMS()

    def crear_formateador_reporte(self) -> FormateadorReporte:
        return _ReporteSMS()


# ===========================================================================
# FAMILIA 3 — PUSH  (título + cuerpo cortos + payload estructurado)
# ===========================================================================
class _TransaccionPush(NotificadorTransaccion):
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        return Mensaje(
            "push",
            _recortar(
                f"{transaccion['cantidad_kwh']} kWh por ${transaccion['total']}",
                LIMITE_CUERPO_PUSH,
            ),
            asunto=_recortar("Operación cerrada", LIMITE_TITULO_PUSH),
            datos={
                "evento": "transaccion",
                "rol": rol,
                "cantidad_kwh": transaccion["cantidad_kwh"],
                "precio_kwh": transaccion["precio_kwh"],
                "total": transaccion["total"],
            },
        )


class _AlertaPush(NotificadorAlertaIoT):
    def alertar(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        return Mensaje(
            "push",
            _recortar(
                f"Lectura {lectura} kWh fuera de umbral ({umbral} kWh)", LIMITE_CUERPO_PUSH
            ),
            asunto=_recortar(f"Alerta: {dispositivo_id}", LIMITE_TITULO_PUSH),
            datos={
                "evento": "alerta_iot",
                "dispositivo_id": dispositivo_id,
                "tipo_dispositivo": tipo_dispositivo,
                "lectura": lectura,
                "umbral": umbral,
            },
        )


class _ReportePush(FormateadorReporte):
    def formatear(self, resumen: dict) -> Mensaje:
        return Mensaje(
            "push",
            _recortar(
                f"Balance {resumen['balance_kwh']} kWh · {resumen['transacciones']} operaciones",
                LIMITE_CUERPO_PUSH,
            ),
            asunto=_recortar("Reporte energético", LIMITE_TITULO_PUSH),
            datos={"evento": "reporte", **resumen},
        )


class CanalPush(CanalNotificacionFactory):
    @property
    def canal(self) -> str:
        return "push"

    def crear_notificador_transaccion(self) -> NotificadorTransaccion:
        return _TransaccionPush()

    def crear_notificador_alerta_iot(self) -> NotificadorAlertaIoT:
        return _AlertaPush()

    def crear_formateador_reporte(self) -> FormateadorReporte:
        return _ReportePush()


# ===========================================================================
# Registro de canales + cliente
# ===========================================================================
_CANALES: dict[str, CanalNotificacionFactory] = {
    "email": CanalEmail(),
    "sms": CanalSMS(),
    "push": CanalPush(),
}

CANALES_DISPONIBLES = tuple(_CANALES)


def obtener_canal(nombre: str) -> CanalNotificacionFactory:
    try:
        return _CANALES[nombre]
    except KeyError:
        disponibles = ", ".join(_CANALES)
        raise ValueError(
            f"Canal de notificación '{nombre}' no soportado. Disponibles: {disponibles}"
        )


class ServicioNotificaciones:
    """Construye la familia completa a partir de UNA fábrica de canal."""

    def __init__(self, fabrica: CanalNotificacionFactory):
        self._fabrica = fabrica
        self._transaccion = fabrica.crear_notificador_transaccion()
        self._alerta = fabrica.crear_notificador_alerta_iot()
        self._reporte = fabrica.crear_formateador_reporte()

    @property
    def canal(self) -> str:
        return self._fabrica.canal

    def avisar_puja_ganada(
        self, transaccion: dict, destinatario: str, rol: str = "comprador"
    ) -> Mensaje:
        return self._transaccion.notificar(transaccion, destinatario, rol)

    def avisar_alerta_iot(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        return self._alerta.alertar(dispositivo_id, tipo_dispositivo, lectura, umbral)

    def enviar_reporte(self, resumen: dict) -> Mensaje:
        return self._reporte.formatear(resumen)


def crear_servicio(canal: str) -> ServicioNotificaciones:
    return ServicioNotificaciones(obtener_canal(canal))
