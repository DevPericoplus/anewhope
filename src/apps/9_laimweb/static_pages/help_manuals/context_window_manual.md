# Ventana de Contexto y Caché de Inferencia — Manual del Administrador

Esta sección describe cómo LAIM gestiona la ventana de contexto de los modelos de lenguaje locales (Ollama) y el proceso automático de compresión de historial denominado **"Chat Context Summarized"**.

---

## ¿Qué es la ventana de contexto?

Cuando LAIM realiza una inferencia, envía al modelo el historial de la conversación junto con el mensaje actual. Cuanto mayor sea ese historial, más tokens ocupa la ventana de contexto del modelo.

Ollama gestiona internamente su propio KV cache de atención. LAIM controla cuántos tokens de historial se envían en cada llamada (`num_ctx`) y durante cuánto tiempo el modelo permanece cargado en VRAM (`keep_alive`).

---

## Memoria y Hardware

### Consumo de VRAM

Ampliar la ventana de contexto (por ejemplo, de 8K a 64K o 128K tokens) requiere una gran cantidad de memoria adicional en la tarjeta gráfica o en la memoria unificada (sistemas Apple Silicon).

**Estimación orientativa para un modelo de 7-8B parámetros:**

| Tokens en contexto | KV cache aprox. | GPU mínima recomendada |
|--------------------|-----------------|------------------------|
| 4 096              | ~1,1 GB         | 6 GB VRAM              |
| 8 192              | ~2,25 GB        | 8 GB VRAM              |
| 16 384             | ~4,5 GB         | 12 GB VRAM             |
| 32 768             | ~9 GB           | 16-24 GB VRAM          |

> **Nota:** estos valores son aproximaciones basadas en ~288 KiB/token para un modelo 8B en FP16. Los modelos cuantizados (Q4, Q8) reducen este coste aproximadamente a la mitad.

### Límites prácticos

Aunque muchos modelos modernos soportan teóricamente 32K, 64K o 128K tokens, los equipos de uso común suelen sufrir desbordamientos de memoria si se maximiza el contexto en paralelo con el tamaño del modelo.

### Rendimiento e Inferencia

- **Pérdida de velocidad:** Procesar textos muy largos de forma local vuelve la generación de respuestas muy lenta, tardando minutos por consulta en hardware básico de consumo.
- **Degradación:** A medida que el contexto se llena, la capacidad del modelo para recordar o prestar atención a los detalles del inicio del texto disminuye considerablemente.

---

## Proceso "Chat Context Summarized"

Cuando el historial acumulado en una sesión supera el umbral configurado, LAIM activa automáticamente el proceso **Chat Context Summarized**:

### Pasos del funcionamiento

1. **Monitoreo de tokens:** LAIM estima los tokens del historial (1 token ≈ 4 caracteres Unicode) antes de cada inferencia.
2. **Activación:** Al superar el porcentaje del límite configurado (por defecto 85%), se activa la función de resumen.
3. **Compresión:** El modelo de tier medio procesa el historial y genera notas concisas con las peticiones y decisiones tomadas.
4. **Optimización:** Los mensajes más antiguos se reemplazan por el resumen, liberando espacio para que la conversación continúe con normalidad.
5. **Notificación:** La interfaz web muestra el mensaje *"Context compressed — history compacted to continue the session."* Desde ese punto, las nuevas inferencias utilizan el historial comprimido.

### Beneficios

- **Conversaciones continuas:** El usuario puede seguir iterando sobre resultados anteriores sin reiniciar la sesión.
- **Menor consumo de VRAM:** El historial activo es siempre más pequeño que el límite configurado.
- **Transparencia:** El proceso es automático y no interrumpe el flujo de trabajo.

---

## Configuración

La ventana de contexto se configura en:

**Configuración › Asistente de configuración › Internal › Local — Configuración de instalación**

en la sección **"Ventana de Contexto y Memoria Caché"**.

