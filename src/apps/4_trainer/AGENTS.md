# Contexto y Reglas para Agentes de IA - Trainer

Este documento proporciona contexto, reglas y guías para agentes de IA que trabajen con el servicio **Backend IA Trainer** y su integración con **Ollama**.

## Contexto del Sistema

### Propósito del Trainer

El **Backend IA Trainer** es un microservicio especializado en:

1. **Entrenamiento de modelos**: Fine-tuning y entrenamiento de modelos de IA
2. **Inferencia local con Ollama**: Generación de texto, chat y embeddings
3. **Gestión de versiones**: Manejo de datasets y versiones para entrenamiento
4. **Automatización con IA**: Procesos automáticos usando capacidades de IA

### Arquitectura del Proyecto

El trainer es parte de un **monorepo** con arquitectura hexagonal:

```
src/
├── 1_shared_domain/          # Entidades y lógica de negocio
├── 2_shared_application/     # Interfaces, DTOs, adaptadores
└── apps/
    ├── 3_backend/            # API principal (orquestación)
    ├── 4_trainer/            # Trainer (IA y entrenamiento)
    ├── 5_web_frontend/       # Frontend web
    └── 6_web_backoffice/     # Backoffice web
```

### Principios de Diseño

1. **Clean Architecture**: Separación en capas (dominio, aplicación, infraestructura)
2. **Dependency Inversion**: Interfaces en lugar de implementaciones concretas
3. **Security by Design**: Validación de permisos en todas las operaciones
4. **Protocols sobre clases abstractas**: Uso de `Protocol` para contratos
5. **Inmutabilidad**: Entidades del dominio con `@dataclass(frozen=True)`
6. **Carga dinámica**: Uso de `importlib.util` para evitar referencias cíclicas

## Reglas para Agentes al Modificar Código

### 1. Estructura de Capas

**SIEMPRE respetar la jerarquía de dependencias:**

```
Infraestructura → Adaptadores → Aplicación → Dominio
```

**❌ NUNCA hacer:**
- Dominio dependiendo de aplicación o infraestructura
- Entidades del dominio importando DTOs
- Lógica de negocio en endpoints FastAPI

**✅ SIEMPRE hacer:**
- Entidades en `1_shared_domain/entities/`
- DTOs en `2_shared_application/dtos/`
- Interfaces en `2_shared_application/interfaces/`
- Adaptadores en `2_shared_application/adapters/`
- Endpoints REST en `apitrainer.py` o `apitrainer_ollama.py`

### 2. Nomenclatura de Archivos

**Entidades del dominio:**
- Nombre en singular: `ollama_models.py` (no `ollama_model.py`)
- Puede contener múltiples entidades relacionadas

**DTOs:**
- Sufijo `_dtos.py`: `ollama_dtos.py`
- Usar Pydantic `BaseModel`

**Interfaces:**
- Sufijo `_repository.py`: `ollama_repository.py`
- Usar `Protocol` de `typing`

**Adaptadores:**
- Sufijo `_adapter.py`: `ollama_adapter.py`
- Implementación concreta de la interfaz

### 3. Convenciones de Código

#### Entidades del Dominio

```python
from dataclasses import dataclass, field
from enum import Enum

class EstadoModelo(str, Enum):
    """Estados del modelo."""
    DISPONIBLE = "disponible"
    ENTRENANDO = "entrenando"

@dataclass(frozen=True, slots=True)
class Modelo:
    """Entidad de modelo de IA."""
    id: int
    nombre: str
    estado: EstadoModelo

    def __post_init__(self) -> None:
        """Validaciones de invariantes."""
        if not self.nombre.strip():
            raise ValueError("El nombre no puede estar vacío")

    def esta_disponible(self) -> bool:
        """Método de negocio."""
        return self.estado == EstadoModelo.DISPONIBLE
```

**Reglas:**
- Usar `@dataclass(frozen=True, slots=True)` para inmutabilidad y eficiencia
- Validar invariantes en `__post_init__`
- Métodos con lógica de negocio, no solo getters/setters
- Docstrings en español
- Type hints en todo

#### DTOs con Pydantic

```python
from pydantic import BaseModel, ConfigDict, Field

class ModeloRequestDto(BaseModel):
    """DTO para solicitud de modelo."""
    model_config = ConfigDict(extra="ignore", validate_assignment=True)

    nombre: str = Field(..., description="Nombre del modelo")
    parametros: dict[str, Any] = Field(default_factory=dict)
```

**Reglas:**
- Heredar de `BaseModel`
- Usar `model_config` con `extra="ignore"`
- `Field(...)` para campos requeridos
- `Field(default=...)` o `Field(default_factory=...)` para opcionales
- Docstrings con `description` en los Fields

