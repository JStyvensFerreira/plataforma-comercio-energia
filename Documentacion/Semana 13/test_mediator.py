"""
Pruebas del patrón MEDIATOR — `mediator`.

Objetivo: verificar que los componentes del hogar (panel, medidor, batería,
mercado) solo hablan con la central; que la central balancea cada intervalo
cuando tiene la lectura del panel y la del medidor; que el excedente carga
la batería y el resto se vende (o se vierte); que el déficit descarga la
batería sin romper la reserva y el faltante se compra; y que cambiar las
reglas de la central no exige tocar ningún componente.
"""

import pytest

from mediator import (
    Bateria,
    CentralEnergiaHogar,
    Componente,
    MediadorEnergia,
    Medidor,
    PanelSolar,
    PuntoMercado,
    ReglasHogar,
)


def armar(capacidad=10, carga=5, **reglas):
    panel, medidor = PanelSolar("panel"), Medidor("medidor")
    bateria, mercado = Bateria("bateria", capacidad, carga), PuntoMercado()
    central = CentralEnergiaHogar(panel, medidor, bateria, mercado, ReglasHogar(**reglas))
    return central, panel, medidor, bateria, mercado


def intervalo(panel, medidor, generacion, consumo):
    panel.reportar_generacion(generacion)
    medidor.reportar_consumo(consumo)


# ---------------------------------------------------------------------------
# 1. Estructura: los componentes solo conocen a la central
# ---------------------------------------------------------------------------
class TestEstructura:
    def test_la_central_es_un_mediador(self):
        assert isinstance(armar()[0], MediadorEnergia)

    def test_la_central_se_registra_en_cada_componente(self):
        central, *componentes = armar()
        assert all(c.mediador is central for c in componentes)

    def test_ningun_componente_referencia_a_otro(self):
        _, *componentes = armar()
        for componente in componentes:
            referencias = [v for k, v in vars(componente).items() if k != "mediador"]
            assert not any(isinstance(v, Componente) for v in referencias)

    def test_un_componente_sin_central_no_puede_reportar(self):
        with pytest.raises(RuntimeError):
            PanelSolar("suelto").reportar_generacion(1)

    def test_evento_desconocido_se_rechaza(self):
        central, panel, *_ = armar()
        with pytest.raises(ValueError):
            central.notificar(panel, "eclipse", 1)


# ---------------------------------------------------------------------------
# 2. Excedente: batería primero, luego mercado
# ---------------------------------------------------------------------------
class TestExcedente:
    def test_solo_el_panel_no_dispara_el_balance(self):
        _, panel, _, bateria, mercado = armar()
        panel.reportar_generacion(8)
        assert bateria.carga_kwh == 5 and mercado.ordenes == []

    def test_el_orden_de_las_lecturas_no_importa(self):
        _, panel, medidor, bateria, _ = armar()
        medidor.reportar_consumo(1)
        panel.reportar_generacion(3)
        assert bateria.carga_kwh == 7

    def test_excedente_que_cabe_en_la_bateria_no_se_vende(self):
        _, panel, medidor, bateria, mercado = armar()
        intervalo(panel, medidor, 5, 2)
        assert bateria.carga_kwh == 8 and mercado.ordenes == []

    def test_lo_que_no_cabe_se_vende_al_precio_configurado(self):
        _, panel, medidor, bateria, mercado = armar(precio_venta_kwh=470)
        intervalo(panel, medidor, 9, 1)
        assert bateria.carga_kwh == 10
        assert mercado.ordenes == [{"tipo": "venta", "cantidad_kwh": 3, "precio_kwh": 470}]

    def test_si_el_hogar_no_vende_el_resto_se_vierte(self):
        central, panel, medidor, _, mercado = armar(vender_excedente=False)
        intervalo(panel, medidor, 9, 1)
        assert mercado.ordenes == []
        assert any("vierten 3" in linea for linea in central.registro)

    def test_sin_bateria_todo_el_excedente_va_al_mercado(self):
        _, panel, medidor, _, mercado = armar(capacidad=0, carga=0)
        intervalo(panel, medidor, 4, 1)
        assert mercado.ordenes[0]["cantidad_kwh"] == 3


# ---------------------------------------------------------------------------
# 3. Déficit: batería sin romper la reserva, luego mercado
# ---------------------------------------------------------------------------
class TestDeficit:
    def test_deficit_cubierto_por_la_bateria(self):
        _, panel, medidor, bateria, mercado = armar(carga=8, reserva_minima_pct=20)
        intervalo(panel, medidor, 1, 4)
        assert bateria.carga_kwh == 5 and mercado.ordenes == []

    def test_la_bateria_nunca_baja_de_la_reserva(self):
        _, panel, medidor, bateria, mercado = armar(carga=5, reserva_minima_pct=30)
        intervalo(panel, medidor, 0, 10)
        assert bateria.carga_kwh == 3
        assert mercado.ordenes == [{"tipo": "compra", "cantidad_kwh": 8, "precio_kwh": 520.0}]

    def test_bateria_bajo_la_reserva_no_entrega_nada(self):
        _, panel, medidor, bateria, mercado = armar(carga=1, reserva_minima_pct=20)
        intervalo(panel, medidor, 0, 2)
        assert bateria.carga_kwh == 1 and mercado.ordenes[0]["cantidad_kwh"] == 2

    def test_empate_no_mueve_energia(self):
        _, panel, medidor, bateria, mercado = armar()
        intervalo(panel, medidor, 3, 3)
        assert bateria.carga_kwh == 5 and mercado.ordenes == []

    def test_decimales_sin_residuos(self):
        _, panel, medidor, bateria, _ = armar(carga=0.3, reserva_minima_pct=0)
        intervalo(panel, medidor, 0.1, 0.4)
        assert bateria.carga_kwh == 0


# ---------------------------------------------------------------------------
# 4. Varios intervalos y reglas
# ---------------------------------------------------------------------------
class TestCoordinacion:
    def test_cada_intervalo_se_balancea_por_separado(self):
        _, panel, medidor, bateria, mercado = armar(carga=6, reserva_minima_pct=20)
        intervalo(panel, medidor, 9, 2)   # carga 4, vende 3
        intervalo(panel, medidor, 0, 11)  # entrega 8, compra 3
        assert [o["tipo"] for o in mercado.ordenes] == ["venta", "compra"]
        assert bateria.carga_kwh == 2

    def test_cambiar_las_reglas_cambia_la_decision_sin_tocar_componentes(self):
        central, panel, medidor, _, mercado = armar(carga=10)
        central.reglas = ReglasHogar(vender_excedente=False)
        intervalo(panel, medidor, 5, 1)
        assert mercado.ordenes == []

    def test_el_registro_explica_cada_decision(self):
        central, panel, medidor, *_ = armar(carga=9)
        intervalo(panel, medidor, 4, 1)
        assert central.registro == [
            "panel reporta generacion: 4 kWh",
            "medidor reporta consumo: 1 kWh",
            "bateria carga 1 kWh (100.0%)",
            "Se venden 2 kWh a 450.0 $/kWh",
        ]

    @pytest.mark.parametrize("metodo", ["reportar_generacion", "reportar_consumo"])
    def test_lecturas_negativas_se_rechazan(self, metodo):
        _, panel, medidor, *_ = armar()
        componente = panel if metodo == "reportar_generacion" else medidor
        with pytest.raises(ValueError):
            getattr(componente, metodo)(-1)

    def test_bateria_con_carga_invalida(self):
        with pytest.raises(ValueError):
            Bateria("b", capacidad_kwh=5, carga_kwh=6)
