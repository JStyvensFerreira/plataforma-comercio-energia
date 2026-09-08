"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: ABSTRACT FACTORY  (Fábrica Abstracta)
-----------------------------------------------------
La plataforma tiene que avisar cosas a los usuarios en tres momentos muy
distintos:

  1. Cuando la subasta cierra una operación   -> notificación de transacción
  2. Cuando una lectura IoT cruza un umbral    -> alerta de dispositivo
  3. Cuando toca el resumen periódico          -> reporte de producción/consumo

Y cada usuario puede recibir esos avisos por un canal diferente: correo,
SMS o notificación push a la app móvil. El problema es que cada canal
impone su propio formato y sus propias restricciones:

  - EMAIL: tiene asunto, cuerpo largo con saludo y despedida.
  - SMS  : no tiene asunto y el cuerpo no puede pasar de 160 caracteres.
  - PUSH : título corto, cuerpo corto y un `payload` estructurado (dict)
           que la app móvil procesa.

Si el código que envía avisos armara cada mensaje "a mano" con `if canal ==
"sms": ...`, tendríamos esa decisión repetida en tres lugares (transacción,
alerta, reporte) y sería fácil equivocarse y mezclar piezas incompatibles
(p. ej. ponerle un asunto de correo a un SMS, o pasarse de los 160
caracteres).

Con ABSTRACT FACTORY definimos UNA fábrica por canal
(`CanalNotificacionFactory`) que sabe crear la FAMILIA COMPLETA de
notificadores de ESE canal, todos coherentes entre sí:

        crear_notificador_transaccion()  -> NotificadorTransaccion
        crear_notificador_alerta_iot()   -> NotificadorAlertaIoT
        crear_formateador_reporte()      -> FormateadorReporte

Esos tres métodos son los MÉTODOS ABSTRACTOS ("abstract method") que cada
canal concreto (`CanalEmail`, `CanalSMS`, `CanalPush`) implementa a su
manera. El código cliente (`ServicioNotificaciones`) elige UNA fábrica y a
partir de ahí todos los mensajes que produzca saldrán en el mismo canal y
respetando sus reglas, sin conocer una sola clase concreta. Agregar un
canal nuevo (WhatsApp, Telegram) se reduce a crear una fábrica más, sin
tocar el código existente (principio abierto/cerrado).

Diferencia con el Factory Method del proyecto:
  - Factory Method crea UN producto (un `DispositivoIoT`).
  - Abstract Factory crea una FAMILIA de productos relacionados que deben
    usarse juntos (los tres notificadores de un mismo canal).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Límite de longitud de un SMS estándar (GSM-7 de un solo segmento).
LIMITE_SMS = 160
# Límites razonables para una notificación push.
LIMITE_TITULO_PUSH = 40
LIMITE_CUERPO_PUSH = 120


# ---------------------------------------------------------------------------
# Objeto de valor común a toda la familia
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Mensaje:
    """
    Resultado uniforme de cualquier notificador, sin importar el canal.
    Así el resto de la plataforma trabaja siempre con el mismo tipo.

    - `asunto` queda vacío en los canales que no lo usan (SMS).
    - `datos`  lleva el payload estructurado; solo push lo rellena.
    """

    canal: str
    cuerpo: str
    asunto: str = ""
    datos: dict = field(default_factory=dict)


def _recortar(texto: str, limite: int) -> str:
    """Recorta respetando el límite del canal, añadiendo un puntito suspensivo."""
    texto = " ".join(texto.split())  # normaliza espacios/saltos de línea
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rstrip() + "…"


# ===========================================================================
# PRODUCTOS ABSTRACTOS — la familia de notificadores
# ===========================================================================
class NotificadorTransaccion(ABC):
    """Avisa a un usuario que la subasta cerró una operación suya."""

    @abstractmethod
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        """
        `transaccion` es una fila del historial de la plataforma:
        {comprador, vendedor, cantidad_kwh, precio_kwh, total, timestamp}.
        `rol` es "comprador" o "vendedor" (para redactar el mensaje).
        """
        raise NotImplementedError


