"""
Plataforma de Comercio de Energía
==================================
Implementa el requerimiento #16:
  - Compra/venta de excedentes energéticos entre usuarios
  - Sistema de subastas en tiempo real
  - Integración con dispositivos IoT domésticos
  - Predicción de producción y consumo

Patrón aplicado: FACADE (Fachada)
-----------------------------------
Dar de alta un dispositivo IoT y dejarlo "listo para operar" hoy requiere
coordinar varios subsistemas por separado, en un orden concreto:
  1. Registrar el dispositivo (subsistema de registro).
  2. Simular algunas lecturas iniciales, para que no aparezca vacío.
  3. Armar un aviso de bienvenida y dejarlo en la bandeja del usuario.

Si cada cliente (el frontend, un futuro script de onboarding masivo, un bot)
tuviera que conocer los tres subsistemas y llamarlos en el orden correcto,
cualquier cambio en ese orden —o un paso nuevo— obligaría a tocar cada punto
que da de alta un dispositivo.

Con FACADE, una sola clase (`OnboardingDispositivo`) conoce el orden
correcto y expone UN método (`conectar_y_activar`). El cliente ya no
necesita conocer `RegistroDispositivos`, `SimuladorLecturas` ni
`ServicioNotificacionesSimple` por separado. La fachada NO reemplaza esos
subsistemas ni oculta su funcionalidad: quien necesite control fino los
puede seguir usando directamente, igual que antes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import random


# ---------------------------------------------------------------------------
# SUBSISTEMA 1 — registro de dispositivos
# ---------------------------------------------------------------------------
@dataclass
class Dispositivo:
    id: str
    usuario_id: str
    tipo: str
    lecturas: list[float] = field(default_factory=list)


class RegistroDispositivos:
    """Subsistema: alta y consulta de dispositivos. No sabe nada de lecturas ni avisos."""

    def __init__(self) -> None:
        self._dispositivos: dict[str, Dispositivo] = {}

    def registrar(self, id_dispositivo: str, usuario_id: str, tipo: str) -> Dispositivo:
        dispositivo = Dispositivo(id_dispositivo, usuario_id, tipo)
        self._dispositivos[id_dispositivo] = dispositivo
        return dispositivo

    def obtener(self, id_dispositivo: str) -> Dispositivo:
        return self._dispositivos[id_dispositivo]


# ---------------------------------------------------------------------------
# SUBSISTEMA 2 — lecturas simuladas
# ---------------------------------------------------------------------------
class SimuladorLecturas:
    """Subsistema: genera lecturas. No sabe nada del registro ni de los avisos."""

    def simular(self, dispositivo: Dispositivo, n: int = 3) -> list[float]:
        nuevas = [round(random.uniform(0.5, 4.0), 2) for _ in range(n)]
        dispositivo.lecturas.extend(nuevas)
        return nuevas


# ---------------------------------------------------------------------------
# SUBSISTEMA 3 — notificaciones (bandeja)
# ---------------------------------------------------------------------------
class ServicioNotificacionesSimple:
    """Subsistema: arma y guarda un mensaje. No sabe nada de dispositivos ni lecturas."""

    def __init__(self) -> None:
        self._bandejas: dict[str, list[dict]] = {}

    def avisar_dispositivo_activo(self, usuario_id: str, dispositivo: Dispositivo) -> dict:
        mensaje = {
            "asunto": "Dispositivo activado",
            "cuerpo": (
                f"Tu dispositivo {dispositivo.id} ({dispositivo.tipo}) ya está enviando "
                f"lecturas: {dispositivo.lecturas}"
            ),
        }
        self._bandejas.setdefault(usuario_id, []).append(mensaje)
        return mensaje

    def bandeja(self, usuario_id: str) -> list[dict]:
        return list(self._bandejas.get(usuario_id, []))


# ---------------------------------------------------------------------------
# FACADE — un solo punto de entrada que coordina los 3 subsistemas
# ---------------------------------------------------------------------------
class OnboardingDispositivo:
    """
    Facade: sabe en qué orden y con qué datos llamar a cada subsistema para
    dejar un dispositivo nuevo listo para operar, en una sola llamada. No
    reemplaza los subsistemas — el cliente que quiera control fino los sigue
    usando directamente.
    """

    def __init__(
        self,
        registro: Optional[RegistroDispositivos] = None,
        simulador: Optional[SimuladorLecturas] = None,
        notificaciones: Optional[ServicioNotificacionesSimple] = None,
    ) -> None:
        self.registro = registro or RegistroDispositivos()
        self.simulador = simulador or SimuladorLecturas()
        self.notificaciones = notificaciones or ServicioNotificacionesSimple()

    def conectar_y_activar(
        self, usuario_id: str, id_dispositivo: str, tipo: str, n_lecturas: int = 3
    ) -> dict:
        """Registra, simula lecturas iniciales y avisa al usuario, en ese orden."""
        dispositivo = self.registro.registrar(id_dispositivo, usuario_id, tipo)
        lecturas = self.simulador.simular(dispositivo, n_lecturas)
        aviso = self.notificaciones.avisar_dispositivo_activo(usuario_id, dispositivo)
        return {
            "dispositivo": {
                "id": dispositivo.id,
                "usuario_id": dispositivo.usuario_id,
                "tipo": dispositivo.tipo,
            },
            "lecturas": lecturas,
            "notificacion": aviso,
        }


# ---------------------------------------------------------------------------
# DEMO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Sin fachada: el cliente coordina los 3 subsistemas a mano\n")
    registro = RegistroDispositivos()
    simulador = SimuladorLecturas()
    notificaciones = ServicioNotificacionesSimple()

    disp = registro.registrar("panel-01", "u1", "panel_solar")
    simulador.simular(disp, 3)
    notificaciones.avisar_dispositivo_activo("u1", disp)
    print(f"  Dispositivo {disp.id} con lecturas {disp.lecturas}")

    print("\nCon fachada: una sola llamada hace lo mismo\n")
    onboarding = OnboardingDispositivo()
    resultado = onboarding.conectar_y_activar("u2", "bateria-01", "bateria")
    print(" ", resultado)

    print("\nLos subsistemas se pueden seguir usando por separado si hace falta:")
    print("  bandeja de u2:", onboarding.notificaciones.bandeja("u2"))
