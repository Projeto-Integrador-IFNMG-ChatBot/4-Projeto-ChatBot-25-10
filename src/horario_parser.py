# src/horario_parser.py

import fitz  # PyMuPDF
import re
from typing import Dict, Optional, List, Any
import pandas as pd
import camelot
import os # Importado para basename em get_raw_tables_from_page


# NOVO: Função para extrair a sala padrão de 'salas_info'
def get_default_room(salas_info_text: Optional[str]) -> Optional[str]:
    """Tenta extrair a primeira sala principal mencionada em salas_info."""
    if not salas_info_text:
        return None

    # Tenta encontrar padrões como "P2 - Sala 7" ou "Sala 9" (ignorando case)
    # Pega a primeira correspondência encontrada
    match = re.search(r"(P\d\s*[-–—]?\s*Sala\s*\d+|Sala\s*\d+)", salas_info_text, re.IGNORECASE)
    if match:
        # Normaliza espaços extras se encontrados
        return ' '.join(match.group(1).split())
    else:
        # Se não encontrar um padrão claro, pode retornar a primeira parte antes da vírgula
        # como uma tentativa menos precisa
        parts = salas_info_text.split(',')
        first_part = parts[0].strip()
        # Evita retornar strings muito genéricas ou vazias
        if len(first_part) > 2 and "indicado" not in first_part.lower():
             return first_part
        else:
             return None # Não conseguiu determinar uma sala padrão razoável
            
def extract_horario_metadata(page: fitz.Page) -> Dict[str, Optional[str]]:
    """Extrai metadados (Semestre, Curso/Turma, Sala) do texto de uma página de horário."""
    metadata = {"semestre": None, "turma": None, "salas_info": None}
    text = page.get_text("text")
    lines = text.split('\n')

    # Padrões Regex (ajuste conforme necessário)
    semestre_pattern = re.compile(r"^\s*\d+/\d{4}\s*$") # Ex: 1/2025 (com espaços opcionais)
    # Captura tudo após "CIÊNCIA DA COMPUTAÇÃO -", incluindo período/optativas/re-ofertas
    turma_pattern = re.compile(r"CIÊNCIA DA COMPUTAÇÃO\s*[-–—]\s*(.+)", re.IGNORECASE)
    salas_pattern = re.compile(r"SALAS?:\s*(.+)", re.IGNORECASE)

    # Limita a busca às primeiras linhas para eficiência
    lines_to_check = lines[:15] # Verifica as primeiras 15 linhas

    for line in lines_to_check:
        line = line.strip()
        if not metadata["semestre"] and semestre_pattern.match(line):
            metadata["semestre"] = line
        elif not metadata["turma"] and turma_pattern.search(line):
            # Pega todo o texto após o traço como informação da turma
            metadata["turma"] = turma_pattern.search(line).group(1).strip()
        elif not metadata["salas_info"] and salas_pattern.search(line):
             metadata["salas_info"] = salas_pattern.search(line).group(1).strip()

        # Otimização: Para quando encontrar os 3 (ou após verificar as linhas limitadas)
        if metadata["semestre"] and metadata["turma"] and metadata["salas_info"]:
             break
    return metadata

def get_raw_tables_from_page(pdf_path: str, page_num: int) -> List[pd.DataFrame]:
    """Extrai todas as tabelas brutas de uma página usando Camelot (lattice)."""
    tables_found = []
    try:
        # line_scale ajuda a detectar linhas finas. edge_tol ajusta a tolerância das bordas.
        tables = camelot.read_pdf(
            pdf_path,
            pages=str(page_num),
            flavor='lattice',
            line_scale=40, # Pode precisar ajustar
            # edge_tol=500 # Descomente e ajuste se colunas estiverem sendo mescladas
            )
        if tables:
            tables_found = [tbl.df for tbl in tables]
    except Exception as e:
        # Imprime erro mas continua, retornando lista vazia
        print(f"Alerta: Erro no Camelot ao processar pág {page_num} de '{os.path.basename(pdf_path)}': {e}")
    return tables_found

# Dentro de src/horario_parser.py

# Dentro de src/horario_parser.py

