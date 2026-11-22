# Pulso Commerce · Analítica de e-commerce

Análisis de punta a punta de una tienda online: **generación de datos → SQL → cohortes, RFM y economía por canal → dashboard interactivo**. Responde una pregunta de negocio concreta: *¿qué canales de marketing traen clientes que vuelven a comprar y cuáles solo cuestan dinero?*

**[Ver el dashboard en vivo →](https://fp-507.github.io/pulso-commerce/)** · **[Leer el reporte →](REPORTE.md)**

![tests](https://github.com/FP-507/pulso-commerce/actions/workflows/tests.yml/badge.svg)

> Los datos son **sintéticos**: una tienda ficticia con 7 800 clientes, 21 700 pedidos y 37 000 líneas de pedido en 2024–2025, generados con reglas realistas (estacionalidad, recompra distinta por canal, inactividad que reduce la probabilidad de volver).

## Hallazgos

| | |
|---|---|
| Crecimiento de ventas 2025 | **+28 %** ($930 k) |
| Mejor canal (LTV:CAC) | **Email, 10,4x** |
| Peor canal (LTV:CAC) | **Instagram Ads, 1,2x** |
| Campeones (RFM) | **21 % de clientes, 39 % de ventas** |
| Clientes en riesgo | **1 378** sin comprar hace ~400 días |

**Recomendación principal:** mover presupuesto de Instagram y TikTok hacia Email y Referidos, y activar una campaña de recuperación para los clientes en riesgo. Detalle completo en [REPORTE.md](REPORTE.md).

## Qué incluye

- **Modelo de datos relacional** de 5 tablas: clientes, productos, pedidos, líneas de pedido y gasto de marketing.
- **5 consultas SQL** con CTE, joins, agregaciones y funciones de fecha ([`sql/`](sql)).
- **Análisis de cohortes**: retención mensual de cada grupo de clientes según su mes de primera compra.
- **Segmentación RFM** por quintiles: Campeones, Leales, Potenciales, Prometedores, En riesgo, Hibernando.
- **Economía por canal**: CAC, margen por cliente, ROAS y LTV:CAC.
- **Dashboard** en HTML y Chart.js, con filtros por año y canal, KPI con variación interanual, mapa de calor de cohortes y modo oscuro. Paleta validada para daltonismo.
- **Tests** de las consultas y de la lógica de cohortes y RFM, con CI en GitHub Actions.

## Arquitectura

```
generar_datos.py ──► datos/crudos/*.csv ──► SQLite ──► sql/*.sql ──► analisis.py ──► docs/data.json ──► dashboard
                                                                              └──► REPORTE.md
```

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
python pipeline/generar_datos.py   # opcional: los CSV ya están en datos/crudos
python pipeline/analisis.py        # crea datos/pulso.db, docs/data.json y REPORTE.md
python -m http.server -d docs      # abre http://localhost:8000
pytest
```

`datos/pulso.db` se puede abrir con DB Browser for SQLite, DBeaver o cualquier cliente SQL para explorar los datos.

## Decisiones de análisis

- **Solo pedidos entregados** cuentan como venta; cancelados y devueltos se excluyen.
- **CAC solo con clientes captados en el período**: los 1 800 clientes que llegaron en 2023 se excluyen para no inflar los canales.
- **LTV:CAC con margen, no con ventas**: un canal puede tener buen ROAS y aun así perder dinero si sus clientes compran productos de bajo margen.
- **Cohortes enmascaradas**: los meses que todavía no ocurrieron para una cohorte se muestran vacíos, no como 0 %.

## Estructura

```
pipeline/   generar_datos.py · analisis.py
sql/        consultas de ventas, cohortes, RFM, canales y categorías
datos/      CSV crudos (y pulso.db al ejecutar)
docs/       dashboard publicado en GitHub Pages
tests/      pytest
```
