import fitz # PyMuPDF
import os
from typing import List, Dict, Any

def extract_images_from_pdf(pdf_path: str, page_number_1_indexed: int, output_dir: str) -> List[Dict]:
    """
    Extrai imagens de uma página específica de um PDF e as salva em um diretório.
    Gera um dicionário de metadados para cada imagem extraída.

    Args:
        pdf_path: Caminho para o arquivo PDF.
        page_number_1_indexed: O número da página (começando de 1) de onde extrair as imagens.
        output_dir: O diretório onde as imagens extraídas serão salvas.

    Returns:
        Uma lista de dicionários, onde cada dicionário contém metadados
        sobre uma imagem extraída (ex: caminho, tipo, dimensões).
    """
    os.makedirs(output_dir, exist_ok=True) # Garante que o diretório de saída exista
    
    extracted_images_info = []
    
    try:
        with fitz.open(pdf_path) as doc:
            # PyMuPDF é 0-indexado para páginas
            page = doc.load_page(page_number_1_indexed - 1)
            
            image_list = page.get_images(full=True) # full=True para detalhes completos
            
            for img_index, img in enumerate(image_list):
                xref = img[0] # xref é o identificador único da imagem no PDF
                base_image = doc.extract_image(xref)
                
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                image_width = base_image["width"]
                image_height = base_image["height"]
                
                # Gera um nome de arquivo único para a imagem
                image_filename = f"{os.path.basename(pdf_path).replace('.pdf', '')}_page{page_number_1_indexed}_img{img_index}.{image_ext}"
                image_filepath = os.path.join(output_dir, image_filename)
                
                # Salva a imagem no disco
                with open(image_filepath, "wb") as img_file:
                    img_file.write(image_bytes)
                
                # Adiciona metadados da imagem
                image_info = {
                    "image_filename": image_filename,
                    "image_filepath": image_filepath,
                    "page_number": page_number_1_indexed,
                    "extension": image_ext,
                    "width": image_width,
                    "height": image_height,
                    # Adicionalmente, pode-se tentar capturar texto ao redor como legenda
                    # ou coordenadas da imagem na página se necessário.
                }
                extracted_images_info.append(image_info)
                
    except Exception as e:
        print(f"Erro ao extrair imagens da página {page_number_1_indexed} de '{os.path.basename(pdf_path)}': {e}")
        
    return extracted_images_info