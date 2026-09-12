"""
Pruebas del patrón PROTOTYPE — `prototype`.

Objetivo: verificar que clonar un dispositivo IoT ya calibrado preserva su
configuración (tipo, umbrales, notas) sin compartir estado mutable con el
original ni entre clones, que el cliente puede ajustar campos puntuales al
clonar, y que el `RegistroPlantillas` resuelve plantillas por nombre igual
que las demás fábricas del proyecto (mismo contrato: `ValueError` con las
opciones disponibles ante un nombre desconocido).
"""

import pytest

from prototype import DispositivoIoT, PrototipoDispositivo, RegistroPlantillas


# ---------------------------------------------------------------------------
# Fixture: un dispositivo "maestro" ya calibrado
# ---------------------------------------------------------------------------
@pytest.fixture
def panel_calibrado() -> DispositivoIoT:
    return DispositivoIoT(
        id="panel-maestro",
        usuario_id="u1",
        tipo="panel_solar",
        umbral_min=0.0,
        umbral_max=2.8,
        notas_calibracion=["Sombra parcial 14:00-16:00"],
    )


# ---------------------------------------------------------------------------
# 1. Identidad y tipo del clon
# ---------------------------------------------------------------------------
class TestIdentidadDelClon:
    def test_dispositivo_implementa_la_interfaz_prototipo(self, panel_calibrado):
        assert isinstance(panel_calibrado, PrototipoDispositivo)

    def test_el_clon_es_un_objeto_distinto_del_original(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon is not panel_calibrado

    def test_el_clon_tiene_el_id_nuevo(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon.id == "panel-02"

    def test_el_original_conserva_su_id(self, panel_calibrado):
        panel_calibrado.clonar("panel-02")
        assert panel_calibrado.id == "panel-maestro"

    def test_sin_nuevo_usuario_el_clon_hereda_el_usuario_del_original(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon.usuario_id == "u1"

    def test_con_nuevo_usuario_el_clon_queda_a_nombre_de_ese_usuario(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02", "u2")
        assert clon.usuario_id == "u2"


# ---------------------------------------------------------------------------
# 2. La configuración calibrada se preserva
# ---------------------------------------------------------------------------
class TestConfiguracionPreservada:
    def test_el_clon_conserva_el_tipo(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon.tipo == "panel_solar"

    def test_el_clon_conserva_los_umbrales_calibrados(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon.umbral_min == 0.0
        assert clon.umbral_max == 2.8

    def test_el_clon_conserva_las_notas_de_calibracion(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon.notas_calibracion == ["Sombra parcial 14:00-16:00"]


# ---------------------------------------------------------------------------
# 3. Copia PROFUNDA: sin estado compartido (la razón de ser de Prototype aquí)
# ---------------------------------------------------------------------------
class TestCopiaProfunda:
    def test_las_notas_del_clon_no_son_el_mismo_objeto_lista(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon.notas_calibracion is not panel_calibrado.notas_calibracion

    def test_modificar_las_notas_del_clon_no_afecta_al_original(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        clon.notas_calibracion.append("Nota exclusiva del clon")
        assert "Nota exclusiva del clon" not in panel_calibrado.notas_calibracion

    def test_dos_clones_del_mismo_original_no_comparten_las_notas(self, panel_calibrado):
        clon_a = panel_calibrado.clonar("panel-02")
        clon_b = panel_calibrado.clonar("panel-03")
        clon_a.notas_calibracion.append("Solo para panel-02")
        assert "Solo para panel-02" not in clon_b.notas_calibracion

    def test_modificar_un_umbral_del_clon_no_afecta_al_original(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        clon.umbral_max = 3.5
        assert panel_calibrado.umbral_max == 2.8


# ---------------------------------------------------------------------------
# 4. Override de campos puntuales al clonar
# ---------------------------------------------------------------------------
class TestOverrideAlClonar:
    def test_se_puede_ajustar_un_umbral_al_clonar(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02", umbral_max=3.5)
        assert clon.umbral_max == 3.5

    def test_el_override_no_afecta_al_original(self, panel_calibrado):
        panel_calibrado.clonar("panel-02", umbral_max=3.5)
        assert panel_calibrado.umbral_max == 2.8

    def test_los_campos_no_sobrescritos_mantienen_el_valor_clonado(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02", umbral_max=3.5)
        assert clon.umbral_min == 0.0
        assert clon.tipo == "panel_solar"

    def test_override_de_un_campo_inexistente_lanza_value_error(self, panel_calibrado):
        with pytest.raises(ValueError):
            panel_calibrado.clonar("panel-02", campo_que_no_existe=1)

    def test_cada_clon_actualiza_su_propio_sello_de_calibracion(self, panel_calibrado):
        clon = panel_calibrado.clonar("panel-02")
        assert clon.calibrado_en != "" and clon.calibrado_en is not None


# ---------------------------------------------------------------------------
# 5. Registro de plantillas (prototype registry)
# ---------------------------------------------------------------------------
class TestRegistroPlantillas:
    def test_plantilla_registrada_aparece_en_las_disponibles(self, panel_calibrado):
        registro = RegistroPlantillas()
        registro.registrar_plantilla("panel_con_sombra", panel_calibrado)
        assert "panel_con_sombra" in registro.plantillas_disponibles

    def test_crear_desde_plantilla_devuelve_un_clon_configurado(self, panel_calibrado):
        registro = RegistroPlantillas()
        registro.registrar_plantilla("panel_con_sombra", panel_calibrado)
        nuevo = registro.crear_desde_plantilla("panel_con_sombra", "panel-10", "u3")
        assert nuevo.id == "panel-10"
        assert nuevo.usuario_id == "u3"
        assert nuevo.umbral_max == 2.8

    def test_crear_desde_plantilla_admite_overrides(self, panel_calibrado):
        registro = RegistroPlantillas()
        registro.registrar_plantilla("panel_con_sombra", panel_calibrado)
        nuevo = registro.crear_desde_plantilla("panel_con_sombra", "panel-10", umbral_max=3.5)
        assert nuevo.umbral_max == 3.5

    def test_plantilla_inexistente_lanza_value_error_con_las_disponibles(self, panel_calibrado):
        registro = RegistroPlantillas()
        registro.registrar_plantilla("panel_con_sombra", panel_calibrado)
        with pytest.raises(ValueError, match="panel_con_sombra"):
            registro.crear_desde_plantilla("bateria_industrial", "bat-99")

    def test_registrar_una_plantilla_guarda_una_copia_no_la_referencia(self, panel_calibrado):
        """Ajustar el objeto original DESPUÉS de registrarlo no debe alterar
        la plantilla ya guardada (si no, la plantilla dejaría de ser un
        estado "congelado" y confiable para clonar)."""
        registro = RegistroPlantillas()
        registro.registrar_plantilla("panel_con_sombra", panel_calibrado)
        panel_calibrado.umbral_max = 99.0
        panel_calibrado.notas_calibracion.append("cambio posterior")

        nuevo = registro.crear_desde_plantilla("panel_con_sombra", "panel-10")
        assert nuevo.umbral_max == 2.8
        assert "cambio posterior" not in nuevo.notas_calibracion

    def test_dos_plantillas_distintas_producen_clones_independientes(self, panel_calibrado):
        bateria = DispositivoIoT(
            id="bat-maestra", usuario_id="u1", tipo="bateria",
            umbral_min=-2.0, umbral_max=2.0,
        )
        registro = RegistroPlantillas()
        registro.registrar_plantilla("panel_con_sombra", panel_calibrado)
        registro.registrar_plantilla("bateria_hogar", bateria)

        panel = registro.crear_desde_plantilla("panel_con_sombra", "panel-20")
        bat = registro.crear_desde_plantilla("bateria_hogar", "bat-20")

        assert panel.tipo == "panel_solar"
        assert bat.tipo == "bateria"
