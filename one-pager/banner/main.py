import functions_framework
import json
import uuid
from PIL import Image
from io import BytesIO
from google.cloud import storage
from google.oauth2 import service_account
from google import genai
from google.genai import types
from datetime import timedelta

# Replace with your project and bucket details
PROJECT_ID = "valiant-complex-467519-d3"
GCS_BUCKET_NAME = "ithaka-one-pagers"
SERVICE_ACCOUNT_FILE = "key.json"

@functions_framework.http
def generate_image(request):
    """HTTP Cloud Function that generates an image using Gemini and uploads it to GCS."""

    # Parse the request body for the prompt
    try:
        request_json = request.get_json(silent=True)
        if request_json and 'prompt' in request_json:
            prompt = request_json['prompt']
        else:
            return json.dumps({"error": "Missing 'prompt' in request body."}), 400
    except Exception as e:
        return json.dumps({"error": f"Invalid JSON in request body: {str(e)}"}), 400

    # Generate image using Gemini
    try:
        client = genai.Client()
        response = client.models.generate_images(
            model='imagen-4.0-generate-preview-06-06',
            prompt=f"Brief description: '{prompt}' Make a banner for it, include the startup name, think of a Linkedin banner.",
            config=types.GenerateImagesConfig(
                number_of_images= 1,
                aspect_ratio= "16:9"
            )
        )

    except Exception as e:
        print(f"An error occurred during image generation: {str(e)}")
        return json.dumps({"error": f"An error occurred during image generation: {str(e)}"}), 500

    # Upload image to GCS
    try:
        credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        storage_client = storage.Client(credentials=credentials, project=PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)

        url = None  # Will hold the signed URL of the image

        for generated_image in response.generated_images:
            image_uuid = uuid.uuid4()
            file_name = f"gemini-generated-image-{image_uuid}.png"
            blob = bucket.blob(file_name)
        # Directly upload the image bytes from the response object
            blob.upload_from_string(generated_image.image.image_bytes, content_type='image/png')
            
            # Generate a signed URL for the image valid for 1 hour
            url = blob.generate_signed_url(expiration=timedelta(hours=1))
        return json.dumps({
            "image_url": url,
            "message": "Image generated and stored successfully."
        }), 200

    except Exception as e:
        print(f"An error occurred during storage upload: {str(e)}")
        return json.dumps({"error": f"An error occurred during storage upload: {str(e)}"}), 500
