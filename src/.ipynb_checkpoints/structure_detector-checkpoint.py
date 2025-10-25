import re
from typing import List, Dict

def detect_structure(text: str) -> List[Dict]:
    """
    Detecta elementos estruturais (capítulos, seções, artigos) em um texto
    e o divide em blocos semânticos.

    Args:
        text: O texto normalizado de uma página ou documento.

    Returns:
        Uma lista de dicionários, onde cada dicionário representa um
        bloco de texto com suas tags estruturais.
    """
    # Padrões de Regex para identificar as estruturas.
    # Usamos re.IGNORECASE para ignorar se está em maiúsculo ou minúsculo.
    patterns = {
        'capitulo': re.compile(r'cap[íi]tulo\s+([ivx\d]+)', re.IGNORECASE),
        'secao': re.compile(r'se[çc][ãa]o\s+([\d\.]+)', re.IGNORECASE),
        'artigo': re.compile(r'art(?:igo)?\s+(\d+º?)', re.IGNORECASE)
    }

    chunks = []
    current_structure = {}
    current_text_lines = []
    
    lines = text.split('\n')

    for line in lines:
        matched = False
        for key, pattern in patterns.items():
            match = pattern.search(line)
            if match:
                # Se encontrarmos uma nova estrutura, salvamos o bloco de texto anterior.
                if current_text_lines:
                    chunk = current_structure.copy()
                    chunk['texto'] = "\n".join(current_text_lines).strip()
                    chunks.append(chunk)
                
                # Atualiza a estrutura atual e limpa o buffer de texto.
                current_structure[key] = match.group(0) # Salva o texto completo, ex: "Capítulo IV"
                
                # Se encontrarmos um novo capítulo, "resetamos" as sub-estruturas
                if key == 'capitulo':
                    current_structure.pop('secao', None)
                    current_structure.pop('artigo', None)
                elif key == 'secao':
                    current_structure.pop('artigo', None)

                current_text_lines = [line] # A linha que deu match faz parte do novo bloco
                matched = True
                break # Passa para a próxima linha do texto

        if not matched:
            current_text_lines.append(line)

    # Adiciona o último bloco de texto que sobrou no buffer
    if current_text_lines:
        chunk = current_structure.copy()
        chunk['texto'] = "\n".join(current_text_lines).strip()
        chunks.append(chunk)
        
    return chunks
