-- Recencia, frecuencia y valor monetario por cliente al cierre del período.
SELECT p.cliente_id,
       c.canal,
       c.provincia,
       CAST(julianday(:fecha_corte) - julianday(MAX(p.fecha)) AS INTEGER) AS recencia_dias,
       COUNT(DISTINCT p.pedido_id)                                         AS frecuencia,
       ROUND(SUM(i.cantidad * i.precio_unitario), 2)                       AS monetario
FROM pedidos p
JOIN clientes c     ON c.cliente_id = p.cliente_id
JOIN items_pedido i ON i.pedido_id = p.pedido_id
WHERE p.estado = 'entregado'
GROUP BY p.cliente_id, c.canal, c.provincia;
