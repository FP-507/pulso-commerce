import sqlite3

import numpy as np
import pandas as pd
import pytest

from pipeline import analisis


def test_matriz_cohortes_oculta_meses_futuros():
    df = pd.DataFrame({
        "cohorte": ["2025-11", "2025-11", "2025-12"],
        "mes_n": [0, 1, 0],
        "activos": [100, 25, 80],
    })
    m = analisis.matriz_cohortes(df, max_meses=3)
    assert m.loc["2025-11", 0] == 1.0
    assert m.loc["2025-11", 1] == 0.25
    assert np.isnan(m.loc["2025-11", 2])      # diciembre + 1 aún no ocurre
    assert np.isnan(m.loc["2025-12", 1])


def test_segmentar_rfm_asigna_campeones_y_en_riesgo():
    n = 100
    rfm = pd.DataFrame({
        "cliente_id": range(n),
        "recencia_dias": np.linspace(1, 400, n),
        "frecuencia": np.linspace(20, 1, n),
        "monetario": np.linspace(500, 10, n),
    })
    rfm.loc[90:, "frecuencia"] = 25  # compraban mucho pero hace tiempo
    seg = analisis.segmentar_rfm(rfm)
    assert seg.loc[0, "segmento"] == "Campeones"
    assert seg.loc[99, "segmento"] == "En riesgo"
    assert set(seg[["R", "F", "M"]].stack().unique()) <= {1, 2, 3, 4, 5}


@pytest.fixture
def db_minima():
    con = sqlite3.connect(":memory:")
    pd.DataFrame({"cliente_id": [1, 2, 3], "fecha_alta": ["2024-01-05", "2024-02-01", "2023-06-01"],
                  "canal": ["Email", "Email", "Email"], "provincia": ["Colón"] * 3}).to_sql("clientes", con)
    pd.DataFrame({"producto_id": [1], "nombre": ["X"], "categoria": ["Hogar"], "precio": [10.0], "costo": [6.0]}).to_sql("productos", con)
    pd.DataFrame({"pedido_id": [1, 2, 3, 4], "cliente_id": [1, 1, 2, 3],
                  "fecha": ["2024-01-10", "2024-03-10", "2024-02-02", "2024-01-15"],
                  "estado": ["entregado", "entregado", "cancelado", "entregado"]}).to_sql("pedidos", con)
    pd.DataFrame({"pedido_id": [1, 2, 3, 4], "producto_id": [1] * 4, "cantidad": [1, 2, 1, 1],
                  "precio_unitario": [10.0] * 4}).to_sql("items_pedido", con)
    pd.DataFrame({"mes": ["2024-01"], "canal": ["Email"], "gasto_usd": [20.0]}).to_sql("gasto_marketing", con)
    yield con
    con.close()


def test_economia_por_canal_solo_cuenta_clientes_nuevos(db_minima):
    r = analisis.consulta(db_minima, "04_canales.sql", inicio="2024-01-01").iloc[0]
    assert r.clientes_nuevos == 2            # el cliente de 2023 no cuenta
    assert r.cac == 10.0                     # 20 / 2
    assert r.ventas == 30.0                  # solo pedidos entregados de clientes nuevos
    assert r.margen_por_cliente == 6.0       # (4 + 8) / 2
    assert r.ltv_cac == 0.6


def test_ventas_mensuales_excluye_cancelados(db_minima):
    df = analisis.consulta(db_minima, "01_ventas_mensuales.sql")
    assert df.ventas.sum() == 40.0
    assert "2024-02" not in set(df.mes)
