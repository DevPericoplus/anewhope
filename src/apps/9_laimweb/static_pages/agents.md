# Agentes

## El ecosistema agéntico de LAIM

LAIM no es un chat suelto. Es un **ecosistema agéntico** que reparte el trabajo entre agentes, **skills** y **tools**, y los encadena en perfiles de flujo, flujos avanzados y pipelines. El objetivo es el mismo en un despacho, un laboratorio o un equipo de operaciones: que la inferencia use las piezas que el administrador ha dejado activas, con las peculiaridades y los límites de ese caso.

Usted confirma lo delicado. Este portal **no ejecuta** agentes: el catálogo vive en el cliente (`Config › Agentes`, comando `laim agents`). Skills y tools no son un escaparate aparte: son apartados de cada agente.

La idea es que LAIM encaje como herramienta válida **en cualquier ecosistema de gestión de equipos**. El administrador recorta lo que no aplica, añade lo que su procedimiento exige y publica solo lo que su política permite.

## Cómo se agrupan en las operaciones

Los agentes de fábrica no son una lista plana. Se agrupan por **operación**:

| Grupo | Qué cubre | Ejemplos |
|-------|-----------|----------|
| **Inferencia (chat, 8 fases)** | Entender, proponer el comando nativo, ejecutar con consentimiento, presentar y sugerir el siguiente paso | Local System, Remote System, Heuristic, Pi, Presenter, Suggestions, Teacher |
| **Red** | Inventario LAN y paquetes (sin MITM) | Network, Scanner, Sniffer |
| **Diagnóstico** | Plan de fuentes de log, parsers en paralelo, correlación | Diagnose, Parser |
| **Orquestación** | Planes, rutas multi-agente y HITL | Router, Planner, Pattern Composer |
| **Técnico / calidad** | Infra, seguridad, evaluación y cableado del propio catálogo | DevOps, SecOps, Ecosystem, Evaluator, Developer, Calibrate, Secure |

Active solo los que su operación necesita. El resto permanece en el catálogo. Los orquestadores de **Config › Técnico** (Ecosystem, Teacher, DevOps, Agent-R1…) inventarian el cableado, aprenden de sus correcciones o diagnostican el entorno. El detalle está en el **Manual de administrador** (§5).

### Agentes del ecosistema

| Agente | Qué hace |
|--------|----------|
| **Local System** | Comandos reales en *este* equipo, con su consentimiento |
| **Remote System** | Lo mismo en equipos de su red por SSH / `laim remote` |
| **Heuristic** | Elige el comando nativo de su SO; no inventa uno |
| **Pi** | Localiza el caso heurístico y se lo entrega a Local/Remote System |
| **Suggestions** | Tras cada respuesta, propone el siguiente paso (concepto, código, ejemplo) |
| **Presenter** | Deja la salida legible: tablas, unidades, párrafos |
| **Developer** | Spec → plan → sandbox TDD para scripts y pequeñas apps |
| **Sniffer** | Inspección de red (sin MITM) |
| **Calibrate** | Firma vocal del micrófono antes de dictar |
| **Secure** | Vigilancia OWASP del propio cliente |

Puede crear agentes propios (formulario, AgentBuilder o API) y asignarlos a un perfil de flujo. Los builtin no se eliminan: se editan parámetros, skills, tools y el perfil de **Agent Box**.

## Skills

Las **skills** son capacidades modulares: instrucciones y flags (`can_read`, `can_write`, `can_execute`…) que se inyectan en el prompt del agente cuando están activas. No se «instalan» desde este portal. Se asignan en **Config › Agentes › Catálogo de skills**.

Sirven para ampliar LAIM sin reinstalar el cliente:

- **Ahorro de tiempo** en tareas frecuentes (el agente ya sabe el tono y los límites de esa capacidad)
- **Configuración reproducible** entre equipos: el mismo ID de skill viaja en `laim.dat` / backup
- **Ampliación progresiva**: se activa o se crea una skill; no hace falta un binario nuevo

### Tipos de skills

- **Oficiales LAIM** — Builtin del producto (sistema, red, seguridad, desarrollo, orquestación…). No eliminables; sí editables
- **Internos de su organización** — Creados por el administrador, con el mismo control de acceso que el resto de `laim.dat`
- **Personalizados** — A medida de un proceso concreto (una plantilla de tarea, un conector interno, un checklist)

El botón **Info** de cada skill abre un informe Ecosystem: diseño, agentes que la usan, recomendaciones y un esquema Mermaid.

### Buenas prácticas

Active solo skills de fuentes de confianza. Revise las capacidades que piden (escritura, ejecución, red) y mantenga copias de seguridad de la configuración. En entornos sensibles, deje únicamente las aprobadas por su departamento de IT. Prefiera reutilizar IDs del catálogo Predefined antes de inventar otro nombre: Ecosystem detecta referencias rotas.

> Familiarícese con una skill oficial y un agente de lectura (`read_only`) antes de desplegar skills con `can_execute` en producción.

## Tools

Las **tools** son unidades **ejecutables**. Donde la skill dice *cómo pensar*, la tool *hace*: consulta el SO, llama a una API, lanza un script o una función Go. Un agente solo puede invocar las tools que el administrador le ha asignado, y solo si su **Agent Box** lo permite.

### Qué hay de fábrica

El catálogo builtin cubre el host y el propio runtime de LAIM: información de sistema, procesos, disco, red, servicios, GPU, sandbox, paginación y colas. No es una tienda de plugins. El administrador las habilita, las asigna y, si hace falta, crea tools propias.

| Tipo de invocación | Ejemplo de uso |
|--------------------|----------------|
| **Función / Go** | Lecturas deterministas del Core (sysinfo, disco, red) |
| **Shell** | Comando acotado, sujeto a consentimiento F6 / RISKY |
| **HTTP / API** | Servicio interno o contrato ya autorizado |
| **Script** | Python u otro runtime, de preferencia dentro del sandbox |
| **Compuesta** | Encadena varias de las anteriores |

Campos que importan al administrador: categoría (`system`, `file`, `network`, `process`, `security`, `data`, `integration`, `automation`), autenticación (`none`, `api_key`, `token`, `oauth2`…) y si la invocación es síncrona o asíncrona. **Info** abre el mismo informe Ecosystem que en skills.

### Buenas prácticas

- No asigne a un agente de presentación (`read_only`) tools de host o de red saliente
- Las tools de ejecución en *este* PC van con Local System / DevOps / SecOps y perfil `localsystem_host`
- Lo remoto va por SSH / `laim remote` (`remote_ssh`), no por un shell local disfrazado
- Código generado o de prueba: sandbox (`sandbox_code`), no el directorio de trabajo del usuario
- Si una tool pide secreto, el filtro de privacy de Agent Box lo tapa al persistir en sesión, `soul.dat` o auditoría
- Tras crear o mover una tool, **Ecosystem → validate**: una referencia colgante rompe el flujo en mitad del turno

## Flujos y pipelines

Skills y tools no se usan solas: se encadenan en **procesos de inferencia**. Recomendaciones para construirlos:

1. **Empiece por el chat de 8 fases** (`flujo8` o un flujo con `command_execution` + `user_authorization`). Es el contrato que ya entiende el usuario: proponer, confirmar, ejecutar, presentar.
2. **Perfil de flujo** — En Config › Perfiles fije prompts por fase, qué agente cubre cada paso y, si quiere, un `suggested_pattern`. Así cada equipo ve el mismo procedimiento.
3. **Pipeline tipado** — En Gestión de agentes › Pipelines elija un patrón del catálogo (`sequential`, `planning`, `human_in_loop`, `react`, `tool_use`…) y la lista de agentes. Ponga `human_checkpoint` cuando un humano deba aprobar el plan o un tramo.
4. **Pipeline dinámico** — El perfil `pipeline:dynamic` deja que Pattern Composer elija patrón y agentes por turno (compose → ejecución → síntesis). Útil para peticiones que cambian de forma; no sustituye a `flujo8` si lo que necesita es el chat clásico.
5. **Plan largo** — Planner descompone; Router ejecuta con HITL. No pida al Router que «piense el plan» y al Planner que «lance comandos».
6. **Calidad** — Swarm (varias lecturas) → Evaluator (score) → Optimizator (mejora). `learn` / `apply` a `soul.dat` solo con aprobación.
7. **Diseño offline** — El orquestador Pipeline (`assess` / `optimize` / `wave`) propone etapas; usted materializa con Pattern Composer o **LAIM FLOW DESIGNER**. No confundir ese agente con `RunPipeline` ni con DevOps CI/CD.
8. **Gobernanza** — Antes de publicar un flujo o un pipeline: Ecosystem `validate` / `consistency`. AgentBuilder no hace `commit` si hay errores. Un flujo con un agente borrado no debe aparecer en el selector del chat.

> Este portal no corre esos pipelines. Se construyen y se prueban en el cliente, en el perímetro de su red.

## Personalización: que LAIM se adapte al equipo

Los administradores de cada instalación deciden **cómo se trabaja aquí**:

| Palanca | Efecto |
|---------|--------|
| **Activar / desactivar** | Agentes, skills y tools que no aplican a su caso quedan fuera del turno |
| **Agent Box** | `read_only`, `sandbox_code`, `localsystem_host`, `remote_ssh`: el agente no puede pedir más de lo que su puesto permite |
| **HITL** | Router, pipelines, SecOps `remediate`, Ecosystem `apply`, captura viva de Sniffer, Scheduler del SO |
| **Consentimiento F6** | Independiente de Agent Box: lo RISKY o FORBIDDEN se confirma o se bloquea |
| **Perfiles y flujos** | El mismo producto, otro procedimiento: helpdesk, laboratorio, guardia de infra |
| **Ecosystem** | El cableado se valida; no se finge un catálogo coherente si hay IDs rotos |

Con esas palancas LAIM deja de ser «un asistente genérico» y pasa a ser **la herramienta de inferencia de ese equipo**: respeta su forma de trabajar, sus limitaciones y el resto de su ecosistema de gestión (ticketing, CMDB, CI/CD, malla Headscale, Share/Connect). El detalle operativo está en **Manuales → Manual de administrador** (§5–§7, Agent Box, sandbox).

### Cómo se usa en el cliente

1. Instale, `laim init` y `laim login`.
2. Abra **Config › Agentes** o `laim agents`.
3. Active solo lo necesario; asigne skills y tools; fije el perfil de Agent Box.
4. Ajuste el perfil de flujo o el pipeline; valide con Ecosystem.
5. En el chat, confirme siempre la ejecución de comandos.

> Los agentes actúan en su perímetro (este equipo o su red). Este portal no los ejecuta.
