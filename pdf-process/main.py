import functions_framework
import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part

@functions_framework.http
def process_user_file(request):
    """
    Procesa un archivo de GCS con un modelo multimodal de Vertex AI.
    La autenticación es automática a través de la cuenta de servicio de la función.
    """
    # Extrae los datos del request JSON
    request_json = request.get_json(silent=True)
    if not request_json:
        return {"error": "Invalid JSON."}, 400

    gcs_uri = request_json.get('gcs_uri')
    prompt = request_json.get('prompt')
    mime_type = request_json.get('mime_type')

    if not all([gcs_uri, prompt, mime_type]):
        return {"error": "Missing required fields: gcs_uri, prompt, mime_type."}, 400

    try:
        # Inicializa Vertex AI usando las credenciales del entorno de la Cloud Function
        project_id = os.environ.get('GCP_PROJECT')
        location = "us-central1"
        vertexai.init(project=project_id, location=location)

        # Carga el modelo y prepara el contenido
        model = GenerativeModel("gemini-2.0-flash-001")
        file_part = Part.from_uri(uri=gcs_uri, mime_type=mime_type)
        contents = [prompt, file_part]

        # Genera la respuesta
        response = model.generate_content(contents)
        print(response.text)
        return {"answer": response.text}, 200

    except Exception as e:
        # Imprime el error en los logs para poder depurarlo
        print(f"ERROR: {str(e)}")
        return {"error": f"An internal error occurred: {str(e)}"}, 500