from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
# from docx.oxml.ns import qn
from docx.shared import Pt

from app.schemas.meeting import MeetingExtraction


class ProtocolDocxGenerator:
    def __init__(
            self,
            template_path: str | Path | None = None,
    ):
        if template_path is None:
            template_path = (Path(__file__).parents[1]
                             / 'templates'
                             / 'protocol_template.docx')

        self.template_path = Path(template_path)

    def generate(
            self,
            extraction: MeetingExtraction,
            output_path: str | Path,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True, exist_ok=True
        )
        # Открываем шаблон
        doc = Document(self.template_path)

        # Находим нужные участки
        heard_heading = self._find_paragraph(
            doc,
            'Заслушали:',
        )

        end_marker = self._find_paragraph_starting_with(
            doc,
            '[При необходимости добавить',
        )

        # Убираем placeholder'ы (заглушки)
        self._remove_placeholder_blocks(
            doc,
            start_paragraph=heard_heading,
            end_paragraph=end_marker,
        )

        # Вставляем наш текст
        for section in extraction.sections:
            self._insert_section(
                anchor=end_marker,
                section=section,
            )

        self._remove_paragraph(end_marker)

        # Сохраняем документ
        doc.save(output_path)

        return output_path

    @staticmethod
    def _find_paragraph(doc, text: str):
        for paragraph in doc.paragraphs:
            if paragraph.text.strip() == text:
                return paragraph

        raise ValueError(
            f"Paragraph was not found in {text}"
        )

    @staticmethod
    def _find_paragraph_starting_with(doc, text: str):
        for paragraph in doc.paragraphs:
            if paragraph.text.strip().startswith(text):
                return paragraph

        raise ValueError(
            f"Paragraph was not found in {text}"
        )

    def _remove_placeholder_blocks(
            self,
            doc,
            start_paragraph,
            end_paragraph,
    ):
        paragraphs = doc.paragraphs

        start_index = next(
            i
            for i, paragraph in enumerate(paragraphs)
            if paragraph._element is start_paragraph._element
        )

        end_index = next(
            i
            for i, paragraph in enumerate(paragraphs)
            if paragraph._element is end_paragraph._element
        )

        for paragraph in paragraphs[
            start_index + 1:end_index
        ]:
            self._remove_paragraph(paragraph)

    @staticmethod
    def _remove_paragraph(paragraph):
        element = paragraph._element
        parent = element.getparent()

        parent.remove(element)

    @staticmethod
    def _add_run(
            paragraph,
            text: str,
            *,
            bold: bool = False,
            italic: bool = False,
    ):
        run = paragraph.add_run(text)

        run.bold = bold
        run.italic = italic
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)

        return run


    def _insert_section(
            self,
            anchor,
            section,
    ):
        speaker = self._section_heading(section)

        speaker_paragraph = (
            anchor.insert_paragraph_before()
        )

        self._add_run(
            speaker_paragraph,
            speaker,
            bold=True,
        )

        summary_paragraph = (
            anchor.insert_paragraph_before()
        )

        summary_paragraph.alignment = (
            WD_ALIGN_PARAGRAPH.JUSTIFY
        )

        self._add_run(
            summary_paragraph,
            section.summary,
        )

        active_items = [
            item
            for item in section.items
            if item.active
        ]

        if not active_items:
            return

        decision_heading = (
            anchor.insert_paragraph_before()
        )

        self._add_run(
            decision_heading,
            'Решение:',
            bold=True,
        )

        for item in active_items:
            item_paragraph = (
                anchor.insert_paragraph_before()
            )

            text = self._format_item(item)

            self._add_run(
                item_paragraph,
                text,
            )

    @staticmethod
    def _section_heading(section) -> str:
        if section.speaker_name:
            return section.speaker_name

        if section.speaker_id:
            return section.speaker_id

        return section.topic

    @staticmethod
    def _format_item(item) -> str:
        parts = [
            item.text.rstrip('.')
        ]

        if item.kind == 'task':
            if item.responsible_name:
                parts.append(
                    f'Ответственный — {item.responsible_name}'
                )

            if item.deadline:
                parts.append(
                    f'срок — {item.deadline}'
                )
        return  '— ' + '; '.join(parts) + '.'