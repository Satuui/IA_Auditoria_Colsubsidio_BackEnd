def detect_signatures(doc) -> list:
    """
    Escanea las páginas del documento buscando texto o imágenes que 
    sugieran una firma (ej. 'Firma', 'Signed', 'Aprobado', etc.)
    """
    signatures = []
    keywords = ["firma", "signed", "autorizado", "aprobado"]

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").lower()
        if any(word in text for word in keywords):
            signatures.append({
                "page": page_num,
                "keywords_detected": [word for word in keywords if word in text]
            })

    return signatures

