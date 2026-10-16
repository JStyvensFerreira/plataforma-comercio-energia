# Patrón Proxy — Plataforma de Comercio de Energía

Implementación del patrón **Proxy** sobre el **acceso al reporte
energético** del usuario: un `ReporteProxy` que protege, cachea y audita
las solicitudes de reporte sin tocar el `DirectorReportes` (Builder, Semana
5) que arma el reporte paso a paso.

- Código del patrón (con demo y docstring explicativo): [`proxy.py`](proxy.py)
- Pruebas del patrón: [`test_proxy.py`](test_proxy.py)
- Documento de casos de prueba: [`Documentacion/README.md`](../README.md#casos-de-prueba--proxy)
- Uso real en la aplicación: [`plataforma-energia-app/backend/reportes_proxy.py`](../../plataforma-energia-app/backend/reportes_proxy.py) — envuelve [`plataforma.py`](../../plataforma-energia-app/backend/plataforma.py) (`generar_reporte`) y se expone en [`main.py`](../../plataforma-energia-app/backend/main.py) (`GET /reportes/seguro/{usuario_id}`, `GET /reportes/auditoria`)

## Por qué este patrón aquí

`PlataformaEnergia.generar_reporte` (Builder, Semana 5 + Abstract Factory,
Semana 4) recolecta lecturas, calcula balances y arma varias secciones; no
es gratis repetirlo en cada clic. Además, nada en ese método evita que un
cliente de la API pida el reporte de **otro** usuario, ni deja rastro de
quién pidió qué.

## Cómo funciona

- **Subject `GeneradorReportes`:** interfaz común (`generar(solicitante_id,
  usuario_id, formato)`) que implementan tanto el objeto real como el
  proxy, para que el cliente no distinga uno de otro.
- **RealSubject `GeneradorReportesReal`:** envuelve
  `PlataformaEnergia.generar_reporte` sin modificarlo.
- **Proxy `ReporteProxy`:** antes de delegar al objeto real, resuelve tres
  responsabilidades que no son del Builder:
  - **Protection Proxy:** si `solicitante_id != usuario_id`, rechaza con
    `PermissionError` antes de tocar el objeto real.
  - **Caching Proxy:** si ya hay un reporte del mismo usuario y formato
    generado hace menos de `ttl_segundos` (30s en la app), lo reutiliza en
    vez de reconstruirlo.
  - **Logging Proxy:** registra cada intento (`generado`, `cache` o
    `denegado`) en `auditoria`, con quién solicitó qué y cuándo.
- **Uso real:** `main.py` instancia `ReporteProxy(GeneradorReportesReal(plataforma))`
  una sola vez y lo expone en `GET /reportes/seguro/{usuario_id}` (403 si el
  solicitante no es el dueño) y `GET /reportes/auditoria`. El endpoint
  original `POST /reportes/generar` (sin proxy) sigue existiendo sin
  cambios, para quien ya confía en su propio usuario autenticado.

```python
proxy = ReporteProxy(real=GeneradorReportesReal(plataforma))
proxy.generar("ana", "ana", "resumen")     # construye y cachea
proxy.generar("ana", "ana", "resumen")     # desde caché, no reconstruye
proxy.generar("luis", "ana", "resumen")    # PermissionError
```

## Qué le aporta a la plataforma

- **Separación de responsabilidades:** `DirectorReportes` solo sabe
  construir el reporte; decidir quién puede pedirlo, cuándo reutilizar uno
  reciente y qué queda auditado vive en el proxy, no mezclado con el
  Builder.
- **Transparente para el cliente:** el proxy implementa el mismo `Subject`
  que el objeto real — un cliente que programe contra `GeneradorReportes`
  no necesita saber cuál de los dos tiene enfrente.
- **Combina tres variantes de Proxy en un solo caso de uso:** Protection
  (quién puede), Caching (evitar reconstruir) y Logging (quién pidió qué),
  igual que se vio en clase con ejemplos como Spring `@Cacheable` o un
  proxy de auditoría.
- **Diferencia con Facade (Semana 9):** Facade simplifica **llamar a
  varios** subsistemas en el orden correcto; Proxy controla el **acceso a
  uno solo**, sin cambiar su interfaz ni su orden de llamada.

## Diagrama

```
        Cliente (main.py)
              │
              ▼
   «interface» GeneradorReportes        (Subject)
   + generar(solicitante, usuario, formato)
         ▲                  ▲
         │                  │
  ReporteProxy        GeneradorReportesReal        (RealSubject)
  (Proxy)             + generar(...)  → PlataformaEnergia.generar_reporte()
  + generar(...)
    1. valida solicitante == usuario   (Protection)
    2. busca en _cache                 (Caching)
    3. delega en `real` si hace falta
    4. registra en `auditoria`         (Logging)
```

## Validación del patrón

```bash
# desde la raíz del repositorio
python -m pytest "Documentacion/Semana 10/test_proxy.py" -v   # 12 casos
python "Documentacion/Semana 10/proxy.py"                     # demo por consola
```
