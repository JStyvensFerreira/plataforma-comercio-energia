# Patrón Facade — Plataforma de Comercio de Energía

Implementación del patrón **Facade** (Fachada) sobre el **alta rápida de
dispositivos IoT**: un solo punto de entrada que coordina Factory Method,
la simulación de lecturas y Builder + Abstract Factory, en vez de que el
cliente tenga que llamar a los tres subsistemas por separado y en orden.

- Código del patrón (con demo y docstring explicativo): [`facade.py`](facade.py)
- Pruebas del patrón: [`test_facade.py`](test_facade.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--facade)
- Uso real en la aplicación: [`plataforma-energia-app/backend/onboarding.py`](../../plataforma-energia-app/backend/onboarding.py) — consume [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`conectar_dispositivo`, `simular_lecturas`, `generar_reporte`) y se expone en [`main.py`](../../plataforma-energia-app/backend/main.py) (`POST /onboarding/dispositivo`)

## Por qué este patrón aquí

Dar de alta un dispositivo IoT y dejarlo listo para operar **hoy** requiere
tres pasos, en un orden concreto:

1. Conectarlo (Factory Method, Semana 3) — resuelve la fábrica por tipo.
2. Simular algunas lecturas iniciales, para que no aparezca vacío.
3. Generar un reporte resumen y dejarlo en la bandeja del usuario (Builder,
   Semana 5 + Abstract Factory, Semana 4).

Si cada cliente (el frontend, un futuro script de alta masiva, un bot) tuviera
que conocer esos tres subsistemas y llamarlos en el orden correcto, cualquier
cambio en ese orden —o un paso nuevo— obligaría a tocar cada punto donde se
da de alta un dispositivo.

## Cómo funciona

- **Subsistemas (ya existentes, sin cambios):** `PlataformaEnergia.conectar_dispositivo`
  (Factory Method), `simular_lecturas`, y `generar_reporte` (Builder +
  Abstract Factory). La fachada no los reemplaza ni oculta su funcionalidad
  individual: siguen pudiéndose llamar por separado, igual que antes de
  existir `OnboardingDispositivo` (así lo hace, por ejemplo, el formulario
  "Conectar dispositivo" de la pestaña IoT).
- **Facade `OnboardingDispositivo`:** conoce el orden correcto y expone un
  único método, `conectar_y_activar(usuario_id, id, tipo, ...)`, que llama a
  los tres subsistemas en secuencia y devuelve un resultado consolidado
  (dispositivo, lecturas, reporte).
- **Uso real:** `main.py` instancia `OnboardingDispositivo(plataforma)` una
  sola vez (igual que la plataforma misma) y lo expone en
  `POST /onboarding/dispositivo`. La tarjeta **"Alta rápida de dispositivo"**
  de la pestaña IoT usa ese único endpoint.

```python
onboarding = OnboardingDispositivo(plataforma)
resultado = onboarding.conectar_y_activar("u1", "panel-02", "panel_solar")
# resultado = {"dispositivo": {...}, "lecturas": [...], "reporte": {...}}
```

## Qué le aporta a la plataforma

- **Menos acoplamiento del cliente con la implementación interna:** el
  frontend (o cualquier otro cliente) no necesita saber que el alta rápida
  implica tres llamadas en un orden concreto.
- **Un solo lugar para cambiar la secuencia:** si mañana el alta rápida
  también debiera enviar un SMS de bienvenida o calibrar umbrales, se cambia
  `OnboardingDispositivo.conectar_y_activar` una vez, no cada punto que da de
  alta un dispositivo.
- **No reduce flexibilidad:** quien necesite control fino (p. ej. el
  formulario "Conectar dispositivo", que no simula lecturas ni envía
  reporte) sigue llamando los subsistemas por separado. La fachada es una
  **alternativa** más simple para el caso común, no la única puerta de
  entrada.
- **Relación con los patrones que coordina:** Facade no decide *qué* clase
  crear (eso es Factory Method) ni *cómo* se arma el reporte (eso es
  Builder) — solo decide el **orden** en que se usan esos subsistemas ya
  existentes.

## Diagrama

```
            Cliente (frontend / main.py)
                       │
                       ▼
            OnboardingDispositivo          (Facade)
            + conectar_y_activar(usuario_id, id, tipo, ...)
                       │
         ┌─────────────┼─────────────────┐
         ▼              ▼                  ▼
  conectar_dispositivo  simular_lecturas   generar_reporte
  (Factory Method)      (PlataformaEnergia) (Builder + Abstract Factory)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 9/test_facade.py" -v   # 12 casos
python "Documentacion/Semana 9/facade.py"                     # demo por consola
```
