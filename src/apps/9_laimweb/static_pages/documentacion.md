# Documentación

## Recursos técnicos del ecosistema LAIM

Esta sección recopila referencia técnica para operar el cliente **LAIM** (*Local Artificial Intelligence Management*) en su equipo: línea de comandos, interfaz web local y enlaces útiles. Para guías paso a paso orientadas al usuario final, consulte **Manuales** tras iniciar sesión.

---

## LAIM CLI — Referencia de comandos

Tras instalar el cliente, puede invocar el binario `laim` desde una terminal o consola. La forma más rápida de ver la ayuda integrada es:

```bash
./bin/mac/laim help
```

En Linux o Windows sustituya la ruta del binario según su instalación (por ejemplo `./bin/linux/laim` o el ejecutable en su carpeta de instalación).

### Salida de ejemplo (`laim help`)

```text
LAIM (Local Artificial Intelligence Management) CLI

Usage: laim <command> [options]

Available Arguments:
  init      Establishes a workspace and initializes the configuration.
  login     Authenticates a user and opens an encrypted session (laim.session).
  config    Interactive assistant to configure LAIM (administrators only; user management in laim.dat).
  info      Retrieves comprehensive technical details regarding the local system.
  connect   Connect client to LAIM Share master (view/edit/test, admin).
  share     Share master status, edit config, credentials and share_api (admin).
  remote    Connects to a remote service hosted on an external server.
  agent     Accesses the autonomous AI agent assistant mode for the current session.
  chat      Enters an interactive chat mode (optional model override; tier mode without argument).
  localmodels  Lists local Ollama models grouped by parameter size (ollama list).
  web       Starts the local Python Reflex web user interface.
  version   Shows the current version of the LAIM application.
  update    Updates LAIM to the latest or specified version.
  help      Shows help and usage information for all available arguments.
```

---

### `init`

Establece el espacio de trabajo e inicializa la configuración local de LAIM. Suele ser el primer paso tras instalar el cliente en un equipo nuevo.

---

### `login`

Autentica al usuario y abre una sesión cifrada (`laim.session`). Necesaria para operar con servicios y modelos asociados a su cuenta.

---

### `config`

Asistente interactivo de configuración. Reservado a **administradores**; incluye gestión de usuarios en `laim.dat`.

---

### `info`

Muestra información técnica detallada del sistema local: entorno, recursos y estado útil para diagnóstico.

---

### `connect`

Conecta el cliente al nodo **LAIM Share** maestro. Permite consultar, editar y probar la configuración (funciones de administración).

---

### `share`

Gestiona el nodo **Share** en modo maestro: estado, configuración, credenciales y `share_api` (administración).

---

### `remote`

Establece conexión con un servicio remoto alojado en un servidor externo, según la política de su organización.

---

### `agent`

Accede al modo asistente de **agente autónomo** de IA para la sesión activa.

---

### `chat`

Inicia un **chat interactivo** en terminal. Acepta un modelo opcional como argumento; sin argumento, usa el modo por niveles (*tier*) configurado.

---

### `localmodels`

Lista los modelos **Ollama** instalados localmente, agrupados por tamaño de parámetros (equivalente a `ollama list`).

---

### `web`

Arranca la **interfaz web local** del usuario (Reflex en Python) en su equipo, complementaria a la CLI.

---

### `version`

Muestra la versión instalada del cliente LAIM.

---

### `update`

Actualiza LAIM a la última versión disponible o a una versión concreta indicada como argumento.

---

### `help`

Muestra la ayuda y el uso de todos los argumentos disponibles (salida mostrada arriba).

---

## Pagina web local (localhost)

**www.laim.app** es la cara web de LAIM: la misma capacidad operativa que el cliente en línea de comandos, presentada con **interfaces más amigables** para quienes prefieren entornos gráficos sin renunciar al espíritu de una consola.

### Interfaz tipo terminal ampliada

Tras iniciar sesión, la aplicación web reproduce la experiencia del CLI en un diseño de **doble panel** con estética CRT (verde fósforo, tipografía monoespaciada):

| Zona | Función |
|------|---------|
| **COMANDOS** | Barra lateral con accesos directos a los argumentos de `laim`: `help`, `version`, `info`, `localmodels`, `config`, `chat`, `init`, `connect`, `share`, `remote`, `direct`, `agent`, `update`, … |
| **TERMINAL** | Área principal que muestra la salida como en una consola real (por ejemplo `$ laim help` y el listado de argumentos disponibles) |

No hace falta memorizar la sintaxis: un clic en el botón equivale a ejecutar el comando correspondiente, y el resultado aparece en el panel **TERMINAL** con el mismo formato que vería en su terminal local.

### Qué aporta respecto al CLI puro

- **Navegación visual** — Los comandos habituales están a un clic; ideal para explorar capacidades sin consultar la ayuda en cada paso.
- **Sesión identificada** — El panel de comandos refleja el usuario activo y su rol (por ejemplo, administrador), alineado con la sesión cifrada del cliente (`laim.session` / autenticación en portal).
- **Misma semántica** — Cada botón del menú **COMANDOS** corresponde a un argumento documentado arriba (`init`, `config`, `chat`, `localmodels`, etc.); la web no sustituye el binario local, sino que lo **complementa** cuando prefiere pantalla gráfica.
- **Catálogo y acompañamiento** — Además del modo terminal, el portal concentra instaladores, manuales, modelos, skills, complementos y soporte: funcionalidades **extendidas** orientadas a descarga, documentación y operación cotidiana, más allá de lo que ofrece una sola ventana de consola.

### ¿CLI, web local o portal?

| Entorno | Cuándo usarlo |
|---------|----------------|
| **`laim` en terminal** | Automatización, scripts, administración remota por SSH |
| **`laim web` (Reflex local)** | Interfaz gráfica en su propio equipo, sin depender del navegador público |
| **www.laim.app** | Acceso desde cualquier navegador: terminal ampliada + catálogo de recursos y área privada tras registro |

Para guías paso a paso (instalación, seguridad, uso diario), use la sección **Manuales** del menú autenticado. La referencia de argumentos CLI sigue en los bloques anteriores de esta página.

---

## Enlaces útiles

- [Ollama — Modelos locales](https://ollama.com/)
- [getmylllm.com — Proyectos y modelos a medida](https://www.getmylllm.com/)
- [Reflex — Documentación](https://reflex.dev/docs/) *(interfaz web local del cliente)*

> La referencia CLI se ampliará en próximas revisiones con ejemplos, opciones y casos de uso por comando.
