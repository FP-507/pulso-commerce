# Notas de desarrollo · Pulso Commerce

Guía para retomar el proyecto: cómo está armado, por qué y cómo cambiarlo.

## Puesta en marcha

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python pipeline/generar_datos.py   # opcional: los CSV ya vienen en datos/crudos (semilla 7)
python pipeline/analisis.py        # datos/pulso.db + docs/data.json + REPORTE.md
python -m http.server -d docs      # dashboard en http://localhost:8000
pytest -q
```

El dashboard es estático (HTML, CSS, JS y Chart.js desde CDN) y se publica con GitHub Pages desde la carpeta `docs/`. **Si cambian los datos, hay que volver a correr `analisis.py` y subir `docs/data.json`.**

## Arquitectura

```
pipeline/generar_datos.py ─► datos/crudos/*.csv ─► pipeline/analisis.py ─┬─► datos/pulso.db (SQLite, no se sube)
                                                     │ ejecuta sql/*.sql  ├─► docs/data.json ─► docs/app.js (dashboard)
                                                     │ + cohortes y RFM   └─► REPORTE.md
```

### Modelo de datos (5 tablas)

| Tabla | Clave | Columnas | Relación |
|---|---|---|---|
| `clientes` | `cliente_id` | fecha_alta, canal, provincia | — |
| `productos` | `producto_id` | nombre, categoria, precio, costo | — |
| `pedidos` | `pedido_id` | cliente_id, fecha, estado (entregado, devuelto, cancelado) | N:1 con clientes |
| `items_pedido` | — | pedido_id, producto_id, cantidad, precio_unitario | N:1 con pedidos y productos |
| `gasto_marketing` | (mes, canal) | gasto_usd | por canal |

`precio_unitario` puede ser menor que `productos.precio` porque incluye descuentos (más frecuentes en noviembre y diciembre).

### Piezas

| Archivo | Qué hace |
|---|---|
| `pipeline/generar_datos.py` | Simula 1 800 clientes de 2023 más 6 000 nuevos. La recompra depende del canal, la estacionalidad y la inactividad (`0.93 ** meses_sin`). El gasto de marketing se deriva de las altas por canal |
| `sql/01..05_*.sql` | Consultas parametrizadas (`:fecha_corte`, `:inicio`) que se pueden correr solas en cualquier cliente SQLite |
| `pipeline/analisis.py` | `cargar_db()` crea la base con índices, `consulta()` ejecuta un `.sql`, `matriz_cohortes()` pivota y enmascara meses futuros, `segmentar_rfm()` puntúa por quintiles y asigna segmentos, `main()` arma `data.json` y `reporte()` el Markdown |
| `docs/app.js` | Lee `data.json`. `filtrar`/`sumar` calculan KPI según año y canal; una función por gráfico (`ventas`, `canales`, `rfm`, `categorias`, `cohortes`); `render()` redibuja todo al cambiar un filtro o el tema |
| `docs/style.css` | Variables de color para tema claro y oscuro; los gráficos leen esas variables con `css("--nombre")` |

## Decisiones

- **SQL para agregar y pandas para lo que en SQL es incómodo** (pivot de cohortes, quintiles). Cada consulta vive en su archivo para leerla y probarla por separado.
- **Solo pedidos `entregado`** cuentan como venta.
- **CAC con clientes captados desde 2024** (`:inicio`): los clientes de 2023 no tienen gasto asociado en el período e inflarían los canales.
- **LTV:CAC con margen, no con ventas:** un canal puede tener buen ROAS y aun así perder dinero.
- **Cohortes enmascaradas:** los meses que una cohorte todavía no vivió quedan en `NaN` (`null` en el JSON) y el dashboard los muestra vacíos, no como 0 %.
- **Orden de los segmentos RFM:** `SEGMENTOS` se recorre en orden inverso y cada condición sobrescribe a la anterior, así que gana la **primera** de la lista. "Necesitan atención" es el valor por defecto.
- **`redondear()`** antes de escribir el JSON: reduce su tamaño y convierte `NaN` en `null` (JSON válido).
- **Paleta validada para daltonismo** y modo oscuro con `prefers-color-scheme`.

## Tests

`tests/test_pipeline.py` usa una base en memoria con 3 clientes y 4 pedidos calculados a mano para comprobar que la economía por canal excluye a los clientes viejos y los pedidos cancelados, que las ventas mensuales excluyen cancelados, que la matriz de cohortes oculta los meses futuros y que el RFM asigna Campeones y En riesgo. La CI corre `pytest` en cada push.

## Cómo extenderlo

- **Nueva consulta:** crear `sql/06_nombre.sql`, llamarla en `main()` con `consulta(con, "06_nombre.sql", parametro=...)`, agregar el resultado a `datos` y dibujarlo en `app.js` con una función nueva llamada desde `render()`.
- **Nuevo segmento RFM:** agregar una tupla `(nombre, condicion)` a `SEGMENTOS` en la posición según su prioridad.
- **Otra fecha de corte:** `FECHA_CORTE` en `analisis.py` (afecta RFM y el enmascarado de cohortes).
- **Datos reales:** reemplazar los CSV de `datos/crudos/` respetando las columnas de las 5 tablas.

## Pendientes

- `generar_datos.py` usa un bucle de Python por cliente y por pedido; tarda unos segundos. Se podría vectorizar si se aumenta el volumen.
- El dashboard no tiene tests; la lógica de `filtrar`/`sumar` se podría extraer a un módulo y probar con Node.
- Las cifras del README están escritas a mano a partir de `REPORTE.md`.
