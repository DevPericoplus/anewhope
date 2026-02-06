"""
Tests de integración para endpoints de Ollama en el trainer.

Estos tests verifican que los endpoints de Ollama funcionan correctamente
con modelos reales instalados en el sistema.
"""

import pytest
import httpx
import time


# Configuración
TRAINER_BASE_URL = "http://localhost:8004"
TIMEOUT = 60.0  # Timeout largo para generación de texto


class TestOllamaIntegration:
    """Tests de integración con Ollama."""

    @pytest.fixture
    def client(self):
        """Cliente HTTP para tests."""
        return httpx.Client(base_url=TRAINER_BASE_URL, timeout=TIMEOUT)

    @pytest.fixture
    async def async_client(self):
        """Cliente HTTP asíncrono para tests."""
        async with httpx.AsyncClient(base_url=TRAINER_BASE_URL, timeout=TIMEOUT) as client:
            yield client

    def generate_with_fallback(self, client, model: str, prompt: str, temperature: float = 0.7, num_predict: int = 100):
        """
        Intenta generar con el endpoint generate, y si la respuesta está vacía,
        usa el endpoint chat como fallback.

        Returns:
            tuple: (response_data, endpoint_used, elapsed_time)
        """
        start_time = time.time()

        # Intento 1: Usar endpoint generate
        response = client.post(
            "/trainer/ollama/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": num_predict
                }
            },
            headers={"X-Client-App": "test-integration"}
        )

        elapsed_time = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            # Si tiene respuesta, retornar
            if data.get("response", "").strip():
                return data, "generate", elapsed_time

            # Si la respuesta está vacía, intentar con chat
            print(f"\n⚠️  Respuesta vacía con generate, intentando con chat...")
            start_time = time.time()

            response = client.post(
                "/trainer/ollama/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {
                        "temperature": temperature
                    }
                },
                headers={"X-Client-App": "test-integration"}
            )

            elapsed_time = time.time() - start_time

            if response.status_code == 200:
                chat_data = response.json()
                # Convertir formato de chat a formato de generate para compatibilidad
                return {
                    "model": chat_data.get("model", model),
                    "response": chat_data.get("message", {}).get("content", ""),
                    "done": chat_data.get("done", True),
                    "total_duration": chat_data.get("total_duration", 0),
                    "eval_count": chat_data.get("eval_count", 0),
                    "eval_duration": chat_data.get("eval_duration", 0),
                }, "chat", elapsed_time

        # Si todo falla, retornar la respuesta original
        return response.json(), "generate", elapsed_time

    # ========================================================================
    # Tests de Health Check
    # ========================================================================

    def test_ollama_health_check(self, client):
        """Verifica que Ollama esté disponible."""
        response = client.get("/trainer/ollama/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ollama"
        print(f"\n✓ Ollama health check: {data['message']}")

    # ========================================================================
    # Tests de Lista de Modelos
    # ========================================================================

    def test_list_models(self, client):
        """Lista los modelos disponibles."""
        response = client.get("/trainer/ollama/models")

        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0

        print(f"\n✓ Modelos disponibles: {len(data['models'])}")
        for model in data["models"][:5]:  # Mostrar solo los primeros 5
            size_gb = model["size"] / (1024**3)
            print(f"  - {model['name']}: {size_gb:.2f} GB")

    # ========================================================================
    # Tests de Generación con Múltiples Modelos
    # ========================================================================

    def test_generate_with_llama3_1(self, client):
        """Test de generación con llama3.1:8b."""
        model = "llama3.1:8b"
        prompt = "¿Qué es la inteligencia artificial? Responde en máximo 50 palabras."

        print(f"\n\n{'='*70}")
        print(f"TEST: Generación con {model}")
        print(f"{'='*70}")
        print(f"Prompt: {prompt}")
        print(f"{'='*70}")

        start_time = time.time()

        response = client.post(
            "/trainer/ollama/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100
                }
            },
            headers={"X-Client-App": "test-integration"}
        )

        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Verificaciones
        assert "model" in data
        assert "response" in data
        assert "done" in data
        assert data["done"] is True
        assert len(data["response"]) > 0

        # Estadísticas
        total_duration_sec = data.get("total_duration", 0) / 1_000_000_000
        eval_count = data.get("eval_count", 0)
        tokens_per_sec = 0
        if data.get("eval_duration", 0) > 0:
            tokens_per_sec = (eval_count * 1_000_000_000) / data["eval_duration"]

        print(f"\n✓ Respuesta generada exitosamente")
        print(f"\nRespuesta:")
        print(f"{'-'*70}")
        print(data["response"])
        print(f"{'-'*70}")
        print(f"\nEstadísticas:")
        print(f"  - Modelo: {data['model']}")
        print(f"  - Tiempo total: {elapsed_time:.2f}s")
        print(f"  - Duración del modelo: {total_duration_sec:.2f}s")
        print(f"  - Tokens generados: {eval_count}")
        print(f"  - Tokens/segundo: {tokens_per_sec:.2f}")

    def test_generate_with_deepseek_r1(self, client):
        """Test de generación con deepseek-r1:1.5b (con fallback a chat si es necesario)."""
        model = "deepseek-r1:1.5b"
        prompt = "¿Qué es la inteligencia artificial? Responde en máximo 50 palabras."

        print(f"\n\n{'='*70}")
        print(f"TEST: Generación con {model}")
        print(f"{'='*70}")
        print(f"Prompt: {prompt}")
        print(f"{'='*70}")

        # Usar helper con fallback automático
        data, endpoint_used, elapsed_time = self.generate_with_fallback(
            client, model, prompt, temperature=0.7, num_predict=100
        )

        # Verificaciones
        assert "model" in data
        assert "response" in data
        assert "done" in data
        assert data["done"] is True
        assert len(data["response"]) > 0

        # Estadísticas
        total_duration_sec = data.get("total_duration", 0) / 1_000_000_000
        eval_count = data.get("eval_count", 0)
        tokens_per_sec = 0
        if data.get("eval_duration", 0) > 0:
            tokens_per_sec = (eval_count * 1_000_000_000) / data["eval_duration"]

        print(f"\n✓ Respuesta generada exitosamente (usando endpoint: {endpoint_used})")
        print(f"\nRespuesta:")
        print(f"{'-'*70}")
        print(data["response"][:200] + "..." if len(data["response"]) > 200 else data["response"])
        print(f"{'-'*70}")
        print(f"\nEstadísticas:")
        print(f"  - Modelo: {data['model']}")
        print(f"  - Tiempo total: {elapsed_time:.2f}s")
        print(f"  - Duración del modelo: {total_duration_sec:.2f}s")
        print(f"  - Tokens generados: {eval_count}")
        print(f"  - Tokens/segundo: {tokens_per_sec:.2f}")

    # ========================================================================
    # Tests de Comparación de Modelos
    # ========================================================================

    def test_compare_models_same_prompt(self, client):
        """Compara dos modelos con el mismo prompt (con fallback automático)."""
        prompt = "Explica qué es Python en una frase."
        models = ["llama3.1:8b", "deepseek-r1:1.5b"]

        print(f"\n\n{'='*70}")
        print("TEST: Comparación de Modelos")
        print(f"{'='*70}")
        print(f"Prompt: {prompt}")
        print(f"Modelos: {', '.join(models)}")
        print(f"{'='*70}\n")

        results = []

        for model in models:
            print(f"\nGenerando con {model}...")

            # Usar helper con fallback automático
            data, endpoint_used, elapsed_time = self.generate_with_fallback(
                client, model, prompt, temperature=0.5, num_predict=50
            )

            results.append({
                "model": model,
                "response": data["response"],
                "time": elapsed_time,
                "tokens": data.get("eval_count", 0),
                "endpoint": endpoint_used
            })

        # Mostrar resultados comparativos
        print(f"\n{'='*70}")
        print("RESULTADOS DE LA COMPARACIÓN")
        print(f"{'='*70}\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. Modelo: {result['model']}")
            print(f"   Endpoint usado: {result['endpoint']}")
            print(f"   Tiempo: {result['time']:.2f}s")
            print(f"   Tokens: {result['tokens']}")
            print(f"   Respuesta:")
            print(f"   {'-'*66}")
            response_text = result['response'][:150] + "..." if len(result['response']) > 150 else result['response']
            print(f"   {response_text}")
            print(f"   {'-'*66}\n")

        # Verificar que ambos modelos respondieron
        assert len(results) == 2
        for result in results:
            assert len(result["response"]) > 0

    # ========================================================================
    # Tests de Chat
    # ========================================================================

    def test_chat_with_llama3_1(self, client):
        """Test de chat conversacional con llama3.1:8b."""
        model = "llama3.1:8b"

        print(f"\n\n{'='*70}")
        print(f"TEST: Chat con {model}")
        print(f"{'='*70}")

        response = client.post(
            "/trainer/ollama/chat",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un asistente útil que responde de forma concisa."
                    },
                    {
                        "role": "user",
                        "content": "¿Cuál es la capital de España?"
                    }
                ],
                "stream": False
            },
            headers={"X-Client-App": "test-chat"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verificaciones
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert len(data["message"]["content"]) > 0
        assert "Madrid" in data["message"]["content"] or "madrid" in data["message"]["content"]

        print(f"\n✓ Chat exitoso")
        print(f"\nConversación:")
        print(f"{'='*70}")
        print(f"Usuario: ¿Cuál es la capital de España?")
        print(f"Asistente: {data['message']['content']}")
        print(f"{'='*70}")

    # ========================================================================
    # Tests de Embeddings
    # ========================================================================

    def test_embeddings_with_nomic(self, client):
        """Test de generación de embeddings con nomic-embed-text."""
        model = "nomic-embed-text:latest"
        text = "La inteligencia artificial está transformando el mundo."

        print(f"\n\n{'='*70}")
        print(f"TEST: Embeddings con {model}")
        print(f"{'='*70}")
        print(f"Texto: {text}")
        print(f"{'='*70}")

        response = client.post(
            "/trainer/ollama/embed",
            json={
                "model": model,
                "input": text
            },
            headers={"X-Client-App": "test-embeddings"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verificaciones
        assert "embeddings" in data
        assert len(data["embeddings"]) > 0
        assert len(data["embeddings"][0]) > 0

        embedding_dim = len(data["embeddings"][0])

        print(f"\n✓ Embedding generado exitosamente")
        print(f"\nDimensiones del embedding: {embedding_dim}")
        print(f"Primeros 10 valores: {data['embeddings'][0][:10]}")

    # ========================================================================
    # Tests de Gestión de Modelos
    # ========================================================================

    def test_show_model_info(self, client):
        """Obtiene información detallada de un modelo."""
        model = "llama3.1:8b"

        print(f"\n\n{'='*70}")
        print(f"TEST: Información del modelo {model}")
        print(f"{'='*70}")

        response = client.post(
            "/trainer/ollama/models/show",
            json={"name": model},
            headers={"X-Client-App": "test-model-info"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verificaciones
        assert "modelfile" in data
        assert "parameters" in data
        assert "template" in data

        print(f"\n✓ Información obtenida exitosamente")
        print(f"\nDetalles:")
        print(f"  - Familia: {data.get('details', {}).get('family', 'N/A')}")
        print(f"  - Parámetros: {data.get('details', {}).get('parameter_size', 'N/A')}")
        print(f"  - Cuantización: {data.get('details', {}).get('quantization_level', 'N/A')}")

    def test_list_running_models(self, client):
        """Lista los modelos actualmente en ejecución."""
        print(f"\n\n{'='*70}")
        print("TEST: Modelos en Ejecución")
        print(f"{'='*70}")

        response = client.get(
            "/trainer/ollama/ps",
            headers={"X-Client-App": "test-ps"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "models" in data

        print(f"\n✓ Modelos en ejecución: {len(data['models'])}")
        for model in data["models"]:
            vram_gb = model["size_vram"] / (1024**3)
            print(f"  - {model['name']}: {vram_gb:.2f} GB VRAM")

    # ========================================================================
    # Tests de Manejo de Errores
    # ========================================================================

    def test_generate_with_nonexistent_model(self, client):
        """Verifica el manejo de errores con modelo inexistente."""
        print(f"\n\n{'='*70}")
        print("TEST: Manejo de Errores - Modelo Inexistente")
        print(f"{'='*70}")

        response = client.post(
            "/trainer/ollama/generate",
            json={
                "model": "modelo-que-no-existe:latest",
                "prompt": "Test",
                "stream": False
            },
            headers={"X-Client-App": "test-error"}
        )

        # Debe retornar error
        assert response.status_code == 404 or response.status_code == 500

        print(f"\n✓ Error manejado correctamente")
        print(f"Status Code: {response.status_code}")
        print(f"Error: {response.json().get('detail', 'N/A')}")


# ============================================================================
# Funciones auxiliares
# ============================================================================

def run_summary():
    """Muestra un resumen de los modelos disponibles antes de ejecutar tests."""
    print("\n" + "="*70)
    print("RESUMEN DE MODELOS DISPONIBLES EN OLLAMA")
    print("="*70)

    import subprocess
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    print(result.stdout)
    print("="*70 + "\n")


if __name__ == "__main__":
    """
    Ejecutar tests directamente:

    python test_ollama_integration.py

    O con pytest:

    pytest test_ollama_integration.py -v -s
    """

    run_summary()

    # Ejecutar con pytest
    pytest.main([__file__, "-v", "-s", "--tb=short"])
