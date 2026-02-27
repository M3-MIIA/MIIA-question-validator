# MIIA Question Validator

Pipeline de validação automática de questões discursivas da plataforma MIIA. A ferramenta verifica se o corretor de IA de uma questão está calibrado corretamente, gerando respostas sintéticas em diferentes níveis de qualidade e submetendo-as à API de correção, depois registrando os resultados em uma planilha Google Sheets para revisão humana.

## Como funciona

Para cada questão (identificada por um `integration_id`), o pipeline executa 5 etapas:

1. **Busca no banco** — Recupera o enunciado e os critérios de avaliação da questão no PostgreSQL.
2. **Geração de respostas sintéticas** — Usa um LLM (via LiteLLM) para gerar três tipos de resposta:
   - **Ruim**: deve atingir menos de 35% da nota máxima.
   - **Média**: deve atingir entre 25% e 85% da nota máxima.
   - **Máxima**: deve atingir mais de 80% da nota máxima.
3. **Submissão à API MIIA** — Cada tipo de resposta é submetido 3 vezes (para medir consistência). Também é submetida uma "receita de bolo de cenoura" como resposta completamente fora de contexto — espera-se nota zero.
4. **Coleta de resultados** — O pipeline faz polling da API até os jobs concluírem e coleta as notas.
5. **Validação e registro** — Critérios são verificados e o resultado é inserido na planilha Google Sheets.

### Critérios de validação

| Critério | Condição de aprovação |
|---|---|
| `pass_bolo` | Receita de bolo recebe nota 0 |
| `pass_ruim_var` | Desvio padrão das 3 respostas ruins < `max(20% × max_score, 0.4)` |
| `pass_med_var` | Desvio padrão das 3 respostas médias < `max(20% × max_score, 0.4)` |
| `pass_max_var` | Desvio padrão das 3 respostas máximas < `max(20% × max_score, 0.4)` |
| `pass_min_score` | Média das respostas ruins < 35% da nota máxima |
| `pass_med_score` | Ver regra detalhada abaixo |
| `pass_max_score` | Média das respostas máximas > 80% da nota máxima |

#### Detalhamento: `pass_ruim_var` / `pass_med_var` / `pass_max_var`

O threshold de variância é adaptativo: `max(20% × max_score, 0.4)`. Isso significa que em questões de escala grande (ex: max_score = 10) o limite aceito é 2.0 pontos; em questões de escala pequena (ex: max_score = 1) o piso de 0.4 evita que o critério fique impossível de atingir. O objetivo é detectar inconsistência do corretor: se as 3 submissões da mesma resposta divergem muito entre si, o correto não está se comportando de forma determinística.

#### Detalhamento: `pass_med_score`

A regra verifica se o corretor consegue distinguir uma resposta mediana de uma resposta ruim e de uma excelente. A aprovação ocorre se **pelo menos uma** das condições abaixo for verdadeira:

1. A **média** das 3 notas medianas está entre 25% e 85% do `max_score`.
2. A **mediana** das 3 notas medianas está entre 25% e 85% do `max_score`.
3. A **maioria** (≥ 2 de 3) dos scores individuais está entre 25% e 85% do `max_score`.

**Escape hatch — corretor com espaço parcial de nota:** se todas as 3 respostas medianas receberem exatamente `max_score`, a regra verifica se existe ao menos um score entre os 9 totais (ruim×3 + med×3 + max×3) que seja diferente de 0 e diferente de `max_score`. Se sim, o corretor é capaz de notas parciais e alguma anomalia gerou o resultado — retorna `True`. Se todos os 9 scores são binários (apenas 0 ou `max_score`), o corretor não possui granularidade parcial e `pass_med_score` retorna `False`, pois não há como gerar uma resposta genuinamente mediana para essa questão.

> **Por que maioria e não unanimidade?** O LLM pode ocasionalmente errar a calibração em uma das 3 submissões. Exigir unanimidade tornaria o critério muito rígido; exigir apenas 1 de 3 seria permissivo demais. A maioria (2/3) é o equilíbrio razoável.

