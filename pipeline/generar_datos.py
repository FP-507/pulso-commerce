"""Genera un dataset SINTÉTICO de una tienda online ficticia ("Pulso") en Panamá.

Simula 2 años de operación (2024-2025) con comportamientos realistas:
- Cada canal de adquisición trae clientes con distinta probabilidad de recompra.
- Estacionalidad: picos en noviembre (Black Friday) y diciembre.
- La probabilidad de volver a comprar cae con el tiempo desde la última compra.
- Gasto de marketing mensual por canal, para calcular CAC y ROAS.

Todo es reproducible con una semilla fija. Uso: python pipeline/generar_datos.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 7
RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"

INICIO, FIN = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")

PROVINCIAS = {
    "Panamá": 0.48, "Panamá Oeste": 0.16, "Colón": 0.08, "Chiriquí": 0.11,
    "Coclé": 0.06, "Veraguas": 0.05, "Herrera": 0.03, "Los Santos": 0.03,
}

# canal: (peso de adquisición, prob. base de recompra mensual, costo por cliente aprox.)
CANALES = {
    "Búsqueda orgánica": (0.24, 0.20, 9.0),    # costo de SEO y contenido
    "Instagram Ads": (0.26, 0.11, 31.0),
    "Google Ads": (0.20, 0.15, 26.0),
    "Referidos": (0.12, 0.27, 12.0),           # crédito de referido
    "Email": (0.08, 0.24, 6.0),
    "TikTok Ads": (0.10, 0.08, 22.0),
}
CLIENTES_BASE = 1800  # clientes captados en 2023 que siguen comprando en 2024

CATEGORIAS = {
    # categoría: (n productos, rango de precio, margen)
    "Electrónica": (10, (25, 320), 0.18),
    "Hogar": (12, (12, 140), 0.34),
    "Moda": (14, (9, 85), 0.48),
    "Belleza": (10, (6, 60), 0.55),
    "Deportes": (8, (15, 180), 0.30),
    "Supermercado": (12, (3, 30), 0.15),
}

ESTACIONALIDAD = {1: 0.85, 2: 0.80, 3: 0.90, 4: 0.92, 5: 1.00, 6: 0.95,
                  7: 1.05, 8: 1.00, 9: 0.92, 10: 1.00, 11: 1.45, 12: 1.65}


def productos(rng: np.random.Generator) -> pd.DataFrame:
    filas, pid = [], 1
    for cat, (n, (pmin, pmax), margen) in CATEGORIAS.items():
        for i in range(n):
            precio = round(float(np.exp(rng.uniform(np.log(pmin), np.log(pmax)))), 2)
            filas.append({
                "producto_id": pid, "nombre": f"{cat} {i + 1:02d}", "categoria": cat,
                "precio": precio, "costo": round(precio * (1 - margen * rng.uniform(0.85, 1.15)), 2),
            })
            pid += 1
    return pd.DataFrame(filas)


def generar(n_clientes: int = 6000) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(SEMILLA)
    prods = productos(rng)
    popularidad = rng.dirichlet(np.full(len(prods), 0.6))

    meses = pd.date_range(INICIO, FIN, freq="MS")
    # Más altas de clientes en meses fuertes y con crecimiento suave del negocio.
    peso_mes = np.array([ESTACIONALIDAD[m.month] * (1 + 0.025 * i) for i, m in enumerate(meses)])
    mes_alta = rng.choice(len(meses), size=n_clientes, p=peso_mes / peso_mes.sum())

    canales = list(CANALES)
    p_canal = np.array([CANALES[c][0] for c in canales])
    canal = rng.choice(canales, size=n_clientes, p=p_canal / p_canal.sum())
    prov = rng.choice(list(PROVINCIAS), size=n_clientes, p=list(PROVINCIAS.values()))

    # Base de clientes de 2023: llegaron antes del período y hacen su primera compra a inicios de 2024.
    canal_base = rng.choice(canales, size=CLIENTES_BASE, p=p_canal / p_canal.sum())
    prov_base = rng.choice(list(PROVINCIAS), size=CLIENTES_BASE, p=list(PROVINCIAS.values()))
    perfiles = [
        (pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 365))),
         INICIO + pd.Timedelta(days=int(rng.integers(0, 90))), canal_base[i], prov_base[i])
        for i in range(CLIENTES_BASE)
    ] + [
        (meses[mes_alta[i]] + pd.Timedelta(days=int(rng.integers(0, 28))), None, canal[i], prov[i])
        for i in range(n_clientes)
    ]

    clientes, pedidos, items = [], [], []
    pedido_id = 1
    for cid, (alta, primera, ch, provincia) in enumerate(perfiles, start=1):
        clientes.append({"cliente_id": cid, "fecha_alta": alta.date(), "canal": ch,
                         "provincia": provincia})
        p_base = CANALES[ch][1] * rng.lognormal(0, 0.35)
        afinidad = rng.dirichlet(np.full(len(CATEGORIAS), 0.8))

        fecha, meses_sin = (primera or alta), 0
        while fecha <= FIN:
            n_items = 1 + rng.poisson(0.7)
            cats = rng.choice(list(CATEGORIAS), size=n_items, p=afinidad)
            for cat in cats:
                cand = prods.index[prods.categoria == cat]
                w = popularidad[cand] / popularidad[cand].sum()
                p = prods.loc[rng.choice(cand, p=w)]
                desc = rng.choice([0, 0, 0, 0.1, 0.15, 0.2]) if fecha.month in (11, 12) else rng.choice([0, 0, 0, 0, 0.1])
                items.append({"pedido_id": pedido_id, "producto_id": int(p.producto_id),
                              "cantidad": int(1 + rng.poisson(0.3)),
                              "precio_unitario": round(float(p.precio) * (1 - desc), 2)})
            pedidos.append({"pedido_id": pedido_id, "cliente_id": cid, "fecha": fecha.date(),
                            "estado": rng.choice(["entregado", "entregado", "entregado", "entregado",
                                                  "entregado", "entregado", "entregado", "entregado",
                                                  "devuelto", "cancelado"])})
            pedido_id += 1
            # Avanza mes a mes hasta la próxima compra; la probabilidad decae con la inactividad.
            while True:
                fecha = fecha + pd.Timedelta(days=int(rng.integers(20, 40)))
                meses_sin += 1
                if fecha > FIN:
                    break
                p = p_base * ESTACIONALIDAD[fecha.month] * (0.93 ** meses_sin)
                if rng.random() < p:
                    meses_sin = 0
                    break
                if meses_sin > 14 and rng.random() < 0.5:
                    fecha = FIN + pd.Timedelta(days=1)
                    break

    cli = pd.DataFrame(clientes)
    nuevos = cli[pd.to_datetime(cli.fecha_alta) >= INICIO]
    altas = nuevos.assign(mes=pd.to_datetime(nuevos.fecha_alta).dt.to_period("M")).groupby(["mes", "canal"]).size()
    gasto = []
    for (mes, ch), n in altas.items():
        cpc = CANALES[ch][2] * rng.uniform(0.8, 1.25)
        gasto.append({"mes": str(mes), "canal": ch, "gasto_usd": round(n * cpc, 2)})

    return {
        "clientes": cli,
        "productos": prods,
        "pedidos": pd.DataFrame(pedidos),
        "items_pedido": pd.DataFrame(items),
        "gasto_marketing": pd.DataFrame(gasto),
    }


if __name__ == "__main__":
    CRUDOS.mkdir(parents=True, exist_ok=True)
    for nombre, df in generar().items():
        df.to_csv(CRUDOS / f"{nombre}.csv", index=False, encoding="utf-8")
        print(f"{nombre:16s} {len(df):>7,} filas")
