# Backend IA Trainer - Documentación

## Descripción General

El **Backend IA Trainer** es un servicio dedicado a operaciones de inteligencia artificial, incluyendo:

- Entrenamiento y fine-tuning de modelos
- Integración con Ollama para inferencia local
- Generación de texto y embeddings
- Gestión de versiones de datasets
- Clonación de datos para entrenamiento

## Arquitectura

```
4_trainer/
├── 1_domain/                    # Dominio específico del trainer
├── 2_application/               # Casos de uso
├── 3_adapters/
│   └── controllers/             # Controladores
├── 4_infrastructure/
│   ├── gpu_processor/          # Procesamiento GPU
│   ├── persistence/            # Persistencia
│   └── web/                    # Clientes HTTP
├── tests/                      # Tests
├── apitrainer.py               # Endpoints de entrenamiento
├── apitrainer_ollama.py        # Endpoints de Ollama
├── routertrainer.py            # Orquestación de negocio
├── trainerbe.py                # App FastAPI
├── main.py                     # Punto de entrada
└── requirements.txt            # Dependencias
```

### Capas Compartidas

El trainer utiliza las siguientes capas compartidas del monorepo:

- **`1_shared_domain/`**: Entidades del dominio (User, Organization, Project, Version, OllamaModels)
- **`2_shared_application/`**: Interfaces, DTOs, adaptadores y servicios compartidos

## Configuración

### Variables de Entorno

```bash
# Servidor
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8004
SERVICE_RELOAD=false

# Ollama
OLLAMA_HOST=http://localhost:11434

# Storage
STORAGE_MODE=mock_and_db
FMANAGEMENT_BASE_URL=http://localhost:1666
FMANAGEMENT_BASE_PATH=/data/files/external

# Base de datos
MARIADB_HOST=localhost
MARIADB_PORT=3306
MARIADB_USER=myllm_admin
MARIADB_PASS=Us3r%40dminP%40ss
MARIADB_DB=myllm_projects_db
```

### Instalación de Dependencias

```bash
# Activar entorno virtual
source .venv_trainer313/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Instalación de Ollama

#### En macOS/Linux:

```bash
curl https://ollama.ai/install.sh | sh
```

#### En entorno de desarrollo:

```bash
# Iniciar Ollama
ollama serve

# Descargar un modelo (ejemplo: llama3.2)
ollama pull llama3.2
```

## Integración con Ollama

### Arquitectura de la Integración

La integración con Ollama sigue el patrón de arquitectura hexagonal utilizado en el proyecto:

```
Cliente → apitrainer_ollama.py → OllamaAdapter → Cliente Python de Ollama → Servidor Ollama
         (FastAPI)              (2_shared_application)
```

### Entidades del Dominio

Ubicación: `src/1_shared_domain/entities/ollama_models.py`

**Principales entidades:**

- `OllamaChatMessage`: Mensaje en una conversación (role, content)
- `OllamaModel`: Información de un modelo (nombre, tamaño, digest)
- `OllamaChatResponse`: Respuesta de chat con métricas
- `OllamaGenerateResponse`: Respuesta de generación de texto
- `OllamaEmbedding`: Vector de embedding
- `OllamaModelInfo`: Detalles técnicos del modelo
- `OllamaRunningModel`: Modelo cargado en memoria (VRAM)

### DTOs de Aplicación

Ubicación: `src/2_shared_application/dtos/ollama_dtos.py`

**DTOs para requests:**

- `ChatRequestDto`: Solicitud de chat
- `GenerateRequestDto`: Solicitud de generación
- `EmbedRequestDto`: Solicitud de embeddings
- `PullModelRequestDto`: Descarga de modelo
- `CreateModelRequestDto`: Creación de modelo personalizado

**DTOs para responses:**

- `ChatResponseDto`: Respuesta de chat
- `GenerateResponseDto`: Texto generado
- `EmbedResponseDto`: Embeddings generados
- `ModelListResponseDto`: Lista de modelos
- `ModelInfoDto`: Información detallada

### Adaptador de Ollama

Ubicación: `src/2_shared_application/adapters/ollama_adapter.py`

**Clase principal:** `OllamaAdapter`

**Métodos sincrónicos:**
- `chat()`: Generación de chat
- `generate()`: Generación de texto
- `embed()`: Generación de embeddings
- `list_models()`: Listar modelos
- `show_model()`: Información de modelo
- `pull_model()`: Descargar modelo
- `delete_model()`: Eliminar modelo
- `copy_model()`: Copiar modelo
- `create_model()`: Crear modelo personalizado
- `list_running_models()`: Modelos en ejecución
- `health_check()`: Verificar disponibilidad

**Métodos asíncronos:**
- Todas las operaciones tienen versión `_async` para uso con `async/await`

### Endpoints REST

Los endpoints de Ollama están disponibles en el prefijo `/trainer/ollama/`:

#### Health Check

```http
GET /trainer/ollama/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "service": "ollama",
  "message": "Ollama está funcionando correctamente"
}
```

#### Chat

```http
POST /trainer/ollama/chat
Content-Type: application/json

