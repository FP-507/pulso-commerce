-- Ventas, margen y pedidos por mes y canal de adquisición (solo pedidos entregados).
WITH lineas AS (
    SELECT p.pedido_id,
           p.cliente_id,
           strftime('%Y-%m', p.fecha)              AS mes,
           c.canal,
           i.cantidad * i.precio_unitario          AS venta,
           i.cantidad * (i.precio_unitario - pr.costo) AS margen
    FROM pedidos p
    JOIN clientes c      ON c.cliente_id = p.cliente_id
    JOIN items_pedido i  ON i.pedido_id = p.pedido_id
    JOIN productos pr    ON pr.producto_id = i.producto_id
    WHERE p.estado = 'entregado'
)
SELECT mes,
       canal,
       ROUND(SUM(venta), 2)            AS ventas,
       ROUND(SUM(margen), 2)           AS margen,
       COUNT(DISTINCT pedido_id)       AS pedidos,
       COUNT(DISTINCT cliente_id)      AS clientes
FROM lineas
GROUP BY mes, canal
ORDER BY mes, canal;
