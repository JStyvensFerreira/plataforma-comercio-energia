# Patrón Strategy — Plataforma de Comercio de Energía

Implementación del patrón **Strategy** sobre la **regla de precio de cierre
de la subasta**: cuando una compra y una venta se cruzan, la estrategia
configurada decide a qué precio por kWh se cierra el trato (el que pide el
vendedor, el que ofrece el comprador o el punto medio). La regla se puede
cambiar mientras la plataforma está en marcha.

- Código del patrón (con demo y docstring explicativo): [`strategy.py`](strategy.py)
- Pruebas del patrón: [`test_strategy.py`](test_strategy.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--strategy)
- Uso real en la aplicación: [`plataforma-energia-app/backend/estrategias_precio.py`](../../plataforma-energia-app/backend/estrategias_precio.py) — usado por `ejecutar_subasta` y `cambiar_estrategia_precio` en [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py), expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET`/`PUT /subasta/estrategia`)

## Por qué este patrón aquí

Hasta ahora la subasta cerraba siempre al precio del vendedor, con la regla
escrita dentro de `ejecutar_subasta`. Pero hay varias reglas válidas y cada
comunidad energética prefiere una: pagar lo que pide el vendedor favorece
al comprador; pagar lo que ofrece el comprador favorece al vendedor; el
punto medio reparte la diferencia. Con un `if/elif` en la subasta, cada
regla nueva obligaría a modificar y volver a probar el algoritmo de
emparejamiento, que no tiene nada que ver con el precio.

## Cómo funciona

- **Strategy `EstrategiaPrecio`:** interfaz común `precio_cierre(compra, venta)`.
- **Concrete Strategies:**

| Estrategia | `nombre` | Precio de cierre |
|---|---|---|
| `PrecioVendedor` | `vendedor` | `venta.precio_kwh` (pay-as-ask) |
| `PrecioComprador` | `comprador` | `compra.precio_kwh` (pay-as-bid) |
| `PrecioPuntoMedio` | `punto_medio` | promedio de los dos precios |

- **Context `MotorSubasta`** (en la app, `PlataformaEnergia.ejecutar_subasta`):
  empareja compras caras con ventas baratas y, en cada cruce, le pide el
  precio a la estrategia. Qué órdenes se cruzan y cuántos kWh no depende de
  la estrategia; solo el precio.
- **Cambio en caliente:** `motor.estrategia = PrecioPuntoMedio()`; en la app,
  `PUT /subasta/estrategia` (400 si la regla no existe). Cada transacción
  guarda `estrategia_precio` para saber con qué regla se cerró. En el
  frontend: pestaña «Mercado», selector «Precio de cierre» del libro de
  órdenes.

```python
motor = MotorSubasta(PrecioVendedor())
motor.ejecutar(ordenes)            # cierra a 440
motor.estrategia = PrecioPuntoMedio()
motor.ejecutar(otras_ordenes)      # cierra a 470
```

## Qué le aporta a la plataforma

- **Abierto/cerrado:** una regla nueva (por ejemplo, precio regulado) es una
  clase más; la subasta no cambia.
- **Responsabilidad única:** emparejar órdenes y fijar el precio quedan en
  clases distintas, y cada regla se prueba por separado.
- **Configurable en ejecución:** la comunidad cambia la regla sin reiniciar.
- **Desventaja:** el cliente tiene que conocer las estrategias que existen
  para elegir una; aquí se resuelve con la lista de `GET /subasta/estrategia`.

## Diagrama

```
   MotorSubasta (Context)                    «interface» EstrategiaPrecio
   - estrategia ───────────────────────────▶ + precio_cierre(compra, venta)
   + ejecutar(ordenes)                                  ▲
       por cada cruce:                 ┌────────────────┼──────────────────┐
       precio = estrategia             │                │                  │
           .precio_cierre(c, v)  PrecioVendedor  PrecioComprador  PrecioPuntoMedio
                                 venta.precio    compra.precio    (c + v) / 2
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 15/test_strategy.py" -v   # 23 casos
python "Documentacion/Semana 15/strategy.py"                     # demo por consola
```
