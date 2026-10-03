"""
Pruebas del patrón COMPOSITE — `composite`.

Objetivo: verificar que hojas (dispositivos) y grupos (hogar, edificio,
comunidad) comparten la interfaz `NodoEnergetico`, que cada grupo resuelve
producción/consumo/balance delegando recursivamente en sus hijos a cualquier
profundidad, que el cliente puede tratar igual a una hoja y a un grupo, y
que la estructura se protege de ciclos y de hijos duplicados.
"""

import pytest

from composite import DispositivoHoja, GrupoEnergetico, NodoEnergetico


# ---------------------------------------------------------------------------
# Árbol de ejemplo: Comunidad → Edificio → Apto → dispositivos, + una Casa
# ---------------------------------------------------------------------------
@pytest.fixture
def arbol():
    comunidad = GrupoEnergetico("Comunidad", "comunidad")
    edificio = GrupoEnergetico("Edificio", "edificio")
    apto = GrupoEnergetico("Apto 101", "hogar")
    panel = DispositivoHoja("panel-01", "panel_solar", [2.0, 3.0])
    medidor = DispositivoHoja("medidor-01", "medidor", [-1.0, -0.5])
    apto.agregar(panel)
    apto.agregar(medidor)
    edificio.agregar(apto)
    casa = GrupoEnergetico("Casa 7", "hogar")
    casa.agregar(DispositivoHoja("panel-07", "panel_solar", [1.5]))
    comunidad.agregar(edificio)
    comunidad.agregar(casa)
    return {
        "comunidad": comunidad,
        "edificio": edificio,
        "apto": apto,
        "casa": casa,
        "panel": panel,
        "medidor": medidor,
    }


# ---------------------------------------------------------------------------
# 1. Interfaz común (Component)
# ---------------------------------------------------------------------------
class TestInterfazComun:
    def test_no_se_puede_instanciar_el_componente_abstracto(self):
        with pytest.raises(TypeError):
            NodoEnergetico("x")

    def test_hoja_y_grupo_implementan_nodo_energetico(self):
        assert isinstance(DispositivoHoja("d", "panel_solar"), NodoEnergetico)
        assert isinstance(GrupoEnergetico("g"), NodoEnergetico)

    def test_el_cliente_trata_igual_a_una_hoja_y_a_un_grupo(self, arbol):
        def resumen(nodo: NodoEnergetico) -> tuple:
            return (nodo.produccion_kwh(), nodo.consumo_kwh(), nodo.balance_kwh())

        assert resumen(arbol["panel"]) == (5.0, 0.0, 5.0)
        assert resumen(arbol["apto"]) == (5.0, 1.5, 3.5)


# ---------------------------------------------------------------------------
# 2. Leaf: dispositivo individual
# ---------------------------------------------------------------------------
class TestHoja:
    def test_produccion_suma_solo_lecturas_positivas(self):
        assert DispositivoHoja("b", "bateria", [1.0, -0.5, 2.0]).produccion_kwh() == 3.0

    def test_consumo_suma_el_valor_absoluto_de_las_negativas(self):
        assert DispositivoHoja("b", "bateria", [1.0, -0.5, -2.0]).consumo_kwh() == 2.5

    def test_hoja_sin_lecturas_tiene_todo_en_cero(self):
        hoja = DispositivoHoja("d", "medidor")
        assert (hoja.produccion_kwh(), hoja.consumo_kwh(), hoja.balance_kwh()) == (0.0, 0.0, 0.0)

    def test_una_hoja_cuenta_como_un_dispositivo(self):
        assert DispositivoHoja("d", "medidor").cantidad_dispositivos() == 1

    def test_una_hoja_no_admite_operaciones_de_hijos(self):
        hoja = DispositivoHoja("d", "medidor")
        otra = DispositivoHoja("e", "medidor")
        with pytest.raises(TypeError):
            hoja.agregar(otra)
        with pytest.raises(TypeError):
            hoja.eliminar(otra)
        with pytest.raises(TypeError):
            hoja.obtener_hijo(0)


