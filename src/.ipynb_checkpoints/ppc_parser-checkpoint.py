# src/ppc_parser.py

import pandas as pd
from typing import Dict, Any, Optional, List
import re
import os

try:
    from src.horario_parser import get_raw_tables_from_page
except ImportError:
    from .horario_parser import get_raw_tables_from_page
try:
    from src.table_extractor import extract_raw_dataframe
except ImportError:
    from .table_extractor import extract_raw_dataframe


# --- Funções Auxiliares de Limpeza ---

def _clean_string(text: Any) -> Optional[str]:
    if text is None or pd.isna(text):
        return None
    cleaned = str(text).replace('\n', ' ').strip()
    cleaned = ' '.join(cleaned.split()) # Remove espaços duplicados
    return cleaned if cleaned else None

def _get_raw_table_text(raw_df: pd.DataFrame) -> str:
    if raw_df is None or raw_df.empty:
        return ""
    # Concatena todas as células em uma única string
    return raw_df.to_string(header=False, index=False).lower()


# --- Parsers Específicos para cada TIPO de Tabela ---

def _parse_matriz_curricular(raw_df: pd.DataFrame) -> Optional[Dict[str, Any]]:

    df = raw_df.copy()
    
    # 1. Encontrar o Título do Período (ex: "1° PERÍODO")
    periodo_title = None
    for i, row in df.iterrows():
        cell_value = _clean_string(row.iloc[0])
        if cell_value and "PERÍODO" in cell_value.upper():
            periodo_title = cell_value
            break
            
    # 2. Encontrar a Linha de Cabeçalho ("DISCIPLINA")
    header_row_index = -1
    for i, row in df.iterrows():
        cell_value_0 = _clean_string(row.iloc[0])
        if cell_value_0 and "DISCIPLINA" in cell_value_0.upper():
            header_row_index = i
            break
            
    if header_row_index == -1:
        print("Alerta PPC_PARSER: _parse_matriz_curricular não encontrou 'DISCIPLINA'.")
        return None

    # 3. Definir o Início dos Dados (LÓGICA CORRIGIDA)
    data_start_index = header_row_index + 2
    
    if data_start_index >= len(df):
         print(f"Alerta PPC_PARSER: Encontrou cabeçalho mas não encontrou linhas de dados para '{periodo_title}'.")
         return None
    
    # 4. Processar o DataFrame
    data_df = df.iloc[data_start_index:].copy()
    
    expected_columns = [
        'DISCIPLINA', 'CH_Semanal_Teorica', 'CH_Semanal_Pratica',
        'CH_Semanal_Total', 'CH_Semestral_Hora_Aula', 'CH_Semestral_Horas',
        'Pre_Requisitos'
    ]
    
    num_cols = len(data_df.columns)
    if num_cols > len(expected_columns):
        data_df = data_df.iloc[:, :len(expected_columns)]
        num_cols = len(expected_columns)
        
    data_df.columns = expected_columns[:num_cols]
    
    for i in range(num_cols, len(expected_columns)):
        data_df[expected_columns[i]] = None
        
    # 5. Limpar os Dados
    data_df = data_df[data_df['DISCIPLINA'].astype(str).str.contains('TOTAL', case=False, na=False) == False]
    
    for col in data_df.columns:
        data_df[col] = data_df[col].apply(_clean_string)
        
    data_df.dropna(how='all', inplace=True)

    if data_df.empty:
        return None

    table_dict_list = data_df.where(pd.notna(data_df), None).to_dict(orient='records')
    
    return {
        "periodo": periodo_title,
        "disciplinas": table_dict_list
    }

def _parse_optativas(raw_df: pd.DataFrame) -> Optional[Dict[str, Any]]:

    if raw_df is None or raw_df.empty:
        return None

    df = raw_df.copy()

    # 1. Tentar Encontrar a Linha de Cabeçalho ("DISCIPLINA")
    header_row_index = -1
    for i, row in df.iterrows():
        cell_value = _clean_string(row.iloc[0])
        if cell_value and "DISCIPLINA" in cell_value.upper():
            header_row_index = i
            break
            
    # 2. Definir o Início dos Dados
    data_start_index = 0
    if header_row_index != -1:
        data_start_index = header_row_index + 2
    else:
        print(f"Info PPC_PARSER: _parse_optativas não encontrou 'DISCIPLINA'. Tratando como página de continuação.")
            
    if data_start_index >= len(df):
         print(f"Alerta PPC_PARSER: _parse_optativas não encontrou linhas de dados após o índice {data_start_index}.")
         return None
    
    # 3. Processar o DataFrame
    data_df = df.iloc[data_start_index:].copy()
    
    expected_columns = [
        'DISCIPLINA', 'CH_Semanal_Teorica', 'CH_Semanal_Pratica',
        'CH_Semanal_Total', 'CH_Semestral_Hora_Aula', 'CH_Semestral_Horas',
        'Pre_Requisitos'
    ]
    
    num_cols = len(data_df.columns)
    if num_cols > len(expected_columns):
        data_df = data_df.iloc[:, :len(expected_columns)]
        num_cols = len(expected_columns)
        
    data_df.columns = expected_columns[:num_cols]
    
    for i in range(num_cols, len(expected_columns)):
        data_df[expected_columns[i]] = None
        
    # 4. Limpar os Dados
    data_df['DISCIPLINA'] = data_df['DISCIPLINA'].ffill()

    for col in data_df.columns:
        data_df[col] = data_df[col].apply(_clean_string)
        
    data_df.dropna(how='all', inplace=True)
    data_df.dropna(subset=['CH_Semanal_Total'], inplace=True)

    if data_df.empty:
        return None

    def aggregate_text(rows):
        return ' '.join(rows.dropna().unique())

    grouped = data_df.groupby('DISCIPLINA')
    
    aggregated_df = pd.DataFrame({
        'CH_Semanal_Teorica': grouped['CH_Semanal_Teorica'].first(),
        'CH_Semanal_Pratica': grouped['CH_Semanal_Pratica'].first(),
        'CH_Semanal_Total': grouped['CH_Semanal_Total'].first(),
        'CH_Semestral_Hora_Aula': grouped['CH_Semestral_Hora_Aula'].first(),
        'CH_Semestral_Horas': grouped['CH_Semestral_Horas'].first(),
        'Pre_Requisitos': grouped['Pre_Requisitos'].apply(aggregate_text)
    }).reset_index()

    table_dict_list = aggregated_df.where(pd.notna(aggregated_df), None).to_dict(orient='records')
    
    return {
        "disciplinas_optativas": table_dict_list
    }

def _parse_docentes(raw_df: pd.DataFrame) -> Optional[Dict[str, Any]]:

    df = raw_df.copy()
    
    header_row_index = -1
    for i, row in df.iterrows():
        row_str = ' '.join(row.dropna().astype(str)).lower()
        if "nome do professor" in row_str and "regime de trabalho" in row_str:
            header_row_index = i
            break
            
    if header_row_index != -1:
        df = df.iloc[header_row_index + 1:].reset_index(drop=True)

    expected_columns = ['Item', 'Nome do Professor', 'Formacao', 'Regime de Trabalho']
    
    num_cols = len(df.columns)
    if num_cols < 4:
        # Tenta lidar com caso da pág 97 onde 'Item' não existe
        if num_cols == 3:
             print("Alerta PPC_PARSER: Tabela de docente com 3 colunas. Assumindo [Nome, Formacao, Regime].")
             df.columns = expected_columns[1:] # Usa Nome, Formacao, Regime
             df['Item'] = pd.NA # Adiciona coluna de Item vazia
        else:
             print(f"Alerta PPC_PARSER: Tabela de docente com colunas inesperadas ({num_cols}). Pulando.")
             return None
    else:
        df = df.iloc[:, :4]
        df.columns = expected_columns
    
    for col in df.columns:
        df[col] = df[col].apply(_clean_string)
        
    df.dropna(how='all', inplace=True)

    # Preenche 'Item' e 'Nome' para baixo para associar as linhas de formação
    df['Item'] = df['Item'].ffill()
    df['Nome do Professor'] = df['Nome do Professor'].ffill()
    
    df.dropna(subset=['Formacao'], inplace=True)
    
    if df.empty:
        return None

    def aggregate_formation(rows):
        full_formation = ' '.join(rows.dropna())
        return full_formation

    grouped = df.groupby('Nome do Professor')
    
    aggregated_df = pd.DataFrame({
        'Item': grouped['Item'].first(), # Pega o primeiro item
        'Formacao': grouped['Formacao'].apply(aggregate_formation),
        'Regime de Trabalho': grouped['Regime de Trabalho'].last()
    }).reset_index() 

    # Reordena colunas
    final_cols = ['Item', 'Nome do Professor', 'Formacao', 'Regime de Trabalho']
    aggregated_df = aggregated_df[[col for col in final_cols if col in aggregated_df.columns]]
    
    aggregated_df = aggregated_df.where(pd.notna(aggregated_df), None)

    return {
        "docentes": aggregated_df.to_dict(orient='records')
    }

