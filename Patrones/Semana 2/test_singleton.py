"""
Pruebas del patrón SINGLETON — `plataforma_energia.PlataformaEnergia`.

Objetivo: verificar que, sin importar cuántas veces se instancie la
plataforma, siempre se obtiene el MISMO objeto y, por lo tanto, un único
estado compartido (libro de órdenes, usuarios, lecturas IoT).
"""

import threading

import pytest

from plataforma_energia import (
    DispositivoIoT,
    Orden,
    PlataformaEnergia,
    SingletonMeta,
    Usuario,
)


# ---------------------------------------------------------------------------
# 1. Identidad de la instancia
# ---------------------------------------------------------------------------
class TestIdentidadSingleton:
    def test_dos_instanciaciones_devuelven_el_mismo_objeto(self):
        a = PlataformaEnergia()
        b = PlataformaEnergia()
        assert a is b

    def test_el_id_de_memoria_no_cambia(self):
        assert id(PlataformaEnergia()) == id(PlataformaEnergia())

    def test_solo_se_registra_una_instancia_en_la_metaclase(self):
        PlataformaEnergia()
        PlataformaEnergia()
        assert len(SingletonMeta._instances) == 1
        assert PlataformaEnergia in SingletonMeta._instances

    def test_init_se_ejecuta_una_sola_vez(self):
        p1 = PlataformaEnergia()
        p1.registrar_usuario("u1", "Ana")
        # una segunda "creación" no debe reinicializar los diccionarios
        p2 = PlataformaEnergia()
        assert p2.usuarios == {"u1": Usuario("u1", "Ana")}


# ---------------------------------------------------------------------------
# 2. Estado compartido
# ---------------------------------------------------------------------------
class TestEstadoCompartido:
    def test_los_cambios_en_una_referencia_se_ven_en_la_otra(self):
        escritor = PlataformaEnergia()
        lector = PlataformaEnergia()

        escritor.registrar_usuario("u2", "Luis")
        escritor.publicar_venta("u2", cantidad_kwh=5, precio_kwh=0.12)

        assert "u2" in lector.usuarios
        assert len(lector.ordenes_venta) == 1

    def test_registrar_usuario_es_idempotente(self):
        p = PlataformaEnergia()
        u_a = p.registrar_usuario("u1", "Ana")
        u_b = p.registrar_usuario("u1", "Ana (repetida)")
        assert u_a is u_b
        assert len(p.usuarios) == 1


# ---------------------------------------------------------------------------
# 3. Seguridad ante concurrencia (Lock + doble verificación)
# ---------------------------------------------------------------------------
class TestConcurrencia:
    def test_multiples_hilos_obtienen_la_misma_instancia(self):
        SingletonMeta._instances.clear()
        instancias: list[int] = []
        barrera = threading.Barrier(20)

        def crear():
            barrera.wait()  # forzar que todos entren casi a la vez
            instancias.append(id(PlataformaEnergia()))

        hilos = [threading.Thread(target=crear) for _ in range(20)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        assert len(set(instancias)) == 1
        assert len(SingletonMeta._instances) == 1


# ---------------------------------------------------------------------------
# 4. Lógica de dominio operando sobre el estado único
# ---------------------------------------------------------------------------
class TestOrdenes:
    def test_publicar_venta_crea_orden_con_tipo_correcto(self):
        p = PlataformaEnergia()
        orden = p.publicar_venta("u1", cantidad_kwh=10, precio_kwh=0.15)
        assert isinstance(orden, Orden)
        assert orden.tipo == "venta"
        assert p.ordenes_venta == [orden]

    def test_ids_de_orden_son_incrementales_y_unicos(self):
        p = PlataformaEnergia()
        o1 = p.publicar_venta("u1", 1, 0.1)
        o2 = p.publicar_compra("u2", 1, 0.1)
        o3 = p.publicar_venta("u1", 1, 0.1)
        assert [o1.id, o2.id, o3.id] == [1, 2, 3]


class TestSubasta:
    def test_empareja_compra_y_venta_al_precio_del_vendedor(self):
        p = PlataformaEnergia()
        p.publicar_venta("vendedor", cantidad_kwh=10, precio_kwh=0.15)
        p.publicar_compra("comprador", cantidad_kwh=6, precio_kwh=0.18)

        txs = p.ejecutar_subasta()

        assert len(txs) == 1
        tx = txs[0]
        assert tx["comprador"] == "comprador"
        assert tx["vendedor"] == "vendedor"
        assert tx["cantidad_kwh"] == 6
        assert tx["precio_kwh"] == 0.15  # cierra al precio del vendedor
        assert tx["total"] == pytest.approx(0.9)

    def test_orden_parcialmente_ejecutada_permanece_con_el_saldo(self):
        p = PlataformaEnergia()
        p.publicar_venta("vendedor", cantidad_kwh=10, precio_kwh=0.15)
        p.publicar_compra("comprador", cantidad_kwh=6, precio_kwh=0.18)

        p.ejecutar_subasta()

        assert len(p.ordenes_venta) == 1
        assert p.ordenes_venta[0].cantidad_kwh == 4
        assert p.ordenes_compra == []

    def test_no_hay_cruce_si_el_comprador_paga_menos_que_el_vendedor(self):
        p = PlataformaEnergia()
        p.publicar_venta("vendedor", cantidad_kwh=5, precio_kwh=0.20)
        p.publicar_compra("comprador", cantidad_kwh=5, precio_kwh=0.10)

        txs = p.ejecutar_subasta()

        assert txs == []
        assert len(p.ordenes_venta) == 1
        assert len(p.ordenes_compra) == 1

    def test_la_transaccion_queda_en_el_historial(self):
        p = PlataformaEnergia()
        p.publicar_venta("v", 3, 0.1)
        p.publicar_compra("c", 3, 0.1)
        p.ejecutar_subasta()
        assert len(p.historial_transacciones) == 1


class TestIoTyPrediccion:
    def test_conectar_dispositivo_lo_registra_y_prepara_sus_lecturas(self):
        p = PlataformaEnergia()
        d = p.conectar_dispositivo("panel-01", "u1", "panel_solar")
        assert isinstance(d, DispositivoIoT)
        assert p.dispositivos["panel-01"] is d
        assert p.lecturas_iot["panel-01"] == []

    def test_enviar_lectura_a_dispositivo_no_registrado_lanza_error(self):
        p = PlataformaEnergia()
        with pytest.raises(ValueError, match="no está registrado"):
            p.enviar_lectura_iot("fantasma", 1.5)

    def test_simular_lecturas_agrega_n_valores(self):
        p = PlataformaEnergia()
        p.conectar_dispositivo("panel-01", "u1", "panel_solar")
        p.simular_lecturas("panel-01", n=5)
        assert len(p.lecturas_iot["panel-01"]) == 5

    def test_prediccion_es_media_movil_de_la_ventana(self):
        p = PlataformaEnergia()
        p.conectar_dispositivo("panel-01", "u1", "panel_solar")
        for valor in (2.0, 4.0, 6.0):
            p.enviar_lectura_iot("panel-01", valor)
        assert p.predecir_siguiente_valor("panel-01", ventana=3) == 4.0

    def test_prediccion_sin_lecturas_devuelve_none(self):
        p = PlataformaEnergia()
        p.conectar_dispositivo("panel-01", "u1", "panel_solar")
        assert p.predecir_siguiente_valor("panel-01") is None
