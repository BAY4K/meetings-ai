from pathlib import Path

from app.docx_generator.generator import (
    ProtocolDocxGenerator,
)
from app.schemas.meeting import (
    MeetingExtraction,
)


data = {
    "heard": [
        {
            "speaker_id": "SPEAKER_00",
            "speaker_name": None,
            "summary": (
                "Поднял вопрос о сроках "
                "тестирования сборки."
            ),
            "resolutions": [
                {
                    "text": (
                        "Протестировать сборку"
                    ),
                    "responsible_name": "Сергей",
                    "responsible_speaker": (
                        "SPEAKER_02"
                    ),
                    "deadline": (
                        "до понедельника"
                    ),
                    "evidence": [
                        (
                            "[60.00] SPEAKER_00: "
                            "Ладно, давай тогда "
                            "до понедельника."
                        ),
                        (
                            "[64.00] SPEAKER_02: "
                            "Да, так нормально."
                        ),
                    ],
                }
            ],
        },
        {
            "speaker_id": "SPEAKER_00",
            "speaker_name": None,
            "summary": (
                "Поднял вопрос о дате релиза."
            ),
            "resolutions": [
                {
                    "text": (
                        "Оставить релиз "
                        "на четверг"
                    ),
                    "responsible_name": None,
                    "responsible_speaker": None,
                    "deadline": None,
                    "evidence": [
                        (
                            "[86.00] SPEAKER_00: "
                            "Хорошо, тогда сам релиз "
                            "оставляем на четверг."
                        )
                    ],
                }
            ],
        },
    ],
    "unresolved_questions": [
        (
            "Что именно нужно закончить "
            "до пятницы?"
        )
    ],
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