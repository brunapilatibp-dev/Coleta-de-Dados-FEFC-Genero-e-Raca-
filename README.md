# FEFC, Gênero e Raça: Desempenho Eleitoral de Vereadores (2020–2024)

Base comparativa do FEFC, perfil e desempenho eleitoral de candidaturas a vereador e prefeito, com recorte de gênero e raça, comparando os ciclos eleitorais de 2020 e 2024.

## Objetivo

Verificar se a destinação de recursos do **FEFC (Fundo Especial de Financiamento de Campanha)** às candidaturas de **mulheres e pessoas negras** apresenta relação com o desempenho eleitoral e com o número de candidaturas eleitas para vereador, comparando 2020 e 2024 em todos os partidos.

---

## Fonte dos dados

Todos os dados eleitorais foram obtidos do portal de **dados abertos do TSE**:

> [https://dadosabertos.tse.jus.br](https://dadosabertos.tse.jus.br)

Arquivo utilizado: `consulta_cand_{ano}.zip` — contém o cadastro de todos os candidatos registrados, incluindo situação final (eleito/não eleito), gênero e cor/raça autodeclarados.

---

## Estrutura do repositório

```
.
├── scripts/
│   ├── 01_vereadores_eleitos.py       # Extrai vereadores eleitos do TSE
│   ├── 02_prefeitos_eleitos.py        # Extrai prefeitos eleitos do TSE
│   └── 03_agregado_genero_raca.py     # Agrega por partido, gênero e raça
│
├── vereadores_eleitos_2020_2024.csv               # Base individual de vereadores eleitos
├── prefeitos_eleitos_2020_2024.csv                # Base individual de prefeitos eleitos
├── vereadores_genero_raca_partido_2020_2024.csv   # Agregado vereadores
├── prefeitos_genero_raca_partido_2020_2024.csv    # Agregado prefeitos
├── fefc_interseccional_2020_2024.csv              # Taxa de eleição por grupo interseccional
└── base_fefc_desempenho_vereador_2020_2024.xls    # Base analítica completa (FEFC + desempenho)
```

---

## Bases geradas

### `vereadores_eleitos_2020_2024.csv` e `prefeitos_eleitos_2020_2024.csv`
Cadastro individual dos eleitos. Uma linha por candidato.

| Coluna | Descrição |
|---|---|
| `ANO_ELEICAO` | Ano da eleição (2020 ou 2024) |
| `SG_UF` | Estado |
| `NM_UE` | Município |
| `SG_PARTIDO` / `NM_PARTIDO` | Sigla e nome do partido |
| `NM_CANDIDATO` | Nome completo |
| `NM_URNA_CANDIDATO` | Nome de urna |
| `DS_GENERO` | Gênero autodeclarado (MASCULINO / FEMININO) |
| `DS_COR_RACA` | Cor/raça autodeclarada (BRANCA / PARDA / PRETA / AMARELA / INDÍGENA) |
| `DS_SIT_TOT_TURNO` | Situação final (ELEITO POR QP / ELEITO POR MÉDIA) |

### `vereadores_genero_raca_partido_2020_2024.csv` e `prefeitos_genero_raca_partido_2020_2024.csv`
Versão agregada. Uma linha por combinação de ano + partido + gênero + raça.

| Coluna | Descrição |
|---|---|
| `ANO_ELEICAO` | Ano da eleição |
| `SG_PARTIDO` / `NM_PARTIDO` | Partido |
| `DS_GENERO` | Gênero |
| `DS_COR_RACA` | Cor/raça |
| `VEREADORES_ELEITOS` / `PREFEITOS_ELEITOS` | Total de eleitos no grupo |

### `fefc_interseccional_2020_2024.csv`
Desempenho eleitoral por grupo interseccional (combinação de gênero e raça), partido e ano.

| Coluna | Descrição |
|---|---|
| `ANO_ELEICAO` | Ano da eleição |
| `PARTIDO` | Sigla do partido |
| `GRUPO_INTERSECCIONAL` | Ex.: Mulher Negra, Homem Não Negro |
| `CANDIDATOS` | Total de candidatos no grupo |
| `ELEITOS` | Total de eleitos |
| `NAO_ELEITOS` | Total de não eleitos |
| `TAXA_ELEICAO_PCT` | Taxa de eleição (%) |

> **Critério**: "Negro/a" = Preto/a + Pardo/a, conforme classificação do IBGE.

---

## Como reproduzir

Requisitos: Python 3.9+ com `pandas` e `requests`.

```bash
pip install pandas requests

# 1. Baixar e extrair os dados do TSE
python scripts/01_vereadores_eleitos.py
python scripts/02_prefeitos_eleitos.py

# 2. Gerar as tabelas agregadas por gênero e raça
python scripts/03_agregado_genero_raca.py
```

Os scripts baixam os dados direto do CDN do TSE (~85 MB por ano) e salvam os CSVs na pasta raiz do projeto.

---

## Números gerais

| | Vereadores 2020 | Vereadores 2024 | Prefeitos 2020 | Prefeitos 2024 |
|---|---|---|---|---|
| **Total eleitos** | 58.192 | 58.174 | 5.601 | 5.568 |
| **Mulheres** | ~17% | ~17% | ~12% | ~13% |
| **Pessoas negras** (pretas + pardas) | ~46% | ~46% | ~33% | ~33% |

---

## Licença

Dados públicos, originados do TSE sob licença aberta (Lei de Acesso à Informação — Lei 12.527/2011).
Scripts disponibilizados para fins acadêmicos e de pesquisa.
