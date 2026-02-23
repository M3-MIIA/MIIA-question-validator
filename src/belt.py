import db
import gemini
import miia_api
import sheet
from dotenv import load_dotenv

def main():
    print("[1/5] Carregando variáveis de ambiente...")
    load_dotenv()
    
    id_sheet = '1MuU9IjueKS0PXx7Dhs9pofS7I0glRZXn50Girq0SqIo'
    tab_name = 'esteira'
    path_google_json = './auth_google.json' 

    clientMIIA = miia_api.MIIA_API()
    clientGemini = gemini.GeminiClient()
    database = db.Database()
    sheets = sheet.SheetManager(path_google_json, id_sheet, tab_name)

    print("\n[Sucesso] Todos os conectores instanciados! O sistema está pronto.")

    #integration_id = input("\nDigite o ID da integração que deseja validar: ")
    integration_id = 3566470
    database.get_question_structure(integration_id)



if __name__ == "__main__":
    main()