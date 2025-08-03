# ingest.py

from pathlib import Path
import docx
import fitz  # PyMuPDF
import pandas as pd

def process_docx(file_path):
    """Lee un archivo .docx y extrae el texto de los párrafos."""
    try:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return ""

def process_pdf(file_path):
    """Lee un archivo .pdf y extrae el texto de cada página."""
    try:
        doc = fitz.open(file_path)
        return "\n".join([page.get_text() for page in doc])
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return ""

def process_csv(file_path):
    """Lee un CSV y convierte cada fila en una descripción textual."""
    try:
        df = pd.read_csv(file_path)
        text_list = []
        for index, row in df.iterrows():
            row_text = ", ".join([f"{col}: {val}" for col, val in row.astype(str).items()])
            text_list.append(row_text)
        return "\n".join(text_list)
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return ""

def load_all_documents(data_path="data/"):
    """Carga todos los documentos de una carpeta y devuelve un único string de texto."""
    all_texts = []
    print("Iniciando procesamiento de documentos...")
    for file_path in Path(data_path).glob("**/*"):
        if file_path.is_file():
            print(f"  - Procesando: {file_path.name}")
            if file_path.suffix == ".docx":
                all_texts.append(process_docx(file_path))
            elif file_path.suffix == ".pdf":
                all_texts.append(process_pdf(file_path))
            elif file_path.suffix == ".csv":
                all_texts.append(process_csv(file_path))
    print("Procesamiento de documentos finalizado.")
    return "\n\n".join(filter(None, all_texts))

def chunk_text(full_text, chunk_size=1000, overlap=100):
    """Divide un texto largo en fragmentos más pequeños con solapamiento."""
    if not full_text:
        return []
    chunks = []
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunks.append(full_text[start:end])
        start += chunk_size - overlap
    return chunks