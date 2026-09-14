from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import OUTPUT_DIR
from app.schemas.meeting import MeetingExtraction

router = APIRouter(
    tags=['downloads'],
)

DOCX_MEDIA_TYPE = (
    'application/'
    'vnd.openxmlformats-officedocument.'
    'wordprocessingml.document'
)

@router.get("/download/{file_id}")
async def download(file_id: str):
    try:
        normalized_id = UUID(
            file_id
        ).hex

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid file ID",
        )

    file_path = (
            OUTPUT_DIR
            / f"{normalized_id}.docx"
    )

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Protocol not found",
        )

    return FileResponse(
        str(file_path),
        media_type=DOCX_MEDIA_TYPE,
        filename='result.docx',
    )

@router.post("/export/docx")
async def export_docx(request: Request, extraction: MeetingExtraction):
    buffer = (
        request.app.state.docx_generator.generate_bytes(extraction)
    )

    return StreamingResponse(
        buffer,
        media_type=DOCX_MEDIA_TYPE,
        headers={
            'Content-Disposition': 'attachment; filename="protocol.docx"'
        }
    )