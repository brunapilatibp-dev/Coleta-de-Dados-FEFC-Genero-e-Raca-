#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Junta as bases finais de FEFC + resultados de 2020 e 2024
em uma única tabela comparativa para uso no Tableau.

Uso:
    python juntar_bases_2020_2024.py

Ou indicando os arquivos:
    python juntar_bases_2020_2024.py ^
        --base-2020 "saida_2020/base_final_fefc_resultados_2020.csv" ^
        --base-2024 "saida_2024/base_final_fefc_resultados_2024.csv" ^
        --saida "base_comparativa_fefc_2020_2024.csv"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def detectar_encoding(caminho: Path) -> str:
    amostra = caminho.read_bytes()[:200_000]
    for encoding in ("utf-8-sig", "utf-8", "latin1", "cp1252"):
        try:
            amostra.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Não foi possível identificar a codificação de {caminho}.")


def ler_base(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    encoding = detectar_encoding(caminho)

    df = pd.read_csv(
        caminho,
        sep=";",
        encoding=encoding,
        dtype="string",
        keep_default_na=False,
        low_memory=False,
    )

    df.columns = [str(coluna).strip().upper() for coluna in df.columns]
    return df


def converter_numeros(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    colunas_inteiras = [
        "AA_ELEICAO",
        "NR_PARTIDO",
        "QT_CANDIDATOS_COM_FEFC",
        "QT_ELEITOS",
        "QT_SUPLENTES",
        "QT_NAO_ELEITOS",
    ]

    for coluna in colunas_inteiras:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(
                df[coluna].replace("", pd.NA),
                errors="coerce",
            ).astype("Int64")

    for coluna in df.columns:
        if coluna.startswith(("VR_", "PE_")):
            serie = (
                df[coluna]
                .replace("", pd.NA)
                .astype("string")
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[coluna] = pd.to_numeric(serie, errors="coerce").astype("Float64")

    return df


def validar_anos(df: pd.DataFrame, ano_esperado: int, nome: str) -> None:
    if "AA_ELEICAO" not in df.columns:
        raise ValueError(f"A base {nome} não possui a coluna AA_ELEICAO.")

    anos = set(
        pd.to_numeric(df["AA_ELEICAO"], errors="coerce")
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    if anos != {ano_esperado}:
        raise ValueError(
            f"A base {nome} deveria conter somente {ano_esperado}, "
            f"mas contém: {sorted(anos)}"
        )


def alinhar_colunas(
    base_2020: pd.DataFrame,
    base_2024: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    colunas_2020 = set(base_2020.columns)
    colunas_2024 = set(base_2024.columns)

    faltam_2020 = sorted(colunas_2024 - colunas_2020)
    faltam_2024 = sorted(colunas_2020 - colunas_2024)

    if faltam_2020:
        print(
            "Aviso: as seguintes colunas existem em 2024, mas não em 2020. "
            "Serão criadas vazias em 2020:"
        )
        print(", ".join(faltam_2020))
        for coluna in faltam_2020:
            base_2020[coluna] = pd.NA

    if faltam_2024:
        print(
            "Aviso: as seguintes colunas existem em 2020, mas não em 2024. "
            "Serão criadas vazias em 2024:"
        )
        print(", ".join(faltam_2024))
        for coluna in faltam_2024:
            base_2024[coluna] = pd.NA

    ordem = list(base_2020.columns)
    ordem.extend(coluna for coluna in base_2024.columns if coluna not in ordem)

    return base_2020[ordem], base_2024[ordem]


def criar_chave_comparativa(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "SG_PARTIDO" in df.columns:
        df["CHAVE_ANO_PARTIDO_GENERO_RACA"] = (
            df["AA_ELEICAO"].astype("string").fillna("")
            + "-"
            + df["SG_PARTIDO"].astype("string").fillna("")
            + "-"
            + df["DS_GENERO"].astype("string").fillna("")
            + "-"
            + df["DS_COR_RACA"].astype("string").fillna("")
        )

    return df


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Junta as bases de FEFC e resultados de 2020 e 2024."
    )
    parser.add_argument(
        "--base-2020",
        type=Path,
        default=Path("saida_2020/base_final_fefc_resultados_2020.csv"),
        help="Caminho da base final de 2020.",
    )
    parser.add_argument(
        "--base-2024",
        type=Path,
        default=Path("saida_2024/base_final_fefc_resultados_2024.csv"),
        help="Caminho da base final de 2024.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("base_comparativa_fefc_2020_2024.csv"),
        help="Arquivo CSV de saída.",
    )
    return parser.parse_args()


def main() -> None:
    args = argumentos()

    print(f"Lendo base de 2020: {args.base_2020}")
    base_2020 = ler_base(args.base_2020)

    print(f"Lendo base de 2024: {args.base_2024}")
    base_2024 = ler_base(args.base_2024)

    validar_anos(base_2020, 2020, "2020")
    validar_anos(base_2024, 2024, "2024")

    base_2020, base_2024 = alinhar_colunas(base_2020, base_2024)

    combinada = pd.concat(
        [base_2020, base_2024],
        ignore_index=True,
        sort=False,
    )

    combinada = converter_numeros(combinada)
    combinada = criar_chave_comparativa(combinada)

    combinada = combinada.sort_values(
        ["AA_ELEICAO", "SG_PARTIDO", "DS_GENERO", "DS_COR_RACA"],
        na_position="last",
    ).reset_index(drop=True)

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    combinada.to_csv(
        args.saida,
        sep=";",
        index=False,
        encoding="utf-8-sig",
        decimal=",",
    )

    print("\nBases unidas com sucesso.")
    print(f"Linhas de 2020: {len(base_2020):,}".replace(",", "."))
    print(f"Linhas de 2024: {len(base_2024):,}".replace(",", "."))
    print(f"Total combinado: {len(combinada):,}".replace(",", "."))
    print(f"Arquivo criado: {args.saida.resolve()}")


if __name__ == "__main__":
    main()
