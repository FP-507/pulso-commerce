"""Carga los CSV en SQLite, ejecuta las consultas de /sql y exporta los resultados.

Salidas:
  datos/pulso.db          base SQLite para explorar con cualquier cliente SQL
  docs/data.json          datos agregados que consume el dashboard
  REPORTE.md              hallazgos con cifras calculadas en esta ejecución

Uso: python pipeline/analisis.py
"""

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"
DB = RAIZ / "datos" / "pulso.db"
SQL = RAIZ / "sql"
SALIDA_JSON = RAIZ / "docs" / "data.json"
REPORTE = RAIZ / "REPORTE.md"
FECHA_CORTE = "2025-12-31"
TABLAS = ["clientes", "productos", "pedidos", "items_pedido", "gasto_marketing"]


def cargar_db() -> sqlite3.Connection:
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    for t in TABLAS:
        pd.read_csv(CRUDOS / f"{t}.csv").to_sql(t, con, index=False)
    con.executescript("""
        CREATE INDEX ix_pedidos_cliente ON pedidos(cliente_id);
        CREATE INDEX ix_items_pedido ON items_pedido(pedido_id);
    """)
    return con


def consulta(con, archivo: str, **params) -> pd.DataFrame:
    return pd.read_sql_query((SQL / archivo).read_text(encoding="utf-8"), con, params=params)


def matriz_cohortes(df: pd.DataFrame, max_meses: int = 12) -> pd.DataFrame:
    """Porcentaje de cada cohorte que vuelve a comprar en el mes N."""
    tabla = df.pivot(index="cohorte", columns="mes_n", values="activos").fillna(0)
    tabla = tabla.reindex(columns=range(max_meses + 1), fill_value=0)
    pct = tabla.div(tabla[0], axis=0)
    # Oculta los meses que aún no han ocurrido para cada cohorte.
    ultimo = pd.Period(FECHA_CORTE, "M")
    for cohorte in pct.index:
        disponibles = (ultimo - pd.Period(cohorte, "M")).n
        pct.loc[cohorte, [c for c in pct.columns if c > disponibles]] = np.nan
    return pct


SEGMENTOS = [
    # (nombre, condición sobre puntajes R y F)
    ("Campeones", lambda r, f: (r >= 4) & (f >= 4)),
    ("Leales", lambda r, f: (r >= 3) & (f >= 4)),
    ("Prometedores", lambda r, f: (r >= 4) & (f <= 2)),
    ("Potenciales", lambda r, f: (r >= 3) & (f >= 2)),
    ("En riesgo", lambda r, f: (r <= 2) & (f >= 3)),
    ("Hibernando", lambda r, f: (r <= 2) & (f <= 2)),
]


