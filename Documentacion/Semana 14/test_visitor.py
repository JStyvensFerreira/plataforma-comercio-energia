"""
Pruebas del patrón VISITOR — `visitor`.

Objetivo: verificar el doble despacho (cada nodo llama al método del
visitante que corresponde a su clase), que cada visitante concreto calcula
su análisis correctamente recorriendo todo el árbol, y que agregar un
análisis nuevo no requiere modificar las clases del árbol.
"""

import pytest

from visitor import (
    FACTOR_EMISION_KG_KWH,
    DispositivoHoja,
    GrupoEnergetico,
    VisitanteDiagnostico,
    VisitanteEnergetico,
    VisitanteExportarCSV,
    VisitanteHuellaCarbono,
)


def comunidad_demo():
    comunidad = GrupoEnergetico("Comunidad", "comunidad")
    comunidad.agregar(
        GrupoEnergetico("Hogar Ana", "hogar")
        .agregar(DispositivoHoja("panel-ana", "panel_solar", [3.0, 2.0]))
        .agregar(DispositivoHoja("medidor-ana", "medidor", [-1.0]))
    )
    comunidad.agregar(
        GrupoEnergetico("Hogar Luis", "hogar")
        .agregar(DispositivoHoja("medidor-luis", "medidor", [-2.0]))
        .agregar(DispositivoHoja("bateria-luis", "bateria"))
    )
    return comunidad


class VisitanteEspia(VisitanteEnergetico):
    def __init__(self):
        self.llamadas = []

    def visitar_dispositivo(self, dispositivo):
        self.llamadas.append(("dispositivo", dispositivo.nombre))

    def visitar_grupo(self, grupo):
        self.llamadas.append(("grupo", grupo.nombre))
        for hijo in grupo.hijos:
            hijo.aceptar(self)

    def resultado(self):
        return self.llamadas


# ---------------------------------------------------------------------------
# 1. Doble despacho
# ---------------------------------------------------------------------------
class TestDobleDespacho:
    def test_la_hoja_llama_a_visitar_dispositivo(self):
        espia = VisitanteEspia()
        DispositivoHoja("d1", "medidor").aceptar(espia)
        assert espia.llamadas == [("dispositivo", "d1")]

    def test_el_grupo_llama_a_visitar_grupo(self):
        espia = VisitanteEspia()
        GrupoEnergetico("g1").aceptar(espia)
        assert espia.llamadas == [("grupo", "g1")]

    def test_el_recorrido_visita_todos_los_nodos_en_orden(self):
        espia = VisitanteEspia()
        comunidad_demo().aceptar(espia)
        assert [n for _, n in espia.llamadas] == [
            "Comunidad", "Hogar Ana", "panel-ana", "medidor-ana",
            "Hogar Luis", "medidor-luis", "bateria-luis",
        ]

    def test_un_visitante_nuevo_no_requiere_cambiar_el_arbol(self):
        class ContadorDispositivos(VisitanteEnergetico):
            def __init__(self):
                self.n = 0

            def visitar_dispositivo(self, d):
                self.n += 1

            def visitar_grupo(self, g):
                for h in g.hijos:
                    h.aceptar(self)

            def resultado(self):
                return self.n

        contador = ContadorDispositivos()
        comunidad_demo().aceptar(contador)
        assert contador.resultado() == 4


# ---------------------------------------------------------------------------
# 2. VisitanteHuellaCarbono
# ---------------------------------------------------------------------------
class TestHuellaCarbono:
    def test_total_es_produccion_por_factor(self):
        v = VisitanteHuellaCarbono()
        comunidad_demo().aceptar(v)
        assert v.resultado()["total_kg_co2"] == round(5.0 * FACTOR_EMISION_KG_KWH, 3)

    def test_desglosa_por_hogar(self):
        v = VisitanteHuellaCarbono(factor_kg_kwh=1.0)
        comunidad_demo().aceptar(v)
        assert v.resultado()["por_hogar"] == {"Hogar Ana": 5.0, "Hogar Luis": 0.0}

    def test_el_consumo_no_suma_co2_evitado(self):
        v = VisitanteHuellaCarbono(factor_kg_kwh=1.0)
        DispositivoHoja("m", "medidor", [-4.0]).aceptar(v)
        assert v.resultado()["total_kg_co2"] == 0.0


# ---------------------------------------------------------------------------
# 3. VisitanteDiagnostico
# ---------------------------------------------------------------------------
class TestDiagnostico:
    def test_detecta_hogares_en_deficit(self):
        v = VisitanteDiagnostico()
        comunidad_demo().aceptar(v)
        assert v.resultado()["hogares_en_deficit"] == [{"hogar": "Hogar Luis", "balance_kwh": -2.0}]

    def test_detecta_dispositivos_sin_lecturas(self):
        v = VisitanteDiagnostico()
        comunidad_demo().aceptar(v)
        assert v.resultado()["dispositivos_sin_lecturas"] == ["bateria-luis"]

    def test_comunidad_sana_no_reporta_problemas(self):
        comunidad = GrupoEnergetico("C", "comunidad").agregar(
            GrupoEnergetico("H", "hogar").agregar(DispositivoHoja("p", "panel_solar", [1.0]))
        )
        v = VisitanteDiagnostico()
        comunidad.aceptar(v)
        assert v.resultado() == {"hogares_en_deficit": [], "dispositivos_sin_lecturas": []}


# ---------------------------------------------------------------------------
# 4. VisitanteExportarCSV
# ---------------------------------------------------------------------------
class TestExportarCSV:
    def test_una_fila_por_nodo_mas_encabezado(self):
        v = VisitanteExportarCSV()
        comunidad_demo().aceptar(v)
        assert len(v.resultado().splitlines()) == 1 + 7

    def test_la_ruta_refleja_la_posicion_en_el_arbol(self):
        v = VisitanteExportarCSV()
        comunidad_demo().aceptar(v)
        assert "Comunidad/Hogar Ana/panel-ana;dispositivo;panel_solar;5.0;0.0;5.0" in v.resultado()

    def test_reutilizar_el_mismo_visitante_acumula_filas(self):
        v = VisitanteExportarCSV()
        DispositivoHoja("a", "medidor").aceptar(v)
        DispositivoHoja("b", "medidor").aceptar(v)
        assert len(v.filas) == 3


# ---------------------------------------------------------------------------
# 5. Contrato
# ---------------------------------------------------------------------------
class TestContrato:
    def test_no_se_puede_instanciar_el_visitante_abstracto(self):
        with pytest.raises(TypeError):
            VisitanteEnergetico()

    def test_los_visitantes_concretos_implementan_la_interfaz(self):
        for v in (VisitanteHuellaCarbono(), VisitanteDiagnostico(), VisitanteExportarCSV()):
            assert isinstance(v, VisitanteEnergetico)
