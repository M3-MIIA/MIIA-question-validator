import os
import json
import db
import liteLLM
import miia_api
import sheet
import validator
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv


def submit_n_times(client, integration_id, answer, n, delay=0.5):
    jobs = []
    for _ in range(n):
        job = client.create_job(integration_id, answer)
        jobs.append(job)
        time.sleep(delay)
    return jobs


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
            "\n\nGere uma resposta RUIM que deve obter menos de 35% da pontuação máxima. "
            "REGRAS OBRIGATÓRIAS:\n"
            "- Trate o tema de forma completamente superficial, como alguém que tem noção vaga do assunto mas não estudou\n"
            "- NÃO atenda nenhum dos critérios de avaliação de forma satisfatória — mencione o tema mas sem profundidade\n"
            "- NÃO use termos técnicos, leis, normas, conceitos específicos da área ou nomenclatura especializada\n"
            "- Use apenas afirmações genéricas e senso comum — sem dados, exemplos, embasamento ou fundamentação\n"
            "- NÃO proponha soluções ou encaminhamentos concretos\n"
            "- Escreva com alguns erros de coesão e argumentação fraca, mas de forma legível"
        )
        prompt_med = (
            base_prompt +
            "\n\nGere uma resposta MEDIANA que deve obter entre 35% e 65% da pontuação máxima. "
            "REGRAS OBRIGATÓRIAS — siga à risca:\n"
            "- Aborde entre 30% e 50% dos critérios de avaliação listados — ignore os demais completamente\n"
            "- Mesmo os critérios abordados devem ser tratados de forma RASA e INCOMPLETA: cubra menos da metade do esperado para cada um\n"
            "- NÃO demonstre domínio técnico: evite termos específicos, leis, normas, conceitos técnicos ou terminologia especializada\n"
            "- Use apenas afirmações genéricas, vagas e sem fundamentação — sem exemplos concretos, sem dados\n"
            "- NÃO proponha soluções ou encaminhamentos específicos\n"
            "- Cometa alguns erros gramaticais e use estrutura de texto pouco refinada"
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
        with ThreadPoolExecutor(max_workers=3) as exc:
            f_ruim = exc.submit(clientLLM.send_prompt, prompt_ruim)
            f_med  = exc.submit(clientLLM.send_prompt, prompt_med)
            f_max  = exc.submit(clientLLM.send_prompt, prompt_max)
        ruim_answer = f_ruim.result()
        med_answer  = f_med.result()
        max_answer  = f_max.result()

        # --- Submissão para a API da MIIA ---
        print("\n[3/5] Submetendo respostas para correção...")
        with ThreadPoolExecutor(max_workers=4) as exc:
            f_bolo = exc.submit(submit_n_times, clientMIIA, integration_id, cake_recipe, 1)
            f_ruim = exc.submit(submit_n_times, clientMIIA, integration_id, ruim_answer, 3)
            f_med  = exc.submit(submit_n_times, clientMIIA, integration_id, med_answer,  3)
            f_max  = exc.submit(submit_n_times, clientMIIA, integration_id, max_answer,  3)
        bolo_job  = f_bolo.result()[0]
        ruim_jobs = f_ruim.result()
        med_jobs  = f_med.result()
        max_jobs  = f_max.result()

        # --- Coleta dos resultados ---
        print("\n[4/5] Aguardando e coletando resultados...")
        all_jobs = [bolo_job] + ruim_jobs + med_jobs + max_jobs

        def _check_job(args):
            idx, job = args
            return idx, clientMIIA.check_status(job, verbose=False)

        with ThreadPoolExecutor(max_workers=len(all_jobs)) as exc:
            all_results = dict(exc.map(_check_job, enumerate(all_jobs)))

        bolo_assessment  = all_results[0]
        ruim_assessments = [all_results[i] for i in range(1, 4)]
        med_assessments  = [all_results[i] for i in range(4, 7)]
        max_assessments  = [all_results[i] for i in range(7, 10)]

        bolo_score  = bolo_assessment["result"]["score"] if bolo_assessment else None
        ruim_scores = [a["result"]["score"] if a else None for a in ruim_assessments]
        med_scores  = [a["result"]["score"] if a else None for a in med_assessments]
        max_scores  = [a["result"]["score"] if a else None for a in max_assessments]

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