{
  "model": "llama3.2",
  "messages": [
    {"role": "user", "content": "¿Qué es la IA?"}
  ],
  "stream": false
}
```

**Respuesta:**
```json
{
  "model": "llama3.2",
  "message": {
    "role": "assistant",
    "content": "La inteligencia artificial es..."
  },
  "done": true,
  "total_duration": 5000000000,
  "eval_count": 50
}
```

#### Generación de Texto

```http
POST /trainer/ollama/generate
Content-Type: application/json

{
  "model": "llama3.2",
  "prompt": "Escribe un poema sobre IA",
  "stream": false
}
```

**Respuesta:**
```json
{
  "model": "llama3.2",
  "response": "En circuitos de luz...",
  "done": true,
  "total_duration": 3000000000,
  "eval_count": 100
}
```

#### Embeddings

```http
POST /trainer/ollama/embed
Content-Type: application/json

{
  "model": "llama3.2",
  "input": "Texto para generar embedding"
}
```

**Respuesta:**
```json
{
  "model": "llama3.2",
  "embeddings": [
    [0.123, -0.456, 0.789, ...]
  ]
}
```

#### Listar Modelos

```http
GET /trainer/ollama/models
```

**Respuesta:**
```json
{
  "models": [
    {
      "name": "llama3.2:latest",
      "model": "llama3.2",
      "size": 4661211904,
      "digest": "abc123...",
      "modified_at": "2024-01-01T00:00:00Z",
      "details": {
        "family": "llama",
        "parameter_size": "3B"
      }
    }
  ]
}
```

#### Información de Modelo

```http
POST /trainer/ollama/models/show
Content-Type: application/json

{
  "name": "llama3.2"
}
```

**Respuesta:**
```json
{
  "modelfile": "FROM llama3.2...",
  "parameters": "num_ctx 4096...",
  "template": "{{ .System }}...",
  "details": {
    "family": "llama",
    "parameter_size": "3B",
    "quantization_level": "Q4_0"
  }
}
```

#### Descargar Modelo

```http
POST /trainer/ollama/models/pull
Content-Type: application/json

{
  "name": "llama3.2",
  "stream": false
}
```

**Respuesta:**
```json
{
  "status": "success",
  "digest": "abc123...",
  "total": 4661211904,
  "completed": 4661211904
}
```

#### Eliminar Modelo

```http
DELETE /trainer/ollama/models/llama3.2
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Modelo llama3.2 eliminado correctamente"
}
```

#### Copiar Modelo

```http
POST /trainer/ollama/models/copy
Content-Type: application/json

{
  "source": "llama3.2",
  "destination": "my-custom-llama"
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Modelo copiado de llama3.2 a my-custom-llama"
}
```

#### Crear Modelo Personalizado

```http
POST /trainer/ollama/models/create
Content-Type: application/json

