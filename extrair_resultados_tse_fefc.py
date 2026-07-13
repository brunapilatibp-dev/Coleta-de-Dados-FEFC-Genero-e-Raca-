"""
Extrai resultados eleitorais de candidaturas a vereador do TSE e junta
os totais agregados por partido, gênero e grupo racial a uma planilha de FEFC.

A classificação usada é:
- Negra: PRETA + PARDA
- Não negra: BRANCA + AMARELA + INDÍGENA
- Eleito: ELEITO POR QP + ELEITO POR MÉDIA
- Suplente: SUPLENTE
- Não eleito: NÃO ELEITO

Registros com gênero, raça ou situação de totalização fora dessas categorias
não são forçados para nenhum grupo: eles são exportados para auditoria.

Exemplo:
    python extrair_resultados_tse_fefc.py \
        --fefc "fefc_cor_raca_2024.csv" \
        --ano 2024

Também é possível usar um ZIP do TSE já baixado:
    python extrair_resultados_tse_fefc.py \
        --fefc "fefc_cor_raca_2024.csv" \
        --ano 2024 \
        --tse-zip "consulta_cand_2024.zip"
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


URL_TSE = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/"
    "consulta_cand_{ano}.zip"
)

COLUNAS_TSE = [
    "ANO_ELEICAO",
    "NR_TURNO",
    "DS_CARGO",
    "SQ_CANDIDATO",
    "SG_PARTIDO",
    "DS_GENERO",
    "DS_COR_RACA",
    "DS_SIT_TOT_TURNO",
]

CHAVES_FINAIS = [
    "AA_ELEICAO",
    "_PARTIDO_CHAVE",
    "DS_GENERO",
    "DS_COR_RACA",
]

COLUNAS_CONTAGEM = ["QT_ELEITOS", "QT_SUPLENTES", "QT_NAO_ELEITOS"]


class ErroDados(ValueError):
    """Erro de estrutura ou consistência dos dados de entrada."""


def sem_acentos(valor: object) -> str:
    """Normaliza texto para comparação, removendo acentos e espaços extras."""
    if valor is None or pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto.strip().upper())
    return texto


def texto_padrao(valor: object) -> str:
    """Padroniza caixa e espaços, preservando acentos."""
    if valor is None or pd.isna(valor):
        return ""
    texto = unicodedata.normalize("NFC", str(valor))
    return re.sub(r"\s+", " ", texto.strip().upper())


def detectar_encoding_csv(caminho: Path) -> str:
    """Escolhe uma codificação comum nos arquivos usados neste projeto."""
    amostra = caminho.read_bytes()[:200_000]
    for encoding in ("utf-8-sig", "latin1", "cp1252"):
        try:
            amostra.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise ErroDados(f"Não foi possível identificar a codificação de {caminho}.")


def ler_csv_fefc(caminho: Path) -> pd.DataFrame:
    encoding = detectar_encoding_csv(caminho)
    df = pd.read_csv(
        caminho,
        sep=";",
        encoding=encoding,
        dtype="string",
        keep_default_na=False,
    )
    df.columns = [texto_padrao(c) for c in df.columns]

    obrigatorias = {
        "AA_ELEICAO",
        "SG_PARTIDO",
        "DS_GENERO",
        "DS_COR_RACA",
        "QT_CANDIDATO",
    }
    ausentes = sorted(obrigatorias - set(df.columns))
    if ausentes:
        raise ErroDados(
            "A planilha de FEFC não contém as colunas obrigatórias: "
            + ", ".join(ausentes)
        )

    # Padronização das chaves usadas na junção.
    df["AA_ELEICAO"] = pd.to_numeric(df["AA_ELEICAO"], errors="raise").astype("Int64")
    df["SG_PARTIDO"] = df["SG_PARTIDO"].map(texto_padrao)
    df["_PARTIDO_CHAVE"] = df["SG_PARTIDO"].map(sem_acentos)
    df["DS_GENERO"] = df["DS_GENERO"].map(classificar_genero)
    df["DS_COR_RACA"] = df["DS_COR_RACA"].map(classificar_raca_fefc)

    chaves_invalidas = df[
        (df["_PARTIDO_CHAVE"] == "")
        | (df["DS_GENERO"].isna())
        | (df["DS_COR_RACA"].isna())
    ]
    if not chaves_invalidas.empty:
        raise ErroDados(
            "Há linhas na planilha de FEFC com partido, gênero ou raça não reconhecidos. "
            "Revise essas linhas antes de continuar."
        )

    duplicadas = df.duplicated(CHAVES_FINAIS, keep=False)
    if duplicadas.any():
        exemplos = df.loc[duplicadas, CHAVES_FINAIS].head(10).to_dict("records")
        raise ErroDados(
            "A planilha de FEFC possui mais de uma linha para a mesma combinação "
            f"ano + partido + gênero + raça. Exemplos: {exemplos}"
        )

    # Converte números brasileiros. Mantém textos e datas como vieram.
    colunas_inteiras = {"NR_PARTIDO", "QT_CANDIDATO", "ST_RENUNCIA"}
    prefixos_decimais = ("VR_", "PE_")

    for coluna in df.columns:
        if coluna in colunas_inteiras:
            df[coluna] = pd.to_numeric(
                df[coluna].replace("", pd.NA), errors="coerce"
            ).astype("Int64")
        elif coluna.startswith(prefixos_decimais):
            serie = (
                df[coluna]
                .replace("", pd.NA)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[coluna] = pd.to_numeric(serie, errors="coerce").astype("Float64")

    return df


def classificar_genero(valor: object) -> str | None:
    chave = sem_acentos(valor)
    mapa = {
        "FEMININO": "FEMININO",
        "MASCULINO": "MASCULINO",
    }
    return mapa.get(chave)


def classificar_raca_tse(valor: object) -> str | None:
    chave = sem_acentos(valor)
    if chave in {"PRETA", "PARDA"}:
        return "NEGRA"
    if chave in {"BRANCA", "AMARELA", "INDIGENA"}:
        return "NÃO NEGRA"
    return None


def classificar_raca_fefc(valor: object) -> str | None:
    chave = sem_acentos(valor)
    if chave in {"NEGRA", "NEGRO"}:
        return "NEGRA"
    if chave in {"NAO NEGRA", "NAO NEGRO"}:
        return "NÃO NEGRA"
    return None


def classificar_resultado(valor: object) -> str | None:
    chave = sem_acentos(valor)
    if chave in {"ELEITO POR QP", "ELEITO POR MEDIA"}:
        return "ELEITOS"
    if chave == "SUPLENTE":
        return "SUPLENTES"
    if chave == "NAO ELEITO":
        return "NAO_ELEITOS"
    return None


def baixar_zip_tse(ano: int, destino: Path) -> Path:
    url = URL_TSE.format(ano=ano)
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists() and destino.stat().st_size > 0:
        print(f"Usando ZIP já existente: {destino}")
        return destino

    print(f"Baixando dados de candidaturas do TSE para {ano}...")
    print(url)

    try:
        with requests.get(url, stream=True, timeout=(30, 300)) as resposta:
            resposta.raise_for_status()
            total = int(resposta.headers.get("content-length", 0))
            baixado = 0
            with destino.open("wb") as arquivo:
                for bloco in resposta.iter_content(chunk_size=1024 * 1024):
                    if not bloco:
                        continue
                    arquivo.write(bloco)
                    baixado += len(bloco)
                    if total:
                        percentual = baixado / total * 100
                        print(f"\rDownload: {percentual:5.1f}%", end="", flush=True)
        if total:
            print()
    except requests.RequestException as exc:
        destino.unlink(missing_ok=True)
        raise RuntimeError(
            "Não foi possível baixar automaticamente o arquivo do TSE. "
            f"Baixe manualmente {url} e execute novamente usando --tse-zip."
        ) from exc

    return destino


def escolher_csv_brasil(zf: zipfile.ZipFile, ano: int) -> str:
    arquivos_csv = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    esperado = f"consulta_cand_{ano}_brasil.csv"

    exatos = [n for n in arquivos_csv if Path(n).name.lower() == esperado]
    if len(exatos) == 1:
        return exatos[0]

    candidatos = [
        n
        for n in arquivos_csv
        if f"consulta_cand_{ano}" in Path(n).name.lower()
        and "brasil" in Path(n).name.lower()
    ]
    if len(candidatos) == 1:
        return candidatos[0]

    raise ErroDados(
        "Não foi possível localizar o CSV nacional dentro do ZIP. "
        f"Esperado: {esperado}. Arquivos encontrados: {arquivos_csv[:20]}"
    )


def ler_candidaturas_tse(zip_tse: Path, ano: int) -> pd.DataFrame:
    with zipfile.ZipFile(zip_tse) as zf:
        nome_csv = escolher_csv_brasil(zf, ano)
        print(f"Lendo {nome_csv} dentro do ZIP...")

        # Valida o cabeçalho antes de carregar o arquivo completo.
        with zf.open(nome_csv) as bruto:
            cabecalho = pd.read_csv(
                bruto,
                sep=";",
                encoding="latin1",
                nrows=0,
            )
        ausentes = sorted(set(COLUNAS_TSE) - set(cabecalho.columns))
        if ausentes:
            raise ErroDados(
                "O arquivo do TSE não contém as colunas esperadas: "
                + ", ".join(ausentes)
            )

        with zf.open(nome_csv) as bruto:
            df = pd.read_csv(
                bruto,
                sep=";",
                encoding="latin1",
                usecols=COLUNAS_TSE,
                dtype="string",
                low_memory=False,
            )

    df["ANO_ELEICAO"] = pd.to_numeric(df["ANO_ELEICAO"], errors="coerce").astype("Int64")
    df["NR_TURNO"] = pd.to_numeric(df["NR_TURNO"], errors="coerce").astype("Int64")
    return df


def preparar_resultados_tse(
    df: pd.DataFrame,
    ano: int,
    cargo: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cargo_chave = sem_acentos(cargo)

    recorte = df[
        (df["ANO_ELEICAO"] == ano)
        & (df["NR_TURNO"] == 1)
        & (df["DS_CARGO"].map(sem_acentos) == cargo_chave)
    ].copy()

    if recorte.empty:
        raise ErroDados(
            f"Nenhuma candidatura encontrada para {cargo} no ano {ano}."
        )

    # Protege contra duplicidade acidental por candidatura.
    recorte = recorte.drop_duplicates(subset=["ANO_ELEICAO", "SQ_CANDIDATO"])

    recorte["SG_PARTIDO"] = recorte["SG_PARTIDO"].map(texto_padrao)
    recorte["_PARTIDO_CHAVE"] = recorte["SG_PARTIDO"].map(sem_acentos)
    recorte["GENERO_AGRUPADO"] = recorte["DS_GENERO"].map(classificar_genero)
    recorte["RACA_AGRUPADA"] = recorte["DS_COR_RACA"].map(classificar_raca_tse)
    recorte["RESULTADO_AGRUPADO"] = recorte["DS_SIT_TOT_TURNO"].map(
        classificar_resultado
    )

    auditoria_situacoes = (
        recorte.groupby("DS_SIT_TOT_TURNO", dropna=False)
        .agg(QT_CANDIDATOS=("SQ_CANDIDATO", "nunique"))
        .reset_index()
        .sort_values("QT_CANDIDATOS", ascending=False)
    )

    mascara_valida = (
        recorte["GENERO_AGRUPADO"].notna()
        & recorte["RACA_AGRUPADA"].notna()
        & recorte["RESULTADO_AGRUPADO"].notna()
        & (recorte["_PARTIDO_CHAVE"] != "")
    )

    excluidos = recorte.loc[
        ~mascara_valida,
        [
            "ANO_ELEICAO",
            "SQ_CANDIDATO",
            "SG_PARTIDO",
            "DS_GENERO",
            "DS_COR_RACA",
            "DS_SIT_TOT_TURNO",
            "GENERO_AGRUPADO",
            "RACA_AGRUPADA",
            "RESULTADO_AGRUPADO",
        ],
    ].copy()

    validos = recorte.loc[mascara_valida].copy()
    validos["AA_ELEICAO"] = validos["ANO_ELEICAO"]
    validos["DS_GENERO"] = validos["GENERO_AGRUPADO"]
    validos["DS_COR_RACA"] = validos["RACA_AGRUPADA"]

    agregado = (
        validos.groupby(
            [
                "AA_ELEICAO",
                "SG_PARTIDO",
                "_PARTIDO_CHAVE",
                "DS_GENERO",
                "DS_COR_RACA",
                "RESULTADO_AGRUPADO",
            ],
            dropna=False,
        )["SQ_CANDIDATO"]
        .nunique()
        .rename("QUANTIDADE")
        .reset_index()
    )

    resultado_longo = (
        agregado.pivot_table(
            index=[
                "AA_ELEICAO",
                "SG_PARTIDO",
                "_PARTIDO_CHAVE",
                "DS_GENERO",
                "DS_COR_RACA",
            ],
            columns="RESULTADO_AGRUPADO",
            values="QUANTIDADE",
            fill_value=0,
            aggfunc="sum",
        )
        .reset_index()
        .rename_axis(columns=None)
    )

    for coluna in ["ELEITOS", "SUPLENTES", "NAO_ELEITOS"]:
        if coluna not in resultado_longo.columns:
            resultado_longo[coluna] = 0

    resultado_longo = resultado_longo.rename(
        columns={
            "ELEITOS": "QT_ELEITOS",
            "SUPLENTES": "QT_SUPLENTES",
            "NAO_ELEITOS": "QT_NAO_ELEITOS",
        }
    )
    resultado_longo[COLUNAS_CONTAGEM] = resultado_longo[COLUNAS_CONTAGEM].astype(
        "Int64"
    )

    return resultado_longo, auditoria_situacoes, excluidos


def criar_tabela_partidos(resultado_longo: pd.DataFrame) -> pd.DataFrame:
    df = resultado_longo.copy()

    mapa_grupo = {
        ("MASCULINO", "NEGRA"): "HOMENS_NEGROS",
        ("MASCULINO", "NÃO NEGRA"): "HOMENS_NAO_NEGROS",
        ("FEMININO", "NEGRA"): "MULHERES_NEGRAS",
        ("FEMININO", "NÃO NEGRA"): "MULHERES_NAO_NEGRAS",
    }
    df["GRUPO"] = [
        mapa_grupo.get((genero, raca))
        for genero, raca in zip(df["DS_GENERO"], df["DS_COR_RACA"])
    ]

    partes: list[pd.DataFrame] = []
    nomes_resultado = {
        "QT_ELEITOS": "ELEITOS",
        "QT_SUPLENTES": "SUPLENTES",
        "QT_NAO_ELEITOS": "NAO_ELEITOS",
    }

    for coluna_origem, prefixo in nomes_resultado.items():
        pivot = df.pivot_table(
            index=["AA_ELEICAO", "SG_PARTIDO"],
            columns="GRUPO",
            values=coluna_origem,
            aggfunc="sum",
            fill_value=0,
        )
        pivot.columns = [f"QT_{prefixo}_{grupo}" for grupo in pivot.columns]
        partes.append(pivot)

    tabela = pd.concat(partes, axis=1).reset_index()

    ordem = [
        "AA_ELEICAO",
        "SG_PARTIDO",
        "QT_ELEITOS_HOMENS_NEGROS",
        "QT_ELEITOS_HOMENS_NAO_NEGROS",
        "QT_ELEITOS_MULHERES_NEGRAS",
        "QT_ELEITOS_MULHERES_NAO_NEGRAS",
        "QT_SUPLENTES_HOMENS_NEGROS",
        "QT_SUPLENTES_HOMENS_NAO_NEGROS",
        "QT_SUPLENTES_MULHERES_NEGRAS",
        "QT_SUPLENTES_MULHERES_NAO_NEGRAS",
        "QT_NAO_ELEITOS_HOMENS_NEGROS",
        "QT_NAO_ELEITOS_HOMENS_NAO_NEGROS",
        "QT_NAO_ELEITOS_MULHERES_NEGRAS",
        "QT_NAO_ELEITOS_MULHERES_NAO_NEGRAS",
    ]

    for coluna in ordem:
        if coluna not in tabela.columns:
            tabela[coluna] = 0

    tabela = tabela[ordem].sort_values(["AA_ELEICAO", "SG_PARTIDO"])
    numericas = [c for c in tabela.columns if c.startswith("QT_")]
    tabela[numericas] = tabela[numericas].astype("Int64")
    return tabela


def juntar_fefc_resultados(
    fefc: pd.DataFrame,
    resultado_longo: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    resultado_para_merge = resultado_longo.drop(columns="SG_PARTIDO").copy()

    final = fefc.merge(
        resultado_para_merge,
        on=CHAVES_FINAIS,
        how="left",
        validate="one_to_one",
    )

    for coluna in COLUNAS_CONTAGEM:
        final[coluna] = final[coluna].fillna(0).astype("Int64")

    # Nome mais explícito no produto final, conforme a descrição da planilha.
    final = final.rename(columns={"QT_CANDIDATO": "QT_CANDIDATOS_COM_FEFC"})

    # Coloca as chaves e as contagens próximas umas das outras.
    inicio = [
        "AA_ELEICAO",
        "SG_PARTIDO",
        "NR_PARTIDO",
        "DS_GENERO",
        "DS_COR_RACA",
        "QT_CANDIDATOS_COM_FEFC",
        "QT_ELEITOS",
        "QT_SUPLENTES",
        "QT_NAO_ELEITOS",
    ]
    inicio = [c for c in inicio if c in final.columns]
    restantes = [
        c
        for c in final.columns
        if c not in inicio and not c.startswith("_")
    ]
    final = final[inicio + restantes]

    # Auditorias de chaves sem correspondência.
    chaves_resultado = resultado_longo[CHAVES_FINAIS + ["SG_PARTIDO"]].drop_duplicates()
    chaves_fefc = fefc[CHAVES_FINAIS + ["SG_PARTIDO"]].drop_duplicates()

    tse_sem_fefc = chaves_resultado.merge(
        chaves_fefc[CHAVES_FINAIS],
        on=CHAVES_FINAIS,
        how="left",
        indicator=True,
    )
    tse_sem_fefc = tse_sem_fefc[tse_sem_fefc["_merge"] == "left_only"].drop(
        columns="_merge"
    )

    fefc_sem_tse = chaves_fefc.merge(
        chaves_resultado[CHAVES_FINAIS],
        on=CHAVES_FINAIS,
        how="left",
        indicator=True,
    )
    fefc_sem_tse = fefc_sem_tse[fefc_sem_tse["_merge"] == "left_only"].drop(
        columns="_merge"
    )

    return final, tse_sem_fefc, fefc_sem_tse


def salvar_csv(df: pd.DataFrame, caminho: Path) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(
        caminho,
        sep=";",
        index=False,
        encoding="utf-8-sig",
        decimal=",",
    )


def imprimir_resumo(
    resultado: pd.DataFrame,
    final: pd.DataFrame,
    excluidos: pd.DataFrame,
    tse_sem_fefc: pd.DataFrame,
    fefc_sem_tse: pd.DataFrame,
) -> None:
    totais = resultado[COLUNAS_CONTAGEM].sum()
    print("\nResumo da extração:")
    print(f"  Eleitos por QP ou média: {int(totais['QT_ELEITOS']):,}".replace(",", "."))
    print(f"  Suplentes: {int(totais['QT_SUPLENTES']):,}".replace(",", "."))
    print(f"  Não eleitos: {int(totais['QT_NAO_ELEITOS']):,}".replace(",", "."))
    print(f"  Linhas na base final FEFC + resultados: {len(final):,}".replace(",", "."))
    print(f"  Registros enviados à auditoria: {len(excluidos):,}".replace(",", "."))
    print(f"  Chaves do TSE sem FEFC: {len(tse_sem_fefc)}")
    print(f"  Chaves do FEFC sem TSE: {len(fefc_sem_tse)}")


def analisar_argumentos(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrai eleitos, suplentes e não eleitos por partido, gênero e raça "
            "e junta os resultados a uma planilha agregada de FEFC."
        )
    )
    parser.add_argument(
        "--fefc",
        required=True,
        type=Path,
        help="Caminho do CSV de FEFC, por exemplo fefc_cor_raca_2024.csv.",
    )
    parser.add_argument(
        "--ano",
        type=int,
        default=None,
        help="Ano eleitoral. Se omitido, será lido da coluna AA_ELEICAO do FEFC.",
    )
    parser.add_argument(
        "--tse-zip",
        type=Path,
        default=None,
        help="ZIP consulta_cand do TSE já baixado. Se omitido, o código baixa o arquivo.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="Pasta de saída. Padrão: saida_<ano>.",
    )
    parser.add_argument(
        "--cargo",
        default="VEREADOR",
        help="Cargo analisado. Padrão: VEREADOR.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = analisar_argumentos(argv)

    if not args.fefc.exists():
        raise FileNotFoundError(f"Arquivo de FEFC não encontrado: {args.fefc}")

    print(f"Lendo planilha de FEFC: {args.fefc}")
    fefc = ler_csv_fefc(args.fefc)

    anos_fefc = sorted(fefc["AA_ELEICAO"].dropna().astype(int).unique().tolist())
    if args.ano is None:
        if len(anos_fefc) != 1:
            raise ErroDados(
                "A planilha contém mais de um ano. Informe explicitamente --ano."
            )
        ano = anos_fefc[0]
    else:
        ano = args.ano

    fefc = fefc[fefc["AA_ELEICAO"] == ano].copy()
    if fefc.empty:
        raise ErroDados(f"A planilha de FEFC não possui registros para {ano}.")

    pasta_saida = args.saida or Path(f"saida_{ano}")
    pasta_saida.mkdir(parents=True, exist_ok=True)

    if args.tse_zip is not None:
        zip_tse = args.tse_zip
        if not zip_tse.exists():
            raise FileNotFoundError(f"ZIP do TSE não encontrado: {zip_tse}")
    else:
        zip_tse = baixar_zip_tse(
            ano,
            pasta_saida / "dados_brutos" / f"consulta_cand_{ano}.zip",
        )

    candidaturas = ler_candidaturas_tse(zip_tse, ano)
    resultado, auditoria_situacoes, excluidos = preparar_resultados_tse(
        candidaturas,
        ano=ano,
        cargo=args.cargo,
    )

    tabela_partidos = criar_tabela_partidos(resultado)
    final, tse_sem_fefc, fefc_sem_tse = juntar_fefc_resultados(fefc, resultado)

    salvar_csv(
        resultado.drop(columns="_PARTIDO_CHAVE"),
        pasta_saida / f"resultados_por_partido_genero_raca_{ano}.csv",
    )
    salvar_csv(
        tabela_partidos,
        pasta_saida / f"resultados_abertos_por_partido_{ano}.csv",
    )
    salvar_csv(
        final,
        pasta_saida / f"base_final_fefc_resultados_{ano}.csv",
    )
    salvar_csv(
        auditoria_situacoes,
        pasta_saida / f"auditoria_situacoes_totalizacao_{ano}.csv",
    )
    salvar_csv(
        excluidos,
        pasta_saida / f"auditoria_registros_excluidos_{ano}.csv",
    )
    salvar_csv(
        tse_sem_fefc.drop(columns="_PARTIDO_CHAVE", errors="ignore"),
        pasta_saida / f"auditoria_tse_sem_correspondencia_fefc_{ano}.csv",
    )
    salvar_csv(
        fefc_sem_tse.drop(columns="_PARTIDO_CHAVE", errors="ignore"),
        pasta_saida / f"auditoria_fefc_sem_correspondencia_tse_{ano}.csv",
    )

    imprimir_resumo(resultado, final, excluidos, tse_sem_fefc, fefc_sem_tse)
    print(f"\nArquivos salvos em: {pasta_saida.resolve()}")
    print(
        "A base principal é: "
        f"base_final_fefc_resultados_{ano}.csv"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ErroDados, FileNotFoundError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"\nERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
