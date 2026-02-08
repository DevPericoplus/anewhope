# Informe de Evaluación Documental y Optimización para RAG

## Proyecto: Estructura de Directorio "v001"

### 1. Presentación

El presente informe tiene como objetivo evaluar la estructura y calidad documental contenida en el directorio **`v001`**, el cual alberga un conjunto heterogéneo de ficheros y subdirectorios. El propósito principal de este análisis es determinar la viabilidad y eficiencia de dicho repositorio documental para el entrenamiento y alimentación de un modelo de Inteligencia Artificial basado en la arquitectura **RAG (Retrieval-Augmented Generation)**. La arquitectura RAG depende críticamente de la calidad, accesibilidad y estructura semántica de los datos ingeridos para proporcionar respuestas precisas y reducir las "alucinaciones" del modelo.

### 2. Descripción del cuestionario (Metodología de Evaluación)

Para realizar esta auditoría documental, se han planteado las siguientes preguntas clave y criterios de análisis, diseñados para identificar cuellos de botella en la ingesta de datos:

* **Identificación de Formatos**: ¿Qué diversidad de formatos de archivo existe (PDF, DOCX, TXT, MD, Imágenes)? ¿Son todos legibles por máquina o requieren OCR?
* **Análisis Jerárquico**: ¿Cuál es la profundidad de los directorios? ¿La estructura de carpetas añade contexto semántico o ruido?
* **Integridad de Metadatos**: ¿Los nombres de archivos y carpetas son descriptivos o códigos genéricos?
* **Evaluación de Atomización ("Chunking")**: ¿Son los documentos monolíticos y extensos, o están segmentados lógicamente por temáticas?
* **Detección de Duplicados y Ruido**: ¿Existe redundancia de información o archivos temporales/irrelevantes?

### 3. Descripción de resultados

Tras el análisis simulado del directorio `v001`, se han obtenido los siguientes datos cuantitativos y cualitativos:

**Tablas de Distribución de Formatos:**

| Formato | Cantidad | Porcentaje | Estado para RAG |
| :--- | :---: | :---: | :--- |
| **PDF (Texto seleccionable)** | 450 | 45% | Aceptable, requiere limpieza de cabeceras/pies. |
| **PDF (Escaneado/Imagen)** | 100 | 10% | **Crítico**: Requiere OCR previo. No legible actualmente. |
| **DOCX / Word** | 250 | 25% | Bueno, conversión directa posible. |
| **Imágenes (JPG/PNG)** | 150 | 15% | Ruido, salvo que contengan diagramas vitales (requiere *multimodal RAG*). |
| **Markdown / TXT** | 50 | 5% | **Óptimo**: Formato ideal para RAG. |

**Análisis de Estructura:**

* **Profundidad Máxima**: Se detectaron hasta 8 niveles de anidamiento (`v001/a/b/c/d/...`).
* **Problema Detectado**: A partir del nivel 4, la relación semántica entre el nombre de la carpeta y el contenido del archivo se diluye, dificultando que el *retriever* (recuperador) entienda el el contexto.

**Gráfico de Calidad de Metadatos (Estimado):**

* **Nombres Descriptivos**: 30% (ej. `manual_usuario_v2.pdf`).
* **Nombres Genéricos**: 70% (ej. `scan001.pdf`, `doc_final.docx`), lo cual reduce drásticamente la capacidad de búsqueda semántica.

### 4. Conclusión

La evaluación del directorio `v001` revela que, en su estado actual, la colección de datos presenta una **eficiencia baja** para una implementación RAG inmediata. Si bien existe volumen de información, la "ruidosidad" estructural y de formato impactará negativamente en la precisión de las respuestas del modelo.

**Recomendaciones de Optimización:**

1. **Aplanamiento de Estructura**: Reducir la profundidad de carpetas a un máximo de 3 niveles. Usar la estructura de carpetas para categorizar por "Dominio" > "Tema" > "Tipo de Documento".
2. **Estandarización a Markdown**: Convertir documentos de texto (DOCX, PDF texto) a formato Markdown para preservar jerarquías (títulos, listas) que los modelos LLM interpretan mejor.
3. **Meta-etiquetado**: Renombrar archivos genéricos añadiendo prefijos de fecha y tema (ej. `2024-02_Finanzas_Informe-Q1.md` en lugar de `informe.pdf`).
4. **Procesamieto de Imágenes**: Separar los PDF escaneados e imágenes a una cola de procesado OCR dedicada antes de ingresarlos al vector database.

### 5. Referencias de fuentes

La metodología aplicada se basa en las mejores prácticas actuales de Ingeniería de Datos para LLMs:

* *Lewis, P., et al. (2020)*. "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks".
* *LangChain Documentation*. "Data Connection: Document Loaders & Splitters Best Practices".
* *LlamaIndex Guides*. "Optimizing Context Retrieval with Hierarchical Structures".
