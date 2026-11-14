# Patrón Visitor — Plataforma de Comercio de Energía

Implementación del patrón **Visitor** sobre el **árbol energético de la
comunidad** (Composite, Semana 8): nuevos análisis — huella de carbono,
diagnóstico y exportación a CSV — se agregan como visitantes, sin agregarle
métodos a `DispositivoHoja` ni a `GrupoEnergetico`.

- Código del patrón (con demo y docstring explicativo): [`visitor.py`](visitor.py)
- Pruebas del patrón: [`test_visitor.py`](test_visitor.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--visitor)
- Uso real en la aplicación: [`plataforma-energia-app/backend/analisis_comunidad.py`](../../plataforma-energia-app/backend/analisis_comunidad.py) — los nodos de [`jerarquia.py`](../../plataforma-energia-app/backend/jerarquia.py) implementan `aceptar`, [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) lo usa en `analizar_comunidad` y [`main.py`](../../plataforma-energia-app/backend/main.py) lo expone en `GET /comunidad/analisis/{analisis}`

## Por qué este patrón aquí

El Composite ya calcula producción, consumo y balance por nivel. Pero
sobre ese mismo árbol aparecen preguntas nuevas: ¿cuánto CO₂ evitó cada
hogar?, ¿qué hogares están en déficit o tienen dispositivos que nunca
reportaron?, ¿cómo exporto el árbol a una hoja de cálculo? Agregar un
método por pregunta a las clases del árbol las haría crecer sin fin y
mezclaría con el modelo responsabilidades de reporte.

## Cómo funciona

- **Element `NodoEnergetico`:** declara `aceptar(visitante)`.
- **ConcreteElements:** `DispositivoHoja.aceptar(v)` llama
  `v.visitar_dispositivo(self)` y `GrupoEnergetico.aceptar(v)` llama
  `v.visitar_grupo(self)`: **doble despacho**, el método que se ejecuta
  depende a la vez del tipo de nodo y del tipo de visitante.
- **Visitor `VisitanteEnergetico`:** `visitar_dispositivo`,
  `visitar_grupo` y `resultado`. Cada visitante decide cómo recorrer a los
  hijos de un grupo (necesario, por ejemplo, para llevar la ruta en el CSV).
- **ConcreteVisitors:**
  - `VisitanteHuellaCarbono`: kg de CO₂ evitados = producción × factor de
    emisión de la red (0,126 kg/kWh, valor ilustrativo), total y por hogar.
  - `VisitanteDiagnostico`: hogares con balance negativo y dispositivos
    sin lecturas.
  - `VisitanteExportarCSV`: una fila por nodo con su ruta en el árbol.
- **Uso real:** `PlataformaEnergia.analizar_comunidad(nombre)` arma el
  árbol (Composite), crea el visitante por nombre y llama
  `arbol.aceptar(visitante)`. En el frontend, pestaña «Comunidad», tarjeta
  «Análisis de la comunidad».

```python
arbol = plataforma.arbol_energetico()
visitante = VisitanteHuellaCarbono()
arbol.aceptar(visitante)
visitante.resultado()   # {'total_kg_co2': 0.713, 'por_hogar': {...}, ...}
```

## Qué le aporta a la plataforma

- **Abierto a nuevas operaciones:** cada análisis nuevo es una clase nueva;
  `jerarquia.py` solo cambió una vez (para agregar `aceptar`).
- **Cohesión:** todo lo que calcula la huella de carbono está en un solo
  visitante, no repartido entre hoja y grupo.
- **Complementa al Composite:** el Composite define la estructura y las
  operaciones esenciales; el Visitor las operaciones que crecen.
- **Desventaja:** agregar un tipo de nodo nuevo (por ejemplo
  `EdificioEnergetico` como clase propia) obliga a añadir un método
  `visitar_...` a **todos** los visitantes. Aquí es aceptable porque los
  niveles del árbol se modelan con una sola clase `GrupoEnergetico`
  etiquetada, así que los tipos de nodo son estables.

## Diagrama

```
  «abstract» NodoEnergetico (Element)        «abstract» VisitanteEnergetico (Visitor)
  + aceptar(v)                               + visitar_dispositivo(d)
        ▲                                    + visitar_grupo(g)
   ┌────┴─────────────┐                      + resultado()
DispositivoHoja   GrupoEnergetico                       ▲
aceptar(v):       aceptar(v):               ┌───────────┼─────────────────┐
 v.visitar_        v.visitar_grupo(self)  HuellaCarbono Diagnostico  ExportarCSV
  dispositivo(self)  (el visitante recorre
                      los hijos)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 14/test_visitor.py" -v   # 15 casos
python "Documentacion/Semana 14/visitor.py"                     # demo por consola
```
