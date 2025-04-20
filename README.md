# DataProject_3

## Project Overview

DataProject_3 is a multi-component application that integrates an AI agent with a FastAPI backend and a Streamlit frontend. The project consists of three main servers:

1. **API Agent**: A FastAPI application that integrates an AI agent using Langraph.
2. **API Data**: A FastAPI application that provides data to the agent through various data.
3. **Streamlit Frontend**: A chat interface that connects to the AI agent via its API.

## Setup Instructions

1. **Clone the Repository**:

    ```bash
    git clone <repository-url>
    cd DataProject_3
    ```

2. **Create .env file**

    ```text
    GEMINI_API_KEY=<your-api-key>
    ```

3. **Docker compose up**:

    ```bash
    docker compose -f 'docker-compose.yml' up -d --build
    ```

## Usage

- Access the API Agent at `http://localhost:8000`.
- Access the API Data at `http://localhost:8001`.
- Access the Streamlit chat interface at `http://localhost:8501`.
