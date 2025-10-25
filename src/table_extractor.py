import camelot
import pandas as pd

def extract_raw_dataframe(pdf_path: str, page: int) -> pd.DataFrame:
    """
    Extrai a primeira tabela de uma página de um PDF e a retorna
    como um DataFrame bruto do Pandas, sem nenhum processamento.
    """
    try:
        tables = camelot.read_pdf(pdf_path, pages=str(page), flavor='lattice')
        if tables:
            # Retorna o DataFrame bruto diretamente
            return tables[0].df
    except Exception as e:
        print(f"Erro no Camelot ao processar pág {page} de {pdf_path}: {e}")
    
    # Se nenhuma tabela for encontrada ou ocorrer um erro, retorna um DataFrame vazio
    return pd.DataFrame()