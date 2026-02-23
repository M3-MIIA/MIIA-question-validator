import os
import psycopg
from google import genai
from dotenv import load_dotenv

# Força o Python a ler e injetar o .env na memória do processo instantaneamente
load_dotenv()

# Agora o os.environ.get() tem garantia de funcionamento
api_key = os.environ.get("GEMINI_API_KEY")
db_host = os.environ.get("DB_HOST")
db_port = os.environ.get("DB_PORT", "5432") # Puxa a porta 5432 como fallback se não achar
db_name = os.environ.get("DB_NAME")
db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASSWORD")

# Fail-Fast
variaveis_banco = [db_host, db_name, db_user, db_pass]
if not all(variaveis_banco):
    raise ValueError("ERRO CRÍTICO: Faltam variáveis do banco no arquivo .env.")

conn_info = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_pass}"
# ... o resto do seu Context Manager de conexão continua igual

# 2. Conecta ao PostgreSQL garantindo o fechamento automático (Context Manager)
try:
    with psycopg.connect(conn_info) as conn:
        with conn.cursor() as cur:
            # Substitua pela sua tabela real de questões
            cur.execute("SELECT id, statement FROM question LIMIT 3;")
            registros = cur.fetchall()
            
            # 3. Constrói o conteúdo dinâmico (Prompt Engineering)
            prompt_base = "Avalie as seguintes questões e aponte se há erros gramaticais ou lógicos:\n\n"
            
            for linha in registros:
                questao_id = linha[0]
                enunciado = linha[1]
                prompt_base += f"Questão {questao_id}: {enunciado}\n"

except Exception as e:
    print(f"Erro no Banco de Dados: {e}")
    exit(1)

# 4. Envia o texto montado para o Gemini
print("Enviando prompt para o Gemini...")
print("-" * 30)
print(prompt_base)
print("-" * 30)

client = genai.Client(api_key=api_key)

try:
    resposta = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt_base
    )
    print("\nRetorno da API:")
    print(resposta.text)

except Exception as e:
    print(f"Erro ao se comunicar com a API do Gemini: {e}")