class NotificadorAlertaIoT(ABC):
    """Avisa que la lectura de un dispositivo cruzó un umbral configurado."""

    @abstractmethod
    def alertar(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        raise NotImplementedError


class FormateadorReporte(ABC):
    """Arma el reporte periódico de producción/consumo de un usuario."""

    @abstractmethod
    def formatear(self, resumen: dict) -> Mensaje:
        """
        `resumen`: {usuario, produccion_kwh, consumo_kwh, balance_kwh,
        transacciones}.
        """
        raise NotImplementedError


# ===========================================================================
# FÁBRICA ABSTRACTA — un canal sabe crear su familia completa
# ===========================================================================
class CanalNotificacionFactory(ABC):
    """
    Creador abstracto. Declara los MÉTODOS ABSTRACTOS que construyen cada
    miembro de la familia. Cada canal concreto los implementa devolviendo
    SUS variantes, garantizando que los tres notificadores son coherentes
    entre sí (mismo canal, mismas restricciones de formato).
    """

    @property
    @abstractmethod
    def canal(self) -> str:
        """Nombre del canal ('email', 'sms', 'push')."""
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
# FAMILIA 1 — CANAL EMAIL
# ===========================================================================
class _TransaccionEmail(NotificadorTransaccion):
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        contraparte = (
            transaccion["vendedor"] if rol == "comprador" else transaccion["comprador"]
        )
        verbo = "compraste" if rol == "comprador" else "vendiste"
        cuerpo = (
            f"Hola {destinatario},\n\n"
            f"La subasta cerró una operación: {verbo} "
            f"{transaccion['cantidad_kwh']} kWh a ${transaccion['precio_kwh']}/kWh "
            f"(total ${transaccion['total']}) con el usuario {contraparte}.\n\n"
            f"Fecha: {transaccion['timestamp']}\n\n"
            f"— Plataforma de Comercio de Energía"
        )
        return Mensaje(canal="email", asunto="Operación cerrada en la subasta", cuerpo=cuerpo)


class _AlertaEmail(NotificadorAlertaIoT):
    def alertar(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        cuerpo = (
            f"Hola,\n\n"
            f"El dispositivo {dispositivo_id} ({tipo_dispositivo}) reportó una lectura "
            f"de {lectura} kWh, fuera del umbral configurado ({umbral} kWh).\n\n"
            f"Revisa el estado del equipo desde el panel.\n\n"
            f"— Plataforma de Comercio de Energía"
        )
        return Mensaje(canal="email", asunto=f"Alerta IoT: {dispositivo_id}", cuerpo=cuerpo)


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
        return Mensaje(canal="email", asunto="Tu reporte energético del período", cuerpo=cuerpo)


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
# FAMILIA 2 — CANAL SMS  (sin asunto, cuerpo <= 160 caracteres)
# ===========================================================================
class _TransaccionSMS(NotificadorTransaccion):
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        verbo = "Compra" if rol == "comprador" else "Venta"
        cuerpo = _recortar(
            f"{verbo} confirmada: {transaccion['cantidad_kwh']} kWh a "
            f"${transaccion['precio_kwh']}/kWh (total ${transaccion['total']}).",
            LIMITE_SMS,
        )
        return Mensaje(canal="sms", cuerpo=cuerpo)


class _AlertaSMS(NotificadorAlertaIoT):
    def alertar(
        self, dispositivo_id: str, tipo_dispositivo: str, lectura: float, umbral: float
    ) -> Mensaje:
        cuerpo = _recortar(
            f"Alerta IoT {dispositivo_id}: lectura {lectura} kWh fuera de umbral "
            f"({umbral} kWh). Revisa el equipo.",
            LIMITE_SMS,
        )
        return Mensaje(canal="sms", cuerpo=cuerpo)


class _ReporteSMS(FormateadorReporte):
    def formatear(self, resumen: dict) -> Mensaje:
        cuerpo = _recortar(
            f"Reporte {resumen['usuario']}: prod {resumen['produccion_kwh']} kWh, "
            f"cons {resumen['consumo_kwh']} kWh, balance {resumen['balance_kwh']} kWh, "
            f"{resumen['transacciones']} operaciones.",
            LIMITE_SMS,
        )
        return Mensaje(canal="sms", cuerpo=cuerpo)


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
# FAMILIA 3 — CANAL PUSH  (título + cuerpo cortos + payload estructurado)
# ===========================================================================
class _TransaccionPush(NotificadorTransaccion):
    def notificar(self, transaccion: dict, destinatario: str, rol: str) -> Mensaje:
        return Mensaje(
            canal="push",
            asunto=_recortar("Operación cerrada", LIMITE_TITULO_PUSH),
            cuerpo=_recortar(
                f"{transaccion['cantidad_kwh']} kWh por ${transaccion['total']}",
                LIMITE_CUERPO_PUSH,
            ),
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
            canal="push",
            asunto=_recortar(f"Alerta: {dispositivo_id}", LIMITE_TITULO_PUSH),
            cuerpo=_recortar(
                f"Lectura {lectura} kWh fuera de umbral ({umbral} kWh)", LIMITE_CUERPO_PUSH
            ),
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
            canal="push",
            asunto=_recortar("Reporte energético", LIMITE_TITULO_PUSH),
            cuerpo=_recortar(
                f"Balance {resumen['balance_kwh']} kWh · {resumen['transacciones']} operaciones",
                LIMITE_CUERPO_PUSH,
            ),
            datos={
                "evento": "reporte",
                "usuario": resumen["usuario"],
                "produccion_kwh": resumen["produccion_kwh"],
                "consumo_kwh": resumen["consumo_kwh"],
                "balance_kwh": resumen["balance_kwh"],
                "transacciones": resumen["transacciones"],
            },
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
# Registro de canales disponibles
# ===========================================================================
_CANALES: dict[str, CanalNotificacionFactory] = {
    "email": CanalEmail(),
    "sms": CanalSMS(),
    "push": CanalPush(),
}


def obtener_canal(nombre: str) -> CanalNotificacionFactory:
    """
    Punto único donde se resuelve qué fábrica de canal usar. Agregar un
    canal nuevo solo requiere registrar su fábrica aquí.
    """
    try:
        return _CANALES[nombre]
    except KeyError:
        disponibles = ", ".join(_CANALES)
        raise ValueError(
            f"Canal de notificación '{nombre}' no soportado. Disponibles: {disponibles}"
        )


# ===========================================================================
# CLIENTE — usa la familia sin conocer las clases concretas
# ===========================================================================
class ServicioNotificaciones:
    """
    Recibe UNA fábrica de canal y construye con ella toda la familia de
    notificadores. Cualquier aviso que emita saldrá por el mismo canal y
    respetará sus reglas. Nunca menciona `CanalEmail`, `_TransaccionSMS`,
    etc.: solo conoce las interfaces abstractas.
    """

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
    """Función de conveniencia: nombre de canal -> servicio listo para usar."""
    return ServicioNotificaciones(obtener_canal(canal))


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tx = {
        "comprador": "u2",
        "vendedor": "u1",
        "cantidad_kwh": 6,
        "precio_kwh": 0.15,
        "total": 0.9,
        "timestamp": "2026-09-07T10:30:00",
    }
    resumen = {
        "usuario": "u1",
        "produccion_kwh": 18.4,
        "consumo_kwh": 12.1,
        "balance_kwh": 6.3,
        "transacciones": 3,
    }

    for nombre in ("email", "sms", "push"):
        servicio = crear_servicio(nombre)
        print("=" * 70)
        print(f"CANAL: {servicio.canal}")
        print("-" * 70)

        m1 = servicio.avisar_puja_ganada(tx, destinatario="u1", rol="vendedor")
        m2 = servicio.avisar_alerta_iot("bat-01", "bateria", lectura=-2.4, umbral=-1.0)
        m3 = servicio.enviar_reporte(resumen)

        for etiqueta, m in (("TRANSACCION", m1), ("ALERTA IoT", m2), ("REPORTE", m3)):
            print(f"[{etiqueta}] canal={m.canal} asunto={m.asunto!r}")
            print(f"  cuerpo ({len(m.cuerpo)} car.): {m.cuerpo}")
            if m.datos:
                print(f"  datos: {m.datos}")
        print()

    # Toda la familia sale coherente: el mismo canal en los 3 mensajes.
    print("Canal no soportado:")
    try:
        crear_servicio("paloma_mensajera")
    except ValueError as e:
        print(" ", e)
