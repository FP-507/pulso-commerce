-- Economía por canal para los clientes captados en el período (desde :inicio).
-- CAC = gasto / clientes captados. LTV:CAC = margen por cliente / CAC.
WITH nuevos AS (
    SELECT cliente_id, canal
    FROM clientes
    WHERE fecha_alta >= :inicio
),
captados AS (
    SELECT canal, COUNT(*) AS clientes_nuevos
    FROM nuevos
    GROUP BY canal
),
gasto AS (
    SELECT canal, SUM(gasto_usd) AS gasto
    FROM gasto_marketing
    GROUP BY canal
),
ingresos AS (
    SELECT n.canal,
           SUM(i.cantidad * i.precio_unitario)                 AS ventas,
           SUM(i.cantidad * (i.precio_unitario - pr.costo))    AS margen,
           COUNT(DISTINCT p.pedido_id)                         AS pedidos
    FROM pedidos p
    JOIN nuevos n       ON n.cliente_id = p.cliente_id
    JOIN items_pedido i ON i.pedido_id = p.pedido_id
    JOIN productos pr   ON pr.producto_id = i.producto_id
    WHERE p.estado = 'entregado'
    GROUP BY n.canal
)
SELECT k.canal,
       k.clientes_nuevos,
       ROUND(g.gasto, 2)                                          AS gasto,
       ROUND(g.gasto / k.clientes_nuevos, 2)                      AS cac,
       ROUND(n.ventas, 2)                                         AS ventas,
       ROUND(n.margen, 2)                                         AS margen,
       ROUND(n.margen / k.clientes_nuevos, 2)                     AS margen_por_cliente,
       ROUND(n.ventas / g.gasto, 2)                               AS roas,
       ROUND((n.margen / k.clientes_nuevos) / (g.gasto / k.clientes_nuevos), 2) AS ltv_cac,
       ROUND(1.0 * n.pedidos / k.clientes_nuevos, 2)              AS pedidos_por_cliente
FROM captados k
JOIN gasto g    ON g.canal = k.canal
JOIN ingresos n ON n.canal = k.canal
ORDER BY ltv_cac DESC;
