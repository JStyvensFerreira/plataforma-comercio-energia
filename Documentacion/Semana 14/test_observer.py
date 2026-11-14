"""
Pruebas del patrón OBSERVER — `observer`.

Objetivo: verificar que `MercadoEnergia` avisa a todos sus observadores
suscritos (y solo a ellos), que se pueden suscribir/desuscribir en tiempo de
ejecución, que cada observador concreto reacciona solo a los eventos que le
interesan, y que un observador defectuoso no impide notificar al resto.
"""

import pytest

from observer import (
    ORDEN_PUBLICADA,
    TRANSACCION_EJECUTADA,
    AlertaPrecio,
    EstadisticasMercado,
    EventoMercado,
    MercadoEnergia,
    ObservadorMercado,
    RegistroAuditoria,
)


class ObservadorRoto(ObservadorMercado):
    def actualizar(self, evento):
        raise RuntimeError("falla simulada")


# ---------------------------------------------------------------------------
# 1. Suscripción y notificación (Subject)
# ---------------------------------------------------------------------------
class TestSuscripcion:
    def test_todos_los_suscritos_reciben_el_evento(self):
        mercado = MercadoEnergia()
        a, b = RegistroAuditoria(), RegistroAuditoria()
        mercado.suscribir(a)
        mercado.suscribir(b)
        mercado.publicar_venta("ana", 5, 450)
        assert len(a.eventos) == 1 and len(b.eventos) == 1

    def test_un_desuscrito_deja_de_recibir_eventos(self):
        mercado = MercadoEnergia()
        auditoria = RegistroAuditoria()
        mercado.suscribir(auditoria)
        mercado.desuscribir(auditoria)
        mercado.publicar_venta("ana", 5, 450)
        assert auditoria.eventos == []

    def test_suscribir_dos_veces_no_duplica_avisos(self):
        mercado = MercadoEnergia()
        auditoria = RegistroAuditoria()
        mercado.suscribir(auditoria)
        mercado.suscribir(auditoria)
        mercado.publicar_venta("ana", 5, 450)
        assert len(auditoria.eventos) == 1

    def test_sin_observadores_el_mercado_funciona_igual(self):
        mercado = MercadoEnergia()
        orden = mercado.publicar_venta("ana", 5, 450)
        assert orden["usuario"] == "ana"

    def test_el_evento_lleva_el_tipo_y_los_datos(self):
        mercado = MercadoEnergia()
        auditoria = RegistroAuditoria()
        mercado.suscribir(auditoria)
        mercado.registrar_transaccion("luis", "ana", 2, 400)
        evento = auditoria.eventos[0]
        assert evento.tipo == TRANSACCION_EJECUTADA
        assert evento.datos["vendedor"] == "ana"

    def test_un_observador_roto_no_impide_avisar_a_los_demas(self):
        mercado = MercadoEnergia()
        auditoria = RegistroAuditoria()
        mercado.suscribir(ObservadorRoto())
        mercado.suscribir(auditoria)
        mercado.publicar_venta("ana", 5, 450)
        assert len(auditoria.eventos) == 1
        assert "ObservadorRoto" in mercado.errores[0]

    def test_un_observador_puede_desuscribirse_mientras_recibe_el_evento(self):
        mercado = MercadoEnergia()
        auditoria = RegistroAuditoria()

        class UnaSolaVez(ObservadorMercado):
            def actualizar(self, evento):
                mercado.desuscribir(self)

        mercado.suscribir(UnaSolaVez())
        mercado.suscribir(auditoria)
        mercado.publicar_venta("ana", 5, 450)
        mercado.publicar_venta("ana", 5, 450)
        assert len(auditoria.eventos) == 2
        assert len(mercado.observadores) == 1


# ---------------------------------------------------------------------------
# 2. AlertaPrecio
# ---------------------------------------------------------------------------
class TestAlertaPrecio:
    def test_avisa_cuando_la_venta_esta_por_debajo_del_maximo(self):
        mercado = MercadoEnergia()
        alerta = AlertaPrecio("luis", precio_max=500)
        mercado.suscribir(alerta)
        mercado.publicar_venta("ana", 5, 450)
        assert len(alerta.avisos) == 1

    def test_el_precio_igual_al_maximo_tambien_avisa(self):
        mercado = MercadoEnergia()
        alerta = AlertaPrecio("luis", precio_max=500)
        mercado.suscribir(alerta)
        mercado.publicar_venta("ana", 5, 500)
        assert len(alerta.avisos) == 1

    def test_no_avisa_si_el_precio_supera_el_maximo(self):
        mercado = MercadoEnergia()
        alerta = AlertaPrecio("luis", precio_max=500)
        mercado.suscribir(alerta)
        mercado.publicar_venta("ana", 5, 650)
        assert alerta.avisos == []

    def test_no_avisa_por_ordenes_de_compra(self):
        mercado = MercadoEnergia()
        alerta = AlertaPrecio("luis", precio_max=500)
        mercado.suscribir(alerta)
        mercado.publicar_compra("pedro", 5, 100)
        assert alerta.avisos == []

    def test_no_avisa_por_las_ventas_del_propio_usuario(self):
        mercado = MercadoEnergia()
        alerta = AlertaPrecio("luis", precio_max=500)
        mercado.suscribir(alerta)
        mercado.publicar_venta("luis", 5, 100)
        assert alerta.avisos == []


# ---------------------------------------------------------------------------
# 3. EstadisticasMercado
# ---------------------------------------------------------------------------
class TestEstadisticas:
    def test_acumula_volumen_y_cantidad_de_transacciones(self):
        mercado = MercadoEnergia()
        stats = EstadisticasMercado()
        mercado.suscribir(stats)
        mercado.registrar_transaccion("luis", "ana", 5, 400)
        mercado.registrar_transaccion("pedro", "ana", 3, 600)
        assert stats.transacciones == 2
        assert stats.volumen_kwh == 8

    def test_el_precio_promedio_es_ponderado_por_volumen(self):
        mercado = MercadoEnergia()
        stats = EstadisticasMercado()
        mercado.suscribir(stats)
        mercado.registrar_transaccion("luis", "ana", 9, 400)
        mercado.registrar_transaccion("pedro", "ana", 1, 800)
        assert stats.precio_promedio == 440.0  # (9*400 + 1*800) / 10

    def test_ignora_las_ordenes_publicadas(self):
        mercado = MercadoEnergia()
        stats = EstadisticasMercado()
        mercado.suscribir(stats)
        mercado.publicar_venta("ana", 5, 450)
        assert stats.transacciones == 0 and stats.precio_promedio == 0.0


# ---------------------------------------------------------------------------
# 4. Contrato del Observer
# ---------------------------------------------------------------------------
class TestContrato:
    def test_los_observadores_concretos_implementan_la_interfaz(self):
        for obs in (AlertaPrecio("x", 1), EstadisticasMercado(), RegistroAuditoria()):
            assert isinstance(obs, ObservadorMercado)

    def test_no_se_puede_instanciar_el_observador_abstracto(self):
        with pytest.raises(TypeError):
            ObservadorMercado()

    def test_el_evento_es_inmutable(self):
        evento = EventoMercado(ORDEN_PUBLICADA, {})
        with pytest.raises(Exception):
            evento.tipo = "otro"
