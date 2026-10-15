"""
Pruebas del patrón FACADE — `facade`.

Objetivo: verificar que `OnboardingDispositivo` coordina correctamente los
tres subsistemas (registro, simulación de lecturas y notificaciones) en el
orden correcto y en una sola llamada, que el resultado consolida la
información de los tres, y que los subsistemas se pueden seguir usando por
separado sin pasar por la fachada.
"""

import pytest

from facade import (
    Dispositivo,
    OnboardingDispositivo,
    RegistroDispositivos,
    ServicioNotificacionesSimple,
    SimuladorLecturas,
)


# ---------------------------------------------------------------------------
# 1. La fachada coordina los 3 subsistemas en una sola llamada
# ---------------------------------------------------------------------------
class TestCoordinacionDeLaFachada:
    def test_conectar_y_activar_registra_el_dispositivo(self):
        onboarding = OnboardingDispositivo()
        resultado = onboarding.conectar_y_activar("u1", "panel-01", "panel_solar")
        assert resultado["dispositivo"]["id"] == "panel-01"
        assert resultado["dispositivo"]["usuario_id"] == "u1"
        assert resultado["dispositivo"]["tipo"] == "panel_solar"

    def test_conectar_y_activar_simula_las_lecturas_pedidas(self):
        onboarding = OnboardingDispositivo()
        resultado = onboarding.conectar_y_activar("u1", "panel-01", "panel_solar", n_lecturas=5)
        assert len(resultado["lecturas"]) == 5

    def test_conectar_y_activar_deja_un_aviso_en_la_bandeja(self):
        onboarding = OnboardingDispositivo()
        resultado = onboarding.conectar_y_activar("u1", "panel-01", "panel_solar")
        assert resultado["notificacion"]["asunto"] == "Dispositivo activado"
        assert "panel-01" in resultado["notificacion"]["cuerpo"]

    def test_el_dispositivo_queda_registrado_en_el_subsistema_de_registro(self):
        onboarding = OnboardingDispositivo()
        onboarding.conectar_y_activar("u1", "panel-01", "panel_solar")
        dispositivo = onboarding.registro.obtener("panel-01")
        assert isinstance(dispositivo, Dispositivo)
        assert len(dispositivo.lecturas) == 3  # valor por defecto de n_lecturas

    def test_la_notificacion_queda_en_la_bandeja_del_usuario_correcto(self):
        onboarding = OnboardingDispositivo()
        onboarding.conectar_y_activar("u1", "panel-01", "panel_solar")
        assert len(onboarding.notificaciones.bandeja("u1")) == 1
        assert onboarding.notificaciones.bandeja("u2") == []

    def test_dos_altas_seguidas_no_se_mezclan(self):
        onboarding = OnboardingDispositivo()
        onboarding.conectar_y_activar("u1", "panel-01", "panel_solar")
        onboarding.conectar_y_activar("u2", "bateria-01", "bateria")
        assert onboarding.registro.obtener("panel-01").usuario_id == "u1"
        assert onboarding.registro.obtener("bateria-01").usuario_id == "u2"


# ---------------------------------------------------------------------------
# 2. Los subsistemas se pueden usar por separado (la fachada no los oculta)
# ---------------------------------------------------------------------------
class TestSubsistemasPorSeparado:
    def test_registro_dispositivos_funciona_sin_la_fachada(self):
        registro = RegistroDispositivos()
        disp = registro.registrar("panel-01", "u1", "panel_solar")
        assert registro.obtener("panel-01") is disp

    def test_simulador_lecturas_funciona_sin_la_fachada(self):
        disp = Dispositivo("panel-01", "u1", "panel_solar")
        nuevas = SimuladorLecturas().simular(disp, n=4)
        assert len(nuevas) == 4
        assert disp.lecturas == nuevas

    def test_servicio_notificaciones_funciona_sin_la_fachada(self):
        disp = Dispositivo("panel-01", "u1", "panel_solar", lecturas=[1.0])
        servicio = ServicioNotificacionesSimple()
        servicio.avisar_dispositivo_activo("u1", disp)
        assert len(servicio.bandeja("u1")) == 1

    def test_la_fachada_acepta_subsistemas_inyectados(self):
        registro = RegistroDispositivos()
        onboarding = OnboardingDispositivo(registro=registro)
        onboarding.conectar_y_activar("u1", "panel-01", "panel_solar")
        assert registro.obtener("panel-01").usuario_id == "u1"


# ---------------------------------------------------------------------------
# 3. Independencia entre instancias de la fachada
# ---------------------------------------------------------------------------
class TestIndependenciaDeInstancias:
    def test_dos_fachadas_no_comparten_estado(self):
        onboarding_a = OnboardingDispositivo()
        onboarding_b = OnboardingDispositivo()
        onboarding_a.conectar_y_activar("u1", "panel-01", "panel_solar")
        with pytest.raises(KeyError):
            onboarding_b.registro.obtener("panel-01")

    def test_simular_sin_pedir_lecturas_no_agrega_ninguna(self):
        onboarding = OnboardingDispositivo()
        resultado = onboarding.conectar_y_activar("u1", "panel-01", "panel_solar", n_lecturas=0)
        assert resultado["lecturas"] == []
        assert onboarding.registro.obtener("panel-01").lecturas == []