| Parámetro | Descripción | Rango | Defecto |
|-----------|-------------|-------|---------|
| **Límite de contexto (tokens)** | Máximo de tokens enviados al modelo por inferencia. Incrementar requiere más VRAM. | 1 024 – 131 072 | 8 192 |
| **Umbral de compresión (%)** | Porcentaje del límite al que se activa Chat Context Summarized. | 50 – 98 | 85 |
| **Turnos a preservar tras comprimir** | Número mínimo de turnos recientes conservados después de cada compresión. | ≥ 1 | 3 |
| **Modelo caliente en VRAM (minutos)** | Tiempo que Ollama mantiene el modelo cargado en VRAM entre peticiones (`keep_alive`). `0` = descargar inmediatamente. | ≥ 0 | 5 |

### Recomendaciones por tipo de hardware

| Hardware | `max_context_tokens` recomendado |
|----------|----------------------------------|
| GPU 6 GB (RTX 3060, RX 6600…) | 4 096 |
| GPU 8 GB (RTX 3070, RX 6700…) | 8 192 |
| GPU 12 GB (RTX 3080, RX 6800…) | 16 384 |
| GPU 16 GB o superior | 32 768 |
| Apple Silicon M1/M2 8 GB RAM unificada | 4 096 – 8 192 |
| Apple Silicon M1/M2 Pro/Max 16-32 GB | 16 384 – 32 768 |
| CPU (sin GPU dedicada) | 2 048 – 4 096 |

---

## Ámbito de aplicación

El sistema de ventana de contexto y compresión automática aplica a tres funcionalidades de LAIM:

| Funcionalidad | Historial gestionado | Evento de compresión |
|---------------|----------------------|----------------------|
| `laim chat` (flujo de 8 fases) | Turnos en `laim.memory` cifrado | Pre-F1, antes de cada turno |
| `laim direct` (conversación directa) | Slice de mensajes en RAM | Antes de cada llamada a Ollama |
| `laim remote` (sugerencias IA en SSH) | Historial de sugerencias de la sesión SSH | Antes de cada sugerencia |

---

## Notas técnicas

- El modelo de tier medio (`model_tiers.medium`) es el responsable de generar el resumen durante la compresión.
- Si el tier medio no está configurado, se utiliza el tier rápido como fallback, y si este tampoco está disponible, el tier lento.
- El parámetro `keep_alive` se pasa a Ollama (`keep_alive: "5m"` para 5 minutos). En Apple Silicon con 16 GB o más, si el valor de fábrica no se ha cambiado, LAIM envía `keep_alive: "-1"` para dejar el modelo cargado en RAM unificada (llama.cpp + Metal; no MLX).
- La estimación de tokens es heurística (`len(runes) / 4`) y puede diferir del conteo real del tokenizador del modelo. Esta estimación es intencionalmente conservadora para evitar superar el límite real.
- El resumen se almacena en `laim.memory` bajo la clave `chat:compaction:summary` (cifrado).

---

## Preguntas frecuentes

**¿Se pierde información importante al comprimir?**
El proceso de compresión está diseñado para preservar peticiones clave, decisiones tomadas, valores de datos mencionados, rutas de ficheros y salidas de comandos referenciadas. Se descartan saludos, contexto repetido y explicaciones verbosas.

**¿Puedo desactivar la compresión?**
Actualmente no hay un interruptor de desactivación. Para evitar la compresión, establece un límite de contexto muy alto (131 072 tokens) y asegúrate de que tu hardware tiene suficiente VRAM.

**¿Cómo sé que se ha producido una compresión?**
En la interfaz web aparece el mensaje *"Contexto comprimido — el historial fue compactado para continuar la sesión."* En el modo terminal, se registra en `logs/console.log`.

**¿Afecta a la calidad de las respuestas?**
Inmediatamente después de una compresión puede haber una ligera pérdida de detalle en el historial muy antiguo. Sin embargo, el proceso preserva los datos más relevantes para que la conversación pueda continuar de forma coherente.
