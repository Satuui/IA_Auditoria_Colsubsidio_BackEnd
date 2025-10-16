import pandas as pd
from pathlib import Path
from typing import Dict, Any

# Ruta fija al CSV
TABLE_CSV = Path(__file__).resolve().parents[3] / "datasets" / "tabla_referencia.csv"


def _safe_strip(val: Any) -> str:
    """Limpia valores a string en mayúsculas, sin None, sin espacios múltiples."""
    if pd.isna(val):
        return ""
    return " ".join(str(val).strip().upper().split())


def load_reference() -> Dict[str, Dict[str, str]]:
    """
    Carga la tabla de referencia (PEDIDO, DOCUMENTO, FECHA PEDIDO, MEDICAMENTO, CANTIDAD)
    y la convierte en dict indexado por nombre de archivo (PEDIDO).
    """
    if not TABLE_CSV.exists():
        raise FileNotFoundError(f"No existe el archivo de referencia: {TABLE_CSV}")

    df = pd.read_csv(TABLE_CSV, dtype=str, encoding="utf-8")

    # Asegurar mayúsculas y limpiar texto sin usar applymap (que Pylance confunde)
    for col in df.columns:
        df[col] = df[col].map(_safe_strip)

    # Diccionario final indexado por "PEDIDO" (ej: "3153711068.pdf")
    reference = {}

    for _, row in df.iterrows():
        file_key = _safe_strip(row.get("PEDIDO"))
        if file_key:  # Aseguramos que no sea vacío
            reference[file_key] = {
                "documento": row.get("DOCUMENTO", ""),
                "fecha_pedido": row.get("FECHA PEDIDO", ""),
                "medicamento": row.get("MEDICAMENTO", ""),
                "cantidad": row.get("CANTIDAD", ""),
            }

    return reference