#### Interfaces con Protocol

```python
from typing import Protocol

class ModeloRepository(Protocol):
    """Contrato para repositorio de modelos."""

    def obtener_por_id(self, id: int) -> Modelo | None:
        """Obtiene un modelo por ID."""
        ...

    def guardar(self, modelo: Modelo) -> Modelo:
        """Guarda un modelo."""
        ...
```

**Reglas:**
- Heredar de `Protocol`
- Solo firmas de métodos (con `...`)
- Docstrings en cada método
- Type hints completos

#### Adaptadores

```python
import logging
from typing import Any

logger = logging.getLogger(__name__)

class ModeloAdapter:
    """Adaptador para gestión de modelos."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.info("ModeloAdapter inicializado")

    def obtener_por_id(self, id: int) -> Modelo | None:
        """Implementación del contrato."""
        try:
            # Lógica de acceso a datos
            logger.debug(f"Buscando modelo: {id}")
            # ...
        except Exception as e:
            logger.error(f"Error obteniendo modelo: {e}")
            raise
```

**Reglas:**
- Implementar todos los métodos de la interfaz
- Logging extensivo (debug, info, error)
- Manejo de excepciones con `try/except`
- Re-lanzar excepciones después de loguear

#### Endpoints FastAPI

```python
from fastapi import FastAPI, HTTPException, status
from typing import Annotated

@app.post("/trainer/ollama/chat", response_model=ChatResponseDto)
def chat(
    request: ChatRequestDto,
    x_client_app: Annotated[str | None, Header()] = None,
) -> ChatResponseDto:
    """
    Genera una respuesta de chat.

    Args:
        request: Datos del chat
        x_client_app: Aplicación cliente

    Returns:
        Respuesta del modelo

    Raises:
        HTTPException: Si hay error en la operación
    """
    try:
        adapter = get_ollama_adapter()
        logger.info(f"Chat from {x_client_app}: model={request.model}")
        return adapter.chat(request)
    except OllamaError as e:
        logger.error(f"Error en chat: {e}")
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message
        ) from e
```

**Reglas:**
- Endpoint con verbo HTTP correcto (POST, GET, DELETE)
- Path con prefijo `/trainer/`
- `response_model` para documentación
- Header `X-Client-App` para trazabilidad
- Try/except con logging
- HTTPException con status code apropiado
- Docstring con formato Google

### 4. Integración con Ollama

#### Usar el Adaptador Existente

**❌ NUNCA hacer:**
```python
# NO llamar directamente al cliente de Ollama
import ollama
response = ollama.chat(model="llama3.2", messages=[...])
```

**✅ SIEMPRE hacer:**
```python
# Usar el adaptador
from src.2_shared_application.adapters.ollama_adapter import OllamaAdapter

adapter = OllamaAdapter(host="http://localhost:11434")
request = ChatRequestDto(model="llama3.2", messages=[...])
response = adapter.chat(request)
```

#### Gestión de Errores de Ollama

**SIEMPRE capturar `OllamaError`:**

```python
from src.2_shared_application.adapters.ollama_adapter import OllamaError

try:
    response = adapter.chat(request)
except OllamaError as e:
    # Manejo específico de errores de Ollama
    if e.status_code == 404:
        # Modelo no encontrado
        logger.warning(f"Modelo no encontrado: {request.model}")
        # Intentar descargarlo o sugerir alternativa
    elif e.status_code == 503:
        # Ollama no disponible
        logger.error("Ollama no está disponible")
        # Reintentar o usar fallback
    else:
        # Error genérico
        logger.error(f"Error de Ollama: {e.message}")
    raise
```

### 5. Operaciones Comunes con Ollama

#### Chat Conversacional

```python
messages = [
    ChatMessageDto(role="system", content="Eres un asistente útil"),
    ChatMessageDto(role="user", content="¿Qué es Python?"),
]

request = ChatRequestDto(
    model="llama3.2",
    messages=messages,
    stream=False
)

response = adapter.chat(request)
answer = response.message.content
```

#### Generación de Texto

```python
request = GenerateRequestDto(
    model="llama3.2",
    prompt="Escribe un resumen sobre IA",
    system="Eres un experto en tecnología",
    options={"temperature": 0.7, "num_predict": 200}
)

response = adapter.generate(request)
text = response.response
```

#### Embeddings para Búsqueda Semántica

