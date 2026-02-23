import os
import time
import requests
from dotenv import load_dotenv


class MIIA_API:

    def __init__(self):
        self.base_url = os.environ.get("BASE_URL")
        self.token = os.environ.get("MIIA_API_TOKEN")
        if not self.base_url or not self.token:
            raise ValueError("ERRO CRÍTICO: BASE_URL ou MIIA_API_TOKEN ausentes.")
    
    def create_job(self, question_id, answer):
        url_post = f"{self.base_url}/textual-corrections/v1/discursive/{question_id}/assess"
        