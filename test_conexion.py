import os
import google.generativeai as genai
from dotenv import load_dotenv

# Carga la clave secreta desde nuestro archivo .env
load_dotenv()

print("1. Intentando configurar la API de Google...")

# Configura el SDK con la clave que cargamos
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    print("   ✅ ¡Éxito! API configurada.")
except TypeError:
    print("   🚨 ¡Error! No se encontró la API Key. Asegúrate de que tu archivo .env está correcto.")
    exit()

# Selecciona el modelo que vamos a usar. Flash es rápido y barato.
model = genai.GenerativeModel('gemini-1.5-flash')

print("2. Enviando una pregunta a Gemini...")

# Hacemos una pregunta simple para probar la conexión
prompt = "¿Cuál es la capital de Uruguay?"
response = model.generate_content(prompt)

print("3. Respuesta recibida:")
print("---------------------------------")
# Imprime solo el texto de la respuesta del modelo
print(f"Pregunta: {prompt}")
print(f"Respuesta de Gemini: {response.text}")
print("---------------------------------")