```python
# Generar embedding de query
query_request = EmbedRequestDto(
    model="llama3.2",
    input="buscar documentación de Python"
)
query_embed = adapter.embed(query_request).embeddings[0]

# Generar embeddings de documentos
docs = ["doc1", "doc2", "doc3"]
docs_request = EmbedRequestDto(model="llama3.2", input=docs)
docs_embeds = adapter.embed(docs_request).embeddings

# Calcular similitud (producto punto)
def similitud(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))

resultados = [
    (i, similitud(query_embed, doc_emb))
    for i, doc_emb in enumerate(docs_embeds)
]
resultados.sort(key=lambda x: x[1], reverse=True)
```

#### Gestión de Modelos

```python
# Listar modelos disponibles
models = adapter.list_models()
for model in models.models:
    print(f"{model.name}: {model.get_size_gb():.2f} GB")

# Descargar un modelo
pull_request = PullModelRequestDto(name="llama3.2")
adapter.pull_model(pull_request)

# Ver información detallada
show_request = ModelShowRequestDto(name="llama3.2")
info = adapter.show_model(show_request)
print(f"Familia: {info.details.get('family')}")
print(f"Parámetros: {info.details.get('parameter_size')}")

# Modelos en ejecución
running = adapter.list_running_models()
for model in running.models:
    print(f"{model.name}: {model.get_vram_gb():.2f} GB VRAM")
```

### 6. Casos de Uso Comunes

#### Automatización: Resumen de Versión

```python
async def generar_resumen_version(
    version_id: int,
    trainer_url: str = "http://localhost:8004"
) -> str:
    """Genera un resumen automático de una versión."""

    # 1. Obtener archivos de la versión
    async with httpx.AsyncClient() as client:
        files_resp = await client.get(
            f"{trainer_url}/trainer/version/{version_id}/files"
        )
        files = files_resp.json()["files"]

    # 2. Construir prompt
    file_list = "\n".join([f"- {f['name']} ({f['type']})" for f in files[:10]])
    prompt = f"""
    Analiza los siguientes archivos de una versión de proyecto:

    {file_list}

    Genera un resumen ejecutivo que incluya:
    - Tipo de proyecto
    - Tecnologías identificadas
    - Estructura del proyecto
    - Recomendaciones
    """

    # 3. Llamar a Ollama
    async with httpx.AsyncClient() as client:
        generate_resp = await client.post(
            f"{trainer_url}/trainer/ollama/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "system": "Eres un analista de proyectos de software."
            }
        )

    return generate_resp.json()["response"]
```

#### Clasificación Automática

```python
async def clasificar_archivo(
    nombre: str,
    contenido: str,
    trainer_url: str = "http://localhost:8004"
) -> dict[str, str]:
    """Clasifica un archivo automáticamente."""

    messages = [
        {
            "role": "system",
            "content": "Eres un clasificador de archivos. Responde solo con el tipo: codigo|documentacion|configuracion|datos|otro"
        },
        {
            "role": "user",
            "content": f"Archivo: {nombre}\n\nContenido:\n{contenido[:500]}"
        }
    ]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{trainer_url}/trainer/ollama/chat",
            json={"model": "llama3.2", "messages": messages}
        )

    tipo = response.json()["message"]["content"].strip().lower()

    return {
        "nombre": nombre,
        "tipo": tipo,
        "confianza": "alta" if tipo in ["codigo", "documentacion"] else "media"
    }
```

#### Generación de Documentación

```python
async def generar_documentacion(
    codigo: str,
    lenguaje: str,
    trainer_url: str = "http://localhost:8004"
) -> str:
    """Genera documentación para código."""

    prompt = f"""
    Genera documentación técnica para el siguiente código en {lenguaje}:

    ```{lenguaje}
    {codigo}
    ```

    La documentación debe incluir:
    - Descripción general
    - Parámetros
    - Valor de retorno
    - Ejemplos de uso
    - Notas técnicas
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{trainer_url}/trainer/ollama/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "system": "Eres un documentador técnico experto."
            }
        )

    return response.json()["response"]
```

### 7. Optimización de Prompts

**Estructura recomendada:**

```python
# 1. Contexto del sistema (role: system)
system_prompt = """
Eres un [ROL].
Tu objetivo es [OBJETIVO].
Debes responder en formato [FORMATO].
"""

# 2. Instrucciones claras (role: user)
user_prompt = """
[TAREA ESPECÍFICA]

Datos:
[DATOS ESTRUCTURADOS]

Formato de salida:
[ESPECIFICACIÓN DEL FORMATO]

Restricciones:
[LIMITACIONES]
"""

# 3. Few-shot examples (opcional)
examples = """
Ejemplo 1:
Input: ...
Output: ...

Ejemplo 2:
Input: ...
Output: ...
"""
```

**Parámetros de control:**

