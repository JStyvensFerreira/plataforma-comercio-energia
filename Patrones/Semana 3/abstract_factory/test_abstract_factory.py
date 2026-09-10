"""
Pruebas del patrón ABSTRACT FACTORY — `abstract_factory`.

Objetivo: verificar que la plataforma nunca instancia notificadores concretos.
Cada fábrica de canal crea la FAMILIA COMPLETA de notificadores de ese canal,
todos coherentes entre sí, y agregar un canal nuevo no obliga a tocar el código
existente (principio abierto/cerrado).
"""

import pytest

from abstract_factory import (
    LIMITE_CUERPO_PUSH,
    LIMITE_SMS,
    LIMITE_TITULO_PUSH,
    CanalEmail,
    CanalNotificacionFactory,
    CanalPush,
    CanalSMS,
    FormateadorReporte,
    Mensaje,
    NotificadorAlertaIoT,
    NotificadorTransaccion,
    ServicioNotificaciones,
    crear_servicio,
    obtener_canal,
)

# ---------------------------------------------------------------------------
# Datos de ejemplo (con la forma que produce la plataforma)
# ---------------------------------------------------------------------------
TX = {
    "comprador": "u2",
    "vendedor": "u1",
    "cantidad_kwh": 6,
    "precio_kwh": 0.15,
    "total": 0.9,
    "timestamp": "2026-09-07T10:30:00",
}
RESUMEN = {
    "usuario": "u1",
    "produccion_kwh": 18.4,
    "consumo_kwh": 12.1,
    "balance_kwh": 6.3,
    "transacciones": 3,
}

TODOS_LOS_CANALES = [
    ("email", CanalEmail),
    ("sms", CanalSMS),
    ("push", CanalPush),
]


def _emitir_los_tres(servicio: ServicioNotificaciones) -> list[Mensaje]:
    """Genera un mensaje de cada tipo de la familia."""
    return [
        servicio.avisar_puja_ganada(TX, destinatario="u1", rol="vendedor"),
        servicio.avisar_alerta_iot("bat-01", "bateria", lectura=-2.4, umbral=-1.0),
        servicio.enviar_reporte(RESUMEN),
    ]


# ---------------------------------------------------------------------------
# 1. Las clases abstractas no se pueden instanciar directamente
# ---------------------------------------------------------------------------
class TestAbstracciones:
    def test_no_se_puede_instanciar_la_fabrica_abstracta(self):
        with pytest.raises(TypeError):
            CanalNotificacionFactory()  # type: ignore[abstract]

    @pytest.mark.parametrize(
        "clase_producto", [NotificadorTransaccion, NotificadorAlertaIoT, FormateadorReporte]
    )
    def test_no_se_pueden_instanciar_los_productos_abstractos(self, clase_producto):
        with pytest.raises(TypeError):
            clase_producto()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# 2. Resolución de la fábrica de canal según el nombre solicitado
# ---------------------------------------------------------------------------
class TestObtenerCanal:
    @pytest.mark.parametrize("nombre, clase_fabrica", TODOS_LOS_CANALES)
    def test_devuelve_la_fabrica_de_canal_correcta(self, nombre, clase_fabrica):
        fabrica = obtener_canal(nombre)
        assert isinstance(fabrica, clase_fabrica)
        assert fabrica.canal == nombre

    def test_canal_no_soportado_lanza_value_error_con_los_disponibles(self):
        with pytest.raises(ValueError) as exc:
            obtener_canal("paloma_mensajera")
        mensaje = str(exc.value)
        assert "paloma_mensajera" in mensaje
        assert "email" in mensaje and "sms" in mensaje and "push" in mensaje


# ---------------------------------------------------------------------------
# 3. Cada fábrica crea la familia COMPLETA con la interfaz común
# ---------------------------------------------------------------------------
class TestFabricaCreaLaFamilia:
    @pytest.mark.parametrize("nombre, _clase", TODOS_LOS_CANALES)
    def test_crea_los_tres_miembros_de_la_familia(self, nombre, _clase):
        fabrica = obtener_canal(nombre)
        assert isinstance(
            fabrica.crear_notificador_transaccion(), NotificadorTransaccion
        )
        assert isinstance(fabrica.crear_notificador_alerta_iot(), NotificadorAlertaIoT)
        assert isinstance(fabrica.crear_formateador_reporte(), FormateadorReporte)

    @pytest.mark.parametrize("nombre, _clase", TODOS_LOS_CANALES)
    def test_los_notificadores_no_son_las_clases_abstractas(self, nombre, _clase):
        fabrica = obtener_canal(nombre)
        assert type(fabrica.crear_notificador_transaccion()) is not NotificadorTransaccion
        assert type(fabrica.crear_notificador_alerta_iot()) is not NotificadorAlertaIoT
        assert type(fabrica.crear_formateador_reporte()) is not FormateadorReporte


# ---------------------------------------------------------------------------
# 4. La familia sale COHERENTE: un solo canal en los tres mensajes
# ---------------------------------------------------------------------------
class TestFamiliaCoherente:
    @pytest.mark.parametrize("nombre, _clase", TODOS_LOS_CANALES)
    def test_todos_los_mensajes_salen_por_el_mismo_canal(self, nombre, _clase):
        servicio = crear_servicio(nombre)
        assert servicio.canal == nombre
        for mensaje in _emitir_los_tres(servicio):
            assert isinstance(mensaje, Mensaje)
            assert mensaje.canal == nombre

    def test_no_se_pueden_mezclar_canales_en_una_misma_familia(self):
        canales = {m.canal for s in (crear_servicio("email"), crear_servicio("sms"))
                   for m in _emitir_los_tres(s)}
        # cada servicio aporta su propio canal, nunca uno ajeno
        assert canales == {"email", "sms"}


# ---------------------------------------------------------------------------
# 5. Cada canal impone sus reglas de formato a TODA su familia
# ---------------------------------------------------------------------------
class TestReglasPorCanal:
    def test_email_siempre_lleva_asunto_y_cuerpo_largo(self):
        for m in _emitir_los_tres(crear_servicio("email")):
            assert m.asunto != ""
            assert "Plataforma de Comercio de Energía" in m.cuerpo
            assert m.datos == {}

    def test_sms_no_lleva_asunto_y_respeta_el_limite_de_160(self):
        for m in _emitir_los_tres(crear_servicio("sms")):
            assert m.asunto == ""
            assert len(m.cuerpo) <= LIMITE_SMS
            assert m.datos == {}

    def test_push_lleva_titulo_cuerpo_cortos_y_payload_estructurado(self):
        for m in _emitir_los_tres(crear_servicio("push")):
            assert 0 < len(m.asunto) <= LIMITE_TITULO_PUSH
            assert len(m.cuerpo) <= LIMITE_CUERPO_PUSH
            assert m.datos and "evento" in m.datos

    def test_sms_recorta_los_textos_muy_largos(self):
        tx_larga = dict(TX, vendedor="usuario-con-identificador-extremadamente-largo-" * 5)
        m = crear_servicio("sms").avisar_puja_ganada(tx_larga, "u1", "comprador")
        assert len(m.cuerpo) <= LIMITE_SMS


# ---------------------------------------------------------------------------
# 6. El cliente usa la familia sin conocer clases concretas
# ---------------------------------------------------------------------------
class TestServicioNotificaciones:
    def test_construye_la_familia_una_sola_vez(self):
        servicio = ServicioNotificaciones(CanalPush())
        assert servicio._transaccion is servicio._transaccion
        # el mismo notificador se reutiliza entre llamadas
        primero = servicio._transaccion
        servicio.avisar_puja_ganada(TX, "u1", "comprador")
        assert servicio._transaccion is primero

    def test_transaccion_distingue_comprador_de_vendedor(self):
        push = crear_servicio("push")
        como_comprador = push.avisar_puja_ganada(TX, "u2", "comprador")
        como_vendedor = push.avisar_puja_ganada(TX, "u1", "vendedor")
        assert como_comprador.datos["rol"] == "comprador"
        assert como_vendedor.datos["rol"] == "vendedor"

    def test_alerta_iot_incluye_el_dispositivo_y_los_valores(self):
        m = crear_servicio("push").avisar_alerta_iot("panel-01", "panel_solar", 0.0, 0.5)
        assert m.datos["dispositivo_id"] == "panel-01"
        assert m.datos["lectura"] == 0.0
        assert m.datos["umbral"] == 0.5

    def test_reporte_expone_el_balance_en_el_payload(self):
        m = crear_servicio("push").enviar_reporte(RESUMEN)
        assert m.datos["balance_kwh"] == RESUMEN["balance_kwh"]
        assert m.datos["transacciones"] == RESUMEN["transacciones"]


# ---------------------------------------------------------------------------
# 7. Abierto/cerrado: un canal nuevo no toca el código existente
# ---------------------------------------------------------------------------
class TestExtensibilidad:
    def test_se_puede_agregar_un_canal_sin_modificar_los_existentes(self):
        """
        Un canal 'webhook' nuevo solo implementa la fábrica abstracta y sus
        productos; `ServicioNotificaciones` lo usa igual que a los demás.
        """

        class _TxWebhook(NotificadorTransaccion):
            def notificar(self, transaccion, destinatario, rol):
                return Mensaje(canal="webhook", cuerpo="tx", datos=dict(transaccion))

        class _AlertaWebhook(NotificadorAlertaIoT):
            def alertar(self, dispositivo_id, tipo_dispositivo, lectura, umbral):
                return Mensaje(canal="webhook", cuerpo="alerta", datos={"id": dispositivo_id})

        class _ReporteWebhook(FormateadorReporte):
            def formatear(self, resumen):
                return Mensaje(canal="webhook", cuerpo="reporte", datos=dict(resumen))

        class CanalWebhook(CanalNotificacionFactory):
            @property
            def canal(self):
                return "webhook"

            def crear_notificador_transaccion(self):
                return _TxWebhook()

            def crear_notificador_alerta_iot(self):
                return _AlertaWebhook()

            def crear_formateador_reporte(self):
                return _ReporteWebhook()

        servicio = ServicioNotificaciones(CanalWebhook())
        for mensaje in _emitir_los_tres(servicio):
            assert mensaje.canal == "webhook"
