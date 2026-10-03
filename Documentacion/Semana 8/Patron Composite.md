# Patrón Composite — Plataforma de Comercio de Energía

Implementación del patrón **Composite** (Compuesto) sobre el **árbol energético
de la comunidad**: calcular la producción, el consumo y el balance de
cualquier nivel (dispositivo, hogar, edificio, comunidad) con una sola
operación recursiva.

- Código del patrón (con demo y docstring explicativo): [`composite.py`](composite.py)
- Pruebas del patrón: [`test_composite.py`](test_composite.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--composite)
- Uso real en la aplicación: [`plataforma-energia-app/backend/jerarquia.py`](../../plataforma-energia-app/backend/jerarquia.py) — consumido por [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`arbol_energetico`) y expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`/comunidad/arbol`)

## Por qué este patrón aquí

Es el mismo problema que se vio en clase con el SGA (Facultad → Programa →
Curso → Estudiante → ¿promedio de la facultad?), pero con energía:

```
Microrred La Floresta                (comunidad)
├── Edificio Los Pinos               (edificio)
│   ├── Apto 101 (Ana)               (hogar)
│   │   ├── panel-01                 (panel solar)   ← hoja
│   │   └── bateria-01               (batería)       ← hoja
│   └── Apto 102 (Luis)              (hogar)
│       └── medidor-02               (medidor)       ← hoja
└── Casa 7 (Marta)                   (hogar)
    └── panel-07                     (panel solar)   ← hoja
```

¿Cómo calcular el balance energético de toda la comunidad **sin escribir
código distinto en cada nivel**? Sin el patrón habría un método para sumar
los dispositivos de un hogar, otro para sumar los hogares de un edificio,
otro para los edificios de la comunidad... y cualquier nivel nuevo (barrio,
ciudad) obligaría a escribir otro más. Además, la profundidad **no es fija**:
la Casa 7 cuelga directo de la comunidad, mientras que los apartamentos
están un nivel más abajo.

## Cómo funciona

- **Component `NodoEnergetico`:** interfaz común para hojas y grupos:
  `produccion_kwh()`, `consumo_kwh()`, `cantidad_dispositivos()`,
  `to_dict()`. `balance_kwh()` y `promedio_balance_por_dispositivo()` se
  definen **una sola vez** en la interfaz y sirven para todos los niveles.
- **Leaf `DispositivoHoja`:** objeto individual (no tiene hijos). Suma sus
  propias lecturas: las positivas son producción y las negativas consumo.
- **Composite `GrupoEnergetico`:** contiene `hijos: list[NodoEnergetico]` y
  **delega** cada operación en ellos, sumando los resultados. El `nivel`
  (`hogar`, `edificio`, `comunidad`) es solo una etiqueta: no hace falta una
  clase por nivel.
- **Variante transparente (la vista en clase):** `agregar`, `eliminar` y
  `obtener_hijo` están declarados en la interfaz común; una hoja los rechaza
  con `TypeError`.
- **Control de ciclos:** `agregar` rechaza con `ValueError` un nodo que ya
  contenga al grupo (él mismo o un ancestro) y un hijo repetido, para mitigar
  una de las desventajas del patrón.
- **Uso real:** `PlataformaEnergia.arbol_energetico()` arma el árbol
  Comunidad → Hogar (un usuario) → Dispositivo con el estado actual del
  Singleton, y `GET /comunidad/arbol` lo expone; la pestaña **Comunidad** del
  frontend muestra cada nivel con sus totales.

```python
comunidad = GrupoEnergetico("Microrred La Floresta", "comunidad")
hogar = GrupoEnergetico("Apto 101 (Ana)", "hogar")
hogar.agregar(DispositivoHoja("panel-01", "panel_solar", [2.5, 3.0]))
comunidad.agregar(hogar)

comunidad.balance_kwh()            # el cliente no sabe si es hoja o grupo
hogar.obtener_hijo(0).balance_kwh()  # misma llamada sobre una hoja
```

## Qué le aporta a la plataforma

- **Uniformidad:** el cliente (API, frontend, reportes) llama `balance_kwh()`
  igual sobre un panel solar que sobre la comunidad entera.
- **Recursividad natural:** la estructura resuelve la profundidad; no hay
  bucles anidados por nivel ni profundidad fija.
- **Abierto/cerrado:** un nuevo tipo de hoja (p. ej. una estación de carga de
  vehículos) o un nuevo nivel de agrupación (barrio) se agrega sin modificar
  `GrupoEnergetico`. La prueba
  `test_se_puede_agregar_un_tipo_de_hoja_sin_modificar_el_composite` lo
  demuestra con una `EstacionCarga` definida dentro del propio test.
- **Promedio correcto:** `promedio_balance_por_dispositivo()` divide los
  **totales** del subárbol, no promedia los promedios de los hijos (un hogar
  con 1 dispositivo no pesa lo mismo que un edificio con 20), igual que el
  promedio académico de una facultad.

## Ventajas y desventajas (vistas en clase)

| Ventajas | Desventajas | Cómo se maneja aquí |
|---|---|---|
| Uniformidad | Sobregeneralización | Solo hay dos clases concretas; el nivel es una etiqueta |
| Recursividad natural | Dificultad para restringir componentes | La hoja rechaza `agregar` con `TypeError` |
| Extensibilidad | Riesgo de ciclos | `agregar` valida con `contiene()` y lanza `ValueError` |
| Abierto/cerrado | Operaciones no uniformes | Todas las operaciones del árbol son sumas sobre los hijos |

**Cuándo usarlo:** cuando el dominio es naturalmente jerárquico (árbol), el
cliente debe ignorar la diferencia entre hojas y ramas, y las operaciones se
pueden definir recursivamente. **No usarlo** si la jerarquía tiene una
profundidad fija y conocida.

## Diagrama

Diagrama UML de clases: [`UML_Composite.png`](UML_Composite.png) (también en el documento Word).

```
                 «interface» NodoEnergetico                   (Component)
                 + produccion_kwh() / consumo_kwh()
                 + balance_kwh() / cantidad_dispositivos()
                 + agregar(n) / eliminar(n) / obtener_hijo(i)
                              ▲
              ┌───────────────┴───────────────┐
      DispositivoHoja                  GrupoEnergetico               (Composite)
      (Leaf: no tiene hijos)           - hijos: list[NodoEnergetico] ◇──┐
      + produccion_kwh()               + produccion_kwh() → Σ hijos     │ 1..*
      + consumo_kwh()                  + agregar(n) / eliminar(n)       │
                                       + obtener_hijo(i)                ▼
                                                              NodoEnergetico
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 8/test_composite.py" -v   # 21 casos
python "Documentacion/Semana 8/composite.py"                     # demo por consola
```
