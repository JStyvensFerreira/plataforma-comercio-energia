"""
Plataforma de Comercio de Energía — alta rápida de dispositivos (patrón
Facade). Coordina PlataformaEnergia (Factory Method), la simulación de
lecturas y el envío de un aviso de bienvenida (Builder + Abstract Factory)
en una sola llamada. Consumido por main.py.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from plataforma import DispositivoIoT, PlataformaEnergia


class OnboardingDispositivo:
    """
    Facade: sabe en qué orden y con qué datos llamar a los subsistemas de
    PlataformaEnergia (conectar_dispositivo, simular_lecturas,
    generar_reporte) para dejar un dispositivo nuevo listo para operar en
    una sola llamada. No reemplaza esos métodos — siguen pudiéndose llamar
    directamente para un control más fino.
    """

    def __init__(self, plataforma: "PlataformaEnergia") -> None:
        self._plataforma = plataforma

    def conectar_y_activar(
        self,
        usuario_id: str,
        id_dispositivo: str,
        tipo: str,
        umbral_min: Optional[float] = None,
        umbral_max: Optional[float] = None,
        n_lecturas: int = 3,
    ) -> dict:
        """Factory Method + simulación + Builder/Abstract Factory, en un solo paso."""
        dispositivo: "DispositivoIoT" = self._plataforma.conectar_dispositivo(
            id_dispositivo, usuario_id, tipo, umbral_min, umbral_max
        )
        if n_lecturas > 0:
            self._plataforma.simular_lecturas(id_dispositivo, n_lecturas)
        reporte = self._plataforma.generar_reporte(usuario_id, formato="resumen")
        return {
            "dispositivo": dispositivo.to_dict(),
            "lecturas": list(self._plataforma.lecturas_iot.get(id_dispositivo, [])),
            "reporte": reporte,
        }
