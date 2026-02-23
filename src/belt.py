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
    integration_id = 3565993
    data = database.get_question_structure(integration_id)
    statemet = data["statement"]
    criteria = data["criteria"]
    
    #print(statemet)
    #print("\n")
    #print(criteria)

    content = f""" Veja o seguinte enunciado: {statemet}, que possui os seguinte critérios de avaliacao: {criteria}, me retorne UNICAMENTE UM JSON estruturado da seguinte forma: {{"content": [{{"answer": ""}}]}}. """
    variation_in_grades = ["Produza uma resposta que dado os critérios avaliativos, tire uma nota ruim, não se respondendo adequadamente os critérios avaliativos e comentendo erros de escrita",
                           "Produza uma resposta que dado os critérios avaliativos, tire uma nota média, respondendo parcialmente os critérios avaliativos e comentendo alguns erros de escrita",
                           "Produza uma resposta que gabarite a questão, dados os critérios avaliativos, resultando em uma nota EXCELENTE/MÁXIMA, respondendo adequadamente os critérios avaliativos e sem erros de escrita"]

    history_answers = []

    for grade in variation_in_grades:

        content += f"\n\n{grade}"
        answer = clientGemini.send_prompt(content)
        history_answers.append(answer)
        print(f"\n\n\n\n {answer}")   



if __name__ == "__main__":
    main()