```python
options = {
    "temperature": 0.7,      # Creatividad (0.0-1.0)
    "top_p": 0.9,            # Nucleus sampling
    "top_k": 40,             # Top-K sampling
    "num_predict": 500,      # Máximo de tokens a generar
    "num_ctx": 4096,         # Tamaño de contexto
    "repeat_penalty": 1.1,   # Penalización por repetición
}
```

### 8. Testing

**SIEMPRE crear tests para:**

1. **Endpoints**: Cada endpoint debe tener al menos un test
2. **Adaptadores**: Tests de integración con mocks
3. **Entidades**: Tests de validaciones y lógica de negocio

**Ejemplo de test:**

```python
import pytest
from fastapi.testclient import TestClient

def test_ollama_chat_success(client: TestClient):
    """Test exitoso de chat."""

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

def test_ollama_chat_model_not_found(client: TestClient):
    """Test con modelo inexistente."""

    response = client.post(
        "/trainer/ollama/chat",
        json={
            "model": "modelo-inexistente",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

### 9. Logging y Monitoreo

**Niveles de logging:**

```python
logger.debug("Información de depuración")      # Desarrollo
logger.info("Operación normal")                # Producción
logger.warning("Situación anormal recuperable") # Alertas
logger.error("Error que impide operación")     # Errores
logger.critical("Fallo crítico del sistema")   # Emergencias
```

**Métricas a incluir:**

```python
logger.info(
    f"Chat completado: "
    f"model={model}, "
    f"tokens={eval_count}, "
    f"duration={total_duration_ms}ms, "
    f"client={x_client_app}"
)
```

### 10. Seguridad

**Validación de inputs:**

```python
# Sanitizar inputs de usuario
def sanitizar_prompt(prompt: str) -> str:
    """Limpia un prompt de caracteres peligrosos."""
    # Limitar longitud
    if len(prompt) > 10000:
        prompt = prompt[:10000]

    # Remover caracteres de control
    prompt = "".join(c for c in prompt if c.isprintable() or c.isspace())

    return prompt.strip()
```

**Rate limiting (recomendado):**

```python
from slowapi import Limiter

limiter = Limiter(key_func=lambda: request.client.host)

@app.post("/trainer/ollama/generate")
@limiter.limit("10/minute")  # 10 requests por minuto
async def generate(...):
    ...
```

## Preguntas Frecuentes para Agentes

### ¿Dónde pongo una nueva entidad de dominio?

En `src/1_shared_domain/entities/[nombre].py`. Si está relacionada con Ollama, en `ollama_models.py`.

### ¿Cómo agrego un nuevo endpoint de Ollama?

1. Agregar DTO en `src/2_shared_application/dtos/ollama_dtos.py`
2. Agregar método al adaptador en `src/2_shared_application/adapters/ollama_adapter.py`
3. Registrar endpoint en `src/apps/4_trainer/apitrainer_ollama.py`
4. Documentar en README.md
5. Crear test

### ¿Qué modelo de Ollama recomendar?

- **Tareas generales**: `llama3.2` (3B parámetros, rápido)
- **Tareas complejas**: `llama3.2:70b` (mejor calidad, más lento)
- **Embeddings**: `llama3.2` o modelos específicos de embeddings
- **Código**: `codellama` o `deepseek-coder`

### ¿Cómo manejo errores de Ollama?

Siempre capturar `OllamaError` y proporcionar fallback o mensaje útil al usuario. Nunca dejar que la excepción llegue al cliente sin procesar.

### ¿Puedo usar streaming?

Actualmente no está implementado. Si lo necesitas, tendrás que:
1. Implementar método `_stream` en el adaptador
2. Usar `yield` en el endpoint
3. Configurar `StreamingResponse` de FastAPI

## Checklist para Cambios

Antes de hacer un commit:

- [ ] Código sigue convenciones de nomenclatura
- [ ] Type hints en todas las funciones
- [ ] Docstrings en español
- [ ] Logging apropiado (info, error)
- [ ] Manejo de excepciones con try/except
- [ ] Tests creados y pasando
- [ ] README.md actualizado si es necesario
- [ ] No hay imports cíclicos
- [ ] Respeta la arquitectura de capas
- [ ] Validación de inputs
- [ ] Código revisado por lint (ruff/pylint)

## Recursos Adicionales

- **README.md**: Documentación completa del trainer
- **routertrainer.py**: Ejemplos de orquestación de negocio
- **apitrainer.py**: Ejemplos de endpoints existentes
- **tests/**: Ejemplos de tests

---

**Nota para Agentes:** Este documento es tu referencia principal al trabajar con el trainer. Si tienes dudas, consulta el código existente que sigue estos patrones. Mantén la consistencia con el estilo del proyecto.
