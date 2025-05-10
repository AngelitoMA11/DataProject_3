# Terraform Configuration for Travel Planner

Este directorio contiene la configuración de Terraform para desplegar la aplicación Travel Planner.

## Estructura

```
terraform/
├── environments/          # Configuraciones específicas por entorno
│   └── dev/              # Configuración de desarrollo
├── modules/              # Módulos reutilizables
│   ├── streamlit/        # Módulo para el frontend
│   ├── api_agent/        # Módulo para el agente de IA
│   └── api_data/         # Módulo para el servicio de datos
├── main.tf              # Configuración principal
└── variables.tf         # Variables globales
```

## Requisitos

- Terraform >= 1.0.0
- Docker
- Docker Compose

## Uso

1. Configura las variables de entorno:
   ```bash
   cp environments/dev/terraform.tfvars.example environments/dev/terraform.tfvars
   # Edita el archivo y añade tu API key de Gemini
   ```

2. Inicializa Terraform:
   ```bash
   terraform init
   ```

3. Planifica los cambios:
   ```bash
   terraform plan
   ```

4. Aplica los cambios:
   ```bash
   terraform apply
   ```

5. Para destruir la infraestructura:
   ```bash
   terraform destroy
   ```

## Módulos

### Streamlit Frontend
- Gestiona el contenedor del frontend de Streamlit
- Expone el puerto 8501
- Conecta con los servicios de API

### API Agent
- Gestiona el contenedor del agente de IA
- Expone el puerto 8000
- Requiere API key de Gemini

### API Data
- Gestiona el contenedor del servicio de datos
- Expone el puerto 8001
- Proporciona datos de vuelos y hoteles

## Variables

- `google_api_key`: API key para Google Gemini
- `environment`: Entorno de despliegue (dev, staging, prod) 