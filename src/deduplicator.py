import hashlib
from typing import List, Dict

def deduplicate_chunks(chunks: List[Dict], min_length: int = 50) -> List[Dict]:
    """
    Remove blocos de texto duplicados de uma lista de chunks.

    A duplicação é verificada com base no hash do conteúdo do texto.
    Blocos de texto muito curtos podem ser ignorados para evitar a remoção
    de frases comuns e curtas.

    Args:
        chunks: A lista de blocos de texto (dicionários) gerada pela
                etapa de detecção de estrutura.
        min_length: O comprimento mínimo de caracteres para um texto ser
                    considerado na verificação de duplicatas.

    Returns:
        Uma nova lista de chunks contendo apenas os blocos de texto únicos.
    """
    seen_hashes = set()
    unique_chunks = []

    for chunk in chunks:
        # Pega o texto do chunk, garantindo que exista
        text = chunk.get('texto', '').strip()
        
        # Ignora textos muito curtos ou vazios
        if len(text) < min_length:
            unique_chunks.append(chunk)
            continue

        # Calcula o hash do texto para criar uma assinatura única
        # Usamos encode('utf-8') pois o hashlib trabalha com bytes
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()

        # Se nunca vimos esse hash antes, o texto é único
        if text_hash not in seen_hashes:
            seen_hashes.add(text_hash)
            unique_chunks.append(chunk)
        # Se o hash já foi visto, este é um chunk duplicado e será ignorado.

    return unique_chunks
