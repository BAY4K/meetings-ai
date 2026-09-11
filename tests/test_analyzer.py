from app.llm.analyzer import Analyzer


analyzer = Analyzer()

transcript = """
[0.00] SPEAKER_00: Коллеги, давайте обсудим подготовку отчёта для заказчика.
[4.20] SPEAKER_00: Анна, подготовь итоговый отчёт и отправь его заказчику до пятницы.
[9.10] SPEAKER_01: Хорошо, я подготовлю отчёт и отправлю его в пятницу утром.
[14.30] SPEAKER_00: Отлично. Сергей, а ты проверь финансовые показатели до четверга.
[19.40] SPEAKER_02: Ладно, но думаю лучше перенести на пятницу.
"""

result = analyzer.analyze(transcript)

print("\n========= Qwen =========\n")
print(
    result.model_dump_json(indent=2)
)