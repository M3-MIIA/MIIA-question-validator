import os
import litellm


class LiteLLMClient:

    def __init__(self):
        self.api_base = os.environ.get("LITELLM_API_BASE")
        self.api_key = os.environ.get("LITELLM_API_KEY")
        self.model = os.environ.get("LLM_DEFAULT_MODEL")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", ""))
        self.timeout = int(os.getenv("LLM_TIMEOUT", ""))

        if not self.api_base or not self.api_key or not self.model:
            raise ValueError("ERROR: LITELLM_API_BASE, LITELLM_API_KEY e LLM_DEFAULT_MODEL devem estar no .env.")

    def send_prompt(self, prompt, temperature=None):
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_base=self.api_base,
                api_key=self.api_key,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
                drop_params=True,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error communicating with LiteLLM: {e}")
            return None
