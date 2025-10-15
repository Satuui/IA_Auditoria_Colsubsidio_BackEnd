from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from app.services.pdf_processor import process_pdf

from app.services.pdf_processor import process_pdf
from app.services.audit_logger import XLSX_PATH

router = APIRouter()

@router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo archivos PDF válidos")

    try:
        result = process_pdf(file)  # <-- pasamos el UploadFile directamente
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------------------
# 1) Auditoría de un PDF
# ----------------------------
@router.post("/audit/pdf")
async def audit_single_pdf(file: UploadFile = File(...)):
    """
    Sube un PDF, lo audita (OCR + reglas + firma visual + cruce con tabla) y devuelve el resultado.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo archivos PDF válidos")

    try:
        result = process_pdf(file)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando PDF: {e!s}")


# ----------------------------
# 2) Alias compatible con tu Postman anterior
# ----------------------------
@router.post("/upload-pdf")
async def upload_pdf_legacy(file: UploadFile = File(...)):
    """
    Alias legado para compatibilidad. Redirige al flujo de /audit/pdf.
    """
    return await audit_single_pdf(file)

# ----------------------------
# 3) Auditoría batch (opcional)
# ----------------------------
# @router.post("/audit/batch")
# async def audit_batch():
#     """
#     Audita todos los PDFs del directorio datasets/ (o la carpeta que definas en batch_processor)
#     y devuelve un resumen. Al finalizar, el Excel consolidado queda actualizado.
#     """
#     try:
#         summary = audit_all_pdfs()
#         return {"status": "ok", "summary": summary}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error en batch: {e!s}")


# ----------------------------
# 4) Descargar Excel consolidado
# ----------------------------
@router.get("/report/download")
async def download_report():
    """
    Devuelve el archivo outputs/resultados_auditoria.xlsx (si existe).
    """
    if not XLSX_PATH.exists():
        raise HTTPException(status_code=404, detail="No hay reporte aún. Genera resultados primero.")

    return FileResponse(
        path=str(XLSX_PATH),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="resultados_auditoria.xlsx",
    )