def parse_cell_content(cell_text: str) -> Dict[str, Optional[str]]:
    """Extrai Disciplina, Professor e Sala de uma célula da tabela de horário (VERSÃO 2 - Foco em Labs)."""
    aula = {"disciplina": None, "professor": None, "sala": None}
    if pd.isna(cell_text) or not str(cell_text).strip():
        return aula

    text = str(cell_text).strip()
    text = ' '.join(text.split()) # Normaliza espaços e quebras de linha

    professor = None
    sala = None
    disciplina = text # Começa assumindo que tudo é disciplina

    # 1. Tenta extrair e REMOVER o professor primeiro
    prof_match = re.search(r"\(([^)]+)\)", disciplina)
    if prof_match:
        professor = prof_match.group(1).strip()
        # Remove professor E espaços adjacentes da string disciplina
        disciplina = (disciplina[:prof_match.start()] + disciplina[prof_match.end():]).strip()

    # 2. Tenta extrair e REMOVER a SALA da string restante (disciplina)
    #    Padrões mais específicos primeiro. Adicionado (?i) para ignorecase direto na regex.
    #    Busca o padrão no FINAL da string ($) ou seguido por espaço/fim ($|\s)
    #    Modificado para tratar espaços opcionais e diferentes traços de forma mais robusta.
    sala_patterns_ordered = [
        # Padrões com Prédio/Lab e número (mais específicos)
        r"(?i)(P\d\s*[-–—]?\s*Sala\s*\d+)",  # P2 – Sala 7
        r"(?i)(LabCC\s*[-–—]?\s*P\d)",      # LabCC – P2
        r"(?i)(LabRedes\s*[-–—]?\s*P\d)",   # LabRedes-P2
        # Padrões mais genéricos
        r"(?i)(Sala\s*\d+)",                # Sala 6
        r"(?i)(LabCC)",                    # LabCC (sozinho)
        r"(?i)(LabRedes)"                  # LabRedes (sozinho)
    ]

    found_sala_match = None
    for pattern in sala_patterns_ordered:
        # Tenta encontrar o padrão na string atual da disciplina
        # Usamos finditer para pegar todas as ocorrências
        matches = list(re.finditer(pattern, disciplina))
        if matches:
            # Pega a ÚLTIMA ocorrência encontrada (mais provável ser a sala no final)
            last_match = matches[-1]
            potential_sala = last_match.group(1).strip()
            potential_sala = ' '.join(potential_sala.split()) # Normaliza espaços internos

            # *** Critério Chave: Aceita o match se ele estiver no final da string ***
            # Tolerância pequena para caracteres residuais (como espaços extras que strip() pegaria)
            if last_match.end() >= len(disciplina) - 1:
                sala = potential_sala
                # Remove a sala encontrada da disciplina
                disciplina = disciplina[:last_match.start()].strip()
                found_sala_match = True # Marca que encontrou
                break # Para no primeiro padrão específico que casou no final

    # Se não encontrou um match no final, verifica se algum match (não necessariamente no final) ocorreu
    # Isso é um fallback caso a sala esteja no meio por algum motivo estranho (menos provável)
    # if not found_sala_match:
        # Lógica de fallback poderia ser adicionada aqui se necessário,
        # mas vamos focar em encontrar no final primeiro.

    # 3. Limpeza final da disciplina
    disciplina = disciplina.strip(' -')

    # Atualiza o dicionário de retorno
    aula["disciplina"] = disciplina if disciplina else None
    aula["professor"] = professor
    aula["sala"] = sala # Contém a sala específica se encontrada, senão None
    # print(f"----> [parse_cell_content V2] Texto: '{cell_text}' -> Resultado: {aula}") # Descomente para depurar
    return aula

# O resto do arquivo (get_default_room, process_horario_df, etc.) permanece igual
# ... (manter as funções get_default_room, get_raw_tables_from_page, process_horario_df, extract_schedule_from_page) ...

# Bloco if __name__ == '__main__': também permanece igual

# O resto do arquivo (get_default_room, process_horario_df, etc.) permanece igual
# ...

