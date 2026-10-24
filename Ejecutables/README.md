# Ejecutables de Voltia

Versión empaquetada de la aplicación (backend FastAPI + frontend Vue) en un solo
archivo. **No requiere instalar Python, dependencias ni Node**: incluye el
intérprete, todas las librerías y el frontend con Vue embebido (funciona sin
internet; solo las fuentes tipográficas se cargan de Google Fonts si hay conexión).

## Cómo usarlo (Windows)

1. Descarga `Voltia-windows.exe`.
2. Haz doble clic. Si Windows SmartScreen muestra "Windows protegió su PC",
   pulsa **Más información → Ejecutar de todas formas** (el ejecutable no está
   firmado digitalmente).
3. Se abre una consola y, a los segundos, el navegador en
   `http://127.0.0.1:8000/app/`. Si el puerto 8000 está ocupado se usa otro
   libre; la consola muestra la URL exacta.
4. Para cerrar la aplicación, cierra la ventana de la consola.

La documentación interactiva de la API (Swagger) queda en `/docs` del mismo puerto.

> El estado (usuarios, órdenes, transacciones) vive en memoria en el Singleton
> `PlataformaEnergia`, así que se reinicia cada vez que se abre el ejecutable.

## Regenerar el ejecutable

Desde la raíz del repositorio:

```bash
pip install -r plataforma-energia-app/backend/requirements.txt pyinstaller==6.11.1
python plataforma-energia-app/ejecutable/construir.py
```

PyInstaller solo genera binarios para el sistema donde se ejecuta: para obtener
`Voltia-linux` o `Voltia-macos`, corre el mismo comando en Linux o macOS.
