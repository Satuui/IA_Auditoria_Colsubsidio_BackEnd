import re
from typing import List, Optional, Tuple

import pdfplumber
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# Visual signature (OpenCV)
import numpy as np
import cv2

# === RUTAS LOCALES (ajusta si es necesario) ===
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler\Library\bin"

# === Parámetros firma visual (tuneables) ===
SIG_ROI_BANDS    = [(0.55, 0.90), (0.65, 0.95), (0.70, 0.98)]
SIG_MIN_AREA     = 50
SIG_MAX_AREA     = 12000
SIG_MIN_STROKES  = 5
SIG_MIN_COMPLEX  = 15
SIG_MAX_COMPLEX  = 1100


# =========================
# Helpers de texto / OCR
# =========================
def _normalize_text(txt: str) -> str:
    return (
        txt.replace("\x0c", " ")
           .replace("\n", " ")
           .replace("\r", " ")
           .replace("\t", " ")
           .strip()
    )


def _has_receipt_context(text: str) -> bool:
    low = text.lower()
    strong = [
        "dispensación", "dispensacion",
        "medicamentos autorizados",
        "presentación", "presentacion",
        "paciente", "identificación", "identificacion",
        "cantidad", "cant.", "unidades",
    ]
    hits = sum(1 for s in strong if s in low)
    return hits >= 3


def _extract_text_pdfplumber(file_path: str) -> str:
    chunks: List[str] = []
    with pdfplumber.open(file_path) as pdf:
        for p in pdf.pages:
            chunks.append(p.extract_text() or "")
    return _normalize_text(" ".join(chunks))


def _extract_text_ocr(file_path: str) -> str:
    pages: List[Image.Image] = convert_from_path(file_path, dpi=200, poppler_path=POPPLER_PATH)
    parts: List[str] = []
    for im in pages:
        im = im.convert("L")
        parts.append(pytesseract.image_to_string(im, lang="spa+eng"))
    return _normalize_text(" ".join(parts))


def _find_near(text: str, anchor_pat: str, value_pat: str, window: int = 80) -> bool:
    for m in re.finditer(anchor_pat, text, flags=re.IGNORECASE):
        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        chunk = text[start:end]
        if re.search(value_pat, chunk, flags=re.IGNORECASE):
            return True
    return False


# =========================
# Validadores semánticos
# =========================
def _find_cedula(text: str) -> bool:
    anchor = r"(?:\bcc\b|c\.c\.|c[eé]dula|identificaci[oó]n|no\.?)"
    value = r"\b\d{6,10}\b"
    return _find_near(text, anchor, value, window=60)


def _find_fecha(text: str) -> bool:
    anchor = r"(?:fecha|fcha)"
    value = r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"
    if _find_near(text, anchor, value, window=60):
        return True
    return len(re.findall(value, text)) >= 2


def _find_cantidad(text: str) -> bool:
    if _find_near(text, r"(?:cantidad|cant\.?|unidades)", r"\b\d{1,4}\b", window=60):
        return True
    return bool(re.search(r"[A-ZÁÉÍÓÚÑ0-9\.\-\(\) ]{6,}\s+\b\d{1,4}\b", text))


def _find_medicamento(text: str) -> bool:
    low = text.lower()
    headers = ["medicamentos autorizados", "medicamento", "presentación", "presentacion"]
    if not any(h in low for h in headers):
        return False

    pat = r"\b[A-ZÁÉÍÓÚÑ]{3,}[A-Z0-9\-\s\(\)]*\s(?:\d+(\.\d+)?\s*(?:mg|ml))"
    if re.search(pat, text):
        return True

    forms = ["tableta", "tabletas", "capsula", "capsulas", "jarabe", "solución", "solucion"]
    return any(f in low for f in forms)


