# Patrón Adapter — Plataforma de Comercio de Energía

Implementación del patrón **Adapter** (Adaptador) sobre el **cobro de las
transacciones** de la plataforma: integrar pasarelas de pago externas
(Stripe, PayU) con SDKs incompatibles entre sí.

- Código del patrón (con demo y docstring explicativo): [`adapter.py`](adapter.py)
- Pruebas del patrón: [`test_adapter.py`](test_adapter.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--adapter)
- Uso real en la aplicación: [`plataforma-energia-app/backend/pagos.py`](../../plataforma-energia-app/backend/pagos.py) — consumido por [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`_cobrar_transaccion`) y expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`/pagos`, `/pagos/pasarelas`, `/usuarios/me/pasarela`)

## Por qué este patrón aquí

La subasta en tiempo real (Singleton) cierra transacciones y calcula un
`total` en dinero, pero la plataforma nunca lo cobra de verdad: falta
conectar una pasarela de pagos externa, como ya contempla el alcance futuro
del proyecto ("puede ampliarse con pagos electrónicos").

El problema es que cada pasarela expone su propio SDK, incompatible con el
de las demás:

| SDK | Método | Unidad | Formato de respuesta |
|---|---|---|---|
| Stripe | `create_charge(amount_cents, currency, metadata)` | centavos, inglés | objeto `StripeCharge` (`status`) |
| PayU | `generar_transaccion(monto, moneda, referencia)` | pesos, español | `dict` (`estado`, `ordenId`) |

Si la plataforma llamara directamente a esos SDKs, la lógica de negocio
terminaría con condicionales ("si es Stripe... si es PayU...") repartidos en
cada punto donde se cobra, y agregar o cambiar de pasarela obligaría a tocar
esa lógica en todos esos puntos.

## Cómo funciona

- **Target `PasarelaPago`:** interfaz única que la plataforma ya espera:
  `procesar_pago(usuario_id, monto, concepto) -> ResultadoPago`.
- **Adaptees `StripeAPI` / `PayUAPI`:** simulan los SDKs reales, con nombres
  de método, unidades y formatos de respuesta incompatibles entre sí.
- **Adapters `AdaptadorStripe` / `AdaptadorPayU`:** implementan
  `PasarelaPago` y traducen la llamada uniforme a la forma que espera cada
  SDK (p. ej. `AdaptadorStripe` convierte el monto a centavos antes de
  llamar a `create_charge`), y traducen la respuesta de vuelta a
  `ResultadoPago`, el mismo objeto de valor sin importar la pasarela.
- **Registro:** `obtener_pasarela(nombre)` — punto único donde se resuelve
  la pasarela; un nombre desconocido lanza `ValueError` con las disponibles,
  igual que `obtener_factory`/`obtener_canal`/`crear_builder`.
- **Uso real:** `PlataformaEnergia._cobrar_transaccion()` cobra el `total`
  de cada transacción cerrada al comprador, usando SU pasarela preferida
  (`Usuario.pasarela_pago`), y guarda el resultado en una bandeja de pagos
  por usuario — expuesto como `PUT /usuarios/me/pasarela` y `GET /pagos`.

```python
pasarela = obtener_pasarela("payu")          # el cliente solo conoce el nombre
resultado = pasarela.procesar_pago("u2", 0.9, "Compra de 6 kWh")
# ResultadoPago(exitoso=True, id_transaccion_externa="PAYU-000001",
#               pasarela="payu", monto=0.9, mensaje="Pago procesado")
```

## Qué le aporta a la plataforma

- **Aísla la lógica de negocio del SDK externo:** la plataforma programa
  contra `PasarelaPago`; el código que cierra una subasta o consulta la
  bandeja de pagos no cambia si mañana se agrega o se retira una pasarela.
- **Un solo objeto de valor uniforme:** `ResultadoPago` es igual sin importar
  qué pasarela se usó, así que el resto del sistema (bandeja, reportes
  futuros) no necesita saber si el pago vino de Stripe o de PayU.
- **Abierto/cerrado:** agregar una pasarela nueva (Mercado Pago, Wompi) es
  crear un Adapter más y registrarlo; el código que cobra no cambia. La
  prueba `test_se_puede_agregar_una_pasarela_sin_modificar_las_existentes` lo
  demuestra con un `AdaptadorFalso` definido dentro del propio test.
- **Relación con las demás fábricas del proyecto:** Factory Method y
  Abstract Factory deciden **qué clase propia** instanciar; Adapter conecta
  la plataforma con una clase **externa y ya existente** cuya interfaz no se
  puede modificar, traduciéndola a la interfaz que la plataforma necesita.

## Diagrama

```
        PlataformaEnergia (Client)
                 │ usa
                 ▼
        «interface» PasarelaPago                    (Target)
        + procesar_pago(usuario_id, monto, concepto) -> ResultadoPago
                 ▲
        ┌────────┴────────┐
  AdaptadorStripe    AdaptadorPayU                   (Adapters)
        │ usa               │ usa
        ▼                   ▼
   StripeAPI            PayUAPI                      (Adaptees:
   + create_charge(...)  + generar_transaccion(...)   SDKs externos,
   + is_charge_successful(...)                        interfaces incompatibles)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 7/test_adapter.py" -v   # 17 casos
python "Documentacion/Semana 7/adapter.py"                     # demo por consola
```