def process_horario_df(raw_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Limpa, estrutura e parseia um DataFrame bruto de horário."""
    if raw_df.empty:
        return None

    df = raw_df.copy()

    # --- Limpeza Preliminar ---
    # Substitui strings vazias por NaN para facilitar dropna e ffill
    df.replace(r'^\s*$', pd.NA, regex=True, inplace=True)

    # --- Identificação do Cabeçalho (Dias da Semana) ---
    header_row_index = -1
    dias_semana_keywords = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
    for i, row in df.iterrows():
        row_str = ' '.join(row.dropna().astype(str))
        if any(dia in row_str for dia in dias_semana_keywords):
            header_row_index = i
            break

    if header_row_index == -1:
        print("Alerta: Não foi possível encontrar a linha de cabeçalho (dias da semana). Tentando a primeira linha.")
        # Se não achar, tenta usar a primeira linha como cabeçalho se ela tiver pelo menos 3 colunas não vazias
        if df.iloc[0].dropna().count() >= 3:
             header_row_index = 0
        else:
             print("Erro: Primeira linha também não parece ser cabeçalho. Abortando processamento da tabela.")
             return None

    # --- Promove Cabeçalho e Limpa Linhas Acima ---
    df.columns = df.iloc[header_row_index]
    df = df.iloc[header_row_index + 1:].reset_index(drop=True)

    # --- Renomeia Coluna de Horário e Remove Colunas Vazias ---
    # Assume que a primeira coluna sempre contém o horário ou metadados da linha
    if df.columns[0] is pd.NA or str(df.columns[0]).strip() == "":
         df.rename(columns={df.columns[0]: "HorarioInfo"}, inplace=True)
    # Remove colunas que são *inteiramente* vazias
    df.dropna(axis=1, how='all', inplace=True)

    # Identifica as colunas que realmente são dias da semana pelo nome
    day_columns = [col for col in df.columns if isinstance(col, str) and any(kw in col for kw in dias_semana_keywords)]

    # --- Tratamento de Células Mescladas e Linhas Irrelevantes ---
    # Preenche valores NaN PARA BAIXO (ffill) nas colunas dos dias
    # Isso propaga a aula da célula mesclada para as linhas abaixo dela
    df[day_columns] = df[day_columns].ffill()

    # Remove linhas onde TODOS os dias da semana são NaN (linhas divisórias, ALMOÇO, etc.)
    df.dropna(subset=day_columns, how='all', inplace=True)

    # --- Parseamento do Conteúdo das Células ---
    for day_col in day_columns:
        if day_col in df.columns: # Checa se a coluna existe
            # Aplica a função parse_cell_content a cada célula da coluna do dia
            df[day_col] = df[day_col].apply(parse_cell_content)

    # --- Limpeza Final ---
    # Remove linhas onde todas as células de dias da semana, após o parse, não têm disciplina
    def check_row_fully_parsed_empty(row):
        for day in day_columns:
            # Verifica se a coluna existe na linha e se o dicionário tem uma 'disciplina' não nula
            if day in row.index and isinstance(row[day], dict) and row[day].get("disciplina"):
                return False # Encontrou uma disciplina, linha não está vazia
        return True # Nenhuma disciplina encontrada em nenhum dia
    df = df[~df.apply(check_row_fully_parsed_empty, axis=1)]

    return df.reset_index(drop=True)


def extract_schedule_from_page(pdf_path: str, page_num: int) -> Optional[Dict[str, Any]]:
    """Função principal: Orquestra a extração e preenche salas vazias."""
    print(f"\n--- Processando Página {page_num} ---")
    doc = None
    metadata = {} # Inicializa metadata
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
             print(f"Erro: Número da página {page_num} inválido.")
             return None
        page = doc.load_page(page_num - 1)
        metadata = extract_horario_metadata(page) # <<< GUARDA OS METADADOS AQUI
        print(f"Metadados encontrados: {metadata}")
    except Exception as e:
        print(f"Erro ao abrir PDF ou extrair metadados da página {page_num}: {e}")
        if doc: doc.close()
        return None
    finally:
         if doc: doc.close()

    raw_tables = get_raw_tables_from_page(pdf_path, page_num)

    if not raw_tables:
        print(f"Nenhuma tabela encontrada por Camelot na página {page_num}.")
        return None

    if len(raw_tables) > 1:
        print(f"Alerta: Múltiplas tabelas ({len(raw_tables)}) encontradas na página {page_num}. Processando a primeira.")

    processed_df = process_horario_df(raw_tables[0])

    if processed_df is not None and not processed_df.empty:
        # --- Limpeza dos nomes das colunas (código anterior) ---
        cleaned_columns = []
        for i, col in enumerate(processed_df.columns):
            if pd.isna(col):
                cleaned_columns.append(f"Coluna_Vazia_{i}")
            else:
                col_str = str(col).strip()
                if not col_str:
                     cleaned_columns.append(f"Coluna_Vazia_{i}")
                else:
                     cleaned_columns.append(col_str)
        processed_df.columns = cleaned_columns
        # --- Fim da Limpeza dos nomes das colunas ---

        # Converte para dicionário ANTES de preencher as salas
        horario_dict = processed_df.to_dict(orient='records')

        # --- >>> INÍCIO: Lógica para preencher salas vazias <<< ---
        default_room = get_default_room(metadata.get("salas_info")) # Pega a sala padrão
        if default_room:
            print(f"----> Sala padrão detectada: '{default_room}'")
            # Itera pelas linhas (horários) e depois pelas colunas (dias)
            for row_dict in horario_dict:
                for key, value in row_dict.items():
                    # Verifica se o valor é um dicionário de aula e se a sala é None/null
                    if isinstance(value, dict) and value.get("disciplina") and value.get("sala") is None:
                        # Preenche com a sala padrão
                        value["sala"] = default_room
        else:
             print(f"----> Nenhuma sala padrão clara encontrada em 'salas_info'. Salas vazias permanecerão null.")
        # --- >>> FIM: Lógica para preencher salas vazias <<< ---


        print(f"Tabela da página {page_num} processada com sucesso (salas vazias preenchidas).")
        return {
            "pagina": page_num,
            **metadata,
            "horario": horario_dict # Retorna o dicionário já modificado
        }
    else:
        print(f"Falha ao processar a tabela da página {page_num} após extração.")
        return None

# Exemplo de como usar (pode ser executado se o script for rodado diretamente)
if __name__ == '__main__':
    # Coloque um PDF de teste na mesma pasta ou ajuste o caminho
    test_pdf = 'exemplo_horario.pdf' # Mude para o nome do seu PDF de horário
    test_page = 1

    if os.path.exists(test_pdf):
         result = extract_schedule_from_page(test_pdf, test_page)
         if result:
             print("\n--- Resultado da Extração ---")
             import json
             print(json.dumps(result, indent=2, ensure_ascii=False))
         else:
             print(f"\nNenhum horário válido extraído da página {test_page}.")
    else:
         print(f"Arquivo de teste '{test_pdf}' não encontrado. Crie um ou ajuste o caminho.")