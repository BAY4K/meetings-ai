from app.llm.analyzer import Analyzer


analyzer = Analyzer()

transcript = """
[0.00] SPEAKER_00: Коллеги, перенесём выпуск новой версии на пятницу.
[4.20] SPEAKER_01: Хорошо. Я подготовлю сборку к четвергу.
[8.50] SPEAKER_00: Отлично.
"""

prompt = f"""
Проанализируй расшифровку встречи.

Определи:
- какие решения были приняты;
- какие поручения были даны;
- кому они поручены;
- какие сроки были названы.

Отвечай на русском языке.

Расшифровка:
{transcript}
"""

result = analyzer.analyze(prompt)

print("\n========= Qwen =========\n")
print(result)