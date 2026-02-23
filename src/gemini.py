import os
from google import genai
from dotenv import load_dotenv


class GeminiClient:
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("ERRO CRÍTICO: GEMINI_API_KEY ausente no arquivo .env.")
        self.client = genai.Client(api_key=self.api_key)

