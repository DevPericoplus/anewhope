# Administrador de Versiones y Repositorio de Contenidos

Gestiona las versiones de tu proyecto y organiza el repositorio de contenidos para el entrenamiento del modelo de lenguaje.

## Gestión de Versiones

El sistema de versionado permite mantener un historial completo de las iteraciones de tu proyecto:

- **Crear versiones**: Define nuevas versiones con nombre descriptivo y notas de cambio
- **Comparar versiones**: Visualiza diferencias entre versiones consecutivas
- **Restaurar versiones**: Vuelve a un estado anterior si es necesario
- **Aprobar versiones**: Flujo de aprobación cliente/GETmylllm antes de entrenar

## Repositorio de Contenidos

Organiza los documentos y datos que alimentarán tu modelo:

| Tipo de contenido | Formatos soportados | Uso recomendado |
|-------------------|---------------------|-----------------|
| Documentos | PDF, DOCX, TXT | Base de conocimiento |
| Hojas de cálculo | XLSX, CSV | Datos estructurados |
| Presentaciones | PPTX | Contenido visual |
| Código | PY, JS, SQL | Asistentes técnicos |

## Estados de Versión

Cada versión pasa por diferentes estados durante su ciclo de vida:

1. **Borrador**: En edición, se pueden añadir/modificar contenidos
2. **En revisión**: Pendiente de revisión por el equipo
3. **Aprobado cliente**: El cliente ha validado el contenido
4. **Aprobado GETmylllm**: El equipo técnico ha validado la estructura
5. **Listo para entrenar**: Ambas aprobaciones completadas
6. **Entrenando**: Proceso de fine-tuning en curso
7. **Entrenado**: Modelo disponible para uso

> **Nota**: Solo las versiones con doble aprobación (cliente + GETmylllm) pueden iniciar el entrenamiento.
