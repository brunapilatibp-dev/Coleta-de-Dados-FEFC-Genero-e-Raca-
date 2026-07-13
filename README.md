# Coleta-de-Dados-FEFC-Genero-e-Raca-
Scripts em Python para integrar dados de FEFC e resultados eleitorais do TSE de 2020 e 2024, com recortes por partido, gênero, raça e situação eleitoral.
O projeto permite analisar comparativamente a distribuição de recursos eleitorais por:

- ano eleitoral;
- partido político;
- gênero;
- grupo racial;
- candidaturas eleitas;
- candidaturas suplentes;
- candidaturas não eleitas.


## Fonte dos dados

Os dados utilizados são disponibilizados pelo Tribunal Superior Eleitoral (TSE), por meio do Portal de Dados Abertos.

### Eleições de 2020

- [Página oficial — Prestação de Contas Eleitorais 2020](https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-2020)
- [Download direto — Fundo Partidário e FEFC 2020](https://cdn.tse.jus.br/estatistica/sead/odsele/fefc_fp/fefc_fp_2020.zip)

### Eleições de 2024

- [Página oficial — Prestação de Contas Eleitorais 2024](https://dadosabertos.tse.jus.br/dataset/prestacao-de-contas-eleitorais-2024)
- [Download direto — Fundo Partidário e FEFC 2024](https://cdn.tse.jus.br/estatistica/sead/odsele/fefc_fp/fefc_fp_2024.zip)

## Arquivos que devem ser baixados manualmente

Os arquivos de FEFC e Fundo Partidário não são baixados automaticamente pelos scripts deste repositório.

Antes da execução:

1. Baixe o ZIP do ano correspondente no Portal de Dados Abertos do TSE.
2. Extraia o conteúdo do arquivo ZIP.
3. Localize o arquivo:
   - `fefc_cor_raca_2020.csv`, para a eleição de 2020;
   - `fefc_cor_raca_2024.csv`, para a eleição de 2024.
4. Copie o CSV para a pasta principal do projeto.

Os arquivos de candidaturas `consulta_cand_2020.zip` e `consulta_cand_2024.zip` são baixados automaticamente pelos scripts, caso ainda não estejam disponíveis localmente.

## Estrutura recomendada do projeto

```text
projeto_tse_fefc/
├── extrair_resultados_tse_fefc.py
├── extrair_resultados_tse_fefc_2020.py
├── juntar_bases_2020_2024.py
├── fefc_cor_raca_2020.csv
├── fefc_cor_raca_2024.csv
├── saida_2020/
└── saida_2024/
```

## Requisitos

- Python 3.10 ou superior;
- `pandas`;
- `requests`.


## Uso de um ZIP de candidaturas já baixado

Por padrão, o script baixa automaticamente o arquivo de candidaturas do TSE. Caso o ZIP já esteja disponível, informe seu caminho com `--tse-zip`.

Exemplo para 2020:

```bash
python extrair_resultados_tse_fefc_2020.py \
  --fefc "fefc_cor_raca_2020.csv" \
  --tse-zip "consulta_cand_2020.zip"
```

## Cargo analisado

O cargo padrão é `VEREADOR`.

Para indicar outro cargo, use o argumento `--cargo`:

```bash
python extrair_resultados_tse_fefc.py \
  --fefc "fefc_cor_raca_2024.csv" \
  --ano 2024 \
  --cargo "VEREADOR"
```

## Classificações utilizadas

### Gênero

São considerados os registros classificados pelo TSE como:

- `FEMININO`;
- `MASCULINO`.

Registros com gênero não reconhecido são enviados para os arquivos de auditoria.

### Grupo racial

As categorias são agrupadas da seguinte forma:

- **Negra:** candidaturas declaradas `PRETA` ou `PARDA`;
- **Não negra:** candidaturas declaradas `BRANCA`, `AMARELA` ou `INDÍGENA`.

Registros sem classificação racial reconhecida não são forçados para nenhum grupo e são enviados para auditoria.

### Resultado eleitoral

As situações são agrupadas da seguinte forma:

- **Eleitos:** `ELEITO POR QP` e `ELEITO POR MÉDIA`;
- **Suplentes:** `SUPLENTE`;
- **Não eleitos:** `NÃO ELEITO`.

As demais situações são mantidas nos arquivos de auditoria.

## Arquivos gerados em cada ano

O processamento gera os seguintes arquivos:

```text
resultados_por_partido_genero_raca_<ano>.csv
resultados_abertos_por_partido_<ano>.csv
base_final_fefc_resultados_<ano>.csv
auditoria_situacoes_totalizacao_<ano>.csv
auditoria_registros_excluidos_<ano>.csv
auditoria_tse_sem_correspondencia_fefc_<ano>.csv
auditoria_fefc_sem_correspondencia_tse_<ano>.csv
```

### Base principal

O arquivo principal de cada ano é:

```text
base_final_fefc_resultados_<ano>.csv
```

Ele combina os dados de FEFC com as seguintes contagens:

- `QT_CANDIDATOS_COM_FEFC`;
- `QT_ELEITOS`;
- `QT_SUPLENTES`;
- `QT_NAO_ELEITOS`.

## União das bases de 2020 e 2024

Depois de gerar as duas bases anuais, execute:

```bash
python juntar_bases_2020_2024.py
```

O script procura, por padrão, os arquivos:

```text
saida_2020/base_final_fefc_resultados_2020.csv
saida_2024/base_final_fefc_resultados_2024.csv
```

A base comparativa será criada com o nome:

```text
base_comparativa_fefc_2020_2024.csv
```

A união é vertical: as linhas de 2020 são acrescentadas às linhas de 2024. A coluna `AA_ELEICAO` identifica o ano de cada registro.
