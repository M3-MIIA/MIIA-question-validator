import os
from google import genai
from dotenv import load_dotenv


class GeminiClient:
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("ERROR: GEMINI_API_KEY not set in environment variables.")
        self.client = genai.Client(api_key=self.api_key)

    def send_prompt(self, prompt):
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Error communicating with Gemini API: {e}")
            return None