# ---------------------------------------------------------------------------
# 3. Composite: delega recursivamente en sus hijos
# ---------------------------------------------------------------------------
class TestComposite:
    def test_grupo_vacio_tiene_todo_en_cero(self):
        grupo = GrupoEnergetico("vacío")
        assert (grupo.produccion_kwh(), grupo.consumo_kwh(), grupo.cantidad_dispositivos()) == (0.0, 0.0, 0)

    def test_el_grupo_suma_a_sus_hijos_directos(self, arbol):
        assert arbol["apto"].produccion_kwh() == 5.0
        assert arbol["apto"].consumo_kwh() == 1.5

    def test_la_recursion_llega_a_cualquier_profundidad(self, arbol):
        # comunidad → edificio → apto → hojas  +  comunidad → casa → hoja
        assert arbol["comunidad"].produccion_kwh() == 6.5
        assert arbol["comunidad"].consumo_kwh() == 1.5
        assert arbol["comunidad"].balance_kwh() == 5.0

    def test_cantidad_de_dispositivos_cuenta_solo_las_hojas(self, arbol):
        assert arbol["comunidad"].cantidad_dispositivos() == 3

    def test_eliminar_un_hijo_actualiza_los_totales_de_los_ancestros(self, arbol):
        arbol["apto"].eliminar(arbol["panel"])
        assert arbol["comunidad"].produccion_kwh() == 1.5

    def test_eliminar_un_nodo_ajeno_lanza_value_error(self, arbol):
        with pytest.raises(ValueError):
            arbol["casa"].eliminar(arbol["panel"])

    def test_obtener_hijo_devuelve_el_hijo_por_indice(self, arbol):
        assert arbol["comunidad"].obtener_hijo(1) is arbol["casa"]

    def test_promedio_se_calcula_con_los_totales_no_promediando_promedios(self, arbol):
        # balance 5.0 / 3 dispositivos; el promedio de promedios daría otro valor
        assert arbol["comunidad"].promedio_balance_por_dispositivo() == round(5.0 / 3, 2)

    def test_to_dict_refleja_el_arbol_anidado(self, arbol):
        d = arbol["comunidad"].to_dict()
        assert d["nivel"] == "comunidad"
        assert d["hijos"][0]["hijos"][0]["hijos"][0]["nombre"] == "panel-01"
        assert d["dispositivos"] == 3


# ---------------------------------------------------------------------------
# 4. Integridad de la estructura (riesgo de ciclos)
# ---------------------------------------------------------------------------
class TestIntegridad:
    def test_un_grupo_no_puede_agregarse_a_si_mismo(self):
        grupo = GrupoEnergetico("g")
        with pytest.raises(ValueError, match="ciclo"):
            grupo.agregar(grupo)

    def test_no_se_puede_agregar_un_ancestro_como_hijo(self, arbol):
        with pytest.raises(ValueError, match="ciclo"):
            arbol["apto"].agregar(arbol["comunidad"])

    def test_no_se_puede_agregar_dos_veces_el_mismo_hijo(self, arbol):
        with pytest.raises(ValueError):
            arbol["apto"].agregar(arbol["panel"])


# ---------------------------------------------------------------------------
# 5. Abierto/cerrado
# ---------------------------------------------------------------------------
class TestExtensibilidad:
    def test_se_puede_agregar_un_tipo_de_hoja_sin_modificar_el_composite(self):
        class EstacionCarga(NodoEnergetico):
            def produccion_kwh(self):
                return 0.0

            def consumo_kwh(self):
                return 7.0

            def cantidad_dispositivos(self):
                return 1

            def to_dict(self):
                return {"nombre": self.nombre}

        hogar = GrupoEnergetico("Hogar", "hogar")
        hogar.agregar(DispositivoHoja("panel", "panel_solar", [10.0]))
        hogar.agregar(EstacionCarga("cargador-ev"))
        assert hogar.balance_kwh() == 3.0
