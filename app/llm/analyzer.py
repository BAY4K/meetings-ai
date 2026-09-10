import httpx


class Analyzer:
    def __init__(
            self,
            model_name: str = 'qwen3:8b',
            base_url: str = 'http://127.0.0.1:11434',
            timeout: float= 300.0,
            ):
        self.model_name = model_name
        self.base_url = base_url
        self.timeout = timeout

    def analyze(self, transcript: str) -> str:
        payload = {
            'model': self.model_name,
            'messages': [
                {
                    'role': 'user',
                    'content': transcript,
                }
            ],
            'stream': False,
            'think': False,
            'options': {
                'temperature': 0,
            },
        }

        with httpx.Client(
            timeout=self.timeout,
            trust_env=False,
        ) as client:
            response = client.post(
            f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )

        if response.is_error:
            print("Ollama status:", response.status_code)
            print("Ollama response:", response.text)

        response.raise_for_status()

        data = response.json()

        return data['message']['content']