# Patrón Flyweight — Plataforma de Comercio de Energía

Implementación del patrón **Flyweight** (Peso Ligero) sobre el **catálogo de
tipos de dispositivo IoT**: una sola ficha técnica compartida por tipo
(panel solar, batería, medidor), en vez de que cada dispositivo guarde su
propia copia de esos datos.

- Código del patrón (con demo y docstring explicativo): [`flyweight.py`](flyweight.py)
- Pruebas del patrón: [`test_flyweight.py`](test_flyweight.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--flyweight)
- Uso real en la aplicación: [`plataforma-energia-app/backend/catalogo_dispositivos.py`](../../plataforma-energia-app/backend/catalogo_dispositivos.py) — consumido por [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`ficha_tecnica`, `catalogo_dispositivos`) y expuesto en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET /iot/catalogo`, `GET /iot/dispositivos/{id}/ficha`)

## Por qué este patrón aquí

Cada dispositivo IoT conectado (Factory Method, Semana 3) ya guarda su `id`,
su dueño y sus propios umbrales calibrados. Pero además de esos umbrales,
describir un dispositivo para la interfaz implica un nombre amigable, una
categoría, una unidad de medida y una descripción — datos que son
**idénticos para todos los dispositivos del mismo tipo**. Si la plataforma
llegara a tener miles de paneles solares conectados, cada uno terminaría
cargando una copia exacta del mismo texto descriptivo.

## Cómo funciona

- **Flyweight `FichaTipoDispositivo`:** clase inmutable (`frozen=True`) con
  el estado intrínseco compartido: `tipo`, `nombre_amigable`, `categoria`,
  `unidad`, `umbral_min`, `umbral_max`, `descripcion`.
- **Flyweight Factory `FabricaFichasDispositivo`:** cachea una ficha por
  tipo y devuelve siempre la **misma instancia** (verificado con `is`, no
  solo con `==`) sin importar cuántos dispositivos o cuántas veces se
  consulte.
- **Estado extrínseco:** el `id`, el `usuario_id` y las lecturas de cada
  dispositivo siguen viviendo en `DispositivoIoT` (Factory Method), sin
  tocarlo; el Flyweight no reemplaza esa clase, solo evita duplicar la
  parte que ya es igual para todos los dispositivos de un tipo.
- **Uso real:** `PlataformaEnergia.ficha_tecnica(tipo)` y
  `catalogo_dispositivos()` reutilizan `factory_method.UMBRALES_IOT` como
  única fuente de verdad para los umbrales, así el catálogo nunca se
  desincroniza de las fábricas concretas. La pestaña **IoT & Predicción**
  muestra el catálogo completo y la ficha de cada dispositivo conectado.

```python
fabrica = FabricaFichasDispositivo()
a = fabrica.obtener_ficha("panel_solar")
b = fabrica.obtener_ficha("panel_solar")
a is b  # True: 50 paneles solares comparten UNA sola ficha
```

## Qué le aporta a la plataforma

- **Menos memoria duplicada:** el catálogo crece con el número de *tipos*
  (3 hoy), no con el número de *dispositivos* conectados.
- **Una sola fuente de verdad por tipo:** si cambia la descripción o la
  categoría de "panel_solar", cambia para todos los dispositivos de ese
  tipo a la vez, porque todos apuntan a la misma ficha.
- **No compite con Factory Method:** Factory Method decide **qué clase**
  de dispositivo crear y construye el objeto completo (con su estado
  extrínseco); Flyweight solo evita duplicar la parte de ese objeto que es
  igual para todos los de su tipo.
- **Prueba de fuego:** `test_muchos_dispositivos_del_mismo_tipo_comparten_una_sola_ficha`
  crea 50 ids distintos del mismo tipo y verifica que la fábrica solo creó
  **una** ficha (`fichas_creadas == 1`).

## Diagrama

```
  FabricaFichasDispositivo        (Flyweight Factory)
  - _cache: dict[tipo, Ficha]
  + obtener_ficha(tipo) -> FichaTipoDispositivo   ───┐
                                                       │ cachea / reutiliza
                                                       ▼
                                   FichaTipoDispositivo        (Flyweight)
                                   + nombre_amigable, categoria,
                                     unidad, umbral_min, umbral_max,
                                     descripcion   (inmutable)
                                                       ▲
                      ┌────────────────────────────────┤ comparten la MISMA instancia
                      │                                │
          DispositivoIoT (panel-01)        DispositivoIoT (panel-02) ...
          id, usuario_id, lecturas          id, usuario_id, lecturas
          (estado extrínseco, único)        (estado extrínseco, único)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 10/test_flyweight.py" -v   # 9 casos
python "Documentacion/Semana 10/flyweight.py"                     # demo por consola
```
