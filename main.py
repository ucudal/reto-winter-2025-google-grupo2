# main.py

import os
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv

from fastapi import FastAPI
from pydantic import BaseModel

# --- 1. Inicialización y Configuración ---

# Carga la API Key
load_dotenv()
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except TypeError:
    print("🚨 Error: No se encontró la API Key. Revisa tu archivo .env.")
    exit()

# Inicializa la app FastAPI
app = FastAPI()

# Modelo Pydantic para validar el cuerpo de la solicitud
class Question(BaseModel):
    query: str

# Conecta con la base de datos ChromaDB existente
print("🧠 Conectando con la base de datos ChromaDB...")
client = chromadb.PersistentClient(path="./chroma")
collection = client.get_collection(name="ithaka_docs")
print("✅ Conexión exitosa.")

# --- 2. Lógica del Endpoint de la API ---

@app.post("/ask")
def ask_question(question: Question):
    """
    Recibe una pregunta, busca en la base de datos y genera una respuesta.
    """
    user_query = question.query

    # --- PASO 1: BUSCAR (Retrieve) ---
    # Crea un embedding para la pregunta del usuario
    query_embedding = genai.embed_content(
        model="models/text-embedding-004",
        content=user_query,
        task_type="RETRIEVAL_QUERY"
    )['embedding']

    # Busca en ChromaDB los 5 fragmentos más relevantes
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=5
    )
    
    # Extrae los documentos encontrados
    context = "\n".join(results['documents'][0])

    # --- PASO 2: AUMENTAR (Augment) ---
    # Crea el prompt aumentado para el modelo generativo
    prompt_template = f"""
    Eres un asistente servicial y amigable para la incubadora Ithaka.
    Tu misión es responder las preguntas de los emprendedores basándote ÚNICAMENTE en el contexto proporcionado.
    Si la respuesta no se encuentra en el contexto, debes decir "Lo siento, no tengo información sobre ese tema en mis documentos. ¿Puedo ayudarte con otra cosa?".
    No inventes información.

    CONTEXTO:
    {context}

    PREGUNTA:
    {user_query}

    RESPUESTA:
    """

    # --- PASO 3: GENERAR (Generate) ---
    # Llama al modelo generativo de Gemini
    generative_model = genai.GenerativeModel('gemini-1.5-flash')
    response = generative_model.generate_content(prompt_template)

    return {"answer": response.text}

# --- 3. Punto de entrada para correr el servidor ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)