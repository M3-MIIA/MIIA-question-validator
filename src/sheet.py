import gspread
from google.oauth2.service_account import Credentials

class SheetManager:
    
    def __init__(self, json_path, sheet_id, tab_name):
        self.caminho_json = json_path
        self.id_planilha = sheet_id
        self.nome_aba = tab_name
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self.credenciais = Credentials.from_service_account_file(self.caminho_json, scopes=self.scopes)
        self.cliente = gspread.authorize(self.credenciais)
        self.planilha = self.cliente.open_by_key(self.id_planilha)
        self.aba = self.planilha.worksheet(self.nome_aba)              


    def insert_line(self, values):
        sanitized = [v if v is not None else "" for v in values]
        self.aba.append_row(sanitized)