FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No ejecutamos nada por defecto
CMD ["echo", "Docker image built successfully."]
