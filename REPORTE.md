# Reporte · Pulso Commerce

> Datos **sintéticos** de una tienda online ficticia, generados con `pipeline/generar_datos.py`.

## Resumen ejecutivo

| Indicador | 2024 | 2025 |
|---|---:|---:|
| Ventas | $725,439 | $930,736 |
| Margen bruto | $190,593 | $243,563 |
| Pedidos entregados | 7,588 | 9,810 |

- Las ventas crecieron **28%** de 2024 a 2025.
- En promedio, **12%** de una cohorte vuelve a comprar al mes siguiente y **13%** al tercer mes.
- **Email** es el canal más rentable (LTV:CAC 10.4x, CAC $5.92); **Instagram Ads** apenas recupera su costo (LTV:CAC 1.2x).
- Los **Campeones** son el 21% de los clientes y generan el 39% de las ventas.
- Hay **1,378 clientes en riesgo** que compraban seguido y llevan 397 días sin volver.
- **Electrónica** lidera en ventas, pero **Belleza** tiene el mejor margen (54%).

## Recomendaciones

1. Mover presupuesto de **Instagram Ads** hacia **Email** y **Referidos**, que traen clientes que recompran más.
2. Lanzar una campaña de recuperación para los clientes **En riesgo** antes de que pasen a **Hibernando**.
3. El mes 1 concentra la mayor caída de retención: un correo de bienvenida con incentivo a la segunda compra tiene el mayor impacto.

## Economía por canal

| Canal | Clientes captados (2024-25) | CAC | Margen por cliente | ROAS | LTV:CAC |
|---|---:|---:|---:|---:|---:|
| Email | 461 | $5.92 | $61.57 | 41.1x | 10.4x |
| Búsqueda orgánica | 1,437 | $8.75 | $52.87 | 23.2x | 6.0x |
| Referidos | 732 | $12.20 | $71.38 | 22.5x | 5.8x |
| Google Ads | 1,240 | $26.12 | $46.06 | 6.7x | 1.8x |
| TikTok Ads | 654 | $22.45 | $33.42 | 5.6x | 1.5x |
| Instagram Ads | 1,476 | $32.24 | $37.97 | 4.5x | 1.2x |

## Segmentos RFM

| Segmento | Clientes | % de ventas | Recencia media |
|---|---:|---:|---:|
| Campeones | 1,520 (21%) | 39% | 33 días |
| En riesgo | 1,378 (19%) | 20% | 397 días |
| Leales | 666 (9%) | 16% | 149 días |
| Potenciales | 1,035 (14%) | 9% | 98 días |
| Hibernando | 1,502 (21%) | 9% | 505 días |
| Prometedores | 871 (12%) | 5% | 38 días |
| Necesitan atención | 229 (3%) | 1% | 150 días |