# =========================
# Firma visual (OpenCV)
# =========================
def _has_signature_visual(file_path: str) -> bool:
    try:
        pages: List[Image.Image] = convert_from_path(file_path, dpi=200, poppler_path=POPPLER_PATH)
        for im in pages:
            w, h = im.size
            gray_full = np.array(im.convert("L"))

            for (top_frac, bot_frac) in SIG_ROI_BANDS:
                y1, y2 = int(h * top_frac), int(h * bot_frac)
                x1, x2 = int(w * 0.05), int(w * 0.95)
                roi = gray_full[y1:y2, x1:x2]

                roi_blur = cv2.GaussianBlur(roi, (5, 5), 0)
                _, th_otsu = cv2.threshold(roi_blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                th_adapt = cv2.adaptiveThreshold(
                    roi_blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 10
                )

                for th in (th_otsu, th_adapt):
                    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, th.shape[1] // 18), 1))
                    th_nolines = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel_h, iterations=1)
                    kernel_s = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                    th_clean = cv2.morphologyEx(th_nolines, cv2.MORPH_OPEN, kernel_s, iterations=1)

                    cnts, _ = cv2.findContours(th_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    stroke_like = 0
                    for c in cnts:
                        area = cv2.contourArea(c)
                        if area < SIG_MIN_AREA or area > SIG_MAX_AREA:
                            continue
                        _, _, cw, ch = cv2.boundingRect(c)
                        aspect = cw / max(1, ch)
                        if aspect > 22 and ch < 6:
                            continue
                        peri = cv2.arcLength(c, True) or 1.0
                        comp = (peri * peri) / max(1.0, area)
                        if SIG_MIN_COMPLEX < comp < SIG_MAX_COMPLEX:
                            stroke_like += 1

                    if stroke_like >= SIG_MIN_STROKES:
                        return True

        return False
    except Exception:
        return False


def _find_firma(text: str, file_path: str) -> Tuple[bool, Optional[str]]:
    low = text.lower()
    n = len(low)
    tail = low[int(n * 0.65):]

    strong = [r"firma\s+del", r"firma\s*y\s*sello", r"firmado\s+por", r"firma:\s"]
    if any(re.search(p, tail) for p in strong):
        return True, "texto"

    name_like = re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,3}\b", tail)
    has_ced = _find_cedula(tail)
    has_fec = _find_fecha(tail)
    if name_like and has_ced and has_fec:
        return True, "texto"

    if _has_signature_visual(file_path):
        return True, "visual"

    return False, None


# =========================
# Extracción de valores
# =========================
def _extract_fecha(text: str) -> str:
    m = re.search(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b", text)
    return m.group(1) if m else ""


def _extract_documento(text: str) -> str:
    patterns = [
        r"(?:documento|doc\.?|no\.?|n[°º])\s*[:\-]?\s*(\d{6,12})",
        r"(?:autorizaci[oó]n|mipres|pedido)\s*[:\-]?\s*(\d{6,12})",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    m2 = re.search(r"\b(\d{6,12})\b", text)
    return m2.group(1) if m2 else ""


def _extract_medicamento(text: str) -> str:
    m = re.search(r"\b([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9\-\s]{2,}?\s\d+(?:\.\d+)?\s*(?:MG|ML))\b", text, flags=re.IGNORECASE)
    return (m.group(1).strip() if m else "").upper()


def _extract_cantidad(text: str) -> str:
    m = re.search(r"(?:cantidad|cant\.?|unidades)\s*[:\-]?\s*(\d{1,4})\b", text, flags=re.IGNORECASE)
    if m:
        return f"{m.group(1)}"
    m2 = re.search(r"[A-ZÁÉÍÓÚÑ0-9\.\-\(\) ]{6,}\s+(\d{1,4})\b", text)
    return m2.group(1) if m2 else ""


# =========================
# Auditor principal
# =========================
def audit_pdf(file_path: str):
    result = {
        "firma": False,
        "cedula": False,
        "medicamento": False,
        "fecha": False,
        "cantidad": False,
        "faltantes": []
    }

    try:
        text_plain = _extract_text_pdfplumber(file_path)
        text = text_plain if len(text_plain.strip()) >= 25 else _extract_text_ocr(file_path)

        if not _has_receipt_context(text):
            result["faltantes"] = ["firma", "cedula", "medicamento", "fecha", "cantidad"]
            result["reason"] = "Documento sin contexto válido de dispensación/tirilla"
            result["extraido"] = {"documento": "", "fecha_pedido": "", "medicamento": "", "cantidad": ""}
            result["debug_text_sample"] = text[:400]
            return result

        result["cedula"] = _find_cedula(text)
        result["fecha"] = _find_fecha(text)
        result["cantidad"] = _find_cantidad(text)
        result["medicamento"] = _find_medicamento(text)
        firma_val, firma_method = _find_firma(text, file_path)
        result["firma"] = firma_val
        result["firma_method"] = firma_method

        result["faltantes"] = [
            k for k, v in result.items()
            if k not in ("faltantes", "reason", "debug_text_sample", "firma_method") and not v
        ]

        # Extraídos (para cruce)
        result["extraido"] = {
            "documento": _extract_documento(text),
            "fecha_pedido": _extract_fecha(text),
            "medicamento": _extract_medicamento(text),
            "cantidad": _extract_cantidad(text),
        }

        # Observaciones amigables
        obs = []
        if "reason" in result:
            obs.append(result["reason"])
        if result["firma"] and result.get("firma_method") == "visual":
            obs.append("Firma detectada por análisis visual")
        elif result["firma"] and result.get("firma_method") == "texto":
            obs.append("Firma detectada por texto OCR")
        if not result["firma"]:
            obs.append("Firma no detectada")
        if not result["cedula"]:
            obs.append("Cédula no detectada")
        if not result["medicamento"]:
            obs.append("Medicamento no detectado")
        if not result["fecha"]:
            obs.append("Fecha no detectada")
        if not result["cantidad"]:
            obs.append("Cantidad no detectada")
        result["observaciones"] = "; ".join(dict.fromkeys(obs))

        result["debug_text_sample"] = text[:400]
        return result

    except Exception as e:
        return {"error": f"OCR/Parse error: {e}"}
