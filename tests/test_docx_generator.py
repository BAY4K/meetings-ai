from pathlib import Path

from app.docx.generator import (
    ProtocolDocxGenerator,
)
from app.schemas.meeting import (
    MeetingExtraction,
)


data = {
    "sections": [
        {
            "topic": "Подготовка отчёта",
            "speaker_name": "Иван",
            "speaker_id": "SPEAKER_00",
            "summary": (
                "Обсуждалась подготовка "
                "итогового отчёта для заказчика."
            ),
            "items": [
                {
                    "kind": "task",
                    "text": "Подготовить итоговый отчёт",
                    "responsible_name": "Анна",
                    "responsible_speaker": "SPEAKER_01",
                    "deadline": "до пятницы",
                    "active": True,
                    "evidence": [
                        "Анна, подготовь итоговый "
                        "отчёт до пятницы."
                    ],
                },
                {
                    "kind": "decision",
                    "text": (
                        "Использовать новый "
                        "формат отчёта"
                    ),
                    "responsible_name": None,
                    "responsible_speaker": None,
                    "deadline": None,
                    "active": True,
                    "evidence": [
                        "Тогда решено, используем "
                        "новый формат."
                    ],
                },
            ],
        }
    ],
    "unresolved_questions": [],
    "ambiguous_fragments": [],
}


extraction = (
    MeetingExtraction.model_validate(data)
)

generator = ProtocolDocxGenerator()

result = generator.generate(
    extraction=extraction,
    output_path=Path(
        "outputs/test_protocol.docx"
    ),
)

print(result)