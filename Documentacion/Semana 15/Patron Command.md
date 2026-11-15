# Patrón Command — Plataforma de Comercio de Energía

Implementación del patrón **Command** sobre las **operaciones del
mercado**: publicar una venta, publicar una compra o cancelar una orden se
convierten en objetos que se programan en una cola, se ejecutan en lote,
quedan registrados y se pueden deshacer.

- Código del patrón (con demo y docstring explicativo): [`command.py`](command.py)
- Pruebas del patrón: [`test_command.py`](test_command.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--command)
- Uso real en la aplicación: [`plataforma-energia-app/backend/operaciones_mercado.py`](../../plataforma-energia-app/backend/operaciones_mercado.py) — usado por `programar_operacion`, `ejecutar_operaciones`, `deshacer_operacion` y `descartar_operaciones` en [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py), expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET`/`POST /operaciones`, `POST /operaciones/ejecutar`, `POST /operaciones/deshacer`, `DELETE /operaciones/pendientes`)

## Por qué este patrón aquí

Un prosumidor quiere preparar varias operaciones (vender el excedente de la
tarde, comprar para la noche, retirar una orden vieja), revisarlas y
ejecutarlas juntas; y si se equivocó, deshacer la última. Si la interfaz
llamara directamente a los métodos del mercado, una operación no se
podría guardar para después ni registrar, y cada botón tendría que saber
cómo revertir cada acción.

## Cómo funciona

- **Receiver `Mercado`** (en la app, `PlataformaEnergia`): sabe publicar y
  cancelar órdenes. No sabe nada de colas ni de deshacer.
- **Command `ComandoMercado`:** `ejecutar()`, `deshacer()`, `descripcion()`.
- **Concrete Commands:**

| Comando | `ejecutar` | `deshacer` |
|---|---|---|
| `PublicarVentaComando` / `PublicarCompraComando` | publica y guarda el id de la orden | cancela esa orden |
| `CancelarOrdenComando` | cancela la orden | la vuelve a poner en el mercado |

- **Invoker `GestorOperaciones`:** `programar` (cola), `ejecutar_pendientes`
  (en orden; un comando que falla se informa y no detiene a los demás ni
  entra al historial), `deshacer` (el último ejecutado; si deshacer falla,
  el comando sigue en el historial), `descartar_pendientes` y `registro`.
- **Uso real:** cada usuario tiene su gestor. Deshacer respeta el ciclo de
  vida de la orden (State): deshacer una publicación ya completada falla
  (**409**), y como una orden cancelada no puede reabrirse, deshacer una
  cancelación vuelve a publicar lo que le quedaba pendiente como orden
  nueva. Una operación mal armada responde **400**. En el frontend: pestaña
  «Operaciones», tarjeta «Operaciones programadas».

```python
gestor.programar(PublicarVentaComando(mercado, "ana", 5, 440))
gestor.programar(CancelarOrdenComando(mercado, "ana", orden_vieja.id))
gestor.ejecutar_pendientes()   # las dos, en orden
gestor.deshacer()              # la orden vieja vuelve al mercado
```

## Qué le aporta a la plataforma

- **Desacoplamiento:** quien pide la operación (la interfaz, el gestor) no
  conoce cómo se hace; solo llama `ejecutar()`.
- **Operaciones diferidas y en lote:** se arman ahora y se ejecutan después.
- **Deshacer:** cada comando sabe revertirse; el gestor solo lleva la pila.
- **Auditoría:** el registro guarda qué se programó, ejecutó, falló o deshizo.
- **Extensible:** una operación nueva es otra clase de comando; el gestor no cambia.
- **Desventaja:** una clase por operación; para acciones triviales puede
  ser más código del necesario.

## Diagrama

```
   Client (API / interfaz)
      │ crea con su receptor
      ▼
   «interface» ComandoMercado ◀─────────── GestorOperaciones (Invoker)
   + ejecutar() + deshacer()               - pendientes: [Comando]
   + descripcion()                         - ejecutados: [Comando]
          ▲                                + programar / ejecutar_pendientes
   ┌──────┼──────────────────┐             + deshacer / registro
   │      │                  │
 PublicarVenta  PublicarCompra  CancelarOrden ──────▶ Mercado (Receiver)
 Comando        Comando         Comando               + publicar / cancelar / reabrir
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 15/test_command.py" -v   # 17 casos
python "Documentacion/Semana 15/command.py"                     # demo por consola
```
