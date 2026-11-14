# Patrón Iterator — Plataforma de Comercio de Energía

Implementación del patrón **Iterator** sobre el **libro de órdenes** del
mercado: el libro entrega iteradores intercambiables (por llegada, por
prioridad precio-tiempo, filtrados) sin exponer las listas donde guarda las
órdenes.

- Código del patrón (con demo y docstring explicativo): [`iterator.py`](iterator.py)
- Pruebas del patrón: [`test_iterator.py`](test_iterator.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--iterator)
- Uso real en la aplicación: [`plataforma-energia-app/backend/recorrido_ordenes.py`](../../plataforma-energia-app/backend/recorrido_ordenes.py) — usado por `libro_ordenes`, `listar_ordenes` y `ejecutar_subasta` en [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py), expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET /ordenes?recorrido=llegada|prioridad&usuario=...`)

## Por qué este patrón aquí

Antes de esta semana la subasta hacía `self.ordenes_venta.sort(...)` y
`self.ordenes_compra.sort(...)` **en sitio**: reordenaba las mismas listas
que leían la API y el frontend, y el criterio de prioridad (precio, y a
igual precio, la que llegó antes) quedaba implícito en dos `lambda`. Cada
cliente que quisiera otro recorrido (solo mis órdenes, por llegada) tenía
que conocer esas listas y volver a ordenarlas o filtrarlas por su cuenta.

## Cómo funciona

- **Iterator `IteradorOrdenes`:** interfaz común con `tiene_siguiente()`,
  `siguiente()` y `reiniciar()`, más `__iter__`/`__next__` para que
  cualquier iterador se use en un `for`.
- **ConcreteIterators:**

| Iterador | Recorrido | Detalle |
|---|---|---|
| `IteradorLlegada` | orden de publicación | índice sobre una copia de la lista |
| `IteradorPrioridad` | precio-tiempo | montículo (`heapq`): ventas baratas primero, compras caras primero; empate por llegada. Cada `siguiente()` es O(log n) y no ordena lo que no se consume |
| `IteradorFiltrado` | el de otro iterador, filtrado | envuelve **cualquier** iterador con un predicado (por usuario, solo negociables) |

- **Aggregate `LibroOrdenes`:** `crear_iterador(recorrido, tipo)` elige el
  iterador concreto; `ordenes_de(usuario)` y `negociables(tipo)` combinan un
  recorrido con un filtro. La colección también es iterable directamente.
- **Instantánea:** cada iterador copia la colección al crearse; publicar
  una orden mientras alguien recorre el libro no altera ese recorrido.
- **Uso real:** la subasta recorre `libro.negociables(COMPRA)` y, por cada
  compra, `libro.negociables(VENTA)`; como las ventas salen de la más barata
  a la más cara, se corta (`break`) en cuanto el precio ya no cruza. La API
  acepta `GET /ordenes?recorrido=prioridad&usuario=ana`, y el frontend tiene
  un selector «Recorrido» y la casilla «Solo mis órdenes» en el libro.

```python
libro = LibroOrdenes()
libro.agregar(Orden(1, "ana", "venta", 5, 480))
libro.agregar(Orden(2, "marta", "venta", 2, 450))
[o.id for o in libro.crear_iterador("prioridad", "venta")]  # [2, 1]
[o.id for o in libro.ordenes_de("ana")]                     # [1]
```

## Qué le aporta a la plataforma

- **Encapsulamiento:** ningún cliente toca las listas internas; la subasta
  ya no reordena lo que ven los demás.
- **Recorridos intercambiables:** agregar «por volumen» o «solo de mi
  comunidad» es un iterador nuevo; la subasta y la API no cambian.
- **Eficiencia:** la prioridad con montículo solo extrae lo que la subasta
  consume y permite detenerse apenas los precios no cruzan.
- **Composición:** `IteradorFiltrado` funciona sobre cualquier recorrido.
- **Desventaja:** para listas pequeñas, un `sorted()` directo es más
  corto; el patrón se justifica porque el libro crece y lo recorren varios
  clientes con criterios distintos.

## Diagrama

```
   «abstract» ColeccionOrdenes            «abstract» IteradorOrdenes
   + crear_iterador(recorrido, tipo) ───▶ + tiene_siguiente()
              ▲                            + siguiente()
              │                            + reiniciar()
        LibroOrdenes                       + __iter__ / __next__
        - _ventas, _compras                         ▲
        + agregar(orden)          ┌─────────────────┼──────────────────┐
        + ordenes_de(usuario)  IteradorLlegada  IteradorPrioridad  IteradorFiltrado
        + negociables(tipo)    - _posicion      - _monticulo       - _interno ◆──▶ IteradorOrdenes
                                                                     - _criterio
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 13/test_iterator.py" -v   # 26 casos
python "Documentacion/Semana 13/iterator.py"                     # demo por consola
```
