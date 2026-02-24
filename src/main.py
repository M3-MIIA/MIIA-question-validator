import os
import db
import liteLLM
import miia_api
import sheet
import belt
from dotenv import load_dotenv

IDS_FILE = os.path.join(os.path.dirname(__file__), '..', 'ids.txt')


def main():
    load_dotenv()

    with open(IDS_FILE, 'r', encoding='utf-8') as f:
        integration_ids = [line.strip() for line in f if line.strip()]

    if not integration_ids:
        print(f"Nenhum integration_id encontrado em {IDS_FILE}. Adicione um ID por linha e tente novamente.")
        return

    print(f"[Pipeline] {len(integration_ids)} questões na fila: {integration_ids}\n")

    id_sheet     = os.environ.get("GOOGLE_SHEET_ID")
    tab_name     = os.environ.get("GOOGLE_SHEET_TAB")
    tab_log_name = os.environ.get("GOOGLE_SHEET_TAB_LOG", "esteira_log")
    path_google_json = './auth_google.json'

    clientMIIA = miia_api.MIIA_API()
    clientLLM = liteLLM.LiteLLMClient()
    database = db.Database()
    sheets     = sheet.SheetManager(path_google_json, id_sheet, tab_name)
    sheets_log = sheet.SheetManager(path_google_json, id_sheet, tab_log_name)

    print("[Sucesso] Todos os conectores instanciados!\n")

    print("[Pré-validação] Verificando vínculos em tenant_question...")
    pre_validation_errors = []
    for integration_id in integration_ids:
        result = database.ensure_tenant_question(integration_id)
        if result is None:
            pre_validation_errors.append(integration_id)
            print(f"[PRÉ-VALIDAÇÃO] AVISO: '{integration_id}' não encontrado na tabela question — será processado mas provavelmente falhará na API.")

    if pre_validation_errors:
        print(f"[PRÉ-VALIDAÇÃO] {len(pre_validation_errors)} IDs não puderam ser vinculados: {pre_validation_errors}")
    print("[Pré-validação] Concluída.\n")

    results = {"ok": [], "failed": []}

    for i, integration_id in enumerate(integration_ids, start=1):
        print(f"[{i}/{len(integration_ids)}] Iniciando: {integration_id}")
        try:
            belt.run(integration_id, clientMIIA, clientLLM, database, sheets, sheets_log)
            results["ok"].append(integration_id)
        except Exception as e:
            print(f"[ERRO] {integration_id} falhou: {e}")
            results["failed"].append(integration_id)

    print(f"\n{'='*60}")
    print(f"[Pipeline] Concluído — {len(results['ok'])} ok, {len(results['failed'])} com erro")
    if results["failed"]:
        print(f"[Pipeline] Falharam: {results['failed']}")


if __name__ == "__main__":
    main()
