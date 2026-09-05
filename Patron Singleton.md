# Patrón Singleton — Plataforma de Comercio de Energía

Implementación del patrón **Singleton** sobre la clase `PlataformaEnergia`, el
"libro mayor" central del sistema.

- Código del patrón (con demo y docstring explicativo): [`src/singleton/plataforma_energia.py`](src/singleton/plataforma_energia.py)
- Pruebas del patrón: [`src/singleton/test_singleton.py`](src/singleton/test_singleton.py)
- Uso real en la aplicación: [`plataforma-energia-app/backend/plataforma.py`](plataforma-energia-app/backend/plataforma.py) — consumido por [`main.py`](plataforma-energia-app/backend/main.py)

<img width="1907" height="1190" alt="Validación del Singleton en la plataforma" src="https://github.com/user-attachments/assets/2665051e-c8ad-444f-9d79-722e7a910088" />

## Cómo funciona

- **Metaclase `SingletonMeta`:** intercepta cada `PlataformaEnergia(...)` con
  *double-checked locking* — si ya existe una instancia guardada, la devuelve;
  si no, la crea una sola vez bajo un `Lock` (evita que dos hilos concurrentes
  creen dos instancias).
- **La clase que lo adopta:** `class PlataformaEnergia(metaclass=SingletonMeta)`.
- **Dónde se consume:** en `main.py` (`plataforma = PlataformaEnergia()`) y todos
  los endpoints (usuarios, órdenes, subasta, IoT, auth) leen/escriben sobre ese
  mismo objeto. El endpoint `/estado` expone `id(plataforma)` justamente para
  poder comprobarlo.

## Qué le aporta a la plataforma

- **Estado único y consistente sin base de datos:** usuarios, contraseñas, libro
  de órdenes, historial de transacciones y lecturas IoT viven en un solo objeto
  compartido por todas las peticiones HTTP.
- **Seguridad ante concurrencia:** uvicorn atiende múltiples requests simultáneos
  (varios usuarios operando, IoT enviando lecturas a la vez); el `Lock` evita
  condiciones de carrera al crear la instancia.
- **Base para el login:** el JWT verifica identidad contra ese mismo `usuarios`
  del Singleton — sin él, cada request podría terminar autenticando contra una
  copia distinta del sistema.
- **Límite conocido:** el estado se pierde si el proceso se reinicia y no escala a
  múltiples workers/procesos (cada uno tendría su propio Singleton) — aceptable
  para el prototipo, pero el primer punto a resolver si migran a una base de
  datos real.

## Validación del patrón

Adjuntamos el link del video de la validación del patrón en la plataforma:

https://unidadestecno-my.sharepoint.com/:f:/g/personal/jsferreira_uts_edu_co/IgCG4eGFTkwyQLdp9vVTYeTBARpYfr_fUcNV3tDZxlGNvM4?e=0Bk46E
