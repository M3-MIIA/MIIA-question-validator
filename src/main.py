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

    id_sheet = os.environ.get("GOOGLE_SHEET_ID")
    tab_name = os.environ.get("GOOGLE_SHEET_TAB")
    path_google_json = './auth_google.json'

    clientMIIA = miia_api.MIIA_API()
    clientLLM = liteLLM.LiteLLMClient()
    database = db.Database()
    sheets = sheet.SheetManager(path_google_json, id_sheet, tab_name)

    print("[Sucesso] Todos os conectores instanciados!\n")

    results = {"ok": [], "failed": []}

    for i, integration_id in enumerate(integration_ids, start=1):
        print(f"[{i}/{len(integration_ids)}] Iniciando: {integration_id}")
        try:
            belt.run(integration_id, clientMIIA, clientLLM, database, sheets)
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