## Estrutura do projeto

```
miia-question-validator/
├── src/
│   ├── main.py        # Ponto de entrada: lê ids.txt e executa o pipeline
│   ├── belt.py        # Lógica central do pipeline por questão
│   ├── validator.py   # Critérios de validação das notas
│   ├── db.py          # Conexão com PostgreSQL e busca da estrutura da questão
│   ├── liteLLM.py     # Cliente LiteLLM para geração de respostas sintéticas
│   ├── miia_api.py    # Cliente da API MIIA (criação de job + polling)
│   ├── sheet.py       # Integração com Google Sheets
│   └── gemini.py      # Cliente Gemini direto (não utilizado no fluxo atual)
├── ids.txt            # Lista de integration_ids a processar (um por linha)
├── auth_google.json   # Credenciais da service account Google (não versionado)
├── .env               # Variáveis de ambiente (não versionado)
└── pyproject.toml
```

## Pré-requisitos

- Python 3.13+
- Acesso ao banco de dados PostgreSQL da MIIA
- Token de acesso à API MIIA
- Instância LiteLLM configurada (com modelo acessível)
- Service account Google com acesso à planilha de destino

## Instalação

```bash
# Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate

# Instale as dependências
pip install -e .
```

## Configuração

Crie um arquivo `.env` na raiz do projeto:

```env
# Banco de dados
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=

# LiteLLM
LITELLM_API_BASE=
LITELLM_API_KEY=
LLM_DEFAULT_MODEL=
LLM_TEMPERATURE=0.1      # temperatura padrão (pode ser sobrescrita por chamada)
LLM_MAX_TOKENS=          # opcional
LLM_TIMEOUT=             # opcional, em segundos

# API MIIA
BASE_URL=
MIIA_API_TOKEN=
TENANT_ID=XX             # tenant vinculado às questões, importante para pré validaćão

# Google Sheets
GOOGLE_SHEET_ID=
GOOGLE_SHEET_TAB=        # aba de resultados resumidos (ex: esteira)
GOOGLE_SHEET_TAB_LOG=    # aba de log completo em JSON (ex: esteira_log)
```

Coloque o arquivo `auth_google.json` da service account Google na raiz do projeto.

## Uso

1. Adicione os `integration_id`s das questões a validar no arquivo `ids.txt` (um por linha):

```
3566465
3566466
3566467
```

2. Execute o pipeline:

```bash
python src/main.py
```

O pipeline processa cada questão sequencialmente, exibindo o progresso no terminal, e insere uma linha de resultado na planilha Google Sheets ao final de cada questão.

## Saída na planilha

O pipeline escreve em duas abas configuradas via `.env`:

### Aba principal (`GOOGLE_SHEET_TAB`) — resultados resumidos

Cada linha inserida contém:

| Coluna | Descrição |
|---|---|
| question_id DEV | ID interno da questão no banco de dev |
| Questão (integration_id) | ID de integração |
| Receita de Bolo | Nota da resposta off-topic (esperado: 0) |
| Ruim 1/2/3 | Notas das 3 respostas ruins |
| Med 1/2/3 | Notas das 3 respostas médias |
| Max 1/2/3 | Notas das 3 respostas máximas |
| Max Score | Nota máxima da questão |
| question_id PRD | Preenchido manualmente após homologação |
| validada_por | Preenchido manualmente |
| pass_bolo | True/False/None |
| pass_ruim_var | True/False/None |
| pass_med_var | True/False/None |
| pass_max_var | True/False/None |
| pass_min_score | True/False/None |
| pass_med_score | True/False/None |
| pass_max_score | True/False/None |
| log_erro | Mensagem de erro, se houver |
| created_at | Timestamp de execução |

> `None` indica que o cálculo não foi possível (dados insuficientes ou `max_score` ausente).

### Aba de log (`GOOGLE_SHEET_TAB_LOG`) — JSONs completos

Registra o payload completo retornado pela API MIIA para cada um dos 10 jobs (bolo + ruim×3 + med×3 + max×3), útil para depuração e auditoria.
