# Patrón State — Plataforma de Comercio de Energía

Implementación del patrón **State** sobre el **ciclo de vida de una orden**
de compra o venta: la orden delega `ejecutar` y `cancelar` en su estado
actual, y cada estado decide qué está permitido y a cuál se pasa.

- Código del patrón (con demo y docstring explicativo): [`state.py`](state.py)
- Pruebas del patrón: [`test_state.py`](test_state.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--state)
- Uso real en la aplicación: [`plataforma-energia-app/backend/estados_orden.py`](../../plataforma-energia-app/backend/estados_orden.py) — la clase `Orden` de [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) es el Context (`ejecutar_subasta`, `cancelar_orden`), expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`POST /ordenes/{id}/cancelar`, `GET /ordenes/historial`)

## Por qué este patrón aquí

Antes de esta semana la subasta restaba la cantidad a mano
(`orden.cantidad_kwh -= cantidad`) y descartaba las órdenes en cero: no
existía la idea de orden *parcialmente ejecutada*, no se podía cancelar una
orden y no quedaba rastro de las órdenes cerradas. Agregar esas reglas con
if/elif sobre un campo de texto `estado` las habría repartido por la
subasta, la cancelación y la API.

## Cómo funciona

- **Context `Orden`:** guarda la cantidad pendiente, la cantidad inicial,
  el estado actual y el `historial_estados`. `ejecutar(cantidad)`,
  `cancelar()` y `puede_negociar()` se delegan en el estado; la orden nunca
  decide sus transiciones (solo expone `cambiar_estado`, que invocan los
  estados).
- **State `EstadoOrden`:** interfaz con `ejecutar`, `cancelar` y
  `puede_negociar`.
- **ConcreteStates:**

| Estado | `ejecutar(c)` | `cancelar()` | ¿Negociable? |
|---|---|---|---|
| `Abierta` | descuenta `c`; → `Parcial` o `Completada` | → `Cancelada` | sí |
| `ParcialmenteEjecutada` | igual que Abierta | → `Cancelada` | sí |
| `Completada` | `TransicionInvalida` | `TransicionInvalida` | no |
| `Cancelada` | `TransicionInvalida` | `TransicionInvalida` | no |

- Los estados no guardan datos propios, así que hay **una sola instancia
  de cada uno** (`ABIERTA`, `PARCIAL`, `COMPLETADA`, `CANCELADA`) compartida
  por todas las órdenes.
- **Uso real:** `ejecutar_subasta` llama `compra.ejecutar(cantidad)` y
  `venta.ejecutar(cantidad)`; al final las órdenes que ya no negocian pasan
  a `ordenes_cerradas`. `POST /ordenes/{id}/cancelar` responde 403 si la
  orden es de otro usuario y **409** si su estado no permite cancelarla.
  En el frontend, el libro de órdenes muestra el estado y la tabla «Órdenes
  cerradas» muestra cada transición (`abierta → parcial → cancelada`).

```python
orden = Orden(1, "ana", "venta", 10, 450)
orden.ejecutar(4)    # parcial, quedan 6
orden.ejecutar(6)    # completada
orden.cancelar()     # TransicionInvalida
```

## Qué le aporta a la plataforma

- **Reglas en un solo lugar por estado:** qué se puede hacer con una orden
  completada está en `Completada`, no esparcido en condicionales.
- **Extensible:** un estado nuevo (por ejemplo `Suspendida` mientras se
  verifica el pago) es una clase nueva; la subasta no cambia.
- **Trazabilidad:** el historial de estados de cada orden queda disponible
  para el usuario y para auditoría.
- **Integra con Observer:** la cancelación emite el evento
  `orden_cancelada` que cuentan las estadísticas del mercado.
- **Desventaja:** más clases para un ciclo de vida que, hoy, tiene solo
  cuatro estados; se justifica porque las reglas de negocio del mercado
  tienden a crecer (vencimiento, suspensión, disputas).

## Diagrama

```
   Orden (Context)                          «abstract» EstadoOrden (State)
   - cantidad_kwh, cantidad_inicial         + ejecutar(orden, c)
   - _estado ──────────────────────────▶    + cancelar(orden)
   - historial_estados                      + puede_negociar()
   + ejecutar(c)   → _estado.ejecutar(self, c)       ▲
   + cancelar()    → _estado.cancelar(self)          │
   + cambiar_estado(nuevo)            ┌──────────────┴──────────────┐
                                _EstadoNegociable               _EstadoFinal
                                  ▲          ▲                  ▲         ▲
                               Abierta   ParcialmenteEjecutada Completada Cancelada

   abierta ──ejecutar parcial──▶ parcial ──ejecutar resto──▶ completada
      └──────────ejecutar todo───────────────────────────────▶ completada
   abierta / parcial ──cancelar──▶ cancelada
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 14/test_state.py" -v   # 23 casos
python "Documentacion/Semana 14/state.py"                     # demo por consola
```
