-- Ventas y margen por categoría y provincia (pedidos entregados).
SELECT pr.categoria,
       c.provincia,
       ROUND(SUM(i.cantidad * i.precio_unitario), 2)              AS ventas,
       ROUND(SUM(i.cantidad * (i.precio_unitario - pr.costo)), 2) AS margen,
       SUM(i.cantidad)                                            AS unidades
FROM pedidos p
JOIN clientes c     ON c.cliente_id = p.cliente_id
JOIN items_pedido i ON i.pedido_id = p.pedido_id
JOIN productos pr   ON pr.producto_id = i.producto_id
WHERE p.estado = 'entregado'
GROUP BY pr.categoria, c.provincia;
