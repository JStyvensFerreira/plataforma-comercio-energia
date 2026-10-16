"""
Pruebas del patrón FLYWEIGHT — `flyweight`.

Objetivo: verificar que `FabricaFichasDispositivo` devuelve la MISMA
instancia de `FichaTipoDispositivo` para un mismo tipo (identidad, no solo
igualdad), que el estado extrínseco (id del dispositivo) nunca forma parte
del Flyweight, y que el registro de tipos es el punto único de verdad.
"""

import pytest

from flyweight import FabricaFichasDispositivo, FichaTipoDispositivo


# ---------------------------------------------------------------------------
# 1. Identidad compartida (el corazón del patrón)
# ---------------------------------------------------------------------------
class TestIdentidadCompartida:
    def test_dos_consultas_del_mismo_tipo_devuelven_la_misma_instancia(self):
        fabrica = FabricaFichasDispositivo()
        a = fabrica.obtener_ficha("panel_solar")
        b = fabrica.obtener_ficha("panel_solar")
        assert a is b

    def test_tipos_distintos_devuelven_instancias_distintas(self):
        fabrica = FabricaFichasDispositivo()
        panel = fabrica.obtener_ficha("panel_solar")
        bateria = fabrica.obtener_ficha("bateria")
        assert panel is not bateria

    def test_muchos_dispositivos_del_mismo_tipo_comparten_una_sola_ficha(self):
        fabrica = FabricaFichasDispositivo()
        ids = [f"panel-{i}" for i in range(50)]
        fichas = [fabrica.obtener_ficha("panel_solar") for _ in ids]
        assert len(set(id(f) for f in fichas)) == 1
        assert fabrica.fichas_creadas == 1


# ---------------------------------------------------------------------------
# 2. Contenido de la ficha (estado intrínseco)
# ---------------------------------------------------------------------------
class TestContenidoDeLaFicha:
    def test_la_ficha_trae_los_umbrales_del_tipo(self):
        fabrica = FabricaFichasDispositivo()
        ficha = fabrica.obtener_ficha("bateria")
        assert ficha.umbral_min == -2.0
        assert ficha.umbral_max == 2.0

    def test_la_ficha_es_inmutable(self):
        fabrica = FabricaFichasDispositivo()
        ficha = fabrica.obtener_ficha("medidor")
        with pytest.raises(Exception):
            ficha.umbral_max = 99.0

    def test_to_dict_expone_todos_los_campos(self):
        fabrica = FabricaFichasDispositivo()
        datos = fabrica.obtener_ficha("panel_solar").to_dict()
        assert set(datos) == {
            "tipo", "nombre_amigable", "categoria", "unidad",
            "umbral_min", "umbral_max", "descripcion",
        }


# ---------------------------------------------------------------------------
# 3. Registro de tipos
# ---------------------------------------------------------------------------
class TestRegistroDeTipos:
    def test_tipo_no_soportado_lanza_value_error_con_los_disponibles(self):
        fabrica = FabricaFichasDispositivo()
        with pytest.raises(ValueError, match="panel_solar"):
            fabrica.obtener_ficha("dron")

    def test_tipos_disponibles_coincide_con_el_catalogo(self):
        fabrica = FabricaFichasDispositivo()
        assert set(fabrica.tipos_disponibles) == {"panel_solar", "bateria", "medidor"}

    def test_cada_fabrica_tiene_su_propia_cache(self):
        fabrica_a = FabricaFichasDispositivo()
        fabrica_b = FabricaFichasDispositivo()
        ficha_a = fabrica_a.obtener_ficha("panel_solar")
        ficha_b = fabrica_b.obtener_ficha("panel_solar")
        assert ficha_a == ficha_b
        assert ficha_a is not ficha_b
