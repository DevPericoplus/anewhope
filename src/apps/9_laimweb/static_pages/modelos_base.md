# Modelos base

`In progress`

## Modelos adaptados a su hardware local

El catálogo **asignable desde este portal** se está cerrando. Ollama y Share/Connect ya funcionan en el cliente (`laim catalog`, `laim localmodels`, Config › Modelos IA).

Los **modelos base** son el punto de partida: un slot por **tier** (Traductor, Rápido, Medio…) y dos familias (**blue** / **green**) para cambiar de juego de modelos sin tocar cada casilla.

**Ver catálogo de modelos base** abre la referencia con la que se ha ejercitado LAIM en el equipo de desarrollo: la misma tabla `tier | blue | green`. Son modelos **probados**, no una talla única. En su instalación pruebe otras versiones o tamaños de esas familias según CPU, GPU y memoria.

### ¿Para qué sirven?

- Inferencia local con **baja latencia** y sin dependencia permanente de la nube
- Pruebas y validación de flujos antes de adoptar modelos más especializados
- Uso seguro en entornos donde la **privacidad** y el **control de datos** son prioritarios

### Perfiles habituales

| Perfil | Orientación |
|--------|-------------|
| **Equipo estándar** | Equilibrio entre calidad y consumo de recursos |
| **Hardware avanzado** | Mayor capacidad de contexto y respuesta más rica |
| **Cliente ligero** | Conexión a nodos LAIM en otros equipos de su red |

### Cómo elegir

**Modelo recomendado para mi equipo** abre una mini-guía: cómo leer cores y memoria de la GPU (`laim info`), cuándo subir la concurrencia, cómo la memoria recorta el tamaño (tabla 6–128 GB) y qué hace el warmup. Luego confirme el modelo con Asesor, Capacidades, `laim eval` y Comparar.

**Comparativa de requisitos** enfrenta monopuesto dedicado y Share + Connect (cores y memoria mínima), avisa de la holgura extra con Headscale / `laim remote`, y recuerda colas, horarios valle y ajustes internos (KV-cache, `num_ctx`, warmup). Si tiene dudas, **FAQ**.

> Los modelos se descargan e instalan desde el cliente LAIM (`laim catalog` o Config › Modelos IA).
