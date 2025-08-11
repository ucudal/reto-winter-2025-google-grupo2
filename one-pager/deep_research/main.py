import functions_framework
import os
import vertexai
import requests
from vertexai.generative_models import GenerativeModel

# Estas variables las pasaremos durante el despliegue
SEARCH_API_KEY = os.environ.get('SEARCH_API_KEY')
SEARCH_ENGINE_ID = os.environ.get('SEARCH_ENGINE_ID')

def google_search(query: str) -> str:
    """
    Realiza una búsqueda en Google con la Custom Search API y devuelve un
    contexto de texto con los 3 primeros resultados.
    """
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': SEARCH_API_KEY,
            'cx': SEARCH_ENGINE_ID,
            'q': query,
            'num': 3
        }
        response = requests.get(url, params=params)
        response.raise_for_status() # Lanza un error si la petición HTTP falla
        search_results = response.json().get('items', [])
        
        context = "Contexto de una búsqueda en Google:\n"
        for i, result in enumerate(search_results):
            context += f"- {result.get('title')}: {result.get('snippet')}\n"
        return context
    except Exception as e:
        print(f"Error al buscar en Google: {e}")
        return "No se pudo realizar la búsqueda en Google para obtener contexto."

@functions_framework.http
def generate_one_pager(request):
    """
    Cloud Function que recibe una idea de negocio, busca en Google empresas
    similares y genera un One-Pager con Gemini.
    """
    request_json = request.get_json(silent=True)
    if not request_json or not request_json.get('idea_description'):
        return {"error": "El campo 'idea_description' es requerido."}, 400

    idea = request_json.get('idea_description')

    try:
        # Paso 1: "Deep Research" a través de la búsqueda manual
        search_query = f"startups o empresas de '{idea}'"
        search_context = google_search(search_query)

        # Paso 2: Inicializar Vertex AI
        project_id = os.environ.get('GCP_PROJECT')
        location = "us-central1"
        vertexai.init(project=project_id, location=location)

        model = GenerativeModel("gemini-2.0-flash-001")

        # Paso 3: Construir el prompt, inyectando el contexto de la búsqueda
        prompt = f"""
        Actúa como un analista de negocios experto. Tu tarea es crear un "One-Pager" conciso para un nuevo emprendimiento.
        Utiliza el siguiente contexto de una búsqueda en Google para informar tu análisis.

        **Contexto de Búsqueda:**
        ---
        {search_context}
        ---

        **Idea de Negocio Propuesta:**
        "{idea}"

        **Genera el One-Pager con las siguientes secciones:**
        # One-Pager: [Genera un nombre creativo y profesional para el proyecto]

        ## 1. El Problema
        [Describe el problema que este emprendimiento resuelve.]

        ## 2. La Solución
        [Describe el producto o servicio propuesto.]

        ## 3. Mercado Potencial
        [Describe el tipo de cliente o mercado al que se dirige.]

        ## 4. Panorama Competitivo
        [Basado en el contexto de la búsqueda, nombra las empresas encontradas y describe brevemente qué hacen.]
        """
        
        # Paso 4: Generar y devolver la respuesta
        response = model.generate_content(prompt)
        return {"one_pager_content": response.text}, 200

    except Exception as e:
        print(f"ERROR: {e}")
        return {"error": f"Ocurrió un error interno: {e}"}, 500