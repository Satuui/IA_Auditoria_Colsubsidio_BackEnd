import os
import shutil
from typing import Any, Dict

from fastapi import UploadFile

from app.core.config import settings
from app.services.pdf_auditor import audit_pdf
from app.services.reference_loader import load_reference
from app.services.audit_logger import log_result


def _as_dict(obj: Any) -> Dict[str, Any]:
    """Devuelve un dict seguro (si no, dict vacío)."""
    return obj if isinstance(obj, dict) else {}


def _norm(s: Any) -> str:
    """Normaliza a string seguro en mayúsculas, sin espacios dobles."""
    return " ".join(str(s or "").strip().upper().split())


def process_pdf(upload_file: UploadFile) -> Dict[str, Any]:
    """
    Guarda el UploadFile, audita y registra en Excel (reemplaza fila si existe).
    Retorna payload listo para API.
    """
    # 1) Directorio de uploads
    upload_dir = settings.UPLOAD_DIR or os.path.join(settings.BASE_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    # 2) Nombre y ruta
    filename = upload_file.filename or "uploaded_file.pdf"
    file_path = os.path.join(upload_dir, filename)

    # 3) Persistir archivo
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    # 4) Auditoría
    audit_result_any: Any = audit_pdf(file_path)
    audit_result: Dict[str, Any] = _as_dict(audit_result_any)

    # 5) Cruce contra tabla de referencia (datasets/tabla_referencia.csv)
    try:
        reference = load_reference()  # Dict[str, Dict[str, str]] indexado por PEDIDO (= nombre PDF)
    except Exception:
        reference = {}

    expected = reference.get(filename) if isinstance(reference, dict) else None

    if isinstance(expected, dict):
        extra: Dict[str, Any] = _as_dict(audit_result.get("extraido"))
        comparacion: Dict[str, Any] = {
            "documento_ok":   _norm(extra.get("documento"))     == _norm(expected.get("documento")),
            "fecha_ok":       _norm(extra.get("fecha_pedido"))   == _norm(expected.get("fecha_pedido")),
            "medicamento_ok": _norm(extra.get("medicamento"))    == _norm(expected.get("medicamento")),
            "cantidad_ok":    _norm(extra.get("cantidad"))       == _norm(expected.get("cantidad")),
            "esperado": {
                "documento": expected.get("documento", ""),
                "fecha_pedido": expected.get("fecha_pedido", ""),
                "medicamento": expected.get("medicamento", ""),
                "cantidad": expected.get("cantidad", ""),
            },
        }
        audit_result["comparacion"] = comparacion
    else:
        audit_result["comparacion"] = {"info": "Sin fila de referencia para este archivo."}

    # 6) Construir payload consistente para API/Excel
    payload: Dict[str, Any] = {
        "filename": filename,
        "path": file_path,
        "result": audit_result,
        "status": "success" if "error" not in audit_result else "error",
    }

    # 7) Registrar en Excel (no romper si falla escritura)
    try:
        log_result(payload)
    except Exception:
        pass

    return payload

