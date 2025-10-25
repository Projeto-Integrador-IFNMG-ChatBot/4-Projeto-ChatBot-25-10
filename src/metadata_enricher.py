from typing import List, Dict

def enrich_with_metadata(chunks: List[Dict], metadata: Dict) -> List[Dict]:
    """
    Adiciona um conjunto de metadados a cada bloco de texto em uma lista.

    Args:
        chunks: A lista de blocos de dados a serem enriquecidos (saída da
                etapa de deduplicação).
        metadata: Um dicionário contendo os metadados a serem adicionados
                  a cada bloco (ex: doc_id, nome_doc, etc.).

    Returns:
        Uma nova lista de blocos, onde cada bloco contém os metadados adicionados.
    """
    enriched_chunks = []
    for chunk in chunks:
        # Usamos o operador de desempacotamento de dicionário (**) para
        # criar um novo dicionário que é a fusão do chunk com os metadados.
        enriched_chunk = {**chunk, **metadata}
        enriched_chunks.append(enriched_chunk)
    
    return enriched_chunks