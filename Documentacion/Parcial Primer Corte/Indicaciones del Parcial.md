# Indicaciones del Parcial — Primer Corte

Texto tal como lo entregó el tutor, más un mapa de dónde queda resuelto cada
punto dentro de este repositorio (para revisar antes de entregar).

## Indicación original

> Este parcial es la revisión detallada en **GitHub** de la aplicación de los
> cinco patrones de diseño creacionales: Singleton, Factory Method, Abstract
> Factory, Builder y Prototype en el proyecto asignado a cada grupo de nuestro
> curso. Se debe presentar:
>
> 1. **Informe Técnico** (lo mínimo a presentar): Portada (incluir los nombres
>    de los integrantes del grupo); Contextualización del proyecto a
>    desarrollar; Objetivo General; Objetivos Específicos; y para cada patrón:
>    Explicación del uso del patrón en el proyecto; UML del patrón (Diseño
>    específico); código de la utilización del patrón y pruebas de la
>    utilización del mismo. **(50%)**
>
> 2. **Código** del proyecto total integrado y las instrucciones necesarias
>    para su ejecución **(50%)**. Validación de las pruebas dispuestas en el
>    informe.

## Dónde queda resuelto cada punto en este repositorio

| Requisito | Dónde está |
|---|---|
| Portada con integrantes | [`Documentacion/plataforma-Comercio-Energia.docx`](../plataforma-Comercio-Energia.docx) (primera página) |
| Contextualización del proyecto | Mismo documento, sección "Contextualización del Proyecto"; también [`Documentacion/Contextualizacion.md`](../Contextualizacion.md) |
| Objetivo General y Objetivos Específicos | Mismo documento, subsecciones dentro de "Contextualización del Proyecto" |
| Explicación + UML + código + pruebas, **por cada uno de los 5 patrones** | Mismo documento: una sección por patrón (Singleton, Factory Method, Abstract Factory, Builder, Prototype), cada una con sus figuras numeradas (24 figuras en total, código real y diagramas UML incluidos) |
| Código de cada patrón (versión educativa, uno por semana) | [`Documentacion/Semana 2`](../Semana%202) a [`Semana 6`](../Semana%206) |
| Código del proyecto **total integrado** (los 5 patrones conectados entre sí, no solo demos aisladas) | [`plataforma-energia-app/backend/`](../../plataforma-energia-app/backend) — `plataforma.py` (Singleton) usa `factory_method.py` (Factory Method), `notificaciones.py` (Abstract Factory), `reportes.py` (Builder) y tiene `clonar_dispositivo()` (Prototype) |
| Instrucciones de ejecución | [`Como Ejecutar el Proyecto (Guia Paso a Paso).md`](Como%20Ejecutar%20el%20Proyecto%20%28Guia%20Paso%20a%20Paso%29.md), en esta misma carpeta, y el [`README.md`](../../README.md) de la raíz |
| Validación de las pruebas dispuestas en el informe | 115 pruebas automatizadas con `pytest` (24 por patrón, más 19 de Singleton) — ver el paso "Ejecutar las pruebas" en la guía de ejecución |

## Checklist rápido antes de entregar

- [ ] El `.docx` tiene los nombres de **todos** los integrantes del grupo en la portada.
- [ ] `python -m pytest` corre sin errores desde la raíz del repositorio (115 passed).
- [ ] El backend levanta con `uvicorn main:app --reload --port 8000` sin errores.
- [ ] El frontend (`plataforma-energia-app/frontend/index.html`) conecta con el backend (punto verde).
- [ ] El repositorio está actualizado en GitHub (`git push` hecho).
