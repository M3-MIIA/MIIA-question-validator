import gspread
from google.oauth2.service_account import Credentials

escopos = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Substitua pelo nome exato do arquivo JSON que você baixou do Google Cloud
caminho_json = "credenciais_google.json" 
credenciais = Credentials.from_service_account_file(caminho_json, scopes=escopos)

cliente = gspread.authorize(credenciais)

try:
    # ID extraído da sua URL
    id_planilha = "1MuU9IjueKS0PXx7Dhs9pofS7I0glRZXn50Girq0SqIo"
    planilha = cliente.open_by_key(id_planilha)
    
    # Buscando a aba exata pelo nome
    aba = planilha.worksheet("esteira")

    # Inserindo uma nova linha. Cada item da lista cai em uma coluna (A, B, C...)
    valores_para_inserir = ["Teste Coluna A", "Teste Coluna B", "Teste Coluna C"]
    aba.append_row(valores_para_inserir)
    
    print("Linha inserida com sucesso na Página1!")

except Exception as e:
    print(f"Erro na execução: {e}")
