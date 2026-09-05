# plataforma-comercio-energia

La Plataforma de Comercio de Energía es un sistema digital diseñado para facilitar la compra y venta de excedentes energéticos entre usuarios. El proyecto integra un mecanismo de subastas en tiempo real, dispositivos IoT domésticos y modelos de predicción de producción y consumo energético. Su propósito es mejorar el aprovechamiento de la energía renovable, promover la participación de los usuarios en el mercado energético y proporcionar herramientas inteligentes para el monitoreo y la toma de decisiones.

La plataforma contempla funcionalidades como el registro de usuarios, publicación de ofertas, participación en subastas, monitoreo del consumo y la producción, integración con dispositivos IoT y análisis predictivo. El sistema está planteado con una arquitectura modular y escalable, que puede ampliarse posteriormente con pagos electrónicos, aplicaciones móviles, integración con empresas distribuidoras y tecnologías como blockchain..


## Patrones de diseño (`src/`)

Todo el código de los patrones de diseño aplicados está bajo `src/`, con una
carpeta por patrón que contiene su implementación y sus pruebas:

```
src/
├── README.md                       # documento de pruebas (casos por patrón)
├── singleton/
│   ├── plataforma_energia.py       # implementación del patrón Singleton
│   ├── test_singleton.py           # pruebas del patrón
│   └── conftest.py
└── factory_method/
    ├── factory_method.py           # implementación del patrón Factory Method
    ├── test_factory_method.py      # pruebas del patrón
    └── conftest.py
```

```bash
pip install -r requirements-dev.txt
python -m pytest              # ejecuta todas las pruebas de los patrones
python validar_pruebas.py     # resumen por patrón (o validar_pruebas.bat en Windows)
```

Ver [`src/README.md`](src/README.md) para el detalle de cada caso de prueba.

## Estructura de la aplicación

```
plataforma-energia-app/
├── backend/
│   ├── plataforma.py     # Lógica de dominio (Singleton PlataformaEnergia)
│   ├── main.py            # API FastAPI que expone el Singleton
│   └── requirements.txt
└── frontend/
    └── index.html         # Dashboard en Vue 3 (sin build, vía CDN)
```

## 1. Levantar el backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Verifica que quedó activo entrando a: http://localhost:8000
(deberías ver `{"mensaje": "API de la Plataforma de Comercio de Energía activa"}`)

Documentación interactiva automática (Swagger): http://localhost:8000/docs

## 2. Abrir el frontend (Vue)

No necesita build ni `npm install`: es un solo archivo HTML que carga Vue 3
desde un CDN. Simplemente:

- Haz doble clic en `frontend/index.html`, o
- Sírvelo con un servidor simple: `python -m http.server 5500` dentro de `frontend/`

Al abrirlo, confirma que el campo de la API (arriba a la derecha) diga
`http://localhost:8000` y que el punto de estado esté en verde.

## 3. Flujo de prueba sugerido

1. **Usuarios** → registra 2 usuarios (ej. `u1` Ana, `u2` Luis)
2. **Mercado** → Ana publica una venta (10 kWh a $0.15), Luis publica una compra (6 kWh a $0.18)
3. Haz clic en **"Ejecutar subasta"** → se genera una transacción
4. **IoT & Predicción** → conecta un panel solar a Ana, simula lecturas y pide la predicción
5. **Historial** → revisa las transacciones cerradas

## Por qué el Singleton sigue siendo clave aquí

El frontend puede hacer cientos de peticiones concurrentes (varios usuarios
publicando órdenes, IoT enviando lecturas al mismo tiempo). Como
`PlataformaEnergia()` en `main.py` siempre devuelve la **misma instancia**
(gracias a `SingletonMeta` con `Lock`), todas esas peticiones leen y escriben
sobre **un solo estado consistente** — el mismo libro de órdenes, el mismo
historial, las mismas lecturas — sin importar cuántas veces FastAPI reconstruya
el objeto en cada request.