# >>> INÍCIO: Adicionar esta nova função <<<
def _parse_ementario(raw_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Função especializada para extrair dados das tabelas de Ementário (págs 33-85).
    Converte a tabela de 2 colunas (Chave, Valor) em um dicionário Python.
    """
    if raw_df is None or raw_df.empty or len(raw_df.columns) < 2:
        return None
    
    ementa_dict = {}
    current_key = None
    
    # Processa a primeira linha (pode ter 3 ou 4 colunas: Disciplina, Carga, Aulas)
    first_row = raw_df.iloc[0]
    try:
        ementa_dict["disciplina"] = _clean_string(first_row.iloc[1])
        ementa_dict["carga_horaria"] = _clean_string(first_row.iloc[2])
        ementa_dict["aulas_semanais"] = _clean_string(first_row.iloc[3])
    except IndexError:
        pass # Ignora se não houver 3a/4a coluna
    
    # Processa o restante das linhas (chave-valor)
    for i in range(1, len(raw_df)):
        row = raw_df.iloc[i]
        key_cell = _clean_string(row.iloc[0])
        value_cell = _clean_string(row.iloc[1])

        if key_cell:
            # Remove o ":" no final da chave
            current_key = key_cell.strip().rstrip(':').lower().replace(' ', '_')
            if current_key and value_cell:
                ementa_dict[current_key] = value_cell
            elif current_key:
                ementa_dict[current_key] = "" # Chave existe, mas valor está em outra linha
        
        # Se a chave está vazia mas o valor não, concatena com a chave anterior
        elif current_key and value_cell:
            if current_key in ementa_dict:
                 ementa_dict[current_key] += " " + value_cell
            else:
                 ementa_dict[current_key] = value_cell # Segurança

    # Limpa os valores concatenados
    for key, value in ementa_dict.items():
        if isinstance(value, str):
            ementa_dict[key] = ' '.join(value.split())

    # Retorna o dicionário apenas se ele for válido (tiver ementa)
    return ementa_dict if "ementa" in ementa_dict else None


def parse_ppc_page(pdf_path: str, page_num: int) -> Dict[str, Any]:
    """
    Função principal do parser de PPC. (Versão 6 - Modular, Multi-Tabela)
    Extrai TODAS as tabelas e roteia CADA UMA para o parser correto.
    """
    
    # 1. Extrai TODAS as tabelas brutas da página
    raw_tables = get_raw_tables_from_page(pdf_path, page_num)
    
    parsed_data_list = [] # Lista para guardar os dados de todas as tabelas processadas
    raw_table_list = []   # Lista para guardar todas as tabelas brutas
    table_types_found = [] # Lista para guardar os tipos de tabela

    if not raw_tables:
        summary = "Nenhuma tabela encontrada nesta página pelo Camelot."
    else:
        summary = f"{len(raw_tables)} tabelas encontradas. Processando..."
        
        for raw_df in raw_tables:
            if raw_df.empty:
                continue
                
            raw_table_list.append(raw_df.where(pd.notna(raw_df), None).to_dict(orient='records'))
            table_text = _get_raw_table_text(raw_df)
            
            parsed_data = None
            table_type = "ppc_tabela_desconhecida" # Padrão para esta tabela

            if ("disciplina:" in table_text and 
                "ementa:" in table_text and 
                "bibliografia básica:" in table_text):
                
                table_type = "ppc_ementario"
                parsed_data = _parse_ementario(raw_df) 

            elif ("disciplina" in table_text and 
                  "ch semanal" in table_text and 
                  ("pré – requisitos" in table_text or "pré- requisitos" in table_text)):
                
                if "disciplinas optativas" not in table_text:
                    table_type = "ppc_matriz_curricular"
                    parsed_data = _parse_matriz_curricular(raw_df)
                else:
                    table_type = "ppc_optativas"
                    parsed_data = _parse_optativas(raw_df)
            
            elif (page_num >= 25 and page_num <= 28 and ("tópicos especiais" in table_text or "algoritmos geométricos" in table_text)):
                table_type = "ppc_optativas"
                parsed_data = _parse_optativas(raw_df) 

            elif ("nome do professor" in table_text or 
                  ("formação" in table_text and "regime de trabalho" in table_text) or
                  (page_num in [97, 98] and "mestrado em" in table_text)):
                
                table_type = "ppc_docentes"
                parsed_data = _parse_docentes(raw_df)
            
            elif ("componentes curriculares" in table_text and "matriz 2015" in table_text):
                 table_type = "ppc_equivalencia"
                 parsed_data = None # TODO
                 

            # --- Fim do roteamento para esta tabela ---
            table_types_found.append(table_type)
            if parsed_data:
                parsed_data_list.append(parsed_data)
            else:
                if table_type not in ["ppc_tabela_desconhecida", "ppc_equivalencia", "ppc_ementario"]: # Ignora placeholders
                     print(f"Alerta PPC_PARSER: Detectou tipo '{table_type}' na pág {page_num}, mas falhou ao processar os dados.")

        # Atualiza o sumário com os tipos de tabelas processadas
        if table_types_found:
             summary = f"Processadas {len(raw_tables)} tabelas. Tipos detectados: {', '.join(table_types_found)}"

    return {
        "page_type": "ppc", # Tipo geral da página
        "parsed_data_list": parsed_data_list, # Lista de todos os dados de tabelas parseados
        "raw_table_list": raw_table_list, # Lista de todas as tabelas brutas
        "summary": summary
    }