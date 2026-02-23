import db
import liteLLM
import miia_api
import sheet
import time
from dotenv import load_dotenv

def main():
    print("[1/5] Carregando variáveis de ambiente...")
    load_dotenv()
    
    id_sheet = '1MuU9IjueKS0PXx7Dhs9pofS7I0glRZXn50Girq0SqIo'
    tab_name = 'esteira'
    path_google_json = './auth_google.json' 

    clientMIIA = miia_api.MIIA_API()
    clientLLM = liteLLM.LiteLLMClient()
    database = db.Database()
    sheets = sheet.SheetManager(path_google_json, id_sheet, tab_name)

    print("\n[Sucesso] Todos os conectores instanciados! O sistema está pronto.")

    #integration_id = input("\nDigite o ID da integração que deseja validar: ")
    integration_id = "CEISC_SIM_05_PC-RS_M-Q6" 
    data = database.get_question_structure(integration_id)
    statemet = data["statement"]
    criteria = data["criteria"]
    
    #print(statemet)
    #print("\n")
    #print(criteria)

    # Gera as respostas sintéticas em 3 níveis de completude esperados para rotas
    content = f""" Veja o seguinte enunciado: {statemet}, que possui os seguinte critérios de avaliacao: {criteria}, me retorne UNICAMENTE UM TEXTO estruturado da seguinte forma: {{"content": [{{"answer": ""}}]}}. OU SEJA, UM JSON as SEM ´´´json .... ´´´"""
    variation_in_grades = ["Produza uma resposta que dado os critérios avaliativos, tire uma nota ruim, não se respondendo adequadamente os critérios avaliativos e comentendo erros de escrita",
                           "Produza uma resposta que dado os critérios avaliativos, tire uma nota média, respondendo parcialmente os critérios avaliativos e comentendo alguns erros de escrita",
                           "Produza uma resposta que gabarite a questão, dados os critérios avaliativos, resultando em uma nota EXCELENTE/MÁXIMA, respondendo adequadamente os critérios avaliativos e sem erros de escrita"]
    history_answers = []
    cake_recipe="""{"content":[{"answer": "Preparar um bolo de cenoura com cobertura de chocolate é uma prática culinária bastante comum nos lares brasileiros, sendo associada a momentos de convivência e simplicidade. A receita, apesar de tradicional, exige atenção a alguns detalhes para que o resultado final seja macio e saboroso.\n\nInicialmente, é necessário separar os ingredientes básicos, como cenouras, ovos, óleo, açúcar e farinha de trigo. As cenouras devem ser descascadas, cortadas em pedaços pequenos e batidas no liquidificador juntamente com os ovos e o óleo, até que se obtenha uma mistura homogênea. Em seguida, adiciona-se o açúcar e bate-se novamente, garantindo que todos os componentes estejam bem incorporados.\n\nApós esse processo, a mistura líquida deve ser transferida para um recipiente maior, no qual se acrescenta a farinha de trigo peneirada, mexendo-se cuidadosamente para evitar a formação de grumos. Por fim, adiciona-se o fermento químico em pó, misturando de forma delicada. A massa é então despejada em uma forma untada e levada ao forno preaquecido, onde deve assar até atingir consistência firme.\n\nEnquanto o bolo assa, pode-se preparar a cobertura, utilizando ingredientes simples como chocolate em pó, açúcar, manteiga e leite. Esses elementos devem ser levados ao fogo baixo, mexendo-se constantemente até formar uma calda lisa. Após retirar o bolo do forno, basta espalhar a cobertura ainda quente sobre a massa.\n\nDessa forma, o bolo de cenoura com chocolate destaca-se como uma receita prática e acessível, adequada tanto para o consumo cotidiano quanto para ocasiões especiais, demonstrando que a culinária pode ser, ao mesmo tempo, funcional e prazerosa."}]}"""

    history_answers.append(cake_recipe)
    for grade in variation_in_grades:
        current_content = content + f"\n\n{grade}"
        answer = clientLLM.send_prompt(current_content)
        history_answers.append(answer)
        print(f"{answer}\n\n\n\n ")   


    # Manda para a api da MIIA corrigir (POST)
    history_jobs = []
    for i in range(len(history_answers)):
        current_job = clientMIIA.create_job(integration_id, history_answers[i])
        history_jobs.append(current_job)
        time.sleep(1)

    history_assessments = []
    for job in history_jobs:
        assessment = clientMIIA.check_status(job)
        history_assessments.append(assessment)
        print(f"{assessment} \n\n\n\n\n")


if __name__ == "__main__":
    main()
