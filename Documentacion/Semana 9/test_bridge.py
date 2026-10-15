"""
Pruebas del patrón BRIDGE — `bridge`.

Objetivo: verificar que `SincronizadorDispositivo` (Abstraction) puede
combinarse con cualquier `ProtocoloLectura` (Implementor) sin conocer su
clase concreta, que `SincronizadorConReintentos` (RefinedAbstraction)
reintenta ante fallas de comunicación independientemente del protocolo que
tenga detrás, y que el registro de protocolos resuelve por nombre con el
mismo contrato que las demás fábricas del proyecto.
"""

import pytest

from bridge import (
    PROTOCOLOS_DISPONIBLES,
    ProtocoloHTTP,
    ProtocoloLectura,
    ProtocoloMQTT,
    ProtocoloSimulado,
    SincronizadorConReintentos,
    SincronizadorDispositivo,
    obtener_protocolo,
)


# ---------------------------------------------------------------------------
# Doble de prueba: protocolo controlable (falla N veces y luego responde)
# ---------------------------------------------------------------------------
class _ProtocoloInestable(ProtocoloLectura):
    nombre = "inestable"

    def __init__(self, fallas_antes_de_responder: int, valor: float):
        self._restantes = fallas_antes_de_responder
        self._valor = valor
        self.llamadas = 0

    def leer(self, dispositivo_id):
        self.llamadas += 1
        if self._restantes > 0:
            self._restantes -= 1
            raise ConnectionError("Timeout simulado")
        return self._valor


# ---------------------------------------------------------------------------
# 1. La Abstraction se combina con cualquier Implementor (desacoplamiento)
# ---------------------------------------------------------------------------
class TestDesacoplamientoAbstractionImplementor:
    def test_sincronizador_funciona_con_protocolo_http(self):
        sinc = SincronizadorDispositivo(ProtocoloHTTP({"panel-01": 2.8}))
        assert sinc.sincronizar("panel-01") == 2.8

    def test_sincronizador_funciona_con_protocolo_mqtt(self):
        sinc = SincronizadorDispositivo(ProtocoloMQTT({"bateria-01": -0.5}))
        assert sinc.sincronizar("bateria-01") == -0.5

    def test_sincronizador_funciona_con_protocolo_simulado(self):
        sinc = SincronizadorDispositivo(ProtocoloSimulado({"medidor-01": -1.2}))
        assert sinc.sincronizar("medidor-01") == -1.2

    def test_el_mismo_sincronizador_puede_cambiar_de_protocolo_en_tiempo_de_ejecucion(self):
        sinc = SincronizadorDispositivo(ProtocoloHTTP({"panel-01": 1.0}))
        assert sinc.sincronizar("panel-01") == 1.0
        sinc._protocolo = ProtocoloMQTT({"panel-01": 9.0})
        assert sinc.sincronizar("panel-01") == 9.0

    def test_no_se_puede_instanciar_el_implementor_abstracto(self):
        with pytest.raises(TypeError):
            ProtocoloLectura()


# ---------------------------------------------------------------------------
# 2. Protocolos concretos (Implementor)
# ---------------------------------------------------------------------------
class TestProtocolosConcretos:
    def test_protocolo_http_lanza_connection_error_si_no_hay_dato(self):
        with pytest.raises(ConnectionError):
            ProtocoloHTTP({}).leer("panel-99")

    def test_protocolo_mqtt_lanza_connection_error_si_no_hay_mensaje(self):
        with pytest.raises(ConnectionError):
            ProtocoloMQTT({}).leer("bateria-99")

    def test_protocolo_simulado_devuelve_valor_por_defecto_si_no_esta_configurado(self):
        assert ProtocoloSimulado({}).leer("lo-que-sea") == 1.0

    def test_cada_protocolo_expone_su_nombre(self):
        assert ProtocoloSimulado().nombre == "simulado"
        assert ProtocoloHTTP().nombre == "http"
        assert ProtocoloMQTT().nombre == "mqtt"


# ---------------------------------------------------------------------------
# 3. RefinedAbstraction: reintentos, independientes del protocolo
# ---------------------------------------------------------------------------
class TestSincronizadorConReintentos:
    def test_devuelve_la_lectura_si_el_protocolo_no_falla(self):
        sinc = SincronizadorConReintentos(ProtocoloHTTP({"panel-01": 3.3}))
        assert sinc.sincronizar("panel-01") == 3.3
        assert sinc.intentos_usados == 1

    def test_reintenta_tras_una_falla_y_termina_devolviendo_el_valor(self):
        protocolo = _ProtocoloInestable(fallas_antes_de_responder=2, valor=4.4)
        sinc = SincronizadorConReintentos(protocolo, intentos=3)
        assert sinc.sincronizar("medidor-03") == 4.4
        assert sinc.intentos_usados == 3
        assert protocolo.llamadas == 3

    def test_agota_los_intentos_y_propaga_el_error(self):
        protocolo = _ProtocoloInestable(fallas_antes_de_responder=5, valor=1.0)
        sinc = SincronizadorConReintentos(protocolo, intentos=3)
        with pytest.raises(ConnectionError):
            sinc.sincronizar("medidor-03")
        assert sinc.intentos_usados == 3

    def test_sin_reintentos_una_falla_se_propaga_de_inmediato(self):
        sinc = SincronizadorDispositivo(ProtocoloHTTP({}))
        with pytest.raises(ConnectionError):
            sinc.sincronizar("panel-02")

    def test_el_reintento_funciona_igual_con_cualquier_protocolo(self):
        protocolo_mqtt = _ProtocoloInestable(fallas_antes_de_responder=1, valor=2.0)
        sinc = SincronizadorConReintentos(protocolo_mqtt, intentos=2)
        assert sinc.sincronizar("x") == 2.0


# ---------------------------------------------------------------------------
# 4. Registro de protocolos
# ---------------------------------------------------------------------------
class TestRegistroDeProtocolos:
    def test_devuelve_el_protocolo_correcto_por_nombre(self):
        assert isinstance(obtener_protocolo("http"), ProtocoloHTTP)
        assert isinstance(obtener_protocolo("mqtt"), ProtocoloMQTT)
        assert isinstance(obtener_protocolo("simulado"), ProtocoloSimulado)

    def test_protocolo_no_soportado_lanza_value_error_con_los_disponibles(self):
        with pytest.raises(ValueError, match="http"):
            obtener_protocolo("zigbee")

    def test_protocolos_disponibles_coincide_con_el_registro(self):
        assert set(PROTOCOLOS_DISPONIBLES) == {"simulado", "http", "mqtt"}

    def test_se_puede_agregar_un_protocolo_sin_modificar_los_existentes(self):
        class ProtocoloFalso(ProtocoloLectura):
            nombre = "falso"

            def leer(self, dispositivo_id):
                return 42.0

        sinc = SincronizadorDispositivo(ProtocoloFalso())
        assert sinc.sincronizar("x") == 42.0
