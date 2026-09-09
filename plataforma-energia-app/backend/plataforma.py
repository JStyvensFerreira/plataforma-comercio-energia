"""
Plataforma de Comercio de Energía — lógica de dominio (patrón Singleton).
Este módulo es consumido por main.py (API FastAPI).
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime
from statistics import mean
from threading import Lock
from typing import Optional
import itertools
import random

from notificaciones import Mensaje, crear_servicio, obtener_canal
from reportes import DatosReporte, DirectorReportes, crear_builder

# Rango "normal" de lectura por tipo de dispositivo. Una lectura fuera de este
# rango dispara una alerta IoT (patrón Abstract Factory: se notifica por el
# canal que el dueño del dispositivo tenga configurado).
UMBRALES_IOT: dict[str, tuple[float, float]] = {
    "panel_solar": (0.0, 3.5),
    "bateria": (-2.0, 2.0),
    "medidor": (-2.5, 0.5),
}


class SingletonMeta(type):
    """Metaclase que garantiza una única instancia, segura ante concurrencia."""
    _instances: dict[type, object] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass
class Usuario:
    id: str
    nombre: str
    password_hash: str = ""
    balance_kwh: float = 0.0
    canal_notificacion: str = "email"  # "email" | "sms" | "push"
    email: str = ""
    telefono: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "balance_kwh": self.balance_kwh,
            "canal_notificacion": self.canal_notificacion,
            "email": self.email,
            "telefono": self.telefono,
        }

    def destino_para(self, canal: str) -> str:
        """Dirección concreta a la que sale una notificación por ese canal."""
        if canal == "email":
            return self.email
        if canal == "sms":
            return self.telefono
        return self.id  # push: token/identificador del dispositivo


@dataclass
class Orden:
    id: int
    usuario_id: str
    tipo: str
    cantidad_kwh: float
    precio_kwh: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class DispositivoIoT:
    id: str
    usuario_id: str
    tipo: str
    umbral_min: Optional[float] = None
    umbral_max: Optional[float] = None

    def to_dict(self):
        return asdict(self)

    def fuera_de_rango(self, lectura: float) -> Optional[float]:
        """Devuelve el umbral cruzado (o None si la lectura es normal)."""
        if self.umbral_min is not None and lectura < self.umbral_min:
            return self.umbral_min
        if self.umbral_max is not None and lectura > self.umbral_max:
            return self.umbral_max
        return None


class PlataformaEnergia(metaclass=SingletonMeta):
    """Punto único de acceso al sistema de comercio de energía."""

    def __init__(self):
        self.usuarios: dict[str, Usuario] = {}
        self.dispositivos: dict[str, DispositivoIoT] = {}
        self.ordenes_venta: list[Orden] = []
        self.ordenes_compra: list[Orden] = []
        self.historial_transacciones: list[dict] = []
        self.lecturas_iot: dict[str, list[float]] = {}
        # Bandeja de notificaciones por usuario (patrón Abstract Factory).
        self.notificaciones: dict[str, list[dict]] = {}
        self._contador_ordenes = itertools.count(1)

    def registrar_usuario(
        self,
        id_: str,
        nombre: str,
        password_hash: str = "",
        canal_notificacion: str = "email",
        email: str = "",
        telefono: str = "",
    ) -> Usuario:
        obtener_canal(canal_notificacion)  # valida el canal antes de crear el usuario
        return self.usuarios.setdefault(
            id_,
            Usuario(
                id_,
                nombre,
                password_hash,
                canal_notificacion=canal_notificacion,
                email=email,
                telefono=telefono,
            ),
        )

    def actualizar_contacto(
        self, usuario_id: str, email: Optional[str] = None, telefono: Optional[str] = None
    ) -> Usuario:
        usuario = self.usuarios[usuario_id]
        if email is not None:
            usuario.email = email
        if telefono is not None:
            usuario.telefono = telefono
        return usuario

    # ---------- Notificaciones (patrón Abstract Factory) ----------
    def _servicio_notificaciones(self, usuario_id: str):
        """
        Construye el servicio de notificaciones para un usuario ELIGIENDO la
        fábrica abstracta según su canal preferido. El resto de la plataforma
        no conoce ninguna clase concreta de notificador.
        """
        usuario = self.usuarios.get(usuario_id)
        canal = usuario.canal_notificacion if usuario else "email"
        return crear_servicio(canal)

    def _guardar_notificacion(self, usuario_id: str, mensaje: Mensaje) -> dict:
        usuario = self.usuarios.get(usuario_id)
        if usuario is not None and not mensaje.destino:
            mensaje = replace(mensaje, destino=usuario.destino_para(mensaje.canal))
        registro = mensaje.to_dict()
        registro["timestamp"] = datetime.now().isoformat()
        self.notificaciones.setdefault(usuario_id, []).append(registro)
        return registro

    def cambiar_canal_notificacion(self, usuario_id: str, canal: str) -> Usuario:
        obtener_canal(canal)  # ValueError si no existe
        usuario = self.usuarios[usuario_id]
        usuario.canal_notificacion = canal
        return usuario

    def bandeja_notificaciones(self, usuario_id: str) -> list[dict]:
        return list(self.notificaciones.get(usuario_id, []))

    # ---------- Reporte energético (patrón Builder) ----------
    def _recolectar_datos_reporte(self, usuario_id: str) -> DatosReporte:
        """
        Reúne la materia prima del reporte desde el estado del Singleton. El
        builder solo le da forma; aquí no se decide ni el formato ni las
        secciones.
        """
        produccion = consumo = 0.0
        lecturas_por_dispositivo: dict[str, list[float]] = {}
        prediccion_por_dispositivo: dict[str, float | None] = {}
        for disp in self.dispositivos.values():
            if disp.usuario_id != usuario_id:
                continue
            lecturas = list(self.lecturas_iot.get(disp.id, []))
            lecturas_por_dispositivo[disp.id] = lecturas
            prediccion_por_dispositivo[disp.id] = self.predecir_siguiente_valor(disp.id)
            for lectura in lecturas:
                if lectura >= 0:
                    produccion += lectura
                else:
                    consumo += -lectura
        transacciones = [
            tx
            for tx in self.historial_transacciones
            if usuario_id in (tx["comprador"], tx["vendedor"])
        ]
        return DatosReporte(
            usuario=usuario_id,
            periodo=datetime.now().strftime("%Y-%m"),
            produccion_kwh=round(produccion, 2),
            consumo_kwh=round(consumo, 2),
            lecturas_por_dispositivo=lecturas_por_dispositivo,
            transacciones=transacciones,
            prediccion_por_dispositivo=prediccion_por_dispositivo,
        )

    def generar_reporte(self, usuario_id: str, formato: str = "detallado") -> dict:
        """
        Construye el reporte energético del usuario PASO A PASO (patrón Builder)
        en el formato pedido, y además deja el resumen en su bandeja por su
        canal (patrón Abstract Factory).
        """
        datos = self._recolectar_datos_reporte(usuario_id)

        # 1) El reporte que se devuelve, en la representación elegida.
        director = DirectorReportes(crear_builder(formato))
        reporte = director.reporte_completo(datos)

        # 2) El aviso por el canal del usuario: el builder "resumen" produce el
        #    dict plano que espera el FormateadorReporte del Abstract Factory.
        director.builder = crear_builder("resumen")
        resumen = director.reporte_ejecutivo(datos)
        mensaje = self._servicio_notificaciones(usuario_id).enviar_reporte(resumen)
        registro = self._guardar_notificacion(usuario_id, mensaje)

        return {
            "formato": formato,
            "reporte": reporte.to_dict() if hasattr(reporte, "to_dict") else reporte,
            "notificacion": registro,
        }

    def publicar_venta(self, usuario_id: str, cantidad_kwh: float, precio_kwh: float) -> Orden:
        orden = Orden(next(self._contador_ordenes), usuario_id, "venta", cantidad_kwh, precio_kwh)
        self.ordenes_venta.append(orden)
        return orden

    def publicar_compra(self, usuario_id: str, cantidad_kwh: float, precio_kwh: float) -> Orden:
        orden = Orden(next(self._contador_ordenes), usuario_id, "compra", cantidad_kwh, precio_kwh)
        self.ordenes_compra.append(orden)
        return orden

    def ejecutar_subasta(self) -> list[dict]:
        self.ordenes_venta.sort(key=lambda o: o.precio_kwh)
        self.ordenes_compra.sort(key=lambda o: -o.precio_kwh)

        transacciones = []
        for compra in list(self.ordenes_compra):
            for venta in list(self.ordenes_venta):
                if compra.precio_kwh >= venta.precio_kwh and compra.cantidad_kwh > 0 and venta.cantidad_kwh > 0:
                    cantidad = min(compra.cantidad_kwh, venta.cantidad_kwh)
                    precio_final = venta.precio_kwh
                    compra.cantidad_kwh -= cantidad
                    venta.cantidad_kwh -= cantidad

                    tx = {
                        "comprador": compra.usuario_id,
                        "vendedor": venta.usuario_id,
                        "cantidad_kwh": cantidad,
                        "precio_kwh": precio_final,
                        "total": round(cantidad * precio_final, 2),
                        "timestamp": datetime.now().isoformat(),
                    }
                    transacciones.append(tx)
                    self.historial_transacciones.append(tx)

                    # Aviso a las dos partes por SU canal (Abstract Factory).
                    for usuario_id, rol in ((tx["comprador"], "comprador"), (tx["vendedor"], "vendedor")):
                        mensaje = self._servicio_notificaciones(usuario_id).avisar_puja_ganada(
                            tx, destinatario=usuario_id, rol=rol
                        )
                        self._guardar_notificacion(usuario_id, mensaje)

                    if compra.cantidad_kwh == 0:
                        break

        self.ordenes_venta = [o for o in self.ordenes_venta if o.cantidad_kwh > 0]
        self.ordenes_compra = [o for o in self.ordenes_compra if o.cantidad_kwh > 0]
        return transacciones

    def conectar_dispositivo(
        self,
        id_dispositivo: str,
        usuario_id: str,
        tipo: str,
        umbral_min: Optional[float] = None,
        umbral_max: Optional[float] = None,
    ) -> DispositivoIoT:
        if umbral_min is None and umbral_max is None:
            umbral_min, umbral_max = UMBRALES_IOT.get(tipo, (None, None))
        dispositivo = DispositivoIoT(id_dispositivo, usuario_id, tipo, umbral_min, umbral_max)
        self.dispositivos[id_dispositivo] = dispositivo
        self.lecturas_iot.setdefault(id_dispositivo, [])
        return dispositivo

    def enviar_lectura_iot(self, id_dispositivo: str, valor_kwh: float) -> None:
        if id_dispositivo not in self.dispositivos:
            raise ValueError(f"Dispositivo {id_dispositivo} no está registrado")
        self.lecturas_iot[id_dispositivo].append(valor_kwh)

        dispositivo = self.dispositivos[id_dispositivo]
        umbral = dispositivo.fuera_de_rango(valor_kwh)
        if umbral is not None:
            mensaje = self._servicio_notificaciones(dispositivo.usuario_id).avisar_alerta_iot(
                id_dispositivo, dispositivo.tipo, valor_kwh, umbral
            )
            self._guardar_notificacion(dispositivo.usuario_id, mensaje)

    def simular_lecturas(self, id_dispositivo: str, n: int = 5) -> None:
        for _ in range(n):
            self.enviar_lectura_iot(id_dispositivo, round(random.uniform(0.5, 4.0), 2))

    def predecir_siguiente_valor(self, id_dispositivo: str, ventana: int = 3) -> Optional[float]:
        lecturas = self.lecturas_iot.get(id_dispositivo, [])
        if not lecturas:
            return None
        return round(mean(lecturas[-ventana:]), 2)
