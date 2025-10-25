from PyPDF2 import PdfReader

def extract_raw(pdf_path: str, doc_id: str):
    """
    Extrai texto bruto de um PDF, página a página.
    Remove quebras de linha e espaços duplicados.
    """
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            text = " ".join(text.split())  # limpeza simples
        pages.append({"doc_id": doc_id, "page": i, "raw_text": text})
    return pages
