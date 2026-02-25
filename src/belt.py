import os
import json
import db
import liteLLM
import miia_api
import sheet
import validator
import time
from dotenv import load_dotenv


def submit_n_times(client, integration_id, answer, n, delay=1):
    jobs = []
    for _ in range(n):
        job = client.create_job(integration_id, answer)
        jobs.append(job)
        time.sleep(delay)
    return jobs


def collect_scores(client, jobs, print_first=False):
    scores = []
    assessments = []
    for i, job in enumerate(jobs):
        assessment = client.check_status(job, verbose=(print_first and i == 0))
        assessments.append(assessment)
        score = assessment["result"]["score"] if assessment else None
        scores.append(score)
    return scores, assessments


def run(integration_id, clientMIIA, clientLLM, database, sheets, sheets_log=None):
    print(f"\n{'='*60}")
    print(f"Processando integration_id: {integration_id}")
    print(f"{'='*60}")

    question_id = None
    bolo_score = None
    ruim_scores = [None, None, None]
    med_scores  = [None, None, None]
    max_scores  = [None, None, None]
    max_score   = None
    row_written = False

    try:
        data = database.get_question_structure(integration_id)
        question_id = data["question_id"]
        statement = data["statement"]
        criteria = data["criteria"]

        # --- Geração das respostas sintéticas ---
        base_prompt = f""" Veja o seguinte enunciado: {statement}, que possui os seguintes critérios de avaliacao: {criteria}, me retorne UNICAMENTE UM JSON estruturado da seguinte forma: {{"content": [{{"answer": ""}}]}}. SEM ```json ... ```"""

        cake_recipe = """{"content":[{"answer": "Preparar um bolo de cenoura com cobertura de chocolate é uma prática culinária bastante comum nos lares brasileiros, sendo associada a momentos de convivência e simplicidade. A receita, apesar de tradicional, exige atenção a alguns detalhes para que o resultado final seja macio e saboroso.\n\nInicialmente, é necessário separar os ingredientes básicos, como cenouras, ovos, óleo, açúcar e farinha de trigo. As cenouras devem ser descascadas, cortadas em pedaços pequenos e batidas no liquidificador juntamente com os ovos e o óleo, até que se obtenha uma mistura homogênea. Em seguida, adiciona-se o açúcar e bate-se novamente, garantindo que todos os componentes estejam bem incorporados.\n\nApós esse processo, a mistura líquida deve ser transferida para um recipiente maior, no qual se acrescenta a farinha de trigo peneirada, mexendo-se cuidadosamente para evitar a formação de grumos. Por fim, adiciona-se o fermento químico em pó, misturando de forma delicada. A massa é então despejada em uma forma untada e levada ao forno preaquecido, onde deve assar até atingir consistência firme.\n\nEnquanto o bolo assa, pode-se preparar a cobertura, utilizando ingredientes simples como chocolate em pó, açúcar, manteiga e leite. Esses elementos devem ser levados ao fogo baixo, mexendo-se constantemente até formar uma calda lisa. Após retirar o bolo do forno, basta espalhar a cobertura ainda quente sobre a massa.\n\nDessa forma, o bolo de cenoura com chocolate destaca-se como uma receita prática e acessível, adequada tanto para o consumo cotidiano quanto para ocasiões especiais, demonstrando que a culinária pode ser, ao mesmo tempo, funcional e prazerosa."}]}"""

        prompt_ruim = (
            base_prompt +
            "\n\nGere uma resposta PÉSSIMA, com expectativa de obter menos de 30% da pontuação máxima. "
            "REGRAS OBRIGATÓRIAS:\n"
            "- NÃO atenda nenhum dos critérios de avaliação listados — ignore todos completamente\n"
            "- NÃO demonstre nenhum conhecimento técnico ou específico sobre o tema\n"
            "- Aborde o assunto de forma genérica e vaga, como alguém que nunca estudou o tema\n"
            "- NÃO use termos técnicos, nomes de leis, políticas públicas, conceitos da área ou qualquer nomenclatura específica\n"
            "- Cometa erros graves de escrita: concordância errada, frases incompletas, repetição de palavras\n"
            "- A resposta deve ser muito curta (2 a 3 frases no máximo) e sem nenhuma argumentação\n"
            "- NÃO proponha nenhuma solução, encaminhamento ou sugestão — apenas afirmações vagas e incorretas\n"
            "- Demonstre completo desconhecimento do assunto."
        )
        prompt_max = (
            base_prompt +
            "\n\nGere uma resposta EXCELENTE E MÁXIMA que gabarite a questão, atingindo a nota mais alta possível. "
            "Para isso: atenda TODOS os critérios de avaliação listados acima de forma completa, precisa e aprofundada; "
            "demonstre domínio pleno do tema com argumentação sólida, bem fundamentada e exemplos pertinentes; "
            "escreva com clareza, coesão e sem nenhum erro gramatical; "
            "a resposta deve ser impecável, bem estruturada e tecnicamente perfeita em todos os pontos avaliados."
        )

        print("\n[2/5] Gerando respostas sintéticas...")
        ruim_answer = clientLLM.send_prompt(prompt_ruim)
        max_answer  = clientLLM.send_prompt(prompt_max)

        prompt_med = (
            f"Veja o seguinte enunciado: {statement}, com os seguintes critérios de avaliação: {criteria}\n\n"
            f"Gere uma resposta MEDIANA que deve obter entre 30% e 55% da pontuação máxima. "
            f"REGRAS OBRIGATÓRIAS — siga à risca:\n"
            f"- Aborde NO MÁXIMO 2 dos critérios de avaliação listados — ignore todos os demais completamente, mesmo que sejam centrais\n"
            f"- Mesmo os 2 critérios escolhidos devem ser tratados de forma RASA e INCOMPLETA: cubra menos da metade do que seria esperado para cada um\n"
            f"- NÃO demonstre domínio técnico: evite termos específicos da área, leis, normas, conceitos técnicos ou terminologia especializada\n"
            f"- Use apenas afirmações genéricas, vagas e sem fundamentação — sem exemplos concretos, sem dados, sem embasamento\n"
            f"- NÃO proponha soluções ou encaminhamentos específicos\n"
            f"- Cometa alguns erros gramaticais e use estrutura de texto pouco refinada\n"
            f"me retorne UNICAMENTE UM JSON estruturado da seguinte forma: {{\"content\": [{{\"answer\": \"\"}}]}}. SEM ```json ... ```"
        )
        med_answer  = clientLLM.send_prompt(prompt_med, temperature=0.7)

        # --- Submissão para a API da MIIA ---
        print("\n[3/5] Submetendo respostas para correção...")
        bolo_job  = submit_n_times(clientMIIA, integration_id, cake_recipe, n=1)[0]
        ruim_jobs = submit_n_times(clientMIIA, integration_id, ruim_answer, n=3)
        med_jobs  = submit_n_times(clientMIIA, integration_id, med_answer,  n=3)
        max_jobs  = submit_n_times(clientMIIA, integration_id, max_answer,  n=3)

        # --- Coleta dos resultados ---
        print("\n[4/5] Aguardando e coletando resultados...")
        bolo_assessment = clientMIIA.check_status(bolo_job, verbose=False)
        bolo_score = bolo_assessment["result"]["score"] if bolo_assessment else None

        ruim_scores, ruim_assessments = collect_scores(clientMIIA, ruim_jobs, print_first=True)
        med_scores,  med_assessments  = collect_scores(clientMIIA, med_jobs,  print_first=True)
        max_scores,  max_assessments  = collect_scores(clientMIIA, max_jobs,  print_first=True)

        ref_assessment = bolo_assessment or (max_assessments[-1] if max_assessments else None)
        max_score = ref_assessment["result"]["max_score"] if ref_assessment else None

        print(f"\nScores — bolo: {bolo_score} | ruim: {ruim_scores} | med: {med_scores} | max: {max_scores} | max_score: {max_score}")

        # --- Validação e inserção na planilha ---
        print("\n[5/5] Inserindo resultado na planilha...")
        v = validator.Validator()
        row = v.build_row(
            question_id=question_id,
            integration_id=integration_id,
            bolo_score=bolo_score,
            ruim_scores=ruim_scores,
            med_scores=med_scores,
            max_scores=max_scores,
            max_score=max_score,
        )
        sheets.insert_line(row)
        row_written = True
        print(f"[Concluído] {integration_id} inserido na planilha com sucesso.")

        # --- Log detalhado na aba esteira_log ---
        if sheets_log:
            def _dump(a):
                return json.dumps(a, ensure_ascii=False) if a else ""

            def _at(lst, i):
                return lst[i] if lst and len(lst) > i else None

            log_row = [
                integration_id,
                _dump(bolo_assessment),
                _dump(_at(ruim_assessments, 0)),
                _dump(_at(ruim_assessments, 1)),
                _dump(_at(ruim_assessments, 2)),
                _dump(_at(med_assessments,  0)),
                _dump(_at(med_assessments,  1)),
                _dump(_at(med_assessments,  2)),
                _dump(_at(max_assessments,  0)),
                _dump(_at(max_assessments,  1)),
                _dump(_at(max_assessments,  2)),
            ]
            sheets_log.insert_line(log_row)
            print(f"[Log] Detalhamento registrado em esteira_log para {integration_id}.")

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        print(f"[ERRO] Falha em {integration_id}: {error_msg}")
        if not row_written:
            v = validator.Validator()
            partial_row = v.build_row(
                question_id=question_id,
                integration_id=integration_id,
                bolo_score=bolo_score,
                ruim_scores=ruim_scores,
                med_scores=med_scores,
                max_scores=max_scores,
                max_score=max_score,
                error_log=error_msg,
            )
            try:
                sheets.insert_line(partial_row)
                print(f"[ERRO] Linha de erro registrada na planilha para {integration_id}.")
            except Exception as sheet_err:
                print(f"[ERRO] Não foi possível registrar erro na planilha: {sheet_err}")
        raise


def main():
    load_dotenv()

    id_sheet = os.environ.get("GOOGLE_SHEET_ID")
    tab_name = os.environ.get("GOOGLE_SHEET_TAB")
    path_google_json = './auth_google.json'

    clientMIIA = miia_api.MIIA_API()
    clientLLM = liteLLM.LiteLLMClient()
    database = db.Database()
    sheets = sheet.SheetManager(path_google_json, id_sheet, tab_name)

    print("[Sucesso] Todos os conectores instanciados! O sistema está pronto.")

    run("3566465", clientMIIA, clientLLM, database, sheets)


if __name__ == "__main__":
    main()
