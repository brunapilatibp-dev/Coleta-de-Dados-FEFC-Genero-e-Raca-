"""
Baixa dados do TSE e extrai vereadores eleitos em 2020 e 2024.
Fonte: dados.tse.jus.br — consulta_cand
Saída: vereadores_eleitos_2020_2024.csv
"""

import io
import zipfile
import requests
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

ANOS = [2020, 2024]

COLUNAS = [
    "ANO_ELEICAO", "NR_TURNO", "SG_UF", "SG_UE", "NM_UE",
    "CD_CARGO", "DS_CARGO", "SQ_CANDIDATO", "NR_CANDIDATO",
    "NM_CANDIDATO", "NM_URNA_CANDIDATO", "NR_CPF_CANDIDATO",
    "SG_PARTIDO", "NM_PARTIDO", "NR_PARTIDO",
    "DS_GENERO", "DS_COR_RACA", "DS_SIT_TOT_TURNO", "DS_SITUACAO_CANDIDATURA",
]


def baixar_e_filtrar(ano: int) -> pd.DataFrame:
    url = (
        f"https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/"
        f"consulta_cand_{ano}.zip"
    )
    print(f"[{ano}] Baixando {url} ...")
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()

    chunks, total = [], 0
    for chunk in resp.iter_content(chunk_size=1024 * 1024):
        chunks.append(chunk)
        total += len(chunk)
        print(f"\r[{ano}] {total/1e6:.1f} MB baixados", end="", flush=True)
    print()

    with zipfile.ZipFile(io.BytesIO(b"".join(chunks))) as z:
        nomes = z.namelist()
        arquivo = next(
            (n for n in nomes if "BRASIL" in n.upper() and n.endswith(".csv")), None
        )
        print(f"[{ano}] Lendo {arquivo}...")
        with z.open(arquivo) as f:
            df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str, on_bad_lines="skip")

    df.columns = [c.strip().upper() for c in df.columns]
    print(f"[{ano}] {len(df):,} linhas brutas")

    # Vereador = CD_CARGO 13
    df = df[df["CD_CARGO"].str.strip() == "13"]
    print(f"[{ano}] {len(df):,} candidatos a vereador")

    # Apenas eleitos
    df = df[df["DS_SIT_TOT_TURNO"].str.upper().str.startswith("ELEITO", na=False)]
    print(f"[{ano}] {len(df):,} vereadores ELEITOS")

    cols_ok = [c for c in COLUNAS if c in df.columns]
    df = df[cols_ok].copy()
    df["ANO_ELEICAO"] = str(ano)
    return df


frames = []
for ano in ANOS:
    frames.append(baixar_e_filtrar(ano))

base = pd.concat(frames, ignore_index=True)
base.sort_values(["ANO_ELEICAO", "SG_UF", "NM_UE", "NM_CANDIDATO"], inplace=True)
base.reset_index(drop=True, inplace=True)

saida = "vereadores_eleitos_2020_2024.csv"
base.to_csv(saida, index=False, encoding="utf-8-sig", sep=";")

print(f"\nBase salva em: {saida}")
print(f"Total: {len(base):,} registros")
print(base["ANO_ELEICAO"].value_counts().to_string())
