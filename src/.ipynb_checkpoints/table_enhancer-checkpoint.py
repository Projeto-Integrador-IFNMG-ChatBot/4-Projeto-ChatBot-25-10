import pandas as pd
from typing import Dict, Any

def enhance_table(raw_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Recebe um DataFrame bruto e realiza um processo completo de limpeza,
    separação de legenda e sumarização semântica, lidando com colunas duplicadas.
    """
    if raw_df.empty:
        return {}

    # 1. SEPARA A LEGENDA DA TABELA
    numero_de_linhas_legenda = 1 
    df_tabela_bruta = raw_df.iloc[:-numero_de_linhas_legenda]
    df_legenda = raw_df.iloc[-numero_de_linhas_legenda:]
    legenda_texto = ' '.join(df_legenda.iloc[:, 0].dropna().astype(str).tolist()).replace('\n', ' ')
    
    # 2. LIMPEZA INTELIGENTE DA TABELA
    table_title = df_tabela_bruta.iloc[0, 0].strip() if not df_tabela_bruta.empty else ""
    header_row_index = -1
    for i, row in df_tabela_bruta.iterrows():
        non_empty_cells = [cell for cell in row if str(cell).strip()]
        if len(non_empty_cells) > 3 and all(len(str(c).strip()) < 5 for c in non_empty_cells):
            header_row_index = i
            break
            
    if header_row_index == -1:
        return {"legend": legenda_texto, "summary": "Não foi possível identificar o cabeçalho da tabela."}

    # --- INÍCIO DA CORREÇÃO PARA COLUNAS DUPLICADAS ---
    header_list = df_tabela_bruta.iloc[header_row_index].astype(str).tolist()
    
    # Lógica para tornar os nomes de colunas únicos (ex: 'Q', 'Q' -> 'Q_1', 'Q_2')
    counts = {}
    unique_header = []
    for col_name in header_list:
        counts[col_name] = counts.get(col_name, 0) + 1
        if counts[col_name] > 1:
            unique_header.append(f"{col_name}_{counts[col_name]}")
        else:
            unique_header.append(col_name)
    # --- FIM DA CORREÇÃO ---

    cleaned_df = df_tabela_bruta.copy()
    cleaned_df.columns = unique_header # Usa a lista de cabeçalhos únicos
    cleaned_df = cleaned_df.iloc[header_row_index + 1:].reset_index(drop=True)
    cleaned_df.dropna(axis=0, how='all', inplace=True)
    cleaned_df.dropna(axis=1, how='all', inplace=True)
    cleaned_df = cleaned_df.astype(str).map(lambda x: ' '.join(str(x).split()))
    
    # 3. GERAÇÃO DO RESUMO SEMÂNTICO
    summary = f"A tabela '{table_title}' descreve um calendário. A legenda informa: '{legenda_texto}'. Detalhes do calendário: "
    rows_summaries = []
    for index, row in cleaned_df.iterrows():
        week_summary_parts = []
        for day_name, day_number in row.items():
            day_name_clean = day_name.split('_')[0] # Remove o sufixo _2, _3 etc.
            if day_name_clean and str(day_number).strip() and str(day_number).lower() not in ['nan', 'none', '']:
                week_summary_parts.append(f"dia {day_name_clean} é {day_number}")
        if week_summary_parts:
            rows_summaries.append(f"na semana {index + 1}, " + ", ".join(week_summary_parts))
            
    summary += "; ".join(rows_summaries) + "."
    
    return {
        "cleaned_table": cleaned_df.to_dict(orient='records'),
        "legend": legenda_texto,
        "summary": summary
    }