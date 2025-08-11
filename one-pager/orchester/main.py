import functions_framework
import requests
import json
import google.auth
import google.auth.transport.requests
from generate_pdf import generate_pdf, save_pdf_to_gcs
import uuid
import os
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token
import pyshorteners

# --- Configuraciones ---
TEXT_FUNCTION_URL = "https://generate-one-pager-591960777083.us-central1.run.app/"
BANNER_FUNCTION_URL = "https://banner-generation-591960777083.us-central1.run.app/"

def get_id_token(audience):
    """Obtiene un ID token usando la cuenta de servicio adjunta o ADC."""
    auth_req = g_requests.Request()
    return id_token.fetch_id_token(auth_req, audience)

@functions_framework.http
def generate_one_pager(request):
    """
    Orquesta la llamada a las funciones de texto y banner usando ID Tokens
    generados automáticamente desde la cuenta de servicio adjunta (ADC).
    """
    try:
        # 1. Validación de la entrada
        data = request.get_json(silent=True)
        if not data:
            return {"error": "Carga JSON inválida o vacía"}, 400

        idea_description = data.get("idea_description")
        banner_prompt = data.get("banner_prompt")

        if not idea_description or not banner_prompt:
            return {
                "error": "Faltan los campos requeridos 'idea_description' o 'banner_prompt'"
            }, 400

        # --- 2. Llamada a la función que genera el texto ---
        text_headers = {
            "Authorization": f"Bearer {get_id_token(TEXT_FUNCTION_URL)}",
            "Content-Type": "application/json"
        }

        print(f"Llamando a {TEXT_FUNCTION_URL}...")
        text_response = requests.post(
            TEXT_FUNCTION_URL,
            json={"idea_description": idea_description},
            headers=text_headers
        )
        text_response.raise_for_status()
        text_result = text_response.json()
        print("Llamada a la función de texto exitosa.")

        # --- 3. Llamada a la función que genera el banner ---
        banner_headers = {
            "Authorization": f"Bearer {get_id_token(BANNER_FUNCTION_URL)}",
            "Content-Type": "application/json"
        }

        print(f"Llamando a {BANNER_FUNCTION_URL}...")
        banner_response = requests.post(
            BANNER_FUNCTION_URL,
            json={"prompt": banner_prompt},
            headers=banner_headers
        )
        banner_response.raise_for_status()
        banner_result = banner_response.json()
        print("Llamada a la función de banner exitosa.")

        # --- 4. Devolver la respuesta combinada ---
        full_response = {
            "idea_text": text_result["one_pager_content"],
            "banner_url": banner_result.get("image_url")
        }

        pdf_title = f'title_{uuid.uuid4()}.pdf'
        generate_pdf(full_response["idea_text"], full_response["banner_url"], pdf_title)

        gcs_url = save_pdf_to_gcs(pdf_title, f"one-pagers/{pdf_title}")

        # Eliminar archivo local después de subirlo
        if os.path.exists(pdf_title):
            os.remove(pdf_title)
        s = pyshorteners.Shortener()

        return {"url":s.tinyurl.short(gcs_url)}, 200

    except requests.exceptions.HTTPError as e:
        error_details = e.response.text if e.response else "Sin detalles de respuesta."
        print(f"Error HTTP al llamar a la función downstream: {e}\nDetalles: {error_details}")
        return {
            "error": f"Error al llamar a la función de destino: {str(e)}",
            "details": error_details
        }, 502

    except Exception as e:
        print(f"Ocurrió un error interno: {e}")
        return {"error": f"Error interno del servidor: {str(e)}"}, 500
