import re
from typing import Dict

def normalize_text(text: str, acronyms: Dict[str, str] = None) -> str:
    """
    Realiza uma normalização linguística básica no texto.

    - Converte para minúsculas.
    - Remove espaços em branco extras e quebras de linha.
    - (Futuramente) Expande siglas/acrônimos.

    Args:
        text: O texto a ser normalizado.
        acronyms: Um dicionário de siglas para expansão (opcional).

    Returns:
        O texto normalizado.
    """
    if not isinstance(text, str):
        return ""

    # Converte para minúsculas
    text = text.lower()

    # Expansão de siglas (funcionalidade para o futuro)
    if acronyms:
        for acronym, expansion in acronyms.items():
            # Usa regex para substituir a sigla como uma palavra inteira
            text = re.sub(r'\b' + re.escape(acronym.lower()) + r'\b', expansion.lower(), text)

    # Remove múltiplos espaços e quebras de linha, substituindo por um único espaço
    text = re.sub(r'\s+', ' ', text).strip()

    return text