def segmentar_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    rfm = rfm.copy()
    # Puntajes 1-5 por quintiles. La recencia se invierte: menos días = mejor.
    rfm["R"] = pd.qcut(rfm.recencia_dias.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm.frecuencia.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm.monetario.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["segmento"] = "Necesitan atención"
    for nombre, cond in reversed(SEGMENTOS):
        rfm.loc[cond(rfm.R, rfm.F), "segmento"] = nombre
    return rfm


def redondear(obj):
    if isinstance(obj, float):
        return None if np.isnan(obj) else round(obj, 4)
    if isinstance(obj, dict):
        return {k: redondear(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redondear(v) for v in obj]
    return obj


def main() -> None:
    con = cargar_db()
    mensual = consulta(con, "01_ventas_mensuales.sql")
    cohortes = matriz_cohortes(consulta(con, "02_cohortes.sql"))
    rfm = segmentar_rfm(consulta(con, "03_rfm.sql", fecha_corte=FECHA_CORTE))
    canales = consulta(con, "04_canales.sql", inicio="2024-01-01")
    cat_prov = consulta(con, "05_categorias_provincias.sql")
    clientes = pd.read_sql_query("SELECT * FROM clientes", con)
    con.close()

    seg = (rfm.groupby("segmento")
              .agg(clientes=("cliente_id", "count"), ventas=("monetario", "sum"),
                   recencia=("recencia_dias", "mean"), frecuencia=("frecuencia", "mean"))
              .sort_values("ventas", ascending=False))
    seg["clientes"] = seg.clientes.astype(int)
    seg["pct_clientes"] = seg.clientes / seg.clientes.sum()
    seg["pct_ventas"] = seg.ventas / seg.ventas.sum()

    altas = (clientes.assign(mes=pd.to_datetime(clientes.fecha_alta).dt.strftime("%Y-%m"))
                     .groupby(["mes", "canal"]).size().rename("nuevos").reset_index())
    mensual = mensual.merge(altas, on=["mes", "canal"], how="left").fillna({"nuevos": 0})

    datos = {
        "generado": FECHA_CORTE,
        "canales": sorted(mensual.canal.unique().tolist()),
        "mensual": mensual.to_dict(orient="records"),
        "cohortes": {
            "cohortes": cohortes.index.tolist(),
            "meses": [int(c) for c in cohortes.columns],
            "valores": cohortes.values.tolist(),
        },
        "segmentos": seg.reset_index().to_dict(orient="records"),
        "canal_economia": canales.to_dict(orient="records"),
        "categorias": cat_prov.groupby("categoria")[["ventas", "margen", "unidades"]].sum()
                              .sort_values("ventas", ascending=False).reset_index().to_dict(orient="records"),
        "provincias": cat_prov.groupby("provincia")[["ventas", "margen"]].sum()
                              .sort_values("ventas", ascending=False).reset_index().to_dict(orient="records"),
    }
    SALIDA_JSON.parent.mkdir(exist_ok=True)
    SALIDA_JSON.write_text(json.dumps(redondear(datos), ensure_ascii=False), encoding="utf-8")

    REPORTE.write_text(reporte(mensual, cohortes, seg, canales, datos), encoding="utf-8")
    print(f"OK: {DB.name}, {SALIDA_JSON.relative_to(RAIZ)}, {REPORTE.name}")


def reporte(mensual, cohortes, seg, canales, datos) -> str:
    anual = mensual.assign(anio=mensual.mes.str[:4]).groupby("anio")[["ventas", "margen", "pedidos"]].sum()
    crec = anual.ventas["2025"] / anual.ventas["2024"] - 1
    ret_m1 = cohortes[1].mean()
    ret_m3 = cohortes[3].mean()
    mejor, peor = canales.iloc[0], canales.iloc[-1]
    camp = seg.loc["Campeones"] if "Campeones" in seg.index else None
    riesgo = seg.loc["En riesgo"] if "En riesgo" in seg.index else None
    top_cat = datos["categorias"][0]
    por_margen = sorted(datos["categorias"], key=lambda c: c["margen"] / c["ventas"], reverse=True)[0]

    filas_canal = "\n".join(
        f"| {r.canal} | {r.clientes_nuevos:,} | ${r.cac:,.2f} | ${r.margen_por_cliente:,.2f} | {r.roas:.1f}x | {r.ltv_cac:.1f}x |"
        for r in canales.itertuples()
    )
    filas_seg = "\n".join(
        f"| {s} | {int(r.clientes):,} ({r.pct_clientes:.0%}) | {r.pct_ventas:.0%} | {r.recencia:.0f} días |"
        for s, r in seg.iterrows()
    )
    return f"""# Reporte · Pulso Commerce

> Datos **sintéticos** de una tienda online ficticia, generados con `pipeline/generar_datos.py`.

## Resumen ejecutivo

| Indicador | 2024 | 2025 |
|---|---:|---:|
| Ventas | ${anual.ventas['2024']:,.0f} | ${anual.ventas['2025']:,.0f} |
| Margen bruto | ${anual.margen['2024']:,.0f} | ${anual.margen['2025']:,.0f} |
| Pedidos entregados | {anual.pedidos['2024']:,} | {anual.pedidos['2025']:,} |

- Las ventas crecieron **{crec:.0%}** de 2024 a 2025.
- En promedio, **{ret_m1:.0%}** de una cohorte vuelve a comprar al mes siguiente y **{ret_m3:.0%}** al tercer mes.
- **{mejor.canal}** es el canal más rentable (LTV:CAC {mejor.ltv_cac:.1f}x, CAC ${mejor.cac:.2f}); **{peor.canal}** apenas recupera su costo (LTV:CAC {peor.ltv_cac:.1f}x).
{f"- Los **Campeones** son el {camp.pct_clientes:.0%} de los clientes y generan el {camp.pct_ventas:.0%} de las ventas." if camp is not None else ""}
{f"- Hay **{int(riesgo.clientes):,} clientes en riesgo** que compraban seguido y llevan {riesgo.recencia:.0f} días sin volver." if riesgo is not None else ""}
- **{top_cat['categoria']}** lidera en ventas, pero **{por_margen['categoria']}** tiene el mejor margen ({por_margen['margen'] / por_margen['ventas']:.0%}).

## Recomendaciones

1. Mover presupuesto de **{peor.canal}** hacia **{mejor.canal}** y **Referidos**, que traen clientes que recompran más.
2. Lanzar una campaña de recuperación para los clientes **En riesgo** antes de que pasen a **Hibernando**.
3. El mes 1 concentra la mayor caída de retención: un correo de bienvenida con incentivo a la segunda compra tiene el mayor impacto.

## Economía por canal

| Canal | Clientes captados (2024-25) | CAC | Margen por cliente | ROAS | LTV:CAC |
|---|---:|---:|---:|---:|---:|
{filas_canal}

## Segmentos RFM

| Segmento | Clientes | % de ventas | Recencia media |
|---|---:|---:|---:|
{filas_seg}
"""


if __name__ == "__main__":
    main()
