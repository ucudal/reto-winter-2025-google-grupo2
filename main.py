from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import vertexai
from vertexai.generative_models import GenerativeModel, Part
# Importa la librería cliente de Vertex AI Search (Discovery Engine)
from google.cloud import discoveryengine
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde .env
load_dotenv()

app = FastAPI()

# Obtén las variables de entorno
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID") # ID de tu motor de búsqueda de Vertex AI Search (engine_id)
DATA_STORE_ID = os.getenv("DATA_STORE_ID") # ID de tu almacén de datos de Vertex AI Search (data_store_id)

# Verifica que las variables de entorno necesarias estén configuradas
if not all([PROJECT_ID, LOCATION, SEARCH_ENGINE_ID, DATA_STORE_ID]):
    raise ValueError(
        "Las variables de entorno PROJECT_ID, LOCATION, SEARCH_ENGINE_ID y DATA_STORE_ID deben estar configuradas."
    )

# Inicializa Vertex AI.
# Si GOOGLE_APPLICATION_CREDENTIALS está configurado en tu entorno,
# vertexai.init() lo detectará automáticamente.
# No necesitas pasar api_key si estás usando credenciales de cuenta de servicio.
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
except Exception as e:
    print(f"Error al inicializar Vertex AI: {e}")
    raise HTTPException(
        status_code=500, detail=f"Error al inicializar Vertex AI: {str(e)}"
    )

# Inicializa el modelo Gemini
model = GenerativeModel("gemini-2.5-flash-lite")

# Inicializa el cliente de Vertex AI Search (Discovery Engine)
# El cliente usará automáticamente las credenciales configuradas por vertexai.init
# o por GOOGLE_APPLICATION_CREDENTIALS.
try:
    search_client = discoveryengine.SearchServiceClient()
except Exception as e:
    print(f"Error al inicializar el cliente de Vertex AI Search: {e}")
    raise HTTPException(
        status_code=500, detail=f"Error al inicializar el cliente de búsqueda: {str(e)}"
    )

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
async def query(request: QueryRequest):
    user_query = request.query

    # Construye el nombre del serving config para el motor de búsqueda.
    # El formato correcto para un motor de búsqueda es:
    # projects/{project_id}/locations/{location}/dataStores/{data_store_id}/servingConfigs/{serving_config_id}
    # Donde serving_config_id es el SEARCH_ENGINE_ID (engine_id)
    serving_config = search_client.serving_config_path(
        project=PROJECT_ID,
        location=LOCATION,
        data_store=DATA_STORE_ID, # Ahora se incluye el data_store_id
        serving_config=SEARCH_ENGINE_ID, # Este es el engine_id
    )

    # 1. Realiza la consulta a Vertex AI Search
    try:
        # Crea una solicitud de búsqueda
        search_request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=user_query,
            page_size=5,  # Puedes ajustar el número de resultados deseados
        )

        # Ejecuta la búsqueda
        search_response = search_client.search(search_request)

        documents = []
        for result in search_response.results:
         for result in search_response.results:
             doc_content = None
             # … rest of processing logic …

            doc_content = None
            if result.document:
                # Priorizamos la extracción de 'extractive_answers' si está presente
                if hasattr(result.document, 'derived_struct_data') and \
                   'extractive_answers' in result.document.derived_struct_data:
                    
                    extractive_answers = result.document.derived_struct_data['extractive_answers']
                    
                    # 'extractive_answers' es una lista de objetos, cada uno con un campo 'content'
                    extracted_texts = []
                    for answer_struct in extractive_answers:
                        if 'content' in answer_struct:
                            extracted_texts.append(answer_struct['content'])
                    
                    if extracted_texts:
                        doc_content = "\n".join(extracted_texts)
                
                # Si no se encontró contenido en 'extractive_answers', intentamos con .content o .struct_data
                if doc_content is None:
                    if result.document.content:
                        doc_content = result.document.content
                    elif result.document.struct_data:
                        # Si el documento es estructurado (ej. JSON), el contenido relevante
                        # podría estar en un campo dentro de struct_data.
                        # Aquí intentamos convertirlo a cadena para incluirlo en el contexto.
                        # Podrías necesitar una lógica más específica para extraer campos concretos.
                        
                        # Intenta extraer de un campo común 'text_content' o 'text'
                        if 'text_content' in result.document.struct_data:
                            doc_content = result.document.struct_data['text_content']
                        elif 'text' in result.document.struct_data:
                            doc_content = result.document.struct_data['text']
                        elif 'body' in result.document.struct_data:
                            doc_content = result.document.struct_data['body']
                        else:
                            # Si no se encuentra un campo específico, convierte todo el struct_data a string
                            doc_content = str(result.document.struct_data)
                
                # Añade el contenido extraído si no es None
                if doc_content:
                    documents.append(doc_content)
                else:
                    documents.append(f"Documento sin contenido claramente extraíble: {result.document.name if result.document else 'N/A'}")
            else:
                documents.append("Resultado de búsqueda sin documento.")


        if not documents:
            document_content = "No se encontraron documentos relevantes en Vertex AI Search."
        else:
            # Concatena los documentos encontrados para usarlos como contexto
            document_content = "\n\n".join(documents)

    except Exception as e:
        print(f"Error al realizar la búsqueda en Vertex AI Search: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error al consultar Vertex AI Search: {str(e)}"
        )

    # 2. Aumenta el prompt con el contexto
    # Asegúrate de que el prompt sea claro para el modelo.
    prompt = f"""Basado en la siguiente información, responde a la pregunta.
Si la información proporcionada no es suficiente para responder la pregunta, indica que no tienes suficiente información.

Contexto:
{document_content}

Pregunta: {user_query}
"""

    # 3. Genera la respuesta usando el modelo Gemini
    try:
        responses = model.generate_content([Part.from_text(prompt)])
        if responses.candidates:
            gemini_response = responses.candidates[0].content.parts[0].text
        else:
            gemini_response = "No se obtuvo respuesta del modelo Gemini."
    except Exception as e:
        # Captura cualquier excepción durante la generación de contenido
        print(f"Error al generar contenido con Gemini: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error al generar contenido con Gemini: {str(e)}"
        )

    # 4. Retorna la respuesta
    return {"response": gemini_response}

