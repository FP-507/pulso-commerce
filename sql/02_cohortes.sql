-- Retención por cohorte: clientes activos en cada mes desde su primera compra.
WITH primera AS (
    SELECT cliente_id, MIN(fecha) AS primera_fecha
    FROM pedidos
    WHERE estado = 'entregado'
    GROUP BY cliente_id
),
actividad AS (
    SELECT DISTINCT p.cliente_id,
           strftime('%Y-%m', f.primera_fecha) AS cohorte,
           (CAST(strftime('%Y', p.fecha) AS INTEGER) - CAST(strftime('%Y', f.primera_fecha) AS INTEGER)) * 12
         + (CAST(strftime('%m', p.fecha) AS INTEGER) - CAST(strftime('%m', f.primera_fecha) AS INTEGER)) AS mes_n
    FROM pedidos p
    JOIN primera f ON f.cliente_id = p.cliente_id
    WHERE p.estado = 'entregado'
)
SELECT cohorte, mes_n, COUNT(*) AS activos
FROM actividad
GROUP BY cohorte, mes_n
ORDER BY cohorte, mes_n;
