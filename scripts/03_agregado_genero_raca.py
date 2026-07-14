"""
Agrega os CSVs de eleitos por ano, partido, gênero e raça.
Entrada:  vereadores_eleitos_2020_2024.csv
          prefeitos_eleitos_2020_2024.csv
Saída:    vereadores_genero_raca_partido_2020_2024.csv
          prefeitos_genero_raca_partido_2020_2024.csv
"""

import pandas as pd
import warnings
warnings.filterwarnings("ignore")

ARQUIVOS = {
    "vereadores": (
        "vereadores_eleitos_2020_2024.csv",
        "vereadores_genero_raca_partido_2020_2024.csv",
        "VEREADORES_ELEITOS",
    ),
    "prefeitos": (
        "prefeitos_eleitos_2020_2024.csv",
        "prefeitos_genero_raca_partido_2020_2024.csv",
        "PREFEITOS_ELEITOS",
    ),
}

for cargo, (entrada, saida, col_count) in ARQUIVOS.items():
    df = pd.read_csv(entrada, sep=";", dtype=str)

    agg = (
        df.groupby(["ANO_ELEICAO", "SG_PARTIDO", "NM_PARTIDO", "DS_GENERO", "DS_COR_RACA"])
        .size()
        .reset_index(name=col_count)
    )

    agg.sort_values(["ANO_ELEICAO", "SG_PARTIDO", "DS_GENERO", "DS_COR_RACA"], inplace=True)
    agg.to_csv(saida, index=False, sep=";", encoding="utf-8-sig")

    print(f"[{cargo}] {saida} — {len(agg):,} linhas | {agg['SG_PARTIDO'].nunique()} partidos")
