# Servicios

## El portal de LAIM: instalar, actualizar y acompañar el cliente

**LAIM** (*Local Artificial Intelligence Management*) es el cliente que instala en **su equipo**. Este portal reúne lo que hace falta alrededor de ese cliente: instaladores, la misma documentación que verá en **Ayuda**, el foro de la comunidad y el canal de soporte.

Los datos del día a día se procesan **en su máquina** (o en un Share de su red). Aquí no corre la inferencia: aquí se descarga, se lee y se pide ayuda.

---

### Instaladores

Cliente **community_edition** para **Windows**, **macOS** (Apple Silicon e Intel) y **Linux** (`.deb` / `.rpm`). El paquete lleva el binario, los `.dat` comunes de producto y los plugins Basic. Tras instalar: `laim init`, `laim login` y `laim web` (interfaz local en `http://localhost:4321`) o `laim chat` en terminal.

Las actualizaciones posteriores las detecta el propio cliente (`laim update`), no esta página.

Pulse **Ir a Instaladores** al pie de esta página para abrir las descargas. Si no hay sesión, se abre el inicio de sesión.

---

### Manuales

Los mismos documentos que el cliente abre en **`laim web` → Ayuda**. Tras iniciar sesión, **Manuales** los muestra completos. Editor y Temas son herramientas de esa página, no manuales.

| Manual | En Ayuda |
|--------|----------|
| Manual de administrador | Instalación, usuarios, tiers, Share/Connect, agentes, seguridad |
| Manual de usuario | Chat, voz, SSH, notificaciones y uso diario |
| Red mesh WireGuard (Headscale) | Malla privada entre equipos sin abrir puertos a Internet |
| Recomendaciones | Uso responsable y avisos legales |
| Ventana de contexto | `num_ctx`, resumen del historial y VRAM |
| Windows remoto (OpenSSH) | Activar SSH en Windows para `laim remote` |

---

### Modelos de IA local

`In progress`

El cliente ya habla con **Ollama** en local y con un **Share** de su red (Connect). El catálogo de modelos base / especializados / a medida **desde este portal** se está cerrando: en breve podrá asignar y descargar modelos a su cuenta; hoy esa parte se configura en el propio cliente (`laim catalog`, `laim localmodels`, Config › Modelos IA).

| Tipo | Estado |
|------|--------|
| **Ollama en su equipo** | Disponible en el cliente |
| **Share / Connect** (IA de otro LAIM de su red) | Disponible en el cliente |
| **Catálogo del portal** (base, especializado, a medida) | `In progress` |

Los proyectos de entrenamiento a medida siguen en **[getmylllm.com](https://www.getmylllm.com/)**.

---

### Agentes

LAIM no es un chat suelto: un **ecosistema agéntico** (Config › Agentes, comando `laim agents`) reparte el trabajo entre agentes, **skills** y **tools**, y los encadena en flujos o pipelines. Usted confirma lo delicado. Skills es un apartado de Agentes, no un escaparate aparte.

| Agente | Qué hace |
|--------|----------|
| **Local System** | Comandos reales en *este* equipo (con su consentimiento) |
| **Remote System** | Lo mismo en equipos de su red por SSH / `laim remote` |
| **Heuristic** | Elige el comando nativo de su SO; no inventa uno |
| **Pi** | Localiza el caso heurístico y se lo entrega a Local/Remote System |
| **Suggestions** | Tras cada respuesta, propone el siguiente paso (concepto, código, ejemplo) |
| **Presenter** | Deja la salida legible: tablas, unidades, párrafos |
| **Developer** | Spec → plan → sandbox TDD para scripts y pequeñas apps |
| **Sniffer** | Inspección de red (sin MITM) |
| **Calibrate** | Firma vocal del micrófono antes de dictar |
| **Secure** | Vigilancia OWASP del propio cliente |

El administrador activa, limita (Agent Box, HITL) y personaliza para que LAIM encaje en la forma de trabajar de cada equipo. El detalle vive en el **Manual de administrador** y en la página **Agentes** de este portal (tras iniciar sesión).

---

### Complementos

Plugins del cliente (tier Basic en community_edition) y utilidades opcionales: almacenamiento, observabilidad, adaptadores. Nada de eso es obligatorio para conversar en local.

---

### Foro

El **Foro LAIM** (menú de la izquierda cuando hay sesión) es el canal de la comunidad: hilos, respuestas y perfil. Distinto de **Soporte**, que es el ticket 1:1 con el equipo.

---

### Soporte y FAQ

- **Soporte** — Formulario de Contacto y seguimiento de su caso
- **FAQ** — Privacidad, modos de uso y buenas prácticas

---

## Cómo se usa el cliente

| Modalidad | Descripción |
|-----------|-------------|
| **CLI** | `laim chat`, `laim remote`, `laim config`… Automatización y administración |
| **Web local** | `laim web` — pantallas CRT en su equipo, mismo núcleo que la CLI |

**Windows**, **macOS** y **Linux** (`.deb` / `.rpm`). El instalador no pide privilegios de administrador en la modalidad script.

---

## Formas de usar la IA

### En su perímetro (recomendado)

| Opción | Descripción |
|--------|-------------|
| **IA local** | Ollama (u otro motor local) en su estación o servidor |
| **Cliente ligero + Share** | Este equipo pregunta; la inferencia corre en otro LAIM de su red |
| **LAIM cloud genérica** | Modelos extendidos en nuestra nube, solo si su política lo permite. Aún no está abierto. `In progress` |

### Integraciones opcionales

Google (Gemini), Mistral o Kimi se configuran **en el cliente**, de forma explícita, cuando existan contrato y claves. No se activan solas desde este portal.

---

## Compromiso

- **Privacidad** — En modo local, el trabajo permanece en su infraestructura
- **Seguridad** — Sesión cifrada, descargas firmadas cuando el trámite de firma esté listo, y las prácticas del manual
- **Actualización** — El cliente (`laim update`) lleva a la última versión desde cualquier instalación anterior

> Empiece por **Instaladores**. Los textos largos están en **Manuales** (sesión) y en **Ayuda** del cliente.
