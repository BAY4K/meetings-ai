from dataclasses import dataclass
import os


@dataclass(frozen=True)
class AsrSettings:
    model_name: str = 'large-v3'
    device: str = 'cuda'
    compute_type: str = 'float16'
    batch_size: int = 1
    language: str = 'ru'
    vad_onset: float = 0.35
    vad_offset: float = 0.25

    diarization_device: str = 'cuda'
    diarization_model: str = 'pyannote/speaker-diarization-community-1'


@dataclass(frozen=True)
class LlmSettings:
    model_name: str = 'qwen3.5:9b-q4_K_M'
    base_url: str = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')

    timeout: float = 300.0
    num_ctx: int = 8192


@dataclass(frozen=True)
class PipelineSettings:
    asr: AsrSettings = AsrSettings()
    llm: LlmSettings = LlmSettings()


settings = PipelineSettings()