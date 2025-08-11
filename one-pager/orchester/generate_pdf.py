import requests
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from markdown import markdown
from io import BytesIO
from google.cloud import storage
from datetime import timedelta
import google.auth
import google.auth.transport.requests as g_requests


# Configuración de GCP
PROJECT_ID = "valiant-complex-467519-d3"
GCS_BUCKET_NAME = "ithaka-one-pagers"

def generate_pdf(texto_en_markdown, url_imagen, output_filename="output.pdf"):
    """
    Genera un PDF que incluye un banner descargado desde una URL y texto formateado desde Markdown.
    """
    # Descargar la imagen
    response = requests.get(url_imagen)
    if response.status_code != 200:
        raise Exception(f"No se pudo descargar la imagen desde {url_imagen}")
    
    img_data = BytesIO(response.content)

    # Crear documento PDF
    doc = SimpleDocTemplate(output_filename, pagesize=A4)
    elements = []

    # Agregar imagen como banner
    banner = Image(img_data)
    banner.drawWidth = A4[0]
    banner.drawHeight = banner.drawWidth * banner.imageHeight / banner.imageWidth
    elements.append(banner)
    elements.append(Spacer(1, 0.5 * inch))

    # Convertir markdown a HTML
    html_text = markdown(texto_en_markdown)

    # Agregar texto
    styles = getSampleStyleSheet()
    paragraph = Paragraph(html_text, styles["Normal"])
    elements.append(paragraph)

    # Generar PDF
    doc.build(elements)
    return output_filename

def save_pdf_to_gcs(source_file_name, destination_blob_name):
    """
    Sube un archivo PDF a Google Cloud Storage y genera una URL firmada.
    """
    try:
        # Obtener las credenciales por defecto (desde el entorno de Cloud Run)
        credentials, project_id = google.auth.default()

        # Es CRUCIAL refrescar las credenciales para asegurar que el token de acceso
        # esté disponible y no sea None.
        auth_req = g_requests.Request()
        credentials.refresh(auth_req)

        storage_client = storage.Client(credentials=credentials)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)

        # 1. Subir el archivo
        blob.upload_from_filename(source_file_name)
        print(f"Archivo {source_file_name} subido a {destination_blob_name} en el bucket {GCS_BUCKET_NAME}.")

        # 2. Generar la URL firmada
        # Pasamos explícitamente el service_account_email y access_token.
        # Esto le dice a la librería que use la API de IAM para firmar.
        if hasattr(credentials, "service_account_email") and credentials.token:
            signed_url = blob.generate_signed_url(
                version="v4", # Versión 4 es la más reciente y preferida
                expiration=timedelta(minutes=10),
                method="GET",
                service_account_email=credentials.service_account_email,
                access_token=credentials.token
            )
            print(f"URL firmada generada: {signed_url}")
            return signed_url
        else:
            print("No se pudo obtener la cuenta de servicio o el token para generar la URL firmada.")
            # Si no se puede generar la URL firmada, podrías devolver una URL pública si el objeto lo permite,
            # o lanzar un error. Para este caso, lanzaremos un error.
            raise RuntimeError("No se pudo obtener la cuenta de servicio o el token para generar la URL firmada.")

    except Exception as e:
        print(f"Error al subir el archivo o generar la URL firmada: {e}")
        raise # Vuelve a lanzar la excepción para que el orquestador la capture
