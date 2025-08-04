# Usa una imagen base de Python oficial
FROM python:3.9-slim-buster

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo requirements.txt y instala las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu aplicación
COPY . .

# Expone el puerto que tu aplicación FastAPI escuchará
# Cloud Run espera que tu aplicación escuche en el puerto definido por la variable de entorno PORT
ENV PORT 8080
EXPOSE 8080

# Comando para iniciar tu aplicación usando Uvicorn
# Asegúrate de que 'main' sea el nombre de tu archivo principal (main.py)
# y 'app' sea la instancia de FastAPI en ese archivo.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
