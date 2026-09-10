# Patrón Abstract Factory — Plataforma de Comercio de Energía

Implementación del patrón **Abstract Factory** (Fábrica Abstracta) sobre los
**canales de notificación** de la plataforma: correo, SMS y push a la app móvil.

- Código del patrón (con demo y docstring explicativo): [`abstract_factory.py`](abstract_factory.py)
- Pruebas del patrón: [`test_abstract_factory.py`](test_abstract_factory.py)
- Documento de casos de prueba: [`Patrones/README.md`](../README.md#casos-de-prueba--abstract-factory)
- Uso real en la aplicación: [`plataforma-energia-app/backend/notificaciones.py`](../../plataforma-energia-app/backend/notificaciones.py) — consumido por [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`_servicio_notificaciones`) y expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`/notificaciones`, `/usuarios/me/canal`, `/reportes/generar`)

## Por qué este patrón aquí

La plataforma tiene que avisar a los usuarios en tres momentos distintos:

1. Cuando la **subasta en tiempo real** cierra una operación → notificación de transacción.
2. Cuando una **lectura IoT** cruza un umbral (batería crítica, panel sin producir) → alerta de dispositivo.
3. Cuando toca el **resumen periódico** de producción/consumo → reporte.

Y cada usuario puede recibir esos avisos por un **canal** diferente. Cada canal
impone su propio formato y sus propias restricciones:

| Canal | Asunto | Cuerpo | Payload |
|---|---|---|---|
| Email | sí | largo, con saludo y firma | — |
| SMS | no | máx. 160 caracteres (se recorta) | — |
| Push | título ≤ 40 | ≤ 120 caracteres | `dict` estructurado para la app |

Sin el patrón, la decisión "¿qué canal?" quedaría repetida con `if/elif` en los
tres puntos donde se arma un mensaje, y sería fácil mezclar piezas incompatibles
(un asunto de correo en un SMS, un cuerpo que se pasa de 160).

## Cómo funciona

- **Familia de productos abstractos:** `NotificadorTransaccion`,
  `NotificadorAlertaIoT`, `FormateadorReporte`. Todos devuelven un `Mensaje`
  (objeto de valor uniforme: `canal`, `asunto`, `cuerpo`, `datos`).
- **Fábrica abstracta `CanalNotificacionFactory`:** declara los **métodos
  abstractos** (`abstract method`) que construyen cada miembro de la familia:
  `crear_notificador_transaccion()`, `crear_notificador_alerta_iot()`,
  `crear_formateador_reporte()`, más la propiedad `canal`.
- **Fábricas concretas:** `CanalEmail`, `CanalSMS`, `CanalPush`. Cada una
  implementa esos métodos abstractos devolviendo **sus** variantes, coherentes
  entre sí (mismo canal, mismas reglas de formato).
- **Cliente `ServicioNotificaciones`:** recibe **una** fábrica de canal y
  construye con ella toda la familia. Cualquier aviso que emita sale por el mismo
  canal y respeta sus reglas. Nunca menciona una clase concreta.
- **Registro:** `obtener_canal(nombre)` / `crear_servicio(nombre)` — punto único
  donde se resuelve el canal; un canal desconocido lanza `ValueError` con la
  lista de canales válidos.

```python
servicio = crear_servicio("sms")          # el cliente solo conoce el nombre
servicio.avisar_puja_ganada(tx, "u1", rol="vendedor")   # -> Mensaje(canal="sms", ...)
servicio.avisar_alerta_iot("bat-01", "bateria", -2.4, -1.0)
servicio.enviar_reporte(resumen)
# Los tres Mensaje salen con canal="sms" y cuerpo <= 160. Nunca se mezclan canales.
```

## Qué le aporta a la plataforma

- **Coherencia garantizada por construcción:** al elegir un canal, los tres tipos
  de aviso se renderizan con las mismas reglas. Es imposible obtener un SMS con
  asunto o un push sin `payload`.
- **Un solo punto de decisión del canal:** la preferencia del usuario se resuelve
  una vez (`crear_servicio`), no en cada lugar que envía un aviso.
- **Abierto/cerrado:** agregar WhatsApp, Telegram o un webhook es crear una
  fábrica concreta más (una clase) y registrarla; el código que envía avisos no
  cambia. La prueba `A-17` lo demuestra con un `CanalWebhook` definido dentro del
  test.
- **Relación con el Factory Method del proyecto:** el Factory Method crea **un**
  producto (`DispositivoIoT`); el Abstract Factory crea una **familia** de
  productos relacionados que deben usarse juntos (los tres notificadores de un
  canal).

## Diagrama

```
        CanalNotificacionFactory  (abstract factory)
        + canal
        + crear_notificador_transaccion()   ─┐  métodos
        + crear_notificador_alerta_iot()    ─┤  abstractos
        + crear_formateador_reporte()       ─┘
                 ▲            ▲            ▲
        ┌────────┘    ┌───────┘    ┌───────┘
   CanalEmail      CanalSMS     CanalPush          (concrete factories)
        │              │            │
   crea la familia coherente de ese canal:
   NotificadorTransaccion + NotificadorAlertaIoT + FormateadorReporte
                 ▲
        ServicioNotificaciones  (cliente: usa la familia, no conoce clases concretas)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Patrones/Semana 3/test_abstract_factory.py" -v   # 27 casos
python validar_pruebas.py abstract                                 # resumen del patrón
python "Patrones/Semana 3/abstract_factory.py"                     # demo por consola
```
