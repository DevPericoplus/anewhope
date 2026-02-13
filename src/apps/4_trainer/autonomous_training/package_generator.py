"""Generador de paquetes para distribución de modelos GGUF.

Este módulo implementa las subfases 9.3-9.5 de la Fase 9:
- Creación de Modelfile para Ollama
- Generación de README con instrucciones
- Empaquetado en ZIP para distribución

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class PackageGenerationError(Exception):
    """Error durante la generación del paquete."""


class PackageGenerator:
    """Generador de paquetes para distribución de modelos GGUF.

    Crea Modelfile, README y ZIP con todo lo necesario para que el cliente
    pueda usar el modelo con Ollama.
    """

    def __init__(
        self,
        id_entrenamiento: int,
        gguf_path: str,
        output_dir: Path,
        training_info: dict[str, Any] | None = None,
    ):
        """Inicializa el generador de paquetes.

        Args:
            id_entrenamiento: ID del entrenamiento
            gguf_path: Ruta al archivo GGUF
            output_dir: Directorio de salida para el paquete
            training_info: Información adicional del entrenamiento (opcional)
        """
        self.id_entrenamiento = id_entrenamiento
        self.gguf_path = Path(gguf_path)
        self.output_dir = Path(output_dir)
        self.training_info = training_info or {}

        # Directorio del paquete
        self.package_dir = self.output_dir / "package"
        self.package_dir.mkdir(parents=True, exist_ok=True)

        # Paths de archivos generados
        self.modelfile_path = None
        self.readme_path = None
        self.zip_path = None

        logger.info(
            f"[Package Generator] Inicializado para entrenamiento {id_entrenamiento}"
        )

    # =========================================================================
    # Subfase 9.3: Crear Modelfile para cliente
    # =========================================================================

    def create_modelfile(
        self,
        system_prompt: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Crea Modelfile para Ollama con el modelo GGUF.

        Args:
            system_prompt: Prompt del sistema (opcional)
            parameters: Parámetros adicionales para Ollama (opcional)

        Returns:
            Información del Modelfile generado

        Raises:
            PackageGenerationError: Si hay error creando el Modelfile
        """
        logger.info("[9.3] Creando Modelfile para cliente...")

        try:
            # Nombre del modelo GGUF (relativo al Modelfile)
            gguf_filename = self.gguf_path.name

            # System prompt por defecto si no se proporciona
            if system_prompt is None:
                system_prompt = (
                    "Eres un asistente especializado entrenado con información "
                    "específica de la organización. Responde de manera clara, "
                    "precisa y basándote en el conocimiento con el que fuiste "
                    "entrenado."
                )

            # Parámetros por defecto
            if parameters is None:
                parameters = {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 40,
                    "num_ctx": 2048,
                    "repeat_penalty": 1.1,
                }

            # Contenido del Modelfile
            modelfile_content = f"""# Modelfile para modelo autónomo ENT{self.id_entrenamiento}
# Generado automáticamente el {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Cargar el modelo GGUF
FROM ./{gguf_filename}

# System prompt
SYSTEM \"\"\"
{system_prompt}
\"\"\"

# Parámetros
"""

            # Añadir parámetros
            for param, value in parameters.items():
                modelfile_content += f"PARAMETER {param} {value}\n"

            # Añadir template (opcional, para deepseek)
            modelfile_content += """
# Template de respuesta (opcional)
TEMPLATE \"\"\"
{{ if .System }}Sistema: {{ .System }}

{{ end }}Usuario: {{ .Prompt }}

Asistente: \"\"\"
"""

            # Guardar Modelfile
            modelfile_path = self.package_dir / "Modelfile"
            modelfile_path.write_text(modelfile_content, encoding="utf-8")

            self.modelfile_path = modelfile_path

            modelfile_info = {
                "status": "created",
                "path": str(modelfile_path),
                "size_bytes": modelfile_path.stat().st_size,
                "gguf_reference": gguf_filename,
            }

            logger.info(f"[9.3] Modelfile creado: {modelfile_path}")

            return modelfile_info

        except Exception as e:
            logger.error(f"[9.3] Error creando Modelfile: {e}", exc_info=True)
            raise PackageGenerationError(f"Error creando Modelfile: {e}") from e

    # =========================================================================
    # Subfase 9.4: Generar README
    # =========================================================================

    def generate_readme(self) -> dict[str, Any]:
        """Genera README con instrucciones para el cliente.

        Returns:
            Información del README generado

        Raises:
            PackageGenerationError: Si hay error generando el README
        """
        logger.info("[9.4] Generando README para cliente...")

        try:
            # Obtener información del entrenamiento
            model_name = f"modelo-ent{self.id_entrenamiento}"
            gguf_filename = self.gguf_path.name
            gguf_size_mb = self.gguf_path.stat().st_size / (1024 * 1024)

            # Extraer info adicional si está disponible
            dataset_size = self.training_info.get("dataset_size", "N/A")
            training_time = self.training_info.get("training_time_seconds", "N/A")
            if isinstance(training_time, (int, float)):
                training_time = f"{training_time // 60} minutos"

            # Contenido del README
            readme_content = f"""# Modelo Autónomo ENT{self.id_entrenamiento}

Este paquete contiene un modelo de lenguaje fine-tuned con LoRA y exportado a formato GGUF para uso con Ollama o LM Studio.

## 📦 Contenido del Paquete

- `{gguf_filename}` - Modelo en formato GGUF ({gguf_size_mb:.2f} MB)
- `Modelfile` - Configuración para crear el modelo en Ollama
- `README.md` - Este archivo con instrucciones

## ℹ️ Información del Entrenamiento

- **ID Entrenamiento**: {self.id_entrenamiento}
- **Ejemplos de entrenamiento**: {dataset_size}
- **Tiempo de entrenamiento**: {training_time}
- **Fecha de generación**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🚀 Instalación con Ollama

### Paso 1: Verificar que Ollama esté instalado

```bash
ollama --version
```

Si no está instalado, descárgalo desde: https://ollama.ai/download

### Paso 2: Crear el modelo

En el directorio que contiene este README, ejecuta:

```bash
ollama create {model_name} -f Modelfile
```

Este comando registrará el modelo en Ollama usando el archivo GGUF incluido.

### Paso 3: Verificar la creación

```bash
ollama list
```

Deberías ver `{model_name}` en la lista de modelos disponibles.

## 💬 Uso del Modelo

### Desde la línea de comandos

```bash
ollama run {model_name}
```

Esto iniciará una sesión interactiva con el modelo.

### Desde código Python

```python
import requests

def consultar_modelo(pregunta: str) -> str:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={{
            "model": "{model_name}",
            "prompt": pregunta,
            "stream": False,
        }}
    )
    return response.json()["response"]

# Ejemplo de uso
respuesta = consultar_modelo("¿Qué información tienes disponible?")
print(respuesta)
```

### Desde API REST

```bash
curl http://localhost:11434/api/generate -d '{{
  "model": "{model_name}",
  "prompt": "Tu pregunta aquí",
  "stream": false
}}'
```

## 🎯 Características del Modelo

Este modelo ha sido entrenado específicamente con información de tu organización y puede:

- Responder preguntas sobre la documentación procesada
- Proporcionar información contextualizada y precisa
- Funcionar completamente offline (no requiere conexión a internet)
- Ejecutarse en hardware local (CPU o GPU)

## ⚙️ Configuración Avanzada

### Modificar parámetros

Puedes editar el `Modelfile` para ajustar:

- **temperature**: Controla la creatividad (0.0 = determinista, 1.0 = creativo)
- **top_p**: Muestreo nucleus (recomendado: 0.9)
- **num_ctx**: Tamaño del contexto en tokens (recomendado: 2048-4096)
- **repeat_penalty**: Penalización por repetición (recomendado: 1.1)

Después de modificar, recrea el modelo:

```bash
ollama create {model_name} -f Modelfile
```

## 🔄 Actualización del Modelo

Para actualizar a una nueva versión:

1. Elimina el modelo anterior:
   ```bash
   ollama rm {model_name}
   ```

2. Crea el nuevo modelo con el nuevo paquete:
   ```bash
   ollama create {model_name} -f Modelfile
   ```

## 🐛 Solución de Problemas

### El modelo no responde adecuadamente

- Verifica que el `SYSTEM` prompt en el Modelfile sea apropiado
- Ajusta la `temperature` (valores más bajos = más conservador)
- Aumenta `num_ctx` si las respuestas se cortan

### Error al crear el modelo

- Verifica que el archivo GGUF esté en el mismo directorio que el Modelfile
- Asegúrate de tener suficiente espacio en disco
- Revisa los logs de Ollama: `ollama logs`

### Rendimiento lento

- Considera usar una GPU si está disponible
- Reduce `num_ctx` para menor uso de RAM
- Usa un modelo con cuantización más agresiva (Q4 en lugar de Q8)

## 📚 Recursos Adicionales

- **Documentación Ollama**: https://github.com/ollama/ollama/blob/main/docs/README.md
- **Modelfile Reference**: https://github.com/ollama/ollama/blob/main/docs/modelfile.md
- **API Documentation**: https://github.com/ollama/ollama/blob/main/docs/api.md

## 🆘 Soporte

Para reportar problemas o solicitar mejoras en el modelo, contacta con el equipo de entrenamiento.

---

**Nota**: Este modelo es propiedad de la organización y contiene información específica. No distribuir sin autorización.
"""

            # Guardar README
            readme_path = self.package_dir / "README.md"
            readme_path.write_text(readme_content, encoding="utf-8")

            self.readme_path = readme_path

            readme_info = {
                "status": "created",
                "path": str(readme_path),
                "size_bytes": readme_path.stat().st_size,
            }

            logger.info(f"[9.4] README generado: {readme_path}")

            return readme_info

        except Exception as e:
            logger.error(f"[9.4] Error generando README: {e}", exc_info=True)
            raise PackageGenerationError(f"Error generando README: {e}") from e

    # =========================================================================
    # Subfase 9.5: Empaquetar entregable
    # =========================================================================

    def create_zip_package(
        self,
        cleanup_temp: bool = True,
    ) -> dict[str, Any]:
        """Empaqueta GGUF + Modelfile + README en ZIP.

        Args:
            cleanup_temp: Si True, elimina archivos temporales después del empaquetado

        Returns:
            Información del ZIP generado

        Raises:
            PackageGenerationError: Si hay error creando el ZIP
        """
        logger.info("[9.5] Empaquetando entregable en ZIP...")

        try:
            # Verificar archivos necesarios
            if not self.gguf_path.exists():
                raise PackageGenerationError(f"GGUF no encontrado: {self.gguf_path}")
            if not self.modelfile_path or not self.modelfile_path.exists():
                raise PackageGenerationError("Modelfile no generado")
            if not self.readme_path or not self.readme_path.exists():
                raise PackageGenerationError("README no generado")

            # Copiar GGUF al directorio del paquete
            gguf_in_package = self.package_dir / self.gguf_path.name
            if not gguf_in_package.exists():
                logger.info(f"[9.5] Copiando GGUF a {self.package_dir}")
                shutil.copy2(self.gguf_path, gguf_in_package)

            # Crear nombre del ZIP
            zip_filename = f"ENT{self.id_entrenamiento}_modelo_autonomo.zip"
            zip_path = self.output_dir / zip_filename

            # Crear ZIP
            logger.info(f"[9.5] Creando ZIP: {zip_path}")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                # Agregar archivos al ZIP
                for file_path in self.package_dir.rglob("*"):
                    if file_path.is_file():
                        # Nombre relativo dentro del ZIP
                        arcname = file_path.relative_to(self.package_dir)
                        logger.debug(f"[9.5] Añadiendo al ZIP: {arcname}")
                        zipf.write(file_path, arcname=arcname)

            # Calcular tamaño del ZIP
            zip_size_mb = zip_path.stat().st_size / (1024 * 1024)

            # Contar archivos incluidos
            file_count = len(list(self.package_dir.rglob("*")))

            self.zip_path = zip_path

            package_info = {
                "status": "packaged",
                "path": str(zip_path),
                "size_mb": round(zip_size_mb, 2),
                "filename": zip_filename,
                "files_included": file_count,
                "contents": [
                    self.gguf_path.name,
                    "Modelfile",
                    "README.md",
                ],
            }

            logger.info(
                f"[9.5] ZIP creado: {zip_size_mb:.2f} MB con {file_count} archivos"
            )

            # Cleanup si se solicita
            if cleanup_temp:
                logger.info("[9.5] Eliminando archivos temporales...")
                # No eliminar package_dir porque contiene los archivos fuente
                # Solo eliminar merged model si existe (lo hace el exporter)

            return package_info

        except Exception as e:
            logger.error(f"[9.5] Error empaquetando ZIP: {e}", exc_info=True)
            raise PackageGenerationError(f"Error creando ZIP: {e}") from e

    # =========================================================================
    # Proceso completo de generación de paquete
    # =========================================================================

    def generate_complete_package(
        self,
        system_prompt: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ejecuta el proceso completo de generación (subfases 9.3-9.5).

        Args:
            system_prompt: Prompt del sistema para el Modelfile
            parameters: Parámetros para Ollama

        Returns:
            Resumen completo de la generación

        Raises:
            PackageGenerationError: Si hay error en alguna subfase
        """
        logger.info("[Package Generator] Iniciando generación de paquete...")

        summary = {
            "id_entrenamiento": self.id_entrenamiento,
            "subfases": {},
        }

        # 9.3: Crear Modelfile
        modelfile_info = self.create_modelfile(system_prompt, parameters)
        summary["subfases"]["9.3"] = modelfile_info

        # 9.4: Generar README
        readme_info = self.generate_readme()
        summary["subfases"]["9.4"] = readme_info

        # 9.5: Crear ZIP
        package_info = self.create_zip_package()
        summary["subfases"]["9.5"] = package_info

        summary["status"] = "completed"
        summary["package_path"] = package_info["path"]
        summary["package_size_mb"] = package_info["size_mb"]

        logger.info("[Package Generator] Generación de paquete completada ✓")

        return summary
