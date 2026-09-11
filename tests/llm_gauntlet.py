from app.llm.analyzer import Analyzer


analyzer = Analyzer()

cases = {
    "proposal_is_not_decision": """
[0.00] SPEAKER_00: Предлагаю перенести релиз на пятницу.
[4.00] SPEAKER_01: Надо ещё подумать.
[7.00] SPEAKER_00: Хорошо, вернёмся к этому завтра.
""",

    "missing_deadline": """
[0.00] SPEAKER_00: Анна, подготовь отчёт для заказчика.
[4.00] SPEAKER_01: Хорошо, сделаю.
""",

    "name_is_only_mentioned": """
[0.00] SPEAKER_00: Вчера я разговаривал с Анной по другому проекту.
[4.00] SPEAKER_01: Я подготовлю отчёт до пятницы.
[8.00] SPEAKER_00: Хорошо.
""",

    "deadline_change_not_accepted": """
[0.00] SPEAKER_00: Сергей, проверь показатели до четверга.
[4.00] SPEAKER_01: Хорошо.
[7.00] SPEAKER_01: Хотя лучше бы перенести на пятницу.
[11.00] SPEAKER_00: Пока оставим как есть.
""",

    "decision_changed": """
[0.00] SPEAKER_00: Давайте выпустим версию в четверг.
[4.00] SPEAKER_01: Согласен.
[7.00] SPEAKER_00: Нет, появилась проблема. Переносим релиз на пятницу.
[12.00] SPEAKER_01: Хорошо, договорились на пятницу.
""",

    "task_cancelled": """
[0.00] SPEAKER_00: Анна, подготовь презентацию к пятнице.
[5.00] SPEAKER_01: Хорошо.
[8.00] SPEAKER_00: Стоп, презентация больше не нужна. Отменяем эту задачу.
[13.00] SPEAKER_01: Поняла.
""",
}


for name, transcript in cases.items():
    print('\n')
    print('=' * 70)
    print(name)
    print('=' * 70)

    result = analyzer.analyze(transcript)

    print(
        result.model_dump_json(
            indent=2
        )
    )