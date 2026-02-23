import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

base_url = os.environ.get("BASE_URL")
token = os.environ.get("MIIA_API_TOKEN")

if not base_url or not token:
    raise ValueError("ERRO CRÍTICO: BASE_URL ou MIIA_API_TOKEN ausentes.")

question_id = 3566470
url_post = f"{base_url}/textual-corrections/v1/discursive/{question_id}/assess"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

payload = {
    "content": [
        {
            "answer": "A) A medida judicial adequada é o Agravo de Petição. Trata-se do recurso cabível contra decisões proferidas pelo Juiz do Trabalho na fase de execução, conforme prevê o Art. 897, alínea 'a', da CLT. B) A tese jurídica é que a prescrição intercorrente no processo do trabalho exige o prazo de 2 anos de inércia do exequente no descumprimento de determinação judicial. Assim, é incabível a extinção com apenas 1 ano, nos termos do Art. 11-A da CLT."
        }
    ]
}

print(f"1. Disparando POST para gerar o Job...")
try:
    resposta_post = requests.post(url_post, headers=headers, json=payload)
    resposta_post.raise_for_status()
    dados_post = resposta_post.json()
    
    # Extrai o ID do ticket retornado
    job_id = dados_post.get("job_id")
    if not job_id:
        raise ValueError("A API não retornou um job_id válido.")
        
    print(f"   [Sucesso] Job criado: {job_id}")

except requests.exceptions.RequestException as e:
    print(f"Falha na requisição POST: {e}")
    if e.response is not None:
        print(e.response.text)
    exit(1)

# ==========================================
# Fase 2: Polling (Verificação do Status)
# ==========================================

url_get = f"{base_url}/textual-corrections/v1/jobs/{job_id}"
print(f"\n2. Iniciando verificação do Job (Polling)...")

tentativas_maximas = 15  # Evita loop infinito (timeout de segurança)
intervalo_segundos = 4   # Tempo de espera entre cada batida na API

for tentativa in range(1, tentativas_maximas + 1):
    try:
        # Note que no GET não enviamos payload (body)
        resposta_get = requests.get(url_get, headers=headers)
        resposta_get.raise_for_status()
        
        dados_get = resposta_get.json()
        status_atual = dados_get.get("status")
        
        if status_atual == "running":
            print(f"   [{tentativa}/{tentativas_maximas}] Status: running. Aguardando {intervalo_segundos}s...")
            time.sleep(intervalo_segundos)
            continue # Pula para a próxima iteração do loop
            
        elif status_atual == "completed" or status_atual == "success": # Ajuste conforme a chave de sucesso exata da sua API
            print("\n[Sucesso Final] Processamento concluído!")
            print("-" * 40)
            print(dados_get) # Aqui estará o seu JSON final correspondente
            print("-" * 40)
            break
            
        elif status_atual == "failed" or status_atual == "error":
            print(f"\n[Erro no Backend] O job falhou internamente: {dados_get}")
            break
            
        else:
            # Captura estados não previstos
            print(f"\n[Aviso] Status desconhecido retornado: '{status_atual}'. Retorno completo: {dados_get}")
            break

    except requests.exceptions.RequestException as e:
        print(f"\nFalha de rede durante o GET: {e}")
        break
else:
    # Este 'else' pertence ao 'for'. Ele só executa se o loop chegar ao fim sem dar 'break'
    print("\n[Timeout] O limite máximo de tentativas foi atingido. O Job demorou demais.")
