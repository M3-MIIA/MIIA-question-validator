# MIIA Question Validator

Pipeline de validação automática de questões discursivas da plataforma MIIA. A ferramenta verifica se o corretor de IA de uma questão está calibrado corretamente, gerando respostas sintéticas em diferentes níveis de qualidade e submetendo-as à API de correção, depois registrando os resultados em uma planilha Google Sheets para revisão humana.

## Como funciona

Para cada questão (identificada por um `integration_id`), o pipeline executa 5 etapas:

1. **Busca no banco** — Recupera o enunciado e os critérios de avaliação da questão no PostgreSQL.
2. **Geração de respostas sintéticas** — Usa um LLM (via LiteLLM) para gerar três tipos de resposta:
   - **Ruim**: deve atingir menos de 35% da nota máxima.
   - **Média**: deve atingir entre 35% e 80% da nota máxima.
   - **Máxima**: deve atingir mais de 80% da nota máxima.
3. **Submissão à API MIIA** — Cada tipo de resposta é submetido 3 vezes (para medir consistência). Também é submetida uma "receita de bolo de cenoura" como resposta completamente fora de contexto — espera-se nota zero.
4. **Coleta de resultados** — O pipeline faz polling da API até os jobs concluírem e coleta as notas.
5. **Validação e registro** — Critérios são verificados e o resultado é inserido na planilha Google Sheets.

### Critérios de validação

| Critério | Condição de aprovação |
|---|---|
| `pass_bolo` | Receita de bolo recebe nota 0 |
| `pass_ruim_var` | Desvio padrão das 3 respostas ruins < 20% da nota máxima |
| `pass_med_var` | Desvio padrão das 3 respostas médias < 20% da nota máxima |
| `pass_max_var` | Desvio padrão das 3 respostas máximas < 20% da nota máxima |
| `pass_min_score` | Média das respostas ruins < 35% da nota máxima |
| `pass_med_score` | 35% ≤ Média das respostas médias ≤ 80% da nota máxima |
| `pass_max_score` | Média das respostas máximas > 80% da nota máxima |

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
DB_PORT=5432
DB_NAME=
DB_USER=
DB_PASSWORD=

# LiteLLM
LITELLM_API_BASE=
LITELLM_API_KEY=
LLM_DEFAULT_MODEL=

# API MIIA
BASE_URL=
MIIA_API_TOKEN=

# Google Sheets
GOOGLE_SHEET_ID=
GOOGLE_SHEET_TAB=
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

Cada linha inserida contém:

| Coluna | Descrição |
|---|---|
| question_id DEV | ID interno da questão |
| Questão (integration_id) | ID de integração |
| Receita de Bolo | Nota da resposta off-topic |
| Ruim 1/2/3 | Notas das 3 respostas ruins |
| Med 1/2/3 | Notas das 3 respostas médias |
| Max 1/2/3 | Notas das 3 respostas máximas |
| Max Score | Nota máxima da questão |
| validada_por | Preenchido manualmente |
| question_id PRD | Preenchido manualmente |
| pass_bolo | True/False |
| pass_ruim_var | True/False |
| pass_med_var | True/False |
| pass_max_var | True/False |
| pass_min_score | True/False |
| pass_med_score | True/False |
| pass_max_score | True/False |