{
  "name": "my-model",
  "modelfile": "FROM llama3.2\nSYSTEM You are a helpful assistant.",
  "stream": false
}
```

**Respuesta:**
```json
{
  "status": "success",
  "message": "Modelo my-model creado correctamente"
}
```

#### Modelos en Ejecución

```http
GET /trainer/ollama/ps
```

**Respuesta:**
```json
{
  "models": [
    {
      "name": "llama3.2:latest",
      "model": "llama3.2",
      "size": 4661211904,
      "digest": "abc123...",
      "expires_at": "2024-01-01T00:05:00Z",
      "size_vram": 3758096384
    }
  ]
}
```

## Integración en el Código

### Inicializar el Adaptador de Ollama

En `trainerbe.py`, agregar al ciclo de vida:

```python
from apitrainer_ollama import init_ollama_adapter, register_ollama_routes
import os

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Gestiona el ciclo de vida de la aplicación."""

    # Configuración existente...
    _configure_logging()

    # Inicializar Ollama
    ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    init_ollama_adapter(host=ollama_host)

    yield

app = FastAPI(title="Backend IA Trainer", lifespan=lifespan)

# Registrar rutas de Ollama
register_ollama_routes(app)
```

### Uso desde Otros Servicios

#### Ejemplo desde el backend (3_backend):

```python
import httpx

async def generate_text(prompt: str) -> str:
    """Genera texto usando Ollama a través del trainer."""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8004/trainer/ollama/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False
            },
            headers={"X-Client-App": "backend"}
        )

        data = response.json()
        return data["response"]
```

#### Ejemplo desde el frontend (5_web_frontend):

```python
# En un componente Reflex
class ChatState(rx.State):
    message: str = ""
    response: str = ""

    async def send_message(self):
        """Envía mensaje a Ollama vía trainer."""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8004/trainer/ollama/chat",
                json={
                    "model": "llama3.2",
                    "messages": [
                        {"role": "user", "content": self.message}
                    ],
                    "stream": False
                }
            )

            data = response.json()
            self.response = data["message"]["content"]
```

## Casos de Uso

### 1. Generación Automática de Resúmenes

```python
async def generar_resumen_version(version_id: int) -> str:
    """Genera un resumen de una versión usando IA."""

    # Obtener archivos de la versión
    files_response = await client.get(f"/trainer/version/{version_id}/files")
    files = files_response.json()["files"]

    # Generar prompt
    prompt = f"Resume los siguientes archivos:\n\n"
    for file in files[:5]:  # Primeros 5 archivos
        prompt += f"- {file['name']}: {file['type']}\n"

    # Llamar a Ollama
    response = await client.post(
        "/trainer/ollama/generate",
        json={"model": "llama3.2", "prompt": prompt}
    )

    return response.json()["response"]
```

### 2. Clasificación Automática de Documentos

```python
async def clasificar_documento(contenido: str) -> str:
    """Clasifica un documento en categorías."""

    messages = [
        {
            "role": "system",
            "content": "Eres un clasificador de documentos. Clasifica en: código, documentación, configuración, datos."
        },
        {
            "role": "user",
            "content": f"Clasifica este contenido:\n\n{contenido[:500]}"
        }
    ]

    response = await client.post(
        "/trainer/ollama/chat",
        json={"model": "llama3.2", "messages": messages}
    )

    return response.json()["message"]["content"]
```

### 3. Búsqueda Semántica con Embeddings

```python
async def buscar_similares(query: str, documentos: list[str]) -> list[tuple[int, float]]:
    """Busca documentos similares usando embeddings."""

    # Generar embedding de la query
    query_embed_response = await client.post(
        "/trainer/ollama/embed",
        json={"model": "llama3.2", "input": query}
    )
    query_embedding = query_embed_response.json()["embeddings"][0]

    # Generar embeddings de documentos
    docs_embed_response = await client.post(
        "/trainer/ollama/embed",
        json={"model": "llama3.2", "input": documentos}
    )
    docs_embeddings = docs_embed_response.json()["embeddings"]

    # Calcular similitud (producto punto)
    similitudes = []
    for i, doc_emb in enumerate(docs_embeddings):
        similitud = sum(a * b for a, b in zip(query_embedding, doc_emb))
        similitudes.append((i, similitud))

    # Ordenar por similitud
    similitudes.sort(key=lambda x: x[1], reverse=True)

    return similitudes
```

### 4. Generación de Informes Automáticos

```python
async def generar_informe_entrenamiento(training_id: int) -> str:
    """Genera un informe narrativo de un entrenamiento."""

    # Obtener métricas
    metrics_response = await client.get(f"/trainer/training/{training_id}/status")
    metrics = metrics_response.json()

    # Generar informe con IA
    prompt = f"""
    Genera un informe profesional de este entrenamiento:

    - Duración: {metrics.get('duration')} minutos
    - Pérdida final: {metrics.get('final_loss')}
    - Precisión: {metrics.get('accuracy')}%
    - Épocas: {metrics.get('epochs')}

    Analiza los resultados y proporciona recomendaciones.
    """

    response = await client.post(
        "/trainer/ollama/generate",
        json={
            "model": "llama3.2",
            "prompt": prompt,
            "system": "Eres un experto en machine learning."
        }
    )

    return response.json()["response"]
```

## Seguridad

### Validación de Permisos

Los endpoints de Ollama NO requieren autenticación actualmente, ya que Ollama se ejecuta localmente. Sin embargo, en producción se debe:

1. **Limitar acceso por IP**: Configurar firewall para que solo el trainer pueda acceder a Ollama
2. **Añadir autenticación**: Usar API keys o tokens JWT para endpoints sensibles
3. **Rate limiting**: Limitar requests por usuario/aplicación
4. **Auditoría**: Registrar todas las operaciones en logs

### Ejemplo de Rate Limiting (futuro):

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/trainer/ollama/generate")
@limiter.limit("10/minute")
def generate(...):
    ...
```

## Testing

### Tests de Integración

```bash
# Ejecutar tests
pytest tests/test_ollama_integration.py -v
```

### Ejemplo de Test:

```python
def test_ollama_chat(client: TestClient):
    """Test de chat con Ollama."""

    response = client.post(
        "/trainer/ollama/chat",
        json={
            "model": "llama3.2",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert len(data["message"]["content"]) > 0
```

## Monitoreo

### Métricas a Monitorear

- **Latencia de inferencia**: Tiempo de respuesta de Ollama
- **Uso de VRAM**: Memoria GPU utilizada por modelos
- **Throughput**: Requests por segundo
- **Tasa de error**: Fallos en llamadas a Ollama
- **Modelos activos**: Cantidad de modelos en memoria

### Logging

Los logs se guardan en:
- `logs/trainer.log`: Logs generales del servicio
- `logs/ollama.log`: Logs específicos de operaciones con Ollama

### Health Checks

Verificar estado del servicio:

```bash
curl http://localhost:8004/trainer/health
curl http://localhost:8004/trainer/ollama/health
```

## Troubleshooting

### Ollama no está disponible

**Error:** `503 Service Unavailable: Ollama no está disponible`

**Solución:**
```bash
# Verificar que Ollama está corriendo
ollama list

# Si no está corriendo, iniciar
ollama serve
```

### Modelo no encontrado

**Error:** `404 Not Found: model 'llama3.2' not found`

**Solución:**
```bash
# Descargar el modelo
ollama pull llama3.2
```

### Timeout en requests largos

**Error:** `Request timeout`

**Solución:**
- Aumentar timeout en el cliente HTTP
- Usar streaming para requests largos
- Optimizar parámetros del modelo (num_ctx, num_predict)

### Alto uso de VRAM

**Problema:** El sistema se queda sin memoria GPU

**Solución:**
- Usar modelos cuantizados (Q4_0, Q4_1)
- Reducir num_ctx en las opciones
- Limitar modelos concurrentes
- Usar offloading a CPU

## Referencias

- [Documentación oficial de Ollama](https://ollama.ai/docs)
- [API de Ollama](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Cliente Python de Ollama](https://github.com/ollama/ollama-python)
- [Modelos disponibles](https://ollama.ai/library)

## Contribución

Para agregar nuevos endpoints o funcionalidad:

1. Actualizar entidades en `1_shared_domain/entities/ollama_models.py`
2. Crear DTOs en `2_shared_application/dtos/ollama_dtos.py`
3. Implementar en adaptador `2_shared_application/adapters/ollama_adapter.py`
4. Agregar endpoint en `apitrainer_ollama.py`
5. Documentar en este README
6. Crear tests en `tests/`
7. Actualizar AGENTS.md con contexto para IA

## Licencia

Propietario - Proyecto interno de Myllm
