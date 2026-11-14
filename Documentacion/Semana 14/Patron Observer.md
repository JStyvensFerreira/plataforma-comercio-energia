# Patrón Observer — Plataforma de Comercio de Energía

Implementación del patrón **Observer** sobre los **eventos del mercado de
energía**: el mercado avisa a quien esté suscrito cada vez que se publica,
ejecuta o cancela una orden, sin conocer las clases concretas de quienes
escuchan. Caso de uso visible: la **alerta de precio** de un comprador.

- Código del patrón (con demo y docstring explicativo): [`observer.py`](observer.py)
- Pruebas del patrón: [`test_observer.py`](test_observer.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--observer)
- Uso real en la aplicación: [`plataforma-energia-app/backend/eventos_mercado.py`](../../plataforma-energia-app/backend/eventos_mercado.py) — usado por [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`publicar_venta`, `publicar_compra`, `ejecutar_subasta`, `cancelar_orden`, `suscribir_alerta_precio`) y expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET/POST/DELETE /mercado/alertas`, `GET /mercado/estadisticas`)

## Por qué este patrón aquí

Cuando aparece una oferta de venta barata, un comprador quiere enterarse sin
estar refrescando el libro de órdenes; cuando se cierra una transacción, las
estadísticas del mercado deben actualizarse. Si `publicar_venta` o
`ejecutar_subasta` llamaran a cada interesado a mano, cada interesado nuevo
obligaría a modificar esos métodos y la lógica del mercado quedaría acoplada
a quién la escucha.

## Cómo funciona

- **Subject `MercadoEnergia`** (en la app, `MercadoEventos`): guarda la
  lista de observadores, permite `suscribir` / `desuscribir` en tiempo de
  ejecución y en `notificar` le pasa a cada uno un `EventoMercado` (tipo +
  datos). Si un observador lanza una excepción, se registra en `errores` y
  se sigue avisando al resto.
- **Observer `ObservadorMercado`:** interfaz con un solo método,
  `actualizar(evento)`.
- **ConcreteObservers:**
  - `AlertaPrecio(usuario_id, precio_max)`: reacciona solo a ventas de
    **otro** usuario con precio ≤ `precio_max`. En la app entrega el aviso
    en la bandeja del usuario, por su canal (Abstract Factory, Semana 4).
  - `EstadisticasMercado`: acumula órdenes publicadas/canceladas,
    transacciones, volumen y precio promedio ponderado por volumen.
  - `RegistroAuditoria` (solo en el módulo didáctico): guarda todos los
    eventos.
- **Uso real:** el Singleton crea el `MercadoEventos` y suscribe
  `EstadisticasMercado` desde el arranque. Cada usuario suscribe su propia
  `AlertaPrecio` con `POST /mercado/alertas` (una por usuario; suscribir
  otra reemplaza la anterior) y la retira con `DELETE /mercado/alertas`.

```python
mercado = MercadoEnergia()
alerta = AlertaPrecio("luis", precio_max=500)
mercado.suscribir(alerta)
mercado.publicar_venta("ana", 5, 450)   # alerta.avisos → 1 aviso
mercado.publicar_venta("ana", 5, 650)   # sin aviso: supera el máximo
mercado.desuscribir(alerta)
```

## Qué le aporta a la plataforma

- **Bajo acoplamiento:** el mercado solo conoce la interfaz
  `ObservadorMercado`; agregar un interesado nuevo (por ejemplo, un
  observador que reentrene la predicción con cada transacción) no toca
  `ejecutar_subasta`.
- **Suscripción dinámica:** cada usuario activa o desactiva su alerta en
  tiempo de ejecución, sin reiniciar nada.
- **Robustez:** un observador defectuoso no puede tumbar la subasta.
- **Desventaja a vigilar:** el orden de notificación no es parte del
  contrato y, con muchos observadores, el costo de cada evento crece; si un
  observador fuera lento convendría notificar de forma asíncrona (cola).

## Diagrama

```
   MercadoEnergia (Subject)                 «interface» ObservadorMercado
   - _observadores: list   ───────────*──▶  + actualizar(evento)
   + suscribir(obs)                                ▲
   + desuscribir(obs)              ┌───────────────┼──────────────────┐
   + notificar(evento)             │               │                  │
   + publicar_venta(...)     AlertaPrecio   EstadisticasMercado  RegistroAuditoria
   + registrar_transaccion   - usuario_id    - volumen_kwh        - eventos
                             - precio_max    + precio_promedio
          │
          └─ crea ─▶ EventoMercado(tipo, datos)   (inmutable)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 14/test_observer.py" -v   # 18 casos
python "Documentacion/Semana 14/observer.py"                     # demo por consola
```
