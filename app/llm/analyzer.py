from pathlib import Path

import httpx

from app.schemas.meeting import MeetingExtraction


class Analyzer:
    def __init__(
            self,
            model_name: str = (
                'qwen3.5:9b-q4_K_M'
            ),
            base_url: str = (
                'http://127.0.0.1:11434'
            ),
            timeout: float = 300.0,
            prompt_path: (
                str | Path | None
            ) = None,
            num_ctx: int = 8192,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.timeout = timeout
        self.num_ctx = num_ctx

        if prompt_path is None:
            prompt_path = (
                Path(__file__)
                .resolve()
                .parents[1]
                / 'prompts'
                / 'meeting_system.txt'
            )

        self.system_prompt = (
            Path(prompt_path)
            .read_text(
                encoding='utf-8'
            )
        )


    def analyze(
            self,
            transcript: str,
    ) -> MeetingExtraction:

        user_message = (
            'Проанализируй следующую '
            'расшифровку встречи согласно '
            'системным правилам.\n\n'
            'Верни только данные согласно '
            'переданной JSON-схеме.\n\n'
            '<transcript>\n'
            f'{transcript}\n'
            '</transcript>'
        )

        payload = {
            'model':
                self.model_name,

            'messages': [
                {
                    'role': 'system',
                    'content':
                        self.system_prompt,
                },
                {
                    'role': 'user',
                    'content':
                        user_message,
                },
            ],
            'stream': False,
            'think': False,
            'format': (
                MeetingExtraction
                .model_json_schema()
            ),

            # После extraction освобождаем
            # VRAM для следующего pipeline.
            'keep_alive': 0,

            'options': {
                'temperature': 0,
                'num_ctx':
                    self.num_ctx,
            },
        }

        with httpx.Client(
            timeout=self.timeout,
            trust_env=False,
        ) as client:
            response = client.post(
                f'{self.base_url}/api/chat',
                json=payload,
            )

        if response.is_error:
            print(
                'Ollama status:',
                response.status_code,
            )

            print(
                'Ollama response:',
                response.text,
            )

        response.raise_for_status()

        data = response.json()

        content = (
            data['message']['content']
        )

        return (
            MeetingExtraction
            .model_validate_json(
                content
            )
        )