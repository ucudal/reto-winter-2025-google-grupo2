import os
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

from ingest import load_all_documents, chunk_text

if __name__ == "__main__":
    load_dotenv()
    print("Configurando API Key...")
    try:
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        print("API Key configurada.")
    except (TypeError, KeyError):
        print("No se encontró la API Key. Revisa tu archivo .env.")
        exit()

    # --- Carga y Procesamiento de Documentos ---
    document_text = load_all_documents(data_path="data/")
    if not document_text:
        print("No se encontró texto en los documentos. Revisa la carpeta 'data'.")
        exit()
    
    text_chunks = chunk_text(document_text)
    print(f"Documentos procesados. Se generaron {len(text_chunks)} fragmentos de texto.")

    # --- Inicialización de ChromaDB ---
    print("\nInicializando ChromaDB...")
    client = chromadb.PersistentClient(path="./chroma")
    collection_name = "ithaka_docs"
    collection = client.get_or_create_collection(name=collection_name)
    print(f"Colección '{collection_name}' lista.")

    # --- Generación de Embeddings y Guardado ---
    print("\nGenerando embeddings con Gemini y guardando en ChromaDB...")
    print("(Esto puede tardar varios minutos)")
    
    count = 0
    batch_size = 100
    for i in range(0, len(text_chunks), batch_size):
        batch_chunks = text_chunks[i:i+batch_size]
        try:
            response = genai.embed_content(
                model="models/text-embedding-004",
                content=batch_chunks,
                task_type="RETRIEVAL_DOCUMENT"
            )
            ids = [f"chunk_{j}" for j in range(i, i + len(batch_chunks))]
            collection.add(
                embeddings=response['embedding'],
                documents=batch_chunks,
                ids=ids
            )
            count += len(batch_chunks)
            print(f"  ... Lote {i//batch_size + 1} procesado. Total guardado: {count}")
        except Exception as e:
            print(f"Error procesando el lote que empieza en el fragmento {i}: {e}")

    print(f"\n¡Éxito! Se guardaron {count} de {len(text_chunks)} fragmentos en la base de datos.")
