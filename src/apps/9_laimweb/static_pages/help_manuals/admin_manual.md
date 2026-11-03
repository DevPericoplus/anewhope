# Manual de Administrador — LAIM

**LAIM** (Local Artificial Intelligence Management) es una plataforma de gestion de IA local (y remota/conectada) disenada para entornos corporativos o domesticos avanzados. Este manual cubre la instalacion, configuracion, mantenimiento y seguridad desde el rol de administrador.

---

## Indice

1. [Instalacion y primer inicio](#1-instalacion-y-primer-inicio)
   - [1.5 Registro de la instalacion en laim.app](#15-registro-de-la-instalacion-en-laimapp)
2. [Navegacion del administrador](#2-navegacion-del-administrador)
3. [Gestion de usuarios y sesiones](#3-gestion-de-usuarios-y-sesiones)
4. [Modelos de IA — Tiers y fases](#4-modelos-de-ia--tiers-y-fases)
   - [4.1 Nueve tiers de modelos](#41-nueve-tiers-de-modelos)
   - [4.9 Tier Alternativo — Pruebas temporales de modelos](#49-tier-alternativo--pruebas-temporales-de-modelos)
   - [4.10 Familias de tiers — Estrategia blue/green en LAIM](#410-familias-de-tiers--estrategia-bluegreen-en-laim)
   - [4.5 Evaluar modelos](#45-evaluar-modelos-laim-eval)
   - [4.6 Comparar modelos](#46-comparar-modelos-laim-compare)
   - [4.7 Estrategia de asignacion de tiers](#47-estrategia-de-asignacion-de-tiers-basada-en-evaluaciones)
   - [4.8 Panel Herramientas](#48-panel-herramientas-analisis-de-modelos-en-la-web)
   - [4.11 Cache de ficha Direct](#411-cache-de-ficha-direct)
5. [Gestion de agentes, skills, tools y pipelines](#5-gestion-de-agentes-skills-tools-y-pipelines)
   - [5.7 LAIM Agent Box — contrato y privacy de agentes](#57-laim-agent-box--contrato-y-privacy-de-agentes)
6. [Perfiles de flujo de inferencia](#6-perfiles-de-flujo-de-inferencia)
7. [Flujos avanzados](#7-flujos-avanzados)
8. [Share y Connect — Red y servicios IA](#8-share-y-connect--red-y-servicios-ia)
   - [8.4 Configurar Connect (perfiles)](#84-configurar-el-modo-connect-cliente)
   - [8.7 Share Network Monitor](#87-laim-share-network-monitor)
9. [Gestion de equipos remotos](#9-gestion-de-equipos-remotos)
   - [9.1.1 Clave SSH (privada LAIM / authorized_keys)](#911-clave-ssh-privada-en-laim-publica-en-el-servidor)
10. [Headscale — Red mesh WireGuard](#10-headscale--red-mesh-wireguard)
   - [10.3 Registrar un equipo](#103-registrar-un-equipo-en-la-red-mesh)
   - [10.5 Windows OpenSSH y malla](#105-windows-openssh-y-malla)
   - [10.6 Chat y Suggestions sobre SSH](#106-chat-y-suggestions-sobre-ssh)
11. [Internal — Configuracion avanzada](#11-internal--configuracion-avanzada)
   - [11.3.0 Firewall y puertos LAIM](#1130-firewall-y-puertos-laim)
   - [11.3.2 Paralelismo Ollama](#1132-paralelismo-ollama)
   - [11.3.3 Configuracion MLX (Apple Silicon)](#1133-configuracion-mlx-apple-silicon)
12. [Seguridad y cifrado](#12-seguridad-y-cifrado)
   - [12.7 Proteccion activa de ficheros (Tier 1 / Tier 2 / Tier 3)](#127-proteccion-activa-de-ficheros-tier-1--tier-2--tier-3)
13. [Agente Teacher y soul.dat](#13-agente-teacher-y-souldat)
13bis. [soulmachine.dat — inventario del equipo local](#13bis-soulmachinedat--inventario-del-equipo-local)
14. [Sistema de plugins](#14-sistema-de-plugins)
15. [Sistema de traduccion i18n](#15-sistema-de-traduccion-i18n)
   - [15.4 Traduccion visual de manuales e informes](#154-traduccion-visual-de-manuales-e-informes)
   - [15.5 Manuales por idioma (`spanish` / `english`)](#155-manuales-por-idioma-spanish--english)
16. [Sesiones y seguridad](#16-sesiones-y-seguridad)
17. [Import/Export y Backup](#17-importexport-y-backup)
18. [Mantenimiento y actualizacion](#18-mantenimiento-y-actualizacion)
19. [Interfaz web y API REST](#19-interfaz-web-y-api-rest)
20. [Referencia de comandos CLI](#20-referencia-de-comandos-cli)
21. [Temperatura de modelos LLM](#21-temperatura-de-modelos-llm)
22. [Sandbox de Agentes LAIM](#22-sandbox-de-agentes-laim)
23. [Agente Developer Orquestador](#23-agente-developer-orquestador)
23bis. [Agente Developer y aprobación de desarrollos](#23bis-agente-developer-y-aprobación-de-desarrollos)
24. [Editor Markdown con IA](#24-editor-markdown-con-ia)
25. [Sistema de Notificaciones](#25-sistema-de-notificaciones)
26. [Ventana de contexto y cache](#26-ventana-de-contexto-y-cache)

---

## 1. Instalacion y primer inicio

### 1.1 Requisitos

- **Go >= 1.20** (para compilar desde fuente)
- **Ollama** instalado y en PATH (para IA local)
- **Python >= 3.8** + entorno `.venv_314` (para interfaz web, creado automaticamente por `laim web`)
- Windows 10/11, macOS o Linux

### 1.2 Inicializacion del workspace

Tras instalar LAIM con el instalador, el binario queda en el PATH. En la consola basta el nombre del comando (`laim` o, en Windows, `laim.exe`). LAIM recuerda la ruta de datos de esta instalacion.

Si compilas desde el repositorio de desarrollo, usa `./bin/<plataforma>/laim` (por ejemplo `./bin/silicon/laim`).

```bash
# Windows
laim.exe init

# macOS / Linux
laim init
```

`laim init` realiza las siguientes acciones:
- Detecta hardware (RAM, CPU, GPU, VRAM)
- Configura Ollama (pregunta si deseas IA local y que modelos tienes)
- Tras Ollama, muestra el catalogo de puertos LAIM y pregunta si autoriza abrir/verificar reglas del firewall del SO (ver [11.3.0](#1130-firewall-y-puertos-laim)); puede omitirse con `n` y configurarse despues en Internal › Local
- Genera `laim.md` (especificaciones) e `identity.dat` (identidad cifrada: hostname, SO, serial y clave maestra de instalacion; la clave **no** queda en claro en `laim.md` ni se nombra el campo interno en ese fichero)
- Crea el almacen cifrado `laim.dat`
- Inicializa `library.dat` (base de conocimiento global)
- Inicializa `translate.dat` (recursos de traduccion)
- Inicializa `soul.dat` (conocimiento dinamico del agente Teacher)
- Crea o sincroniza `soulmachine.dat` (inventario cifrado de **este** equipo: `laim info` + `laim.md` sin clave maestra)
- En una instalacion limpia, crea automaticamente el usuario administrador `localadmin` por defecto (con aviso de seguridad para cambiar la contrasena)

> **Nunca** copies `laim.dat` ni `soulmachine.dat` entre equipos. Cada instalacion tiene su propia clave maestra y su propio inventario de hardware.

**Ejemplo (desarrollo).** En un Mac Apple Silicon, compilando el repo: `bash scripts/compile_core.sh` → `./bin/silicon/laim init`. Respondes `s` a Ollama si ya tienes modelos, `n` al firewall si lo configuraras despues en Internal › Local. El usuario `localadmin` existe; cambias la contrasena en `laim config`.

### 1.3 Crear el primer administrador

Tras `init`, ejecuta `laim config` para crear el primer usuario admin. Si no hay usuarios, el acceso es anonimo. El primer usuario siempre recibe el rol `admin`.

### 1.4 Arrancar la interfaz web

```bash
laim.exe web   # Windows
laim web       # macOS / Linux
```

Abre **http://localhost:4321** en el navegador.

> **Direcciones (Web 0.64.33).** Toda dirección que LAIM muestra o abre dice `localhost` (`http://localhost:4321` para la interfaz web, `http://localhost:4320` para la página de arranque, el editor, el diseñador de flujos y las pestañas de terminal). `localhost` es este mismo equipo: los servidores siguen escuchando solo en `127.0.0.1`, y `http://127.0.0.1:4321` sigue funcionando — la página de inicio de sesión lo lleva a `http://localhost:4321` para que la sesión quede bajo un solo nombre. Si tenías la sesión abierta en `127.0.0.1`, inicia sesión una vez más.

`laim web` realiza estas acciones automaticamente:
1. Inicia la API REST en `127.0.0.1:4320`
2. Diagnostica e instala/reinstala `.venv_314` si esta corrupto o es de otro SO
3. Lanza Reflex (interfaz web) en el puerto 4321

**Ejemplo.** Tras `laim web`, el API queda en `127.0.0.1:4320` y Reflex en `:4321`. Si Connect apunta a un Share, el selector de ruta IA del chat muestra Localhost y el nombre del perfil alcanzable.

> **Las pruebas automáticas nunca tocan este LAIM** (Web 0.64.18). Bajo `go test`, cada `laim web` / `laim webdebug` que arranca una prueba lleva `LAIM_TEST_WEB_ISOLATED=1`: no revisa los puertos 4320/4321, no cierra ningún proceso que no haya arrancado (nunca «cerrando procesos residuales de LAIM web»), su API escucha en un puerto libre de `127.0.0.1` y no arranca Share, mesh, Reflex ni el navegador. El LAIM instalado se comporta exactamente como se describe arriba.

### 1.5 Registro de la instalacion en laim.app

Asocie cada copia de LAIM de su equipo a su cuenta del portal ([https://www.laim.app](https://www.laim.app) › **Registro**). Puede registrar varias (casa, oficina, laboratorio). Hay **dos caminos**; elija uno por instalacion. En el portal, el boton **Instrucciones de Registro** abre esta misma guia.

Cada serial solo puede registrarse una vez. La clave maestra de la instalacion **nunca** sale del equipo.

#### Registro manual (desde el portal)

Ideal si acaba de instalar LAIM y tiene delante la pantalla de login.

1. Abra LAIM en ese equipo (`laim web` → http://localhost:4321). En la **ventana de login**, debajo del boton de entrar, aparece el numero de serie, por ejemplo `2-K3MP-9QRA-LW7N-4BXT-M8HJ12C`.
2. Pulse el boton **⎘** (Copiar serial). Queda en el portapapeles; no hace falta transcribirlo a mano.
3. Entre en [https://www.laim.app](https://www.laim.app) con su cuenta (p. ej. usuario `ana`, correo `ana@empresa.com`) y abra **Registro**.
4. Pulse **Registro manual** y pegue el serial. Cuando sea autentico vera **✅ Validado**.
5. Nombre de maquina: el que muestra el equipo, p. ej. `PORTATIL-CASA`. Alias opcional: `Portatil de casa`. Sistema operativo: `windows`, `mac` o `linux`.
6. Pulse **Guardar**. La fila queda **Registrada**.

El serial y el nombre de maquina no se pueden cambiar despues. El alias si.

#### Desde LAIM (propuesta automatica)

Ideal cuando ya ha iniciado sesion en LAIM.

1. En LAIM: **Configuracion › Internal › Local › Registro en laim.app › Registrar**.
2. Escriba el **usuario** y el **e-mail** de **esta** cuenta del portal, los mismos del alta. Ejemplo: usuario `ana`, correo `ana@empresa.com`.
3. Pulse **Enviar propuesta** **una sola vez**.
4. En el portal, pagina **Registro** (o **Actualizar**). Vera la fila **Pendiente de reconocer**.
5. Pulse **✅ Reconocer**. Con eso confirma que esa instalacion es suya.

Si pulsa Enviar propuesta otra vez con el mismo serial, el portal dira que ya esta registrado: no es un fallo, es que la propuesta ya llego. **Rechazar** descarta la propuesta; despues puede volver a registrarla.
En LAIM, **Internal › Local › Registro en laim.app** muestra un emoji: **⚪ No registrada** o **✅ Registrada**, guardado en `identity.dat`. Pulse **Registrar**: si ya esta reconocida en el portal, solo se actualiza el emoji (sin formulario); si el serial no esta, se abre el formulario. Si `identity.dat` ya dice que esta verificada, el boton no hace nada. Tras enviar la propuesta, reconozca en laim.app y pulse Registrar otra vez para verificar.


---

## 2. Navegacion del administrador

Como administrador veras en el sidebar:

| Boton | Descripcion |
|---|---|
| `help` | Ayuda y manuales |
| `version` | Version instalada |
| `info` | Hardware y sistema local |
| `chat` | Chat interactivo con la IA |
| `direct` | Inferencia directa |
| `remote` | Gestion de equipos SSH |
| **`config`** | Asistente de configuracion completo (solo admin) |

### Menu de configuracion (config)

El menu de configuracion tiene 9 secciones principales:

| Opcion | Funcion |
|---|---|
| **1. Gestion de usuarios** | CRUD de usuarios y sesiones |
| **2. Modelos IA** | Tiers de modelos y mapa fases/tier |
| **3. Gestion de agentes** | Agentes, skills, tools, pipelines, patrones |
| **4. Perfiles de flujo** | Perfiles de inferencia personalizados |
| **5. Flujos avanzados** | Pipelines estructurados y editor grafico |
| **6. Share** | Servicio master Share (red local) |
| **7. Connect** | Perfiles Share (la ruta IA se elige en chat / Direct) |
| **8. Gestion de equipos remotos** | Equipos, grupos, accesos, Headscale |
| **9. Internal** | Import/Export, configuracion local, API Info, monitor de sistema, colas, programador, plugins, aprobaciones, revision del alma, **Comandos** |

### Accesos directos administrativos

En **Configuración › Asistente de configuración**, debajo del menú numerado, la sección **Accesos directos** muestra los **5 botones que eligió el administrador** (desde web 0.64.23, pkg81), cada uno con su emoji encima del nombre. Los de por defecto y las alternativas que admite cualquier posición:

| Posición por defecto | Botón | Abre (página existente) |
|---|---|---|
| 1 | 👤 Nuevo usuario | Gestión de usuarios › Crear usuario |
| 2 | 💻 Nuevo equipo | Gestión de equipos remotos › Equipos › Añadir equipo |
| 3 | 🔐 Acceso de usuarios | Gestión de equipos remotos › Acceso de usuarios |
| 4 | 🦙 Modelos Ollama | Modelos IA › Listar modelos Ollama |
| 5 | 🤖 Listar agentes | Gestión de agentes › Listar agentes |
| — | 🖥️ Configuración de instalación | Internal › Local |
| — | 📊 Monitor de sistema | Internal › Monitor de sistema |
| — | 🕐 Programador de tareas | Internal › Programador de tareas |
| — | ⚙️ Gestor de trabajos | Internal › Gestor de colas |

Se eligen en **Internal › Local → Accesos directos** (posiciones 1 a 5, un selector cada una; ver [11.3](#113-local--configuracion-de-instalacion)). Cada página que abre un acceso directo tiene su botón **Volver**, que regresa al Asistente de configuración, para saltar enseguida a otro acceso directo. La elección se guarda con identificadores que no dependen del idioma: en español o en inglés se ven los mismos botones, en el mismo orden, con el nombre traducido.

La sección muestra solo estos accesos directos dinámicos. Los comandos de administración que no están en la barra lateral pasan a **Internal › 11. ⌨️ Comandos** (mismos botones, mismo comportamiento, **Volver** a Interno):

```
[language]  [localmodels]  [catalog]  [eval]  [compare]
[init]      [connect]      [share]    [agents]  [update]
```

**Ruta de navegación activa.** El título de cada página de configuración es su ruta, por ejemplo **Configuración › Asistente de configuración › Interno**, y cada tramo es un enlace: **Configuración** y **Asistente de configuración** abren el asistente, **Interno** abre el menú Interno. El último tramo es la página en la que está (texto sin enlace). Las páginas de Internal con vista propia (Gestor de trabajos, Programador de tareas, Plugins, Aprobación de desarrollos, Revisión del alma) muestran la misma ruta. El clic va por página, no por texto, así que funciona igual en los dos idiomas.

Equivalentes CLI:

```bash
laim localmodels    # Lista modelos Ollama
laim catalog        # Catalogo publico Ollama
laim init           # Re-inicializar workspace
laim connect        # Cliente Connect
laim share          # Master Share
laim agents         # Modo agente
laim update         # Actualizar LAIM
```

---

## 3. Gestion de usuarios y sesiones

Accede desde **config → 1. Gestion de usuarios**.

### 3.1 Crear un usuario

| Campo | Reglas |
|---|---|
| `username` | Solo letras minusculas y numeros (`a-z0-9`), unico |
| `email` | Direccion e-mail valida |
| `password` | Min. 8 caracteres, 1 mayuscula, 1 numero |
| `role` | `admin` o `user` — el primer usuario siempre es admin |

**Ejemplo.** Creas `maria` / `maria@empresa.local` / `Maria2026x` / rol `user`. Maria ve Chat y Direct, no Config. Concedes equipos en **config → Computers**. Un `admin` adicional puede Share/Connect y el panel Tecnico.

### 3.2 Roles y permisos

| Rol | Permisos |
|---|---|
| **admin** | CRUD de usuarios, configuracion completa, accesos directos, Share/Connect |
| **user** | Chat, inferencia directa, equipos concedidos por admin |

### 3.3 Politica de contrasenas

Las contrasenas se almacenan como hash bcrypt dentro de `laim.dat` (cifrado AES-256-GCM). **Nunca** se guardan en texto plano.

### 3.4 Preferencia de idioma por usuario

Cada usuario puede tener un idioma preferido (`en` o `es`) que se guarda en su perfil. La interfaz web lo carga automaticamente en cada inicio de sesion.

### 3.5 Gestion de sesiones

Desde **config → 1 → 2. Gestionar sesiones** puedes ver:
- **Sesiones activas**: quien esta conectado ahora, hora de inicio, canal (web/cli/remote)
- **Sesiones cerradas**: historial de sesiones con `closed_at`
- Opciones: cerrar una sesion remota activa, reanudar una sesion cerrada
- La lista muestra una **referencia de sesión** corta (`sr-` + 16 caracteres hexadecimales), nunca el token de la sesión; cerrar y reanudar usan esa referencia (pkg90).

---

## 4. Modelos de IA — Tiers y fases

Accede desde **config → 2. Modelos IA** o desde el acceso directo `localmodels`.

### 4.1 Nueve tiers de modelos

LAIM organiza los modelos Ollama en nueve slots independientes divididos en dos grupos:

#### Tiers de texto (activos en el flujo de inferencia)

| Tier | Cuando se usa | Recomendacion |
|---|---|---|
| **Traductor** | F1 deteccion de idioma, F7 traduccion al idioma del usuario | Modelo multilingue ligero (ej. `gemma3:4b`) |
| **Rapido** | F2 clasificacion, fast path F5, denegaciones | Modelo pequeno y veloz |
| **Medio** | F3-F5 analisis, F7 formato, F8 sugerencias, agente localsystem | Modelo equilibrado |
| **Lento** | Agente **reprocessing** (maximo refinamiento) | Modelo grande/potente |
| **Alternativo** | Slot reservado para pruebas A/B sin alterar la configuracion activa | Cualquier modelo; vease seccion 4.9 |

#### Tiers especializados (para agentes y flujos avanzados)

| Tier | Uso previsto | Nota |
|---|---|---|
| **Imagenes** | Agentes o flujos que procesen imagen/vision | Modelos con capacidad `vision` (ej. `llava`, `gemma3:4b` con vision) |
| **Video** | Agentes de analisis de video fotograma a fotograma | Experimental — modelos multimodal video cuando esten disponibles en Ollama |
| **Sonido** | Transcripcion voz→texto (Direct y Chat 🎤) y agentes de audio | **Obligatorio** para el mic en Direct/Chat. Modelo con encoder de audio: **`gemma4:e2b` (recomendado; probado con exito en LAIM)** o `gemma4:e4b`. Instalacion: `ollama pull gemma4:e2b` → asignar en Tiers → Sonido. No usar `gemma4:12b` (vision), Orpheus (TTS) ni Whisper community sin mmproj. Sin modelo asignado la API STT responde error (no hay fallback a Medium) |
| **TTS EN** | Texto a voz en ingles (Orpheus) | Default `legraphista/Orpheus:latest`. Direct con login en ingles. Distinto de Sonido (STT). |
| **TTS ES** | Texto a voz en espanol (Orpheus) | Default `sematre/orpheus:ft-it_es-3b`. Direct con login en espanol y University (`lang=es`). Hay que `ollama pull` del modelo. El administrador puede cambiar el tag en este slot. |
| **Desarrollo** | Agentes especializados en generacion y revision de codigo | Modelos `coder` (ej. `qwen2.5-coder:14b`, `deepseek-coder`) |

> **Nota sobre tiers especializados:** se usan en agentes personalizados, flujos avanzados y, para **Sonido**, en la capa STT reutilizable de Inferencia directa (🎤). Si Imagenes/Video/Desarrollo estan vacios, el sistema cae en **Medio** como fallback. **Excepcion Sonido (STT):** `ResolveSpeechModel` no hace fallback a Medium — exige un modelo con encoder de audio. Configuracion validada en pruebas: `ollama pull gemma4:e2b` y asignarlo al tier Sonido. La captura de microfono es **interna al binario** (WASAPI en Windows, AudioQueue en macOS, PipeWire en Linux); no requiere ffmpeg. En macOS se usa AudioQueue (no el convertidor AUHAL de gominiaudio, que en algunos equipos provoca segmentation fault al grabar). El enlace necesita los frameworks AudioToolbox y CoreAudio (el script `compile_core.sh` los pasa). Ver manual de usuario §7.2.

> Los modelos se seleccionan de la lista de `ollama list`. Si no aparecen, ejecuta `ollama pull <nombre>` primero.

**Ejemplo.** Asignas Traductor = `gemma3:4b`, Rapido/Medio/Lento segun VRAM, Sonido = `gemma4:e2b`, TTS EN = `legraphista/Orpheus:latest`, TTS ES = `sematre/orpheus:ft-it_es-3b`. Sin Sonido, el 🎤 de Direct/Chat falla cerrado (no cae a Medio).

### 4.2 Configurar los tiers

Desde **config → 2. Modelos IA → Tiers de modelos**:

- **Tiers de texto (1-5):** Traductor, Rapido, Medio, Lento y Alternativo — usados en el flujo de inferencia de 8 fases.
- **Tiers especializados (6-11):** Imagenes, Video, Sonido, TTS EN, TTS ES y Desarrollo — reservados para agentes, STT y sintesis de voz.
- Selecciona un modelo Ollama de la lista numerada para cada tier.
- El tier Traductor puede quedar vacio si no necesitas traduccion (cae en Medio como fallback).
- Los tiers especializados pueden quedar vacios; si un agente o flujo los usa y no tienen modelo asignado, caen en Medio automaticamente.

> Para pruebas rapidas de un modelo candidato sin alterar la configuracion productiva, usa el **tier Alternativo** (seccion 4.9). Para gestionar conjuntos completos de tiers, usa las **Familias de tiers** (seccion 4.10).

### 4.3 Mapa de fases a tiers

Desde **config → 2 → 2. Mapa fases a tiers** puedes personalizar que tier usa cada fase F1-F8:

| Fase | Tier por defecto | Por que |
|---|---|---|
| F1 deteccion de idioma | Traductor | Modelo multilingue ligero |
| F2 rol | Rapido | Latencia baja |
| F3-F4 contexto y peticion | Medio | Razonamiento y sintesis |
| F5 respuesta | Medio | Calidad de inferencia |
| F5 fast path | Rapido | Consultas simples |
| F6 sintesis localsystem | Medio | Enriquecimiento con datos reales |
| F6 reprocessing | Lento | Refinamiento profundo |
| F7 formato y traduccion | Traductor | Modelo multilingue |
| F8 sugerencias | Medio | Propuestas adicionales |

### 4.3.1 Personalizar prompts de cada fase (`prompts.dat`)

A la derecha de cada selector de tier aparece el boton **Prompts**. Al pulsarlo se abre un modal con los prompts reales que LAIM usa en esa fase, ya rellenos y listos para editar.

#### Que contiene cada fase

Segun la fase, el modal muestra entre 2 y 3 campos de texto:

| Fase | Campos del modal |
|---|---|
| F1 — Idioma | Sistema, Usuario |
| F2 — Rol | Sistema, Usuario |
| F3 — Contexto | Sistema, Usuario, Sin adjunto |
| F4 — Peticion | Sistema, Usuario |
| F5 — Respuesta / Fast path | Sistema base, Tarea |
| F5 — Calidad | Sistema calidad, Usuario calidad |
| F7 — Salida | Sistema, Formato, Premisa |
| F8 — Sugerencias | Sistema, Usuario, Complemento |
| Traduccion | Usuario, Estricto |

#### Como funcionan los cambios

Los prompts que editas en este modal se guardan en **`prompts.dat`** — un fichero cifrado que actua como capa de defaults personalizados de esta instalacion. La resolucion de prompts sigue este orden de prioridad:

```
1. Override de perfil activo (laim.dat → WorkflowProfile.PhasePrompts)
2. prompts.dat — defaults personalizados de la instalacion  ← editas aqui
3. Defaults hardcoded de Go (en inference_workflow.go)
```

Al guardar, los cambios aplican a **todos los perfiles** que no tengan un override especifico. Si un perfil tiene su propio override para esa fase, ese override tiene prioridad sobre `prompts.dat`.

#### Tokens de plantilla disponibles

En los prompts puedes usar estos tokens que LAIM sustituye en tiempo de ejecucion:

| Token | Se sustituye por |
|---|---|
| `{{INPUT}}` | El mensaje del usuario |
| `{{CONTEXT}}` | El bloque de contexto generado |
| `{{RESPONSE}}` | La respuesta actual en ingles |
| `{{LANG}}` | Codigo de idioma del usuario (p.ej. `es`, `en`) |
| `{{PLATFORM}}` | Plataforma de ejecucion (`windows`, `mac`, `linux`) |

#### Ejemplo: afinar el prompt de traduccion (F7)

El prompt de traduccion por defecto es:

```
Translate the text below into {{LANG}}.
CRITICAL formatting rules:
1. Markdown tables: keep EVERY row on its OWN separate line...
Output the translation only:
{{RESPONSE}}
```

Si quieres que el estilo de traduccion sea mas formal en espanol, puedes editar el campo **Usuario** de la fase Traduccion y guardar. A partir de ese momento todas las traducciones de esta instalacion usaran tu prompt personalizado.

#### Restaurar los defaults originales

Para volver al prompt hardcoded de Go, borra el contenido del campo correspondiente y guarda. Con el campo vacio, LAIM usara el prompt original del codigo en la siguiente inferencia.

> **Nota:** `prompts.dat` es un **fichero comun** (como `library.dat` y `translate.dat`). Si el equipo mejora los prompts base y los distribuye junto con una nueva version de LAIM, puedes actualizar tu instalacion ejecutando `scripts/distribute_common_files.sh` (Silicon/mac/Linux) o `.ps1` (Windows). Tus personalizaciones locales se conservan si las guardaste explicitamente.

### 4.4 Override global de modelo

```bash
laim chat llama3.2:3b
```

Cuando inicias chat con un modelo especifico, ese modelo se usa en TODAS las fases ignorando los tiers configurados. Util para pruebas o hardware limitado.

---

### 4.5 Evaluar modelos (`laim eval`)

Antes de asignar un modelo a un tier conviene conocer como rinde en tu hardware especifico. LAIM incorpora un benchmark propio que mide el comportamiento real de cada modelo Ollama con tu CPU/GPU local.

#### Por que evaluar

- Los valores de referencia publicados por el fabricante del modelo se obtienen en hardware de alto rendimiento (GPUs A100, H100) que raramente coincide con tu equipo local.
- La velocidad real depende de factores como RAM disponible, presencia de GPU dedicada, VRAM, numero de capas que caben en VRAM, temperatura del sistema y carga de otros procesos.
- Evaluar con LAIM te da las metricas reales **en tu propia maquina**, lo que hace que la eleccion de tiers sea objetiva y no especulativa.

#### Metricas del benchmark

El benchmark ejecuta **9 prompts** en **3 categorias** (3 por categoria):

| Categoria | Prompts incluidos | Que mide |
|---|---|---|
| **coding** | Fibonacci Python, QuickSort Go, consulta SQL | Capacidad de generacion estructurada y precision tecnica |
| **general_text** | Explicacion IA, diferencias ML, ciudad futurista | Fluencia y coherencia en texto abierto |
| **summarization** | Bateria, Revolucion Industrial, CRISPR | Compresion semántica y brevedad |

Metricas calculadas (promedio sobre los 9 prompts):

| Metrica | Unidad | Interpretacion |
|---|---|---|
| **Velocidad de generacion** | tok/s | Tokens de respuesta por segundo — cuanto mayor, mejor |
| **Velocidad de prompt** | tok/s | Tokens del prompt procesados por segundo — cuanto mayor, mejor |
| **Duracion total** | s | Tiempo total por prompt (incluyendo carga) — cuanto menor, mejor |
| **Carga del modelo** | s | Tiempo de carga inicial en VRAM/RAM — cuanto menor, mejor |
| **Tokens generados** | media | Extension media de respuesta — informativo |

#### Uso CLI

```bash
# Evaluar un modelo especifico
laim eval gemma3:4b

# Sin argumento: muestra lista interactiva de modelos disponibles
laim eval
```

Flujo completo:
1. LAIM comprueba si el modelo ya tiene evaluacion almacenada en `laim.dat`.
2. Si existe, muestra los resultados y pregunta si desea re-evaluar (sobreescribir).
3. Si no existe (o confirma re-evaluacion), ejecuta los 9 prompts mostrando progreso en tiempo real.
4. Guarda los resultados en `laim.dat` y muestra la tabla de resultados.

Ejemplo de salida:

```
⚡  Benchmark — gemma3:4b  (9 prompts)

  · [1/9] coding — fibonacci
  · [2/9] coding — sort_algo
  · [3/9] coding — sql_query
  ...

✓  Evaluacion guardada en laim.dat.

══════════════════════════════════════════════════════════════════
  RESULTADOS — gemma3:4b    (2024-01-15)
══════════════════════════════════════════════════════════════════
  Metrica                               Valor global
  ──────────────────────────────────────────────────────
  Velocidad de generacion               32.45 tok/s
  Velocidad de prompt                   18.72 tok/s
  Duracion total promedio                8.23 s
  Carga del modelo                       2.14 s
  Tokens generados (media)             267
  ──────────────────────────────────────────────────────
  Categoria             Eval (tok/s)  Prompt (tok/s)  Duracion (s)
  ──────────────────────────────────────────────────────
  coding                       30.21           17.50          9.10
  general_text                 35.82           20.14          7.42
  summarization                31.32           18.52          8.17
══════════════════════════════════════════════════════════════════
```

> **Nota:** La evaluacion puede tardar varios minutos dependiendo del tamano del modelo y del hardware disponible. En la interfaz web (Inferencia directa → Evaluar) hay una barra de progreso en tiempo real.

#### Uso web

En el panel **Inferencia directa**, selecciona el modelo con el selector y pulsa **Evaluar**. **Evaluar** y **Comparar** usan Ollama: si el interruptor **LMStudio** esta activo, esos botones quedan deshabilitados.
- Si el modelo ya tiene evaluacion: muestra los resultados almacenados con boton **Re-evaluar**.
- Si no tiene evaluacion: boton **Evaluar ahora** lanza el benchmark con progreso SSE en tiempo real.

---

### 4.6 Comparar modelos (`laim compare`)

Una vez evaluados dos o mas modelos puedes compararlos directamente para tomar decisiones objetivas sobre la asignacion de tiers.

#### Cuando usar comparar

- Tienes varios modelos instalados y quieres elegir cual asignar al tier **Rapido** (prioriza velocidad de generacion y tiempo de carga minimo).
- Quieres elegir el mejor candidato para el tier **Lento** / **reprocessing** (prioriza profundidad: mas tokens generados, mayor calidad en coding/summarization).
- Quieres verificar si un modelo nuevo supera al que tienes asignado actualmente antes de cambiar la configuracion.

#### Uso CLI

```bash
# Comparar dos modelos especificos
laim compare gemma3:4b llama3.1:8b

# Sin argumentos: elige los dos modelos de forma interactiva
laim compare
```

Si uno o ambos modelos no han sido evaluados, LAIM lo indica y sugiere ejecutar `laim eval` primero.

Ejemplo de salida:

```
══════════════════════════════════════════════════════════════════
  COMPARAR MODELOS
══════════════════════════════════════════════════════════════════
  A: gemma3:4b           (2024-01-15)
  B: llama3.1:8b         (2024-01-15)
══════════════════════════════════════════════════════════════════
  Metrica                          Modelo A      Modelo B  Ganador
  ────────────────────────────────────────────────────────────────
  Vel. generacion (tok/s)          32.45        28.10      ✓ A
  Vel. prompt (tok/s)              18.72        22.30      ✓ B
  Duracion total (s) *              8.23         9.80      ✓ A
  Carga del modelo (s) *            2.14         3.40      ✓ A
  Tokens generados (media)        267.00       312.00      ✓ B
  ────────────────────────────────────────────────────────────────
  * menor = mejor  |  ✓ = mejor valor
══════════════════════════════════════════════════════════════════
  Resultado: gemma3:4b lidera en 3/5 metricas.
  Candidato para tiers de velocidad: Rapido / Medio.
  Tip: Complemente con capacidades del modelo (razonamiento, vision, voz, tools)
       antes de asignar los tiers en:  laim config > Modelos IA > Tiers
══════════════════════════════════════════════════════════════════
```

#### Uso web

En el panel **Inferencia directa**, pulsa **Comparar modelos**:
- Dos selectores de modelo (A y B) con mini-resumen de cada evaluación.
- Barras horizontales por métrica con indicador KPI (✓ verde = ganador, ✗ rojo = perdedor).
- Si un modelo aún no está evaluado, LAIM pregunta si evaluarlo ahora. Al aceptar se abre **Evaluar**; al terminar, vuelve a **Comparar** con las métricas (si el otro modelo también falta, pregunta de nuevo). Puedes declinar y pulsar **Evaluar ahora** en la tarjeta más tarde.

---

### 4.7 Estrategia de asignacion de tiers basada en evaluaciones

#### Paso a paso recomendado

1. **Evalua todos tus modelos** con `laim eval` o desde el panel web.
2. **Compara los candidatos** para cada tier con `laim compare`.
3. **Consulta las capacidades del modelo** (ver tabla siguiente) para complementar las metricas.
4. **Asigna los tiers** en `laim config → 2. Modelos IA → 1. Configurar tiers`.

#### Guia de asignacion por tier

| Tier | Metrica clave | Capacidades adicionales recomendadas |
|---|---|---|
| **Rapido** | Mayor velocidad de generacion y menor duracion total | No necesita razonamiento profundo; solo texto fluido y rapido |
| **Medio** | Equilibrio velocidad/calidad; buena velocidad de generacion | Util si tiene capacidad de seguir instrucciones complejas |
| **Lento / reprocessing** | Mas tokens generados (respuestas largas y detalladas) | Modelos con razonamiento (`thinking`), mayor numero de parametros |
| **Traductor** | Velocidad de generacion aceptable; duracion baja | Modelo multilingue (entrena en muchos idiomas); no necesita razonamiento |

#### Capacidades del modelo a verificar antes de asignar

Las metricas de benchmark miden rendimiento, no capacidades. Antes de asignar un tier, consulta la ficha del modelo en [https://ollama.com/search](https://ollama.com/search) o en [https://huggingface.co](https://huggingface.co) para verificar:

| Capacidad | Descripcion | Tier beneficiado |
|---|---|---|
| **Razonamiento** (`thinking`, `reasoning`) | El modelo genera un bloque de razonamiento interno antes de responder. Mejora mucho la calidad en tareas complejas. | Lento / reprocessing |
| **Vision** (`multimodal`, `vision`) | Puede analizar imagenes adjuntas al prompt. Util si los usuarios comparten capturas de pantalla o diagramas. | Medio / Rapido |
| **Voz** (`speech`, `audio`) | Soporte de entrada o salida de audio. | Segun el caso de uso |
| **Tools / Function calling** | El modelo puede invocar funciones externas (APIs, busquedas). Mejora agentes F6. | Medio / Lento |
| **Contexto largo** (`128k`, `1M context`) | Puede procesar documentos muy largos sin perder coherencia. | Medio / Lento |
| **Multilingue** | Soporta muchos idiomas de forma nativa sin perder fluidez. Critico para el tier Traductor. | Traductor |
| **Codigo** (`code`, `coder`) | Especializado en generacion y analisis de codigo. | Medio / Lento |
| **Instrucciones seguidas** (`instruct`) | Optimizado para seguir instrucciones del sistema. Todos los tiers. | Todos |

> **Recomendacion:** no asignes un modelo con razonamiento (`thinking`) al tier Rapido aunque tenga buena velocidad de generacion — el bloque de razonamiento interno aumenta mucho la latencia percibida por el usuario y no tiene sentido para tareas simples de clasificacion o deteccion de idioma.

#### Ejemplo practico de decision

Supongamos que tienes tres modelos evaluados:

| Modelo | Vel. gen. (tok/s) | Duracion (s) | Capacidades |
|---|---|---|---|
| `gemma3:4b` | 32.4 | 8.2 | texto, codigo, multilingue |
| `llama3.1:8b` | 28.1 | 9.8 | texto, codigo, tools, 128k ctx |
| `qwen3:14b` | 18.3 | 15.4 | razonamiento, tools, multilingue, vision |

Asignacion optima:

| Tier | Modelo elegido | Razon |
|---|---|---|
| **Traductor** | `gemma3:4b` | Mas rapido, multilingue, duracion baja |
| **Rapido** | `gemma3:4b` | Mayor velocidad de generacion sin razonamiento |
| **Medio** | `llama3.1:8b` | Equilibrio; tools y contexto largo para analisis F5 |
| **Lento** | `qwen3:14b` | Razonamiento profundo para reprocessing; tools para F6 |

---

### 4.8 Panel Herramientas — Analisis de modelos en la web

Accede desde **config → 2. Modelos IA → Tiers de modelos → botón 🔧 Herramientas**.

Se abre un **modal** sobre la pantalla de tiers (la columna de temperatura y familias sigue visible detrás). El modal ofrece análisis independientes, comparativa de evaluaciones y un visor de guía de optimización. Está diseñado para que el administrador tome decisiones informadas antes de asignar un modelo a un tier.

```
[Selector de modelo]   ← mismo catálogo que los selectores de tier

[🔍 Capacidades]  [📊 Analizar]  [⚡ Memoria]
[🧪 Verificación]  [🆚 Comparar]
```

---

#### 4.8.1 Capacidades del modelo (`🔍 Capacidades`)

**¿Que hace?** Consulta la API de Ollama (`/api/show`) para el modelo seleccionado y muestra su ficha tecnica.

**Datos que devuelve:**

| Campo | Descripcion |
|---|---|
| **Capacidades** | Lista de etiquetas: `thinking`, `tools`, `vision`, `embedding`, `completion`, etc. |
| **Familia** | Arquitectura del modelo (llama, gemma, qwen, phi, mistral...) |
| **Tamano de parametros** | Numero de parametros del modelo (ej. 8B, 14B, 70B) |
| **Cuantizacion** | Nivel de compresion del modelo (Q4_K_M, Q6_K, Q8_0, FP16...) |

**Como usarlo:**
1. Selecciona un modelo en el selector del panel.
2. Pulsa **🔍 Capacidades**.
3. Comprueba las etiquetas antes de asignarlo a un tier:
   - `thinking` → solo para tier Lento (aumenta latencia)
   - `tools` → recomendado para tiers Medio y Lento (agente F6)
   - `vision` → util si los usuarios trabajan con imagenes
   - `embedding` → no apto para chat; no asignar a ningun tier de inferencia

> **Consejo:** combina esta informacion con las metricas de `laim eval` para una decision completa. Las capacidades dicen **que puede hacer** el modelo; la evaluacion dice **como rinde** en tu hardware.

---

#### 4.8.2 Memoria Ollama (`⚡ Memoria`)

**¿Que hace?** Consulta la API de Ollama (`/api/ps`) para ver que modelos estan **cargados en RAM/VRAM en este preciso momento**.

**Cuando usarlo:**
- Para comprobar si un modelo esta retenido en memoria (efecto de `OLLAMA_KEEP_ALIVE=-1`).
- Para diagnosticar consumo de VRAM cuando tienes varios modelos asignados a distintos tiers y los usas en la misma sesion de chat.
- Para verificar que el modelo correcto se esta usando antes de iniciar un chat importante.

**Datos que muestra:**

| Columna | Descripcion |
|---|---|
| Modelo | Nombre completo del modelo cargado |
| RAM | Memoria del sistema ocupada por este modelo |
| VRAM | Memoria de GPU ocupada (0 si corre en CPU) |
| Ctx | Tamano de contexto con el que se cargo el modelo |

**Estado del boton:**
- Sin pulsarlo: aparece el mensaje *"Pulsa ⚡ Memoria para ver los modelos cargados en Ollama ahora mismo."* — indica que la consulta no se ha realizado todavia.
- Durante la consulta: el boton cambia a `⚡ …` y se deshabilita para evitar dobles llamadas.
- Resultado: tabla de modelos activos o aviso *"Ningun modelo cargado en este momento"*.
- El icono **↺** junto al titulo refresca la lista sin necesidad de volver al boton principal.

> **Nota:** si VRAM es 0 para un modelo grande, Ollama lo esta ejecutando en CPU, lo que implica latencia muy alta. En ese caso consulta la seccion 4.9 o el visor de Recomendaciones para estrategias de optimizacion.

---

#### 4.8.3 Recomendacion de tier (`📊 Analizar`)

**¿Que hace?** Combina la ficha tecnica del modelo (`/api/show`) con su evaluacion de rendimiento (si existe en `laim.dat`) para calcular una **puntuacion de idoneidad (0-100)** por cada tier.

**Como interpretar la puntuacion:**

| Puntuacion | Interpretacion |
|---|---|
| 80-100 | Excelente candidato para ese tier |
| 60-79 | Buen candidato, considera tambien otros modelos |
| 40-59 | Candidato aceptable con limitaciones |
| < 40 | No recomendado para ese tier |

**Criterios de scoring por tier:**

| Tier | Factores principales |
|---|---|
| **Traductor** | Velocidad de generacion alta, duracion baja, sin `thinking` |
| **Rapido** | Velocidad de generacion alta, sin `thinking`, tamano < 10B preferido |
| **Medio** | Equilibrio velocidad/calidad; penalizacion si tiene `thinking` |
| **Lento** | Tokens generados altos, calidad de coding/summarization; `thinking` suma puntos |

**Comparacion con los modelos actuales:**
Ademas de la puntuacion absoluta, el panel indica si el modelo analizado es **mejor o peor** que el modelo actualmente asignado a cada tier (requiere que el modelo actual tambien haya sido evaluado).

**Como usarlo:**
1. Selecciona el modelo que quieres valorar.
2. Pulsa **📊 Analizar**.
3. Revisa la puntuacion por tier y el indicador comparativo.
4. Complementa con **🔍 Capacidades** para verificar etiquetas funcionales.
5. Si la puntuacion es alta pero el modelo no ha sido evaluado aun, ejecuta primero `laim eval <modelo>` o pulsa **Evaluar** en Inferencia directa.

> **Importante:** el scoring es orientativo. Un modelo con `thinking` puede obtener puntuacion baja en tier Rapido pero ser la mejor opcion para tier Lento aunque tenga menor velocidad de generacion bruta. Usa el analisis como punto de partida, no como decision automatica.

---

#### 4.8.4 Recomendaciones — Guia de optimizacion Ollama (`📚 Recomendaciones`)

**¿Que hace?** Abre un visor de documento (modal de solo lectura) con la guia completa de optimizacion de Ollama: diagnostico de cuellos de botella, trucos de configuracion y estrategias de hardware.

**Como acceder:** boton **📚 Recomendaciones** a la derecha de **🔧 Herramientas** en la pantalla de Tiers de modelos.

**Contenido del documento:**

| Seccion | Que encontraras |
|---|---|
| Diagnostico rapido | 4 sintomas comunes y su causa (carga lenta, CPU en lugar de GPU, throttling termico...) |
| Trucos inmediatos (5 min) | `OLLAMA_KEEP_ALIVE=-1`, cuantizacion optima por VRAM, Flash Attention |
| Optimizaciones GPU | `num_gpu`, `num_ctx`, forzar uso de GPU |
| Optimizaciones de sistema | mmap, NVMe, temperatura GPU, batch size para APIs |
| Comparativa antes/después | Caso real con RTX 4060 Ti 16GB — 9X de mejora en primera respuesta |
| Checklist completo | Lista por nivel (basico / intermedio / avanzado) |
| Cuando el hardware es el limite | Tabla de upgrades con precio y ganancia estimada |
| FAQ | Tokens por segundo esperados por GPU, calidad de cuantizacion, multi-GPU... |

**Idioma:** banderas flotantes 🇬🇧/🇪🇸 (igual que Informes y Ayuda). Ambos cuerpos viven en `library.dat` (seeds `ollama-recommendations-es` / `-en`, comunes a todas las instalaciones). No hay traducción LLM: el Core sirve el HTML del idioma pedido.

**Tema gráfico:** el visor usa tokens del tema activo (CRT, Soft UI, cuero, metal). Cajas de código (`nvidia-smi`) y barras de aviso heredan `--crt-code-*` / `--crt-accent`; no hay verde CRT embebido en el HTML.

**Relacion con las otras herramientas:**

- Si **⚡ Memoria** muestra VRAM=0 → el modelo corre en CPU → consulta la seccion *"Forzar uso de GPU"* de este documento.
- Si el scoring de **📊 Analizar** es bajo aunque el modelo sea potente → puede ser un problema de cuantizacion o contexto excesivo → consulta la seccion *"Cuantizacion adecuada para tu VRAM"*.
- Si `laim eval` da velocidades muy bajas → consulta *"Diagnostico rapido"* y el checklist de optimizacion.

> **El visor es de solo lectura.** Para cerrar, pulsa el boton **Cerrar** o la X de la cabecera.

#### 4.8.4b Asesor de modelos (`🧭 Asesor`)

**¿Que hace?** Puntua un catalogo curado contra el hardware de **esta** instalacion (`laim info` / runtime de inferencia). Bandas tipo llmfit: Perfect / Good / Marginal / Too Tight. Ollama en todos los SO; MLX solo en Apple Silicon. No scrapea Hugging Face.

**Como acceder:** boton **🧭 Asesor** junto a **📚 Recomendaciones** en Tiers de modelos.

**Filtros:** chips de caso (general / chat / coding / reasoning) y, debajo, un boton por cada slot de Tiers de modelos: texto (Traductor, Rapido, Medio, Lento, Alternativo) y especializados (Imagenes, Video, Sonido, TTS EN, TTS ES, Desarrollo). Cada chip muestra recomendados y soportados para ese slot (el nucleo Go filtra y puntua). El desplegable Asignar usa el mismo slot si pulsa un chip de tier.

**Recomendados vs soportados:** *Soportados* son modelos que caben en el hardware de esta instalacion. *Recomendados* ademas encajan en el **uso del tier** (Traductor = texto pequeno y rapido, sin thinking; Sonido = audio/STT; Desarrollo = coder; Imagenes = vision; Lento = razonamiento / thinking). Si el administrador ya evaluo un modelo (`laim eval` o Evaluar en Inferencia directa), el Asesor reutiliza esas categorias en `laim.dat` (coding, general_text, summarization) para afinar la lista. Un 4B que cabe en VRAM puede ser recomendado en Traductor/Rapido y solo soportado en Lento.

**Descargar:** el boton Instalar encola `model_download` en la cola de **red**. Puede cambiar de pagina: un chip **Descargando** reabre el progreso. Too Tight exige confirmar (HITL). Si la descarga falla o queda incompleta, llega una notificacion `download_failed`; responda «reanudar» o «reintentar». **No** se ejecuta `ollama rm` de blobs parciales (Ollama reanuda capas).

---

#### 4.8.5 Flujo de trabajo recomendado con el panel Herramientas

El orden optimo para decidir la asignacion de un modelo nuevo a un tier:

```
1. [🔍 Capacidades]
   └─ ¿tiene 'thinking'?  → NO asignar a Rapido ni Traductor
   └─ ¿tiene 'tools'?     → recomendado para Medio/Lento
   └─ ¿tiene 'embedding'? → descartar para cualquier tier de chat

2. [⚡ Memoria]
   └─ ¿VRAM = 0?          → corre en CPU → revisar Recomendaciones (sección GPU)
   └─ ¿ocupa demasiada VRAM? → puede desplazar otros modelos → ajustar cuantizacion

3. **Comparar** (si no hay evaluación previa, LAIM pregunta si evaluarlo ahora)
   └─ mismo flujo que Inferencia directa → Comparar
   └─ o `laim eval <modelo>` / Evaluar en Direct

4. [📊 Analizar]
   └─ revisar puntuacion por tier
   └─ comparar con el modelo actual de ese tier

5. [📚 Recomendaciones]
   └─ consultar solo si aparecen problemas de rendimiento en los pasos anteriores

6. Asignar tier en config → 2. Modelos IA → Tiers de modelos → Guardar tiers
```

---

### 4.9 Tier Alternativo — Pruebas temporales de modelos

El tier **Alternativo** es un slot de sustitucion rapida disenado para que el administrador pueda probar un modelo diferente en cualquier fase o agente sin tocar la configuracion productiva.

#### Para que sirve

Cuando aparece un modelo nuevo interesante (ej. `qwen3:8b` acaba de publicarse o `deepseek-r1:7b` promete mejor razonamiento), el flujo habitual seria:
1. Descargar el modelo con `ollama pull`.
2. Evaluar con `laim eval`.
3. Asignarlo al tier correspondiente, **sobreescribiendo el modelo que ya funciona bien**.
4. Probar en chat durante unos dias.
5. Si no convence, volver a asignar el modelo anterior.

Este proceso es correcto pero arriesgado: mientras pruebas, el tier queda ocupado por el candidato y la calidad del sistema puede verse afectada.

El tier **Alternativo** resuelve esto:

```
Tier Medio    = llama3.1:8b       ← produccion, sin tocar
Tier Alternativo = qwen3:8b       ← candidato a prueba
```

Luego, en el mapa de fases, asignas temporalmente una fase (por ejemplo F5 o F6) al tier Alternativo para comparar resultados. Cuando termines la evaluacion:
- Si convence → reasigna ese tier definitivamente al modelo nuevo.
- Si no convence → borra el Alternativo o asigna otro candidato.

El tier **Medio** nunca cambio durante toda la prueba.

#### Cuando usar el Alternativo

| Situacion | Accion recomendada |
|---|---|
| Sale un modelo nuevo que quieres probar en produccion ligera | Asignarlo a Alternativo, redirigir una fase menos critica (ej. F8 sugerencias) |
| Quieres comparar razonamiento: modelo A vs B en la misma fase | Asigna A a Medio, B a Alternativo; cambia el mapa de F6 entre sesiones de chat |
| Evaluacion de un modelo en hardware real sin interrumpir el servicio | Asignar a Alternativo; los chats en curso siguen usando los tiers de texto normales |
| Tests A/B entre sesiones de usuarios | Asignar Alternativo y cambiar el mapa de fases segun el usuario (via Override global) |

#### Como configurarlo

Desde CLI:
```bash
laim config
# Opcion: 2. Modelos IA
# Opcion: 5. Alternativo
# Selecciona el modelo candidato de la lista
```

Desde la web: **config → 2. Modelos IA → Tiers de modelos → Alternativo → selector de modelo → Guardar tiers**.

Para redirigir una fase al Alternativo: **config → 2. Modelos IA → Mapa fases → seleccionar la fase → opcion 4. Alternativo**.

> **Fallback:** si el tier Alternativo esta vacio y una fase lo tiene asignado, el sistema cae automaticamente en **Medio**, por lo que nunca se queda sin modelo.

---

### 4.10 Familias de tiers — Estrategia blue/green en LAIM

#### Concepto: blue/green deployment adaptado a la IA local

La estrategia **blue/green** es un patron de despliegue continuo (popularizado por Jez Humble y David Farley, y utilizado ampliamente en la industria — por ejemplo por IBM y Netflix) en el que se mantienen **dos entornos de produccion identicos**, uno activo ("blue") y otro en espera o preparacion ("green"). Cuando el nuevo entorno esta listo y validado, el trafico se redirige instantaneamente al entorno verde sin tiempo de inactividad. Si algo falla, la vuelta atras es inmediata.

LAIM adopta conceptualmente esta estrategia aplicandola a la **configuracion de modelos de IA**, no a la infraestructura. En lugar de servidores o contenedores, lo que se intercambia son **asignaciones tier → modelo**:

```
Familia blue  (activa):     Familia green (en espera):
  Traductor = gemma3:4b       Traductor = gemma3:4b
  Rapido    = gemma3:4b       Rapido    = phi4:14b       ← candidato
  Medio     = llama3.1:8b     Medio     = qwen3:14b      ← candidato
  Lento     = qwen3:14b       Lento     = deepseek-r1    ← candidato
  ...                         ...
```

Con un solo clic o comando el administrador **activa la familia green**, y todos los chats nuevos empiezan a usar los modelos candidatos. Si algo no funciona bien, **activa de nuevo la familia blue** y en menos de un segundo la instalacion vuelve al estado conocido y estable.

#### Como funciona en LAIM

Cada familia es un contenedor nombrado que almacena una asignacion completa de los 9 tiers. Al activar una familia:

1. Sus asignaciones se copian al campo `store.ModelTiers` que usa todo el codigo de inferencia.
2. Los chats que empiecen a partir de ese momento usan los nuevos modelos.
3. Los chats ya en curso **no se interrumpen** (siguen con el modelo que cargaron al inicio de la sesion).

```
[Familia blue] → activa → store.ModelTiers → todos los tiers resueltos aqui
[Familia green] → en espera → no afecta a la inferencia hasta que se active
```

#### Por que dos familias y no simplemente cambiar los tiers

| Con familias blue/green | Sin familias (cambio directo de tiers) |
|---|---|
| Puedes preparar la nueva configuracion completa sin afectar al sistema | Cada cambio de tier es inmediato y afecta a los usuarios activos |
| La vuelta atras es instantanea (un clic/comando) | Para deshacer hay que recordar y reintroducir cada modelo uno a uno |
| Puedes documentar cada familia con un nombre significativo | La configuracion activa es un estado opaco |
| Puedes mantener la familia de referencia congelada indefinidamente | No hay "punto de restauracion" claro |
| Facilita pruebas sistematicas comparando sesiones en blue vs green | Las comparaciones requieren notas manuales |

#### Beneficios para el administrador de LAIM

**Sin tiempo de inactividad:** al activar una familia, el cambio es instantaneo. No hay que reiniciar servicios, recargar Ollama ni interrumpir el servidor web.

**Vuelta atras inmediata:** si los modelos de la familia green dan peores resultados o son mas lentos de lo esperado, basta con activar de nuevo la familia blue. El tiempo de recuperacion es de menos de un segundo.

**Pruebas A/B controladas:** puedes ejecutar la familia blue durante la manana (horas punta, usuarios demandantes) y cambiar a green por la tarde (pruebas, feedback limitado). Compara la calidad de las respuestas, la latencia y el consumo de VRAM de forma sistematica.

**Adaptacion a modelos nuevos:** el ecosistema de modelos Ollama evoluciona rapidamente. Cada semana aparecen nuevas versiones de Llama, Qwen, Gemma, Phi, DeepSeek... Con familias, el administrador puede:
- Tener la instalacion en produccion estable (blue).
- Ir actualizando la familia experimental (green) con modelos nuevos a medida que salen.
- Activar green cuando haya validado que los nuevos modelos son mejores.
- Nunca interrumpir el servicio durante la evaluacion.

**Entornos diferenciados por infraestructura:** si la instalacion LAIM corre en diferentes momentos en hardware distinto (por ejemplo una maquina con GPU los dias laborables y una maquina sin GPU los fines de semana), puedes tener:
- Familia `blue` = configuracion para GPU (modelos grandes: `qwen3:14b`, `llama3.1:70b`).
- Familia `green` = configuracion para CPU (modelos ligeros: `gemma3:4b`, `phi4-mini`).
- Cambiar la familia activa al cambiar de hardware en lugar de reconfigurar tier a tier.

#### Limitaciones y diferencias respecto a blue/green clasico

| Aspecto | Blue/green clasico (infraestructura) | Familias de tiers en LAIM |
|---|---|---|
| Que se intercambia | Servidores, contenedores, entornos de ejecucion | Asignaciones tier → modelo (configuracion) |
| Tiempo de cambio | Milisegundos (redireccion de trafico) | Inmediato (actualizacion en memoria) |
| Sesiones en curso | Pueden verse afectadas segun el balanceador | No se interrumpen (terminan con el modelo original) |
| Necesita dos entornos identicos | Si (doble infraestructura) | No (los modelos ya estan en Ollama local) |
| Costo adicional | Doble infraestructura durante la transicion | Solo el espacio en disco de los modelos Ollama |
| Replicacion de bases de datos | Reto tecnico importante | No aplica (laim.dat es local por instalacion) |
| Vuelta atras total | Instantanea | Instantanea |

La principal diferencia con el blue/green clasico es que **no necesitas duplicar infraestructura**. Los modelos Ollama ya estan descargados en la maquina. El cambio de familia es simplemente un cambio de puntero en la configuracion. El "costo" de tener dos familias es solo el espacio en disco de los modelos adicionales que quieras incluir en la familia experimental.

#### Casos de uso practicos

**Caso 1: Actualizacion controlada de modelos**

```
Estado inicial:
  blue (activa): Rapido=gemma3:4b, Medio=llama3.1:8b, Lento=qwen3:14b

Llega qwen3.5:9b, se anuncia como superior a llama3.1:8b en benchmark publico.

Accion:
  1. ollama pull qwen3.5:9b
  2. laim eval qwen3.5:9b  ← verificar que el benchmark publico se cumple en tu hardware
  3. Editar familia green: Medio=qwen3.5:9b (resto igual que blue)
  4. Activar green durante periodo de prueba (2-3 dias)
  5. Evaluar calidad subjetiva de las respuestas
  6. Si es mejor: renombrar green a blue (o copiar sus valores) y archivar la antigua
  7. Si no convence: activar blue de nuevo en 1 clic
```

**Caso 2: Configuracion por turnos horarios**

```
blue: modelos grandes para GPU (horario laboral, maquina con RTX 4060)
  Medio=llama3.1:8b, Lento=qwen3:14b

green: modelos ligeros para CPU (mantenimiento nocturno o maquina sin GPU)
  Medio=gemma3:4b, Lento=llama3.2:3b

Automatizacion posible: script que active blue a las 08:00 y green a las 20:00
via la API REST: PUT /api/v1/config/tier-families/active
```

**Caso 3: Equipos con diferentes perfiles de uso**

```
blue: configuracion para usuarios tecnicos (modelos con tools y razonamiento)
  Medio=qwen3:14b (con tools), Lento=deepseek-r1:7b (con thinking)

green: configuracion para usuarios no tecnicos (modelos mas conversacionales)
  Medio=llama3.1:8b, Lento=qwen3:8b
```

#### Operaciones disponibles

**Desde CLI** (`laim config → 2. Modelos IA → 11. Familias de tiers`):

| Operacion | Descripcion |
|---|---|
| Ver familias disponibles | Lista las familias con indicador de cual esta activa |
| Activar una familia | Copia sus tiers en produccion al instante |
| Crear nueva familia | Parte de cero o duplica una existente |
| Editar tiers de una familia | Modifica los modelos asignados sin activarla |
| Eliminar una familia | Solo si no esta activa |

**Desde la web** (`config → 2. Modelos IA → Tiers de modelos → seccion Familias de tiers`):

- Lista de familias con badge verde para la activa.
- Boton **Activar** en cada familia no activa.
- Boton **✕** para eliminar familias no activas.
- Campo de texto + boton **+ Crear** para nueva familia.

**Via API REST** (para automatizacion y scripts):

```bash
# Ver familias y cual esta activa
GET /api/v1/config/tier-families

# Activar familia green
PUT /api/v1/config/tier-families/active
Body: {"name": "green"}

# Crear nueva familia copiando los tiers actuales
POST /api/v1/config/tier-families
Body: {"name": "production_2025", "tiers": {...}}

# Actualizar los tiers de una familia sin activarla
PUT /api/v1/config/tier-families/green
Body: {"medium": "qwen3.5:9b", "slow": "deepseek-r1:7b"}

# Eliminar una familia (error si esta activa)
DELETE /api/v1/config/tier-families/experimental
```

#### Convencion de nombres recomendada

| Convencion | Ejemplo | Cuando usarla |
|---|---|---|
| Colores (blue/green) | `blue`, `green` | Instalaciones simples con dos configuraciones alternantes |
| Fecha | `config_2025_07`, `config_2025_Q4` | Versionado temporal de configuraciones |
| Hardware | `gpu_4060`, `cpu_only` | Instalaciones que alternan hardware |
| Proposito | `production`, `experimental`, `testing` | Separacion por madurez de la configuracion |
| Usuarios | `power_users`, `casual_users` | Perfiles de usuario diferenciados |

> **Punto de partida:** LAIM crea automaticamente las familias `blue` y `green` al primera carga si no existen, copiando la configuracion actual de tiers en ambas. Ambas parten del mismo punto y `blue` queda activa. Desde ahi el administrador puede editar `green` para preparar la configuracion experimental.

### 4.11 Cache de ficha Direct

La primera vez que Direct presenta un modelo para una combinacion **motor + modelo + idioma**, LAIM infiere la ficha y la guarda en `laim.dat` → `Direct.ModelPresentations`. Las siguientes veces reutiliza esa copia desde el pool **network**: sin slot GPU, sin generacion Ollama/MLX, sin PresenterAgent. Una **nueva conversacion** o un cambio de selector vuelve a presentar la ficha (desde cache o en vivo).

| Regla | Detalle |
|---|---|
| Clave de cache | motor + modelo + idioma |
| Timeout de stream | **20 minutos** (`OllamaStreamHTTPTimeout`) en streams Direct/chat en vivo |
| Fichas parciales | **No** se cachean: un intro incompleto se muestra una vez y no se guarda |
| Fichas MLX | El cue incluye PANEL FACTS medidos en Go (`mlx_lm.server` `:4325`, carpeta safetensors, `LocalSettings.MLX`); el last-mile quita `ollama list` / `:11434` |
| Ruta IA Share | La presentacion usa solo PresenterPost (sin Ollama local) |

Al cambiar el cue en codigo, subir `DirectModelPresentationFormatVersion` para regenerar fichas antiguas.

**Ejemplo.** Un usuario abre Direct con `qwen3.5:9b` en espanol: el primer turno infiere y cachea la ficha. La siguiente conversacion con el mismo motor+modelo+idioma pinta desde cache (pool network). Una ficha a medias tras un timeout se muestra una vez y se descarta.

---

## 5. Gestion de agentes, skills, tools y pipelines

Accede desde **config → 3. Gestion de agentes**.

### 5.1 Agentes integrados (builtin)

| Agente | Funcion | Tier |
|---|---|---|
| **localsystem** | Ejecuta y repara comandos en el equipo local (F6) | Medio |
| **reprocessing** | Mejora el analisis con el tier lento tras F6 | Lento |
| **teacher** | Aprende del feedback del usuario, gestiona soul.dat | Configurable |
| **devops** | Orquestador DevOps: evaluar infra, planificar CI/CD con aprobacion y rollback, diagnosticar, seguridad operativa y runbooks de recuperacion. API admin `/api/v1/devops/*` o frases tipo «agente devops» / «runbook» / «desplegar con rollback» en el chat (heuristica). Memoria de contexto de sesion + tips en soul.dat. | Desarrollo (fallback medio/lento) |
| **secops** | Orquestador Ingeniero de Seguridad / SecOps: `assess`/`audit` ejecutan probes de solo lectura en local o computer (SSH), analizan con tier medio y recomiendan por hallazgo; `scan_plan` solo planifica; `remediate` con HITL; informes `reports/secops_*` (grupo **Secops**). API `/api/v1/secops/*`; panel Config › Tecnico › SecOps. Heuristica `secops_request`. Distinto de SecureAgent e InferenceSecurity. | Medio |
| **compare** | Orquestador de comparacion: matriz de capacidades, pros/contras y recomendacion (frameworks ↔ patrones LAIM). Perfil Agent Box `read_only`. API `/api/v1/compare/*`; panel Config › Tecnico › Compare. Heuristica `compare_request`. Informes opcionales `reports/compare_*`. | Medio |
| **pipeline** | Orquestador de optimizacion de secuencias/Flows/`AgentPipelineConfig`: etapas, ola paralela, staleness, validacion mecanica (metodologia stay-learning). Perfil Agent Box `read_only`. API `/api/v1/pipeline/*`; panel Config › Tecnico › Pipeline. Heuristica `pipeline_request` (no CI/CD). Informes opcionales `reports/pipeline_*`. Distinto de `RunPipeline` y DevOps. | Medio |
| **planner** | Especialista en diseño, activacion, seguimiento y verificacion de planes (Jeomon + ECC + AgentScope). Perfil Agent Box `read_only`. API `/api/v1/planner/*`; panel Config › Tecnico › Planner. Heuristica `planner_request`. Handoff a Router via `ToRouterPlan`. Informes opcionales `reports/planner_*`. Distinto de Router (ejecuta), Pipeline y Pattern Composer. | Medio |
| **evaluator** | Evaluacion de resultados, procesos y trayectorias (llm-evaluation + ECC). Perfil Agent Box `read_only`. API `/api/v1/evaluator/*`; panel Config › Tecnico › Evaluator. Heuristica `evaluator_request`. `learn`→soul.dat con HITL. Handoff a Optimizator via `ToOptimizatorHandoff`. Informes opcionales `reports/evaluator_*`. Pareja de Optimizator. | Medio |
| **swarm** | Fan-out multi-agente analitico (plan/run/synthesize) con roles analyst/critic/security_lens/synthesizer; handoffs a Evaluator/Optimizator. Perfil Agent Box `read_only`. API `/api/v1/swarm/*`; panel Config › Tecnico › Swarm. Heuristica `swarm_request` (chat solo plan/status). Distinto de Router, Diagnose y Pipeline. | Medio |
| **optimizator** | Optimizacion de resultados, procesos y contexto (agents-md-optimizer + GEO + ECC). Perfil Agent Box `read_only`. API `/api/v1/optimizator/*`; panel Config › Tecnico › Optimizator. Heuristica `optimizator_request`. `apply`→soul.dat con HITL. Acepta `eval_handoff` del Evaluator. Informes opcionales `reports/optimizator_*`. Pareja de Evaluator. | Medio |
| **audit** | Accountability y uso de recursos (awesome-auditable-ai). Perfil Agent Box `localsystem_host`. API `/api/v1/audit-agent/*` (no confundir con `GET /api/v1/audit`). Panel Config › Tecnico › Audit. Heuristica `audit_request`. Acciones trail/attribute/resources/suggest_brief. Distinto de SecOps y del panel Internal › Auditoria. Informes opcionales `reports/audit_*`. | Medio |
| **calibrate** | Firma vocal y gate STT (ARTPARK Calibrate / Audio LLM Judge). Perfil Agent Box `localsystem_host`. Almacen `voice.dat` cifrado; enrollment 20s; verify MATCH/MISMATCH con tier Sound antes de transcribir. API `/api/v1/calibrate/*` + `/speech/enroll/*`. Panel Config › Tecnico › Calibrate. Heuristica `calibrate_request`. Distinto de Evaluator y del STT plano. Informes opcionales `reports/calibrate_*`. | Sound (juez) |
| **images** | Vision y OCR con el tier Imagenes (Ollama multimodal). Perfil Agent Box `read_only`. PNG/JPEG/GIF/WebP/BMP via `images[]`; no Tesseract. API `/api/v1/images/*`. Panel Config › Tecnico › Images. Heuristica `images_request` (chat solo status). Distinto de Compare (frameworks) y del adjunto Direct (mismo payload). Informes opcionales `reports/images_*`. | Imagenes |
| **file_to_md** | Fichero → Markdown como contexto para otros procesos agenticos. Tool `Read_upload_file` (recibe el fichero: ruta en este equipo o bytes) + skill `read_by_format` (firma, contenedor ZIP, texto/binario WHATWG, MIME y extension → lector Go: PDF, DOCX/XLSX/PPTX, ODF, EPUB, RTF, HTML, EML/mbox, CSV, JSON, codigo…). Perfil Agent Box `read_only`. Lo usa Inferencia directa (Adjuntar fichero › **Subir**): cualquier usuario sube un fichero desde su navegador (multipart, guardado en memoria para su envio, 2 h, solo para el); **leer y explorar rutas del equipo LAIM es solo para administradores** (`GET /api/v1/direct/attachment/list`, `POST /api/v1/file-to-md/upload` con `path`, `attachment_path` del job Direct → 403 para el resto). API `POST /api/v1/file-to-md/upload` (`convert=true` devuelve el Markdown). Los documentos pasan por el modelo de su tier con control de fidelidad; si el agente se desactiva o el tier no tiene modelo, solo extraccion determinista. **Chat (pkg51c):** caso heuristico `file_to_markdown` (es/en) o un turno de `POST /api/v1/chat/stream` con `attachment_upload_id` / `attachment_path` (ruta solo admin, 403 si no; rechazado en Connect/Share) → «convertir» responde con el Markdown, una pregunta se contesta solo con el documento; sin fichero → respuesta honesta «adjúntalo». **Panel del Chat (pkg51d):** **📄** para todos los usuarios (subida desde el navegador, como **⬆ Subir** de Direct) y **🗂** solo para administradores (el explorador del equipo LAIM de Direct; el resto ve solo el aviso «solo administradores» sobre 📄); el job de chat en cola (`POST /api/v1/queue/submit`, tipo `chat`) lleva `attachment_upload_id` + `attachment_name`, o `attachment_path` (solo admin, 403 si no, comprobado de nuevo al ejecutar el job; rechazado en Connect/Share), solo para ese turno. **Pipelines / flujos:** un paso `file_to_md` lee el fichero de la ejecucion (`attachment_upload_id` / `attachment_path` en `POST /api/v1/config/agent-pipelines-run`, el adjunto del chat en un turno de flujo, o un upload_id / ruta en la entrada del paso) y pasa al siguiente la entrada + `## File context (file_to_md)`; misma regla de propietario/admin. Modo de automatizacion **direct** (lo llaman Direct, el chat, los pasos de pipeline/flujo y REST; sin bus de eventos). Triggers es/en («pdf a markdown / pdf to markdown», «fichero adjunto / attached file»…) para Pattern Composer. | Medio |
| **example** | Pedagogia de una inferencia (pregunta + resultado presentado): analogias cotidianas y tabla de mapeo. Perfil Agent Box `read_only`. API `/api/v1/example/*`. Panel Config › Tecnico › Example. Boton F8 **Ejemplo** del chat (Complemento). Heuristica `example_request` (chat solo status). Distinto de F8 Codigo/script y de `suggestion_example`. Informes opcionales `reports/example_*`. | Medio |
| **pi** | Apoyo a la inferencia: localiza el caso heuristico vivo y los comandos nativos. Perfil Agent Box `read_only`. Ecosystem supervisa. localsystem y remotesystem ejecutan. API `/api/v1/pi/*`. Panel Config › Tecnico › Pi. Direct y Suggestions reciben un bloque de direccion en preguntas de inventario de host. Heuristica `pi_request` (chat solo status). Informes opcionales `reports/pi_*`. | Rapido (sin LLM) |
| **sniffer** | Captura y analisis de paquetes en una NIC o un pcap. Perfil Agent Box `localsystem_host`. Cableado a **network** (inventario LAN ≠ paquetes). Captura viva con HITL. API `/api/v1/sniffer/*`. Panel Config › Tecnico › Sniffer. Heuristica `sniffer_request` (chat solo status/interfaces). Distinto de `net_scan` y SecOps. Informes opcionales `reports/sniffer_*`. | Rapido (sin LLM) |
| **ecosystem** | Validador del ecosistema agentico (skill-validator + AgentV): inventaria y valida el cableado de agentes/skills/tools/flows/pipelines/perfiles en `laim.dat`; inspect + grafo Mermaid; `apply` de patches solo con HITL. Perfil Agent Box `read_only`. API `/api/v1/ecosystem/*`; panel Config › Tecnico › Ecosystem. Heuristica `ecosystem_request`. Distinto de Pipeline, Router, Audit y pattern_composer. Informes opcionales `reports/ecosystem_*`. | Rapido (sin LLM) |
| **agent_r1** | Complemento de Teacher para aprendizaje del ecosistema (MDP por paso, supervisado por Ecosystem). No sustituye `soul.dat`. `apply` HITL via Ecosystem. API `/api/v1/agent-r1/*`; panel Config › Tecnico › Agent-R1. Heuristica `agent_r1_request` (chat solo status/classify). Sugerir mejora + University (`POST /api/v1/university/agent-r1`). Informes opcionales `reports/agentr1_*`. | Rapido (sin LLM) |
| **developer** | Orquestador de desarrollo: planifica, genera y verifica scripts/apps pequenas (Python, PowerShell, Bash, **Go**) via `sandbox_dev` + sandbox. API `/api/v1/developer/*`; panel Config › Tecnico. Snippets verificados en soul.dat. | Desarrollo (fallback medio/lento) |
| **mlx** | Inventario de modelos safetensors (LM Studio `publisher/model`) e inferencia Direct via `mlx_lm.server` en `127.0.0.1:4325`. Solo Apple Silicon. Distinto del boton **LMStudio** (GGUF). API `/api/v1/mlx/*`. Heuristica `mlx_request` (chat solo status/list). | n/a (Direct) |
| **scheduler** | Tareas programadas LAIM (flujos/agentes/`invoke_kind=job`) y crontab/schtasks del SO (HITL). Panel Internal › Programador. API `/api/v1/scheduler/*`. Heuristica `scheduler_request` (chat solo list/calendar/status). | Medio |
| **logic** | Evaluador **determinista** de puertas logicas / algebra booleana (AND, OR, XOR, NAND…). Combina flags de otros agentes, condiciones de flujos y predicados del diagrama de 8 fases (D1–D8). Sin LLM. API `/api/v1/logic/*`. | n/a |
| **diagnose** | Orquestador de diagnosticos por logs (patron estrella). Planifica fuentes OS/servicio/app, lanza parsers en paralelo y correlaciona por marca de tiempo. API `/api/v1/diagnose/*`. | Medio |
| **parser** | Hoja del diagnostico: parsea un unico log (syslog, JSON, eventos Windows, nginx…). Tier rapido, nucleo determinista. API `/api/v1/parser/parse`. | Rapido |
| **remotesystem** | Ejecucion en equipos remotos via SSH (en desarrollo) | Medio |

Los agentes builtin (`localsystem`, `reprocessing`, `devops`, `secops`, `compare`, `pipeline`, `planner`, `evaluator`, `optimizator`, `audit`, `calibrate`, `images`, `file_to_md`, `example`, `pi`, `sniffer`, `ecosystem`, `agent_r1`, `developer`, `mlx`, `scheduler`, `logic`, `diagnose`, `parser`, `router`, …) **no pueden eliminarse**. Solo pueden modificarse sus parametros.

**Ejemplo.** Un usuario pide «valida el ecosistema de agentes». Gana `ecosystem_request` (no Router). Un admin abre Config › Tecnico › Ecosystem → `inventory`. Para crear un agente nuevo: AgentBuilder + gate Ecosystem + HITL `commit`.

#### Usar el agente Logic

1. **API:** `POST /api/v1/logic/eval` con `{ "action":"eval_gate", "op":"and", "inputs":[true,false] }` (o `eval_expr` / `truth_table` / `explain` / `decide`). Lista de operaciones: `GET /api/v1/logic/ops`.
2. **Chat:** preguntas sobre puertas logicas, tablas de verdad o expresiones (`true AND false`) — heuristica `logic_request` corta el turno y responde sin pasar por F4–F6.
3. **Flujos:** elemento `agent_call` con `agent_id=logic` y entrada JSON o texto (`{"action":"decide","predicate":"D6A","inputs":[true]}`).
4. **Predicados de fase:** los rombos del esquema `flujo_inferencia_8_fases.mmd` (entrada valida, hay comandos, permiso, …) se pueden evaluar con `action=decide` para trazabilidad.
5. **Que NO es:** no sustituye a `localsystem` ni a filtros de seguridad InferenceSecurity; solo calcula resultados Booleanos deterministas.

#### Usar el agente Router (orquestador multi-agente)

1. **Cuando:** la peticion es compleja (varios dominios: desarrollar + desplegar + ejecutar + interpretar) o pide explicitamente «modo Plan» / «orquestar agentes».
2. **Chat:** la heuristica `router_request` muestra el **plan** (sin ejecutar). Para ejecutar: API con `approved: true` o CLI con confirmacion HITL.
3. **API:** `POST /api/v1/router/plan`, `/execute`, `/route`, `/analyze`; `GET /ops`.
4. **Skills temporales:** cada paso puede llevar `skill_overrides` (no se guardan en el agente de `laim.dat`).
5. **Ejemplo:** developer (sandbox) → devops deploy → run con aprobacion → analisis de resultados.

#### Usar los agentes Diagnose y Parser

1. **Plan (sin contenido):** `POST /api/v1/diagnose/plan` con `{ "request":"errores ssh", "platform":"linux" }` → parsers a instanciar + **FetchHints**.
2. **Diagnostico completo:** obtener el texto de cada log (F6 / localsystem) y llamar `POST /api/v1/diagnose/run` con `contents: { "auth":"…", "nginx_error":"…" }`.
3. **Un solo fichero:** `POST /api/v1/parser/parse` con `{ "source":"syslog", "content":"…", "format":"auto", "mode":"simplified" }`.
4. **Catalogo de rutas:** `GET /api/v1/diagnose/paths?platform=windows|mac|linux`.
5. **Chat:** «diagnostica los logs de nginx» → heuristica `diagnose_request` (plan + hints). JSON con `contents` ejecuta el analisis completo.
6. **Correlacion:** agrupa eventos de distintas fuentes en la misma ventana temporal (~5 s).
7. **Que NO es:** no sustituye a DevOps para infra/CI-CD; no ejecuta comandos por si mismo (solo FetchHints). Parseo en Go, no en Python. Nota: la accion DevOps `diagnose` es distinta del agente `diagnose` de logs.

#### Usar el agente DevOps

1. **Desde la API (admin):** `POST /api/v1/devops/request` con `{ "action": "assess|plan|diagnose|runbook|context", "request": "…" }` → respuesta **202** con `job_id`; consultar resultado en `GET /api/v1/devops/result/{job_id}`.
2. **Contexto operativo:** `GET/PUT /api/v1/devops/context` guarda entorno/servicio/host en la memoria de sesion (filtrado de secretos).
3. **Desde el chat:** frases que activen la heuristica `devops_request` (p. ej. «necesito el agente devops para un plan de despliegue con rollback», «terraform apply idempotente», «reintentar el despliegue sin duplicar»).
4. **Idempotencia:** assess/plan/runbook exigen convergencia a estado deseado: volver a aplicar el mismo cambio no debe crear recursos extra (upsert, clave unica, `AlreadyPresent` en deploy de apps). No uses incrementos (`+1`) como reintento.
5. **Que NO es:** no sustituye a `localsystem` para ejecutar cada comando F6 ni a `developer` para generar una app pequena; orquesta el plan y recomienda tools LAIM.
6. **Salud del host:** `GET /api/v1/devops/health` resume metricas utiles antes de un assess/diagnose; combinalo con el contexto de sesion.
7. **Sandbox en DevOps:** puede proponer o invocar scripts en el sandbox (Python/Shell/Go) como apoyo a runbooks; la frontera de ficheros sigue siendo la del sandbox (§22). No uses DevOps para «crear una calculadora»: eso es Developer.
8. **Panel web:** **Configuracion › Asistente › 10. Tecnico** (solo admin) → boton **DevOps**. Elige accion (`assess|plan|diagnose|runbook|context|deploy|run`), escribe la peticion; para `deploy`/`run` indica `app_slug` y computer (p. ej. `dirsize` + `server1`). El resultado aparece al completar el job.
9. **Historial / Repetir:** al pie del panel hay una tabla con los ultimos trabajos (persistidos en `laim.dat`). **Repetir** (🔄) solo recarga el formulario; hay que pulsar Ejecutar de nuevo. `GET /api/v1/devops/history`.
10. **Apps generadas:** el panel Tecnico lista binarios registrados (`laim.dat`); ver §23.9.

Skills propias: infra, CI/CD, observabilidad, security ops, recovery. Tools propias: context get/set, runbook, health snapshot (mas sysinfo, shell, red, firewall, SSH, sandbox). Perfil Agent Box: `localsystem_host` (§5.7).

#### Usar el agente SecOps

1. **Cuando:** auditorias de seguridad, deteccion de vulnerabilidades, hardening o informes SecOps (local o equipo registrado en Computers).
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **SecOps**. Acciones: `assess`, `scan_plan`, `audit`, `report`, `harden_plan`, `remediate`, `context`. Indica el computer (ej. `server1`) para probes SSH; vacio = host local. `assess`/`audit` ejecutan checks de solo lectura y analizan con el tier **medio**; el panel muestra la evidencia. Marca **Aprobado** para `remediate` (HITL).
3. **API:** `POST /api/v1/secops/request` → **202** + `job_id`; resultado en `GET /api/v1/secops/result/{job_id}` (incluye `probe_evidence`, `findings`). Contexto: `GET/PUT /api/v1/secops/context`. Historial: `GET /api/v1/secops/history`.
4. **Chat:** frases tipo «auditoria de seguridad», «agente secops», «plan de deteccion de vulnerabilidades» → heuristica `secops_request` (assess o scan_plan; **nunca** remedia sola).
5. **Informes:** se guardan en `reports/secops_*.md` (con evidencia de probes) y aparecen en el panel Informes bajo el grupo **Secops**.
6. **Historial / Repetir:** tabla inferior del panel; **Repetir** restaura accion, request, computer, aprobacion y contexto sin auto-ejecutar.
7. **Fase 2 (securizacion):** tras el diagnostico, usa `harden_plan` y luego `remediate` con aprobacion. Para utilidades de prueba (TDD) o multi-paso, pide al **Router** orquestar SecOps + Developer (+ localsystem/DevOps).
8. **Que NO es:** no sustituye a SecureAgent (bloqueo de amenazas en runtime) ni al catalogo InferenceSecurity REJECT; no genera exploits ni PoCs ofensivos.

#### Usar el agente Compare

1. **Cuando:** comparar frameworks de orquestacion (LangGraph, CrewAI, …), agentes LAIM, tiers o enfoques de flujo con matriz, pros/contras y recomendacion documentada.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Compare**. Acciones: `matrix`, `diff`, `recommend`, `analyze`, `context`. Opciones A/B opcionales; marca **Escribir informe** para `reports/compare_*.md`.
3. **API:** `POST /api/v1/compare/request` → **202** + `job_id`; resultado en `GET /api/v1/compare/result/{job_id}`. Contexto: `GET/PUT /api/v1/compare/context`. Catalogo de ejes: `GET /api/v1/compare/catalog`. Historial: `GET /api/v1/compare/history`.
4. **Chat:** frases tipo «compara LangGraph vs CrewAI», «matriz de capacidades», «pros y contras» → heuristica `compare_request` (solo analisis; sin ejecutar host).
5. **Que NO es:** no sustituye al **Router** (orquestacion multi-agente con HITL) ni al **Pattern Composer** (componer pipelines/flujos). Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Pipeline

1. **Cuando:** optimizar secuencias, Flows avanzados o `AgentPipelineConfig` (etapas lentas en serie, ola paralela, staleness, checklist de validacion mecanica). Metodologia tipo [stay-learning](https://github.com/bhf/stay-learning).
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Pipeline**. Acciones: `assess`, `optimize`, `wave`, `validate`, `status`, `context`. Opcional: target kind/id, etapas separadas por coma; marca **Escribir informe** para `reports/pipeline_*.md`.
3. **API:** `POST /api/v1/pipeline/request` → **202** + `job_id`; resultado en `GET /api/v1/pipeline/result/{job_id}`. Contexto: `GET/PUT /api/v1/pipeline/context`. Catalogo: `GET /api/v1/pipeline/catalog`. Historial: `GET /api/v1/pipeline/history`.
4. **Chat:** frases tipo «agente pipeline», «optimizar flujo con ola paralela», «staleness del workflow» → heuristica `pipeline_request` (solo analisis). Frases CI/CD (jenkins/actions/deploy) van a **DevOps**, no a Pipeline.
5. **Materializar:** tras aprobar el plan, usar **Pattern Composer** o el diseñador de Flows; ejecucion multi-agente con **Router** + HITL.
6. **Que NO es:** no ejecuta `RunPipeline`, no sustituye a DevOps CI/CD ni al Pattern Composer. Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Planner

1. **Cuando:** diseñar un plan de implementacion, dividir una meta en tareas, activar la siguiente, seguir el avance o verificar criterios de exito (sin ejecutar host).
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Planner**. Acciones: `decompose`, `refine`, `activate`, `track`, `verify`, `status`, `context`. Marca **Escribir informe** para `reports/planner_*.md`.
3. **API:** `POST /api/v1/planner/request` → **202** + `job_id`; resultado en `GET /api/v1/planner/result/{job_id}` (incluye `router_handoff`). Contexto: `GET/PUT /api/v1/planner/context`. Historial: `GET /api/v1/planner/history`.
4. **Chat:** frases tipo «diseña un plan», «divide en tareas», «verifica el plan», «agente planner» → heuristica `planner_request` (solo analisis). «Orquestar / ejecuta multi-agente» va a **Router**.
5. **Ejecutar:** usar **Router** con HITL; el handoff `ToRouterPlan()` convierte tareas Planner en pasos Router.
6. **Que NO es:** no sustituye a Router (ejecucion), Pipeline (optimizar Flows) ni Pattern Composer. Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Swarm

1. **Cuando:** necesitas varias perspectivas analiticas en paralelo (analyst/critic/security_lens) y una sintesis Markdown antes de Evaluar/Optimizar — sin ejecutar host.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Swarm**. Acciones: `plan`, `run`, `synthesize`, `evaluate`, `optimize`, `status`, `context`.
3. **API:** `POST /api/v1/swarm/request` → **202** + `job_id`; resultado en `GET /api/v1/swarm/result/{job_id}`. Contexto: `GET/PUT /api/v1/swarm/context`. Historial: `GET /api/v1/swarm/history`.
4. **Chat:** frases tipo «agente swarm», «swarm plan», «fan-out swarm» → heuristica `swarm_request` (solo plan/status). `run`/`synthesize`/`evaluate`/`optimize` via panel/API.
5. **Que NO es:** no sustituye a Router (ejecucion HITL), Diagnose (logs) ni Pipeline (ola/staleness de Flows). Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Evaluator

1. **Cuando:** evaluar la calidad de un resultado, proceso o trayectoria de agente (score mecanico, rubrica, checklist); complementar el aprendizaje de `soul.dat` junto a Teacher.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Evaluator**. Acciones: `assess`, `score`, `trajectory`, `rubric`, `learn`, `status`, `context`. Marca **Aprobado** para `learn` (HITL → soul.dat). Opcional: **Escribir informe** → `reports/evaluator_*.md`.
3. **API:** `POST /api/v1/evaluator/request` → **202** + `job_id`; resultado en `GET /api/v1/evaluator/result/{job_id}` (incluye `optimize_hint` / findings). Contexto: `GET/PUT /api/v1/evaluator/context`. Historial: `GET /api/v1/evaluator/history`.
4. **Chat:** frases tipo «agente evaluator», «puntuacion mecanica», «score the trajectory» → heuristica `evaluator_request` (solo analisis; no escribe soul).
5. **Bucle de mejora:** pasar hallazgos a **Optimizator** (`ToOptimizatorHandoff` / campo `eval_handoff`); tras apply, volver a evaluar.
6. **Que NO es:** no sustituye a SecOps assess ni a Planner.verify. Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Optimizator

1. **Cuando:** optimizar contexto/procesos, aplicar filtro de discoverability, comprimir ruido, minar gotchas operativos o proponer mejoras de capacidad (tiers, colas, slots) alineadas con LAIM.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Optimizator**. Acciones: `analyze`, `compress`, `propose`, `gotchas`, `apply`, `status`, `context`. Campo opcional **eval_handoff** (texto del Evaluator). Marca **Aprobado** para `apply` (HITL → soul.dat).
3. **API:** `POST /api/v1/optimizator/request` → **202** + `job_id`; resultado en `GET /api/v1/optimizator/result/{job_id}` (incluye `evaluate_hint`). Contexto: `GET/PUT /api/v1/optimizator/context`. Historial: `GET /api/v1/optimizator/history`.
4. **Chat:** frases tipo «agente optimizator», «discoverability filter», «mine gotchas», «comprimir contexto» → heuristica `optimizator_request` (solo analisis; no escribe soul).
5. **Bucle de mejora:** tras `apply`, re-evaluar con **Evaluator**. Tips en `soul.dat` enriquecen el alma de la instalacion (complemento a Teacher / ML interno).
6. **Que NO es:** no sustituye a Pipeline (ola/staleness de Flows) ni a Pattern Composer. Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Audit

1. **Cuando:** accountability (decision records), atribucion de fallos, auditoria de capacidad/recursos LAIM u host, o briefing para Suggestions SSH.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Audit**. Acciones: `trail`, `attribute`, `resources`, `suggest_brief`, `report`, `status`, `context`. Equipo remoto opcional; ventana/grupo para `trail`; marca **Aprobado** solo para encolar Suggestions desde `suggest_brief`.
3. **API:** `POST /api/v1/audit-agent/request` → **202** + `job_id` (prefijo distinto de `GET /api/v1/audit` del ledger). Resultado: `GET /api/v1/audit-agent/result/{job_id}`.
4. **Chat:** frases tipo «agente audit», «decision records», «audit resources» → heuristica `audit_request` (solo analisis; **nunca** encola Suggestions).
5. **Fronteras:** seguridad/hardening → **SecOps**; score de resultados → **Evaluator**; listado crudo de eventos → Internal › Auditoria.
6. **Informes:** opcional `write_report` → `reports/audit_*.md` (grupo UI **Audit**). Perfil Agent Box: `localsystem_host` (§5.7).

#### Usar el agente Calibrate

1. **Cuando:** asociar una firma vocal al usuario LAIM, verificar hablante antes de STT, o resetear una firma (admin).
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Calibrate**. Acciones: `speaker_enroll`, `speaker_verify`, `speaker_reset`, `status`, `context`, `report`. Marca **Aprobado** para resetear la firma de otro usuario.
3. **Enrollment (Direct / Chat / mic):** al usar el microfono sin firma, LAIM pide grabar **20 segundos** (modal CRT). La captura es del host (proceso Go), no del navegador. Requiere tier **Sonido** configurado (modelo con audio, p. ej. `gemma4:e2b`/`e4b`). En Chat el boton 🎤 escribe en el prompt del chat (mismo API que Direct).
4. **Gate STT:** todo `POST /api/v1/speech/record/stop` verifica la voz. Sin enrollment → `voice_enrollment_required`; mismatch → `voice_mismatch` + `secure.log` / Audit / notificacion; juez no disponible → `voice_judge_unavailable`. Solo MATCH llama a STT y muestra badge «Voz reconocida».
5. **Reset:** en la tabla de usuarios (icono de voz) o accion `speaker_reset` / `POST /api/v1/speech/voice/reset`. El siguiente uso de mic pide re-enrollment.
6. **API:** `POST /api/v1/calibrate/request` → **202** + `job_id`; resultado `GET /api/v1/calibrate/result/{job_id}`. Chat: heuristica `calibrate_request` solo **status** (nunca enroll/verify/reset destructivo).
7. **Fronteras:** score de resultados → **Evaluator**; accountability → **Audit**; captura/transcripcion cruda → capa Speech (siempre detras del gate Calibrate).
8. **Informes:** opcional `write_report` → `reports/calibrate_*.md` (grupo UI **Calibrate**). Perfil Agent Box: `localsystem_host` (§5.7). Incluir `voice.dat` en Backup/Restore de instalacion.

#### Usar el agente Images

1. **Cuando:** describir una captura, extraer texto visible (OCR) o comparar dos mapas de bits con el tier Imagenes.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Images**. Acciones: `describe`, `extract_text`, `caption`, `compare`, `status`, `context`, `report`. Indica la **ruta local** del PNG/JPEG/GIF/WebP (el Core lee el fichero; Reflex no lo abre).
3. **API:** `POST /api/v1/images/request` → **202** + `job_id`; resultado `GET /api/v1/images/result/{job_id}`. Chat: heuristica `images_request` solo **status** (describe/OCR necesitan fichero).
4. **Connect:** el fichero se lee en este host; los bytes van al Share en `images[]`.
5. **Fronteras:** adjuntar en Inferencia directa usa el mismo payload sin el orquestador; comparar frameworks → **Compare**; no se usa Tesseract.
6. **Informes:** opcional `write_report` → `reports/images_*.md` (grupo UI **Images**). Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Example

1. **Cuando:** explicar una inferencia ya mostrada con analogias cotidianas (objetivo, historia, por que ese resultado, tabla de mapeo). No sirve para generar codigo (F8 **Codigo / Script**) ni para inventario de host.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Example**. Acciones: `analyze`, `status`, `context`, `report`. Rellena **entrada** (pregunta) y **salida** (resultado presentado); el contexto extra es opcional.
3. **Chat F8:** tras un turno, el modal ofrece **Ejemplo**. LAIM llama al mismo agente (tier medio) con el prompt, el analisis y `phase6:command_output`, y anade el informe como **Complemento**. No escribe `reports/` desde F8.
4. **API:** `POST /api/v1/example/request` → **202** + `job_id`; resultado `GET /api/v1/example/result/{job_id}`. Chat: heuristica `example_request` solo **status**.
5. **Fronteras:** scripts → **Developer** F8; sugerencias de codigo/ejemplo legado → `suggestion_example` (fallback). Perfil Agent Box: `read_only` (§5.7).
6. **Informes:** opcional `write_report` en el panel → `reports/example_*.md` (grupo UI **Example**).

#### Usar el agente Pi

1. **Cuando:** localizar el caso heuristico vivo y los comandos nativos de un inventario de host (RAM, disco, procesos) para que localsystem o remotesystem los ejecuten. No sustituye Direct ni flujo8.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Pi**. Acciones: `locate`, `plan`, `observe`, `supervise`, `status`, `context`, `report`. Plataforma `linux` / `mac` / `windows`. Ejecutor `local` o `remote`.
3. **Direct y Suggestions:** si la pregunta es inventario de host, el prompt lleva los comandos nativos de la guia. Ecosystem supervisa la compatibilidad; Pi no aplica parches.
4. **API:** `POST /api/v1/pi/request` → **202** + `job_id`; resultado `GET /api/v1/pi/result/{job_id}`. Chat: heuristica `pi_request` solo **status**.
5. **Fronteras:** la ejecucion sigue en localsystem / remotesystem (HITL si el comando es de riesgo). Comandos destructivos no salen de Pi.
6. **Informes:** opcional `write_report` → `reports/pi_*.md` (grupo UI **Pi**). Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Sniffer

1. **Cuando:** listar interfaces, analizar un pcap/tcpdump o planificar una captura corta en una NIC de **esta** red (trafico propio). No sirve para enumerar hosts de la LAN (`net_scan`) ni para hardening (SecOps).
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Sniffer**. Acciones: `interfaces`, `capture`, `analyze`, `summarize`, `status`, `context`, `report`. Indica la **interfaz** (`en0` / `eth0`) y, para analisis offline, la **ruta local** del pcap (el Core lee el fichero; Reflex no lo sube). Marca **Aprobado** para captura viva (HITL); sin aprobacion el agente solo devuelve el plan (`tcpdump` / `dumpcap` / `pktmon`).
3. **API:** `POST /api/v1/sniffer/request` → **202** + `job_id`; resultado `GET /api/v1/sniffer/result/{job_id}`. Chat: heuristica `sniffer_request` solo **status** / **interfaces** (nunca captura viva).
4. **Cableado:** par de **network** (`DelegateAgentIDs`). Network = inventario LAN; Sniffer = paquetes. Ecosystem `validate` / Framework `imp-sniffer-network` deben seguir verdes.
5. **Fronteras:** dispositivos en la subred → **network** / `net_scan`; auditoria de seguridad → **SecOps**; logs → **Diagnose**. Sin MITM, sin NFQUEUE, sin PoCs de exploit.
6. **Informes:** opcional `write_report` → `reports/sniffer_*.md` (grupo UI **Sniffer**). Perfil Agent Box: `localsystem_host` (§5.7).

#### Usar el agente Ecosystem

1. **Cuando:** validar el cableado del ecosistema agentico (referencias colgantes de skills/tools, perfiles runtime, delegates, agent_call/pattern_call), inventariar componentes o inspeccionar un agente/flujo con grafo Mermaid.
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Ecosystem**. Acciones: `inventory`, `validate`, `inspect`, `consistency`, `propose`, `apply`, `status`, `context`, `report`. Marca **Aprobado** solo para `apply` (HITL); si no hay patches en el body, el agente regenera propuestas desde `ValidateEcosystem`.
3. **API:** `POST /api/v1/ecosystem/request` → **202** + `job_id`. Resultado: `GET /api/v1/ecosystem/result/{job_id}`.
4. **Chat:** frases tipo «agente ecosystem», «validar ecosistema» → heuristica `ecosystem_request` (solo `inventory`/`validate`/`status`/`inspect`; **nunca** `apply`).
5. **Fronteras:** crear flujos/pipelines → **pattern_composer**; optimizar etapas → **Pipeline**; ejecutar multi-agente → **Router**; accountability/recursos → **Audit**; seguridad → **SecOps**.
6. **Informes:** opcional `write_report` → `reports/ecosystem_*.md` (grupo UI **Ecosystem**). Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Agent-R1

1. **Cuando:** el usuario pide evolucionar el ecosistema (skills, tools, flujos, Framework) o pega un fence University; no para un comando F5/F6 incorrecto (eso es **Teacher** → `soul.dat`).
2. **Panel web (admin):** **Configuracion › Asistente › 10. Tecnico** → boton **Agent-R1**. Acciones: `classify`, `observe`, `rollout`, `propose`, `apply`, `university`, `teacher_bridge`, `status`, `context`, `report`. Marca **Aprobado** solo para `apply` (HITL); Agent-R1 delega en Ecosystem y **nunca** escribe `laim.dat` el mismo.
3. **API:** `POST /api/v1/agent-r1/request` → **202** + `job_id`. Resultado: `GET /api/v1/agent-r1/result/{job_id}`. University loopback: `POST /api/v1/university/agent-r1` (solo `127.0.0.1`; observe+propose, `applied=false`).
4. **Chat:** frases tipo «agente agent-r1», «aprendizaje del ecosistema» → heuristica `agent_r1_request` (solo `status`/`classify`; **nunca** `apply`).
5. **Sugerir mejora:** Teacher sigue guardando tips heuristicos; si el texto habla de ecosistema/Framework/University, Agent-R1 propone parches Ecosystem (sin aplicar).
6. **Fronteras:** validar cableado → **Ecosystem**; analogia de una inferencia → **Example**; score/trajectory → **Evaluator**.
7. **Informes:** opcional `write_report` → `reports/agentr1_*.md` (grupo UI **Agent-R1**). Perfil Agent Box: `read_only` (§5.7).

#### Usar el agente Developer

1. **Panel web:** **Configuracion › Asistente › 10. Tecnico** → **Developer**. Acciones: `spec` (DEFINE), `plan`, `develop` (BUILD), `test` (VERIFY sandbox TDD), `review`, `deliver` (SHIP: binario Go o snippet Python), `research`, `recall`. Idioma (`python`, `powershell`, `bash`, **`go`**); el job es asincrono (202 + poll). `test`/`deliver` reutilizan el codigo del resultado anterior si la peticion esta vacia.
2. **API (admin):** `POST /api/v1/developer/request` con `{ "action":"spec"|"plan"|"develop"|"test"|"deliver", "request":"…", "language":"go", "code":"…" }` → `job_id`; resultado en `GET /api/v1/developer/result/{job_id}`. Snippets: `GET/DELETE /api/v1/developer/snippets`. Historial: `GET /api/v1/developer/history`.
3. **Historial / Repetir:** tabla inferior del panel; **Repetir** restaura accion, lenguaje y peticion (sin auto-ejecutar).
4. **Ciclo DEFINE→SHIP:** DEFINE congela lenguaje (Go binario vs Python sandbox) y aceptacion. VERIFY llama `ExecuteInSandbox` (`runtime_profile sandbox_code`). SHIP Go registra `GeneratedApps`; el despliegue lo hace **DevOps** con `approved=true` (localsystem/remotesystem). Python no inventa un slug Go.
5. **Lenguaje Go:** el sandbox debe tener el toolchain `go` en PATH (`GET /api/v1/sandbox/status` → `go_ok`). El codigo generado debe ser un solo fichero `package main` con stdlib; se ejecuta con `go run` en un modulo aislado bajo `sandbox/workspace/temp/` (no usa el `go.mod` del repo LAIM).
6. **Que NO es:** no sustituye a DevOps para planes de despliegue/infra ni a `localsystem` para comandos F6 del host. No porta frontend/git/CI de agent-skills. Perfil Agent Box: `sandbox_code` (§5.7 / §23).
7. **Chat:** heuristica `developer_request` → short-circuit **spec/plan** (sin generar codigo). BUILD/VERIFY/SHIP van por el panel o la API. F8 Codigo/script: `chat_script` (sin informe `developer_*.md` por iteracion). Tras F6 y **valido**, escribe `reports/developer_script_*`. Comandos FORBIDDEN no se ejecutan.

### 5.2 Crear agentes personalizados

Hay tres formas de crear un agente (panel **Configuracion › Agentes › Crear agente**):

1. **Formulario avanzado** — edicion fina de todos los campos (abajo).
2. **Asistente / Prompt (AgentBuilder)** — orquestador Go (`agent_builder`) que guia el borrador, lo valida contra **Ecosystem** (cero findings de severidad error) y solo hace `commit` con aprobacion HITL. Tras el commit, la UI puede ofrecer crear un Flow con Pattern Composer.
3. **API** — `POST /api/v1/agent-builder/request` (acciones `start`/`answer`/`validate`/`commit`/`catalog`).

Desde el formulario (**config → 3 → Crear agente**):

| Campo | Descripcion |
|---|---|
| `id` | Identificador unico (snake_case) |
| `name` / `description` | Nombre y descripcion del agente |
| `model_tier` | `fast`, `medium`, `slow` o `translator` |
| `memory_policy` | `session` (solo en sesion), `persistent` (cifrado en laim.dat) o `none` |
| `instructions` | Prompt de sistema del agente |
| **Skills asignadas** | Capabilities que el agente puede usar |
| **Tools asignadas** | Herramientas ejecutables que puede invocar |
| **Automatizacion** | Trigger (evento, cron) y accion automatica |
| **Orquestacion** | Modo de coordinacion con otros agentes |
| **`runtime_profile`** (opcional) | Perfil de la *Agent Box* (§5.7): limita sandbox, host, soul y red. Si se deja vacio, LAIM asigna uno por tipo de agente |

> **Regla:** AgentBuilder y Ecosystem viven en Go; la UI solo llama API y muestra Markdown. No inventar IDs de skills/tools: preferir reutilizar los Predefined.

### 5.3 Catálogo de patrones de diseno multiagente

Desde **Configuración → Gestión de agentes → Catálogo de patrones** (web) o el equivalente en `laim config` puedes consultar el catálogo tipado de LAIM. Cada tarjeta muestra familia, madurez, si el motor `RunPipeline` ya lo implementa, con qué otros patrones se compone, referencias (Ng / Codex / Gulli) y un diagrama Mermaid.

**Patrones base (Andrew Ng):** ReAct, Reflection, Tool Use, Planning. LAIM los mapea a IDs concretos y añade orquestación/gobernanza.

| ID | Familia | Implementado en pipeline | Notas |
|----|---------|--------------------------|-------|
| `single` | core | Sí | Un solo agente (baseline) |
| `sequential` | orchestration | Sí | Prompt chaining |
| `parallel` | orchestration | Sí | Parallelization + síntesis |
| `loop` | orchestration | Sí | Hasta StopCriteria / MaxIterations |
| `review_critique` | quality | Sí | Reflection con agente crítico |
| `iterative_refinement` | quality | Sí | Self-reflection |
| `coordinator` | orchestration | Sí | Routing / triage |
| `react` | core | Sí | Think → Act → Observe |
| `tool_use` | core | Sí | Alias operativo de ReAct con tools |
| `planning` | orchestration | Sí | Plan-then-execute; `HumanCheckpoint>0` pausa el plan (modal) |
| `human_in_loop` | governance | Sí | Pausa tras N agentes; reanudar con modal / `POST …/agent-pipelines-resume` |

Filtros en la UI: **Todos / Núcleo / Orquestación / Calidad / Gobernanza**. El conocimiento educativo también vive en `library.dat` (categoría `agentic_pattern`) para enriquecer prompts futuros.

Los pipelines (**§5.6**) eligen uno de estos IDs en `AgentPipelineConfig.pattern`. El agente **`pattern_composer`** (Phase C) propone patrón + agentes desde un objetivo en lenguaje natural (`POST /api/v1/config/pattern-composer/compose` o modal «Componer con Pattern Composer»; body opcional `prefer_pattern`). En el chat, el perfil **Pipeline dinámico** (`pipeline:dynamic`) usa el mismo compositor por turno con contrato en **tres fases**: (1) Compose — `mode`/`phases[]`; (2) Swarm execute — olas paralelas de agentes `read_only` + puertas seriales HITL/host; (3) Synthesize — Markdown + PresenterPost. Si elige `flujo8`/`direct`, se mantiene el flujo de 8 fases. El catálogo factory del desplegable Perfil (`flujo8`, `direct`, `pipeline:dynamic`, `flujo8_experimental`, `flow:base8`, `flow:example`) vive en `library.dat` (keyword `chat_profile`) para todas las instalaciones.

**Phase D — perfil `suggested_pattern`:** en Config → Perfiles puedes fijar un patrón sugerido. No sustituye el chat de 8 fases: solo añade una pista en inglés al prompt F5 del perfil activo y sesga el compositor (`prefer_pattern` / `PreferPattern`) cuando el body API no trae uno explícito.

### 5.4 Skills (capacidades)

Las **skills** son conjuntos de instrucciones y capacidades que guian el comportamiento del agente. Se inyectan como contexto en el prompt cuando estan activas.

Desde **Configuración → Gestión de agentes → Catálogo de skills → Skills disponibles**:
- 14 skills predefinidas (builtin, no eliminables): analisis de sistema, red, seguridad, etc.
- Posibilidad de crear skills personalizadas
- **Info** abre un modal con un informe del agente Ecosystem: diseño, agentes que usan la skill, recomendaciones de uso y un esquema Mermaid (Presenter, tier medio). Las banderas 🇬🇧/🇪🇸 traducen el informe (mismo camino que manuales e informes). Si editas la skill, el informe se regenera.

Desde **config → 3 → 6. Catalogo de skills** (CLI):

| Campo | Descripcion |
|---|---|
| `category` | `core`, `system`, `analysis`, `communication`, `integration`, `automation`, `custom` |
| `capabilities` | Flags: `can_read`, `can_write`, `can_execute`, `can_network`, `can_analyze`, `can_generate`, `can_transform` |
| `instructions` | Bloque de prompt inyectado cuando la skill esta activa |
| `constraints` | Limites que la IA debe respetar con esta skill |
| `platforms` | `windows`, `mac`, `linux` o todos |

### 5.5 Tools (herramientas ejecutables)

Las **tools** son unidades ejecutables que un agente puede invocar para interactuar con el SO, la red o servicios externos.

Desde **Configuración → Gestión de agentes → Catálogo de tools → Tools disponibles**:
- 12 tools predefinidas (builtin): sysinfo, procesos, disco, red, servicios, GPU, etc.
- Posibilidad de crear tools personalizadas
- **Info** abre el mismo tipo de modal que en skills (informe Ecosystem + Mermaid + banderas EN/ES).

Desde **config → 3 → 7. Catalogo de tools** (CLI):

| Campo | Descripcion |
|---|---|
| `category` | `system`, `file`, `network`, `process`, `security`, `data`, `integration`, `automation` |
| `invocation.type` | `shell`, `http`, `python`, `go_func` |
| `invocation.command` | Comando o URL a ejecutar |
| `auth_type` | `none`, `api_key`, `token`, `basic`, `certificate`, `oauth2` |

> Los iconos de las tools del sistema se muestran en la interfaz web.

### 5.6 Pipelines multiagente

Desde **Configuración → Gestión de agentes → Pipelines** puedes crear orquestaciones tipadas por patrón (`AgentPipelineConfig`):

| Campo | Uso |
|-------|-----|
| `pattern` | ID del catálogo (§5.3): `sequential`, `planning`, `human_in_loop`, etc. |
| `agent_ids` | Orden de participantes (en `coordinator`/`review_critique` el índice 0 tiene rol especial) |
| `max_iterations` | Tope de bucles / ReAct (0 = default del patrón) |
| `stop_criteria` | Frase que corta un `loop` cuando aparece en la salida |
| `human_checkpoint` | En `human_in_loop`: pausa tras N agentes (default 1). En `planning`: si >0, pausa **tras el plan** para aprobarlo en modal |

**Human-in-the-loop (modal):** al ejecutar un pipeline que alcanza un checkpoint, la API responde `202` con `paused=true` y `run_id`. La UI abre un modal CRT con la vista previa (plan o salida parcial); **Aprobar** llama `POST /api/v1/config/agent-pipelines-resume` (`approved=true`) y continúa; **Rechazar** detiene el run.

**Pattern Composer (modal):** en el formulario de pipelines, «Componer con Pattern Composer» envía un `goal` al agente; la propuesta rellena patrón, agentes e iteraciones. Con «Guardar como pipeline» (`persist=true`) se crea un `AgentPipelineConfig`; `async=true` responde `202` y persiste en segundo plano.

### 5.7 LAIM Agent Box — contrato y privacy de agentes

Esta seccion explica, en lenguaje de administracion, que es la **Agent Box** en LAIM, para que sirve y como usarla en el dia a dia. No hace falta conocer Docker, Nix ni redes criptograficas externas: todo ocurre **dentro de tu instalacion LAIM**, en el nucleo Go.

#### Que problema resuelve

Cuando un agente (Teacher, sandbox, localsystem, un agente custom o un paso de un flujo avanzado) trabaja por ti, el administrador necesita tres garantías simples:

1. **Que no haga de mas** — por ejemplo, que un agente pensado solo para analizar no ejecute codigo en el host.
2. **Que lo que guarde no filtre secretos** — contrasenas, tokens o claves no deben quedar en claro en memoria de sesion, `soul.dat` o el detalle de auditoria.
3. **Que el comportamiento sea predecible** — el mismo tipo de agente se comporta igual en CLI, web y flujos.

La **Agent Box** es el nombre de ese marco: cada agente «ocupa una caja» con reglas claras. No es un contenedor Docker aparte; es **politica de LAIM** aplicada antes de ejecutar y antes de guardar.

> Analogia: la caja es el *puesto de trabajo* del agente. El perfil dice que herramientas hay en el puesto; el filtro de privacy revisa todo lo que el agente intenta archivar.

#### Dos pilares (MVP actual)

| Pilar | Nombre tecnico | Que hace en la practica |
|-------|----------------|-------------------------|
| **Contrato de runtime (P1)** | `AgentRuntimeContract` / `runtime_profile` | Define si el agente puede usar sandbox, ejecutar en el host, escribir en `soul.dat`, usar red saliente, etc. Si pide algo no permitido, LAIM **lo deniega** (fail-closed). |
| **Privacy middleware (P3)** | `ApplyPrivacyFilter` | Antes de persistir texto en memoria de sesion, soul o auditoria, **tapa secretos** tipicos (passwords, Bearer tokens, PEM, `master_key_cipher`, etc.). |

Documentacion de diseno interna: `internal/docs/ADR_LAIM_Agent_Box_MVP.md`. Conocimiento en `library.dat` con la palabra clave `agent_box` (util si mas adelante enriqueces prompts con la biblioteca).

#### Perfiles de runtime — cual elegir

El campo opcional del agente es `runtime_profile`. Si esta vacio, LAIM elige un default segun el *kind* del agente.

| Perfil | Pensado para | Puede sandbox | Puede comandos en este PC | Puede escribir soul.dat | Notas para el admin |
|--------|--------------|---------------|---------------------------|-------------------------|---------------------|
| `read_only` | Presenter, Mermaid, analisis, **compare**, la mayoria de agentes «de lectura» | No | No | No | Puede guardar en memoria de sesion (chat). Es el default seguro. |
| `sandbox_code` | Teacher, Sandbox Dev, agentes que generan/prueban codigo | Si | No (solo dentro del sandbox) | Si (si el flujo lo pide) | Ideal para aprender o prototipar **sin** tocar el SO del host. Ver §22. |
| `localsystem_host` | `localsystem`, elevacion, **devops**, **secops** | Si | Si (F6 + consentimiento / reglas RISKY) | No* | El agente de sistema local / DevOps / SecOps; no debe «aprender» secretos en soul por el perfil. *DevOps puede guardar tips de runbook filtrados en soul.dat. |
| `remote_ssh` | `remotesystem` / trabajo remoto | No | Si, en el equipo remoto | No | La ejecucion vive en el host SSH, no en el sandbox local. |

**Defaults automaticos (si no configuras el campo):**

| Tipo de agente (kind) | Perfil por defecto |
|-----------------------|--------------------|
| `localsystem`, `elevate_privilege`, `devops` | `localsystem_host` |
| `remotesystem` | `remote_ssh` |
| `teacher`, `sandbox_dev` | `sandbox_code` |
| `compare`, presenter, mermaid, custom sin perfil, … | `read_only` |

#### Como usarlo como administrador

1. **Agentes builtin** — no hace falta tocar nada al principio: ya tienen un perfil coherente con su funcion. Solo cambia el perfil si entiendes el riesgo (por ejemplo, **no** pongas `localsystem_host` a un agente de presentacion).
2. **Agentes personalizados** — al crear o editar el agente (config → Gestion de agentes), asigna `runtime_profile` segun lo que deba poder hacer:
   - Solo razonar / formatear → `read_only`
   - Generar o probar scripts en el sandbox → `sandbox_code`
   - Ejecutar comandos en esta maquina (con las salvaguardas F6) → `localsystem_host`
   - Trabajar via SSH en equipos remotos → `remote_ssh`
3. **Sandbox (§22)** — cuando un llamador indica el perfil en la peticion de ejecucion y ese perfil **no** permite sandbox, LAIM no ejecuta el codigo: registra la negativa (consola / violacion) y el proceso no corre. Asi un agente «solo lectura» no puede «colarse» al sandbox por error de programacion.
4. **Flujos avanzados (§7)** — al usar elementos `agent_call` / `pattern_call`, el agente invocado sigue sujeto a su perfil. Combinalo con autorizacion humana (`user_authorization` / HITL) antes de side-effects peligrosos.
5. **Teacher y soul.dat (§13)** — el Teacher usa por defecto `sandbox_code` (puede aprender y escribir soul). El middleware de privacy **limpia secretos** en los campos de texto de la entrada antes de guardarlos. Sigue siendo buena practica no pegar contrasenas en el feedback del Teacher.

#### Privacy — que se protege automaticamente

No tienes que activar un interruptor: al guardar, LAIM aplica el filtro:

| Donde se guarda | Politica | Efecto tipico |
|-----------------|----------|---------------|
| Memoria de sesion (`laim.memory` / chat) | Estricta | Sustituye secretos por marcadores `[REDACTED:…]` |
| `soul.dat` (resumen, wrong/correct, etc.) | Estricta | Igual |
| Detalle de auditoria (`audit.dat`) | Suave | Redacta secretos pero deja el relato admin-legible |
| Eventos de actividad (reservado) | Suave | Misma idea que auditoria |

**Ejemplos de lo que se tapa:** `password=…`, `Bearer …`, bloques `PRIVATE KEY`, literales `master_key_cipher=…` / `connection_key_cipher=…`, tokens tipo `sk-…`.

**Lo que no hace la Agent Box (a proposito):**

- No sustituye el consentimiento F6 ni las categorias FORBIDDEN/RISKY de comandos.
- No sustituye la Seguridad de inferencia (REJECT) ni el agente Secure.
- No impide que un admin con rol adecuado configure Share, firewall o equipos remotos.
- No es un producto Nostr/Nix: es politica local de LAIM.

#### Relacion con el Sandbox (§22)

| Concepto | Pregunta que responde |
|----------|------------------------|
| **Agent Box (perfil)** | ¿*Este agente* tiene permiso para pedir sandbox / host / soul? |
| **Sandbox** | Si tiene permiso, ¿*donde* corre el codigo y con que limites de disco/red/tiempo? |

Ambos se complementan. Primero el contrato; luego el sandbox aplica su frontera de ficheros y red.

#### Buenas practicas

- Empieza siempre por el perfil **mas restrictivo** que cubra el caso de uso.
- Tras cambiar el perfil de un agente en produccion, prueba un turno o un run de flujo y revisa Auditoria / `secure.log` si esperabas una denegacion.
- No copies pegando API keys en prompts de Teacher ni en analisis que se guardan en memoria: aunque el filtro ayuda, el mejor secreto es el que no se pega.
- Documenta en la descripcion del agente *por que* tiene un perfil concreto (ayuda a otros admins).
- Para diseno de flujos con side-effects, combina Agent Box + HITL (§5.6 / §7) + sandbox (§22).

#### Donde mirar si algo falla

| Sintoma | Donde mirar |
|---------|-------------|
| Codigo de agente no se ejecuta; mensaje de violacion / denegacion de perfil | `logs/console.log` (evento sandbox / agent_box); resultado con `violation` |
| Sospecha de secreto en un log | No deberia estar en claro en detail de audit ni en soul; si aparece, abre incidencia y rota la clave |
| Quieres recordar la politica | Manual §5.7; ADR interno; entrada `library.dat` keyword `agent_box` |

---

## 6. Perfiles de flujo de inferencia

Accede desde **config → 4. Perfiles de flujo de inferencia**.

Los perfiles permiten personalizar el flujo de inferencia de 8 fases sin modificar el codigo. Cada perfil puede tener:

- **Overrides de prompts por fase**: reemplaza el prompt de una fase concreta con uno personalizado
- **Bindings de agente por fase**: asigna un agente especifico a una fase
- **`suggested_pattern` (Phase D)**: ID del catálogo (§5.3); pista suave F5 + sesgo del Pattern Composer (no cambia el motor flujo8)
- **Flags experimentales** (solo laboratorio): ver perfil `flujo8_experimental` abajo

> **Relacion con `prompts.dat`:** los overrides de perfil tienen **maxima prioridad** sobre `prompts.dat`. El orden completo es: override de perfil > `prompts.dat` > defaults hardcoded de Go. Usa `prompts.dat` (boton Prompts en "Mapa Fases → Tiers") para personalizar los defaults de toda la instalacion; usa los perfiles para variaciones por caso de uso (p.ej. un perfil tecnico, uno divulgativo, uno formal).

### Perfiles builtin relevantes

| ID | Rol |
|----|-----|
| `flujo8` | Baseline estable del workflow de 8 fases (produccion) |
| `direct` | Inferencia directa sin el ciclo F1–F8 completo |
| `flujo8_experimental` | Laboratorio: mismas fases conceptuales + flags (`ParallelReads`, `IterationReuse`, `SwarmAssist`, `EvalLoop`, …) y prompts mas sinteticos. **No** es el default |

**Promocion de mejoras:** medir con Compare `ab_profiles` (inference_id A/B) → Evaluator → Optimizator → implementar en Go + registrar en LAIM Framework / `library.dat`. No promover flags solo por wall-clock de F6 (incluye HITL).

**Calidad de salida LocalHost:** PresenterPost + `EnsureGroundedHostFacts` mantienen tablas FreeGB/TotalGB y reparan forma (cabeceras, celdas con prosa, fuga CoT). El camino rapido puede omitir algunos LLM (diagram/presenter/reprocess) cuando los hechos ya estan en `command_output`, sin saltarse PresenterPost.

### Crear un perfil

1. Desde **config → 4 → 2. Crear perfil**
2. Asigna un nombre y descripcion
3. Define los overrides de fase que necesites
4. Guarda el perfil

### Activar un perfil

1. En la lista de perfiles, haz clic en el boton **Activar** del perfil deseado
2. El perfil activo se usa en todas las sesiones de chat nuevas

El perfil **Default** / `flujo8` (sin overrides de laboratorio) siempre esta disponible y no puede eliminarse.

---

## 7. Flujos avanzados

Accede desde **config → 5. Flujos avanzados**.

> **Agent Box:** cada `agent_call` / `pattern_call` respeta el `runtime_profile` del agente invocado (§5.7). Combina perfiles restrictivos con autorizacion humana antes de comandos o efectos laterales.

Los flujos avanzados son pipelines estructurados y reproducibles que combinan:
- Llamadas a LLM con templates de prompt
- Invocaciones a agentes
- Ejecucion de comandos shell
- Peticiones HTTP a servicios externos
- Condiciones, bucles y paralelismo

### Tipos de elementos de un flujo

| Tipo | Que hace |
|---|---|
| `prompt` | Llamada al LLM con template y configuracion de modelo |
| `agent_call` | Invoca un agente registrado |
| `pattern_call` | Ejecuta un patrón/pipeline (`RunPipeline`): `pipeline_id` opcional o config inline (`pattern`, `agent_ids`, `max_iterations`). Si HITL pausa, escribe `{output, paused, run_id}` en el contexto sin colgar el flujo; reanudar con `POST …/agent-pipelines-resume` |
| `shell` | Ejecuta un comando shell (con timeout y consentimiento) |
| `http_request` | Peticion HTTP/HTTPS a un endpoint externo |
| `go_snippet` | Expresion Go ejecutada en el runtime del flujo |
| `condition` | Rama booleana (`if_true` / `if_false`) |
| `loop` | Itera sobre una coleccion o repite N veces |
| `parallel` | Ejecuta ramas concurrentemente |
| `transform` | Transforma datos (extract, map, format) |

### Modos de ejecucion

| Modo | Comportamiento |
|---|---|
| **sequential** | Fases en orden; el primer error para el flujo |
| **parallel** | Ejecucion por grafo (DAG): fases con Fork se ejecutan en goroutines paralelos |
| **conditional** | Fase activa solo si su condicion de activacion es verdadera |

### Editor visual de flujos

Desde **config → 5 → 3. Herramienta grafica** se abre el **editor visual** (LAIM FLOW DESIGNER) en una nueva pestana. Permite:
- Ver el grafo de fases con puertos multiples (entrada/salida success, failure, fork)
- Crear y mover conexiones arrastrando extremos entre fases (se persisten en `edges`)
- Anadir fases desconectadas (**+ Fase**) y **Podar** las que queden sin aristas
- Doble clic → DETAILS: seleccionar nodo/arista, mover destino, quitar o podar nodos huérfanos
- Guardar posiciones del canvas (`canvas_x` / `canvas_y`) junto al flujo
- La paleta drag-and-drop para crear elementos nuevos queda para una fase posterior

### Crear un flujo desde la interfaz

1. Desde **config → 5 → 2. Crear flujo avanzado**
2. El editor visual muestra un acordeon de fases (F1-F8)
3. Para cada fase puedes:
   - Anadirle subfases, tareas y elementos
   - Configurar el tipo de elemento y sus parametros
   - Definir transiciones (OnSuccess, Forks para paralelismo)
4. Guarda el flujo con nombre y descripcion

---

## 8. Share y Connect — Red y servicios IA

### 8.1 Arquitectura Share/Connect

LAIM puede funcionar en modo distribuido. Connect es un **router de servicios IA**, no un inventario SSH.

| Rol | Que hace |
|---|---|
| **Share (master)** | Servidor IA: Ollama, tiers, usuarios y el workflow. Expone `share_api` (por defecto TCP **4322**). |
| **Connect (cliente)** | Guarda **perfiles** de uno o varios Share. El **selector de ruta IA** elige Localhost (Ollama de este equipo) o un Share alcanzable. |

Cuando la ruta IA es un Share, chat, Direct, Suggestions, STT, editor y traduccion usan la GPU del master. Los comandos F6 de «este equipo» se ejecutan en el cliente. Los equipos de **laim remote** / Acceso remoto / Equipo destino viven en el `laim.dat` **local** y respetan el ACL del usuario.

**Ejemplo.** Windows GPU es Share (`share.enabled`, puerto 4322, firewall abierto). El Mac Silicon guarda un perfil Connect con el handoff. En el banner de Chat eliges ese Share: Direct y STT van al master; `df`/`Get-Partition` de «este equipo» corre en el Mac. Los Computers de `laim remote` siguen en el `laim.dat` del Mac.

### 8.2 Connect no es un bastion SSH

No proxifique `GET /remote/computers` ni las sesiones SSH al Share. Cada instalacion mantiene su propio inventario de equipos. Para alcanzar hosts por mesh use Headscale/Tailscale (§10); eso es independiente de la ruta IA.

### 8.3 Configurar el modo Share (master)

Desde **config → 6. Share** o acceso directo `share`:

- **Habilitar/deshabilitar** el servicio Share
- **Puerto de escucha** (por defecto **4322**)
- **Clave de conexion**: genera o regenera la clave compartida
- **Handoff para clientes**: los valores `user_connection` y `password_connection` que debes dar a cada cliente Connect
- **Regenerar credenciales** (pkg90, Share 0.5.66) cierra todas las sesiones Connect abiertas con la clave anterior e indica cuántas: cada cliente Connect deja de funcionar hasta que su administrador pegue los valores nuevos (§8.4.3).
- **Abrir regla de firewall**: configura automaticamente la regla TCP entrante en el firewall del SO

> Si el cliente Connect no puede conectar, comprueba que el firewall permite TCP entrante en el puerto 4322 (o el que hayas configurado). Para el panel completo de monitorizacion y reparacion (catalogo, hardening OS, boton Reparar), vea [11.3.0 Firewall y puertos LAIM](#1130-firewall-y-puertos-laim).

> **Las pruebas automáticas nunca tocan el firewall de este equipo** (Share 0.5.63). Bajo `go test`, activar Share (Config › Share, arranque de `share_api`) omite el paso del sistema operativo — ni `socketfilterfw`, ni `netsh`, ni `ufw`, ni el aviso de administrador de macOS — y responde «unsupported» con la pista *go test: el firewall del equipo no se modifica en las pruebas*. Solo una prueba viva explícita con `LAIM_TEST_ALLOW_REAL_INSTALL=1` aplica la regla real. LAIM instalado se comporta exactamente como se describe arriba.

### 8.4 Configurar el modo Connect (cliente)

Desde **config → 7. Connect** o `laim connect`:

- Cree **perfiles Share**: nombre, IP/puerto del master y handoff (`user_connection` / `password_connection`).
- **Prueba de conexion**: autentica el perfil del formulario (live). No registra este cliente en el Share Network Monitor.
- **No hay checkbox «Activar cliente Connect».** Guardar perfiles deja el nodo listo. La activacion es el **selector de ruta IA** (chat, Direct, Acceso remoto): Localhost o un Share que responda.

`IsConnectClient` = hay perfiles y este host **no** es master Share. Un master Share puede guardar perfiles Connect para el selector **sin** apagar `share_api`.

> Export/Import puede llevar ambas familias (Share + Connect) para copiarlas a maquinas distintas. El import solo apaga `enabled` del rol que no corresponde aqui.

#### 8.4.1 Perfiles Share y ruta IA

Puede haber **varios perfiles** (un Share por perfil): por ejemplo Windows GPU y Silicon GPU. Cada perfil guarda host, puerto y handoff.

| Accion | Donde |
|---|---|
| Crear / eliminar / editar perfiles | Config → Connect (admin) o `laim config` → Connect |
| Elegir Localhost o un Share | Banner de chat / Direct / Acceso remoto (`PUT /api/v1/ia-route`) |
| Elegirla desde el CLI | `laim chat --ruta-ia <localhost\|n\|nombre\|id>`, `/ruta` dentro de `laim chat`, `laim connect ruta [<n\|nombre\|id>]` |
| Probar el perfil del formulario | Config → Connect **Probar** (`POST /config/connect/test`) |
| API perfiles | `GET/POST /api/v1/config/connect/profiles`, `DELETE …/profiles/{id}` |

Comportamiento:

- El selector de ruta IA lista **siempre Localhost** y solo los Shares **alcanzables**. Si ninguno responde, el valor por defecto es Localhost.
- La eleccion (`Connect.IARoute`) aplica a chat, Direct, Suggestions, STT, editor y traduccion hasta que se cambie en cualquiera de esas pantallas.
- **CLI (Connect 0.4.72, chat 0.24.168):** `laim chat --ruta-ia <valor>` (alias `--ia-route`) fija la ruta antes de empezar el chat; dentro del chat `/ruta` (alias `/route`) lista las rutas numeradas y `/ruta <n|nombre|id>` la cambia, reiniciando el chat en la nueva ruta; `laim connect ruta [<valor>]` (alias `route`) hace lo mismo para scripts, sin la comprobacion rapida del sistema. El valor es el numero de la lista (1 = Localhost), `localhost`, el id de un perfil o su nombre (sin distinguir mayusculas). Las reglas son las de la web: `SetIARoute` sobre el mismo `Connect.IARoute` (el selector web muestra el cambio), solo se aceptan Shares alcanzables, y un nodo que no es cliente Connect recibe el mismo motivo que en la web («Share y Connect están activos a la vez…» / «configure al menos un perfil Share…»), en el idioma del CLI y con la lista de opciones validas. Permiso: una sesion iniciada, no admin (la web solo pide sesion web); `laim connect` sin `ruta` sigue siendo solo admin. Cada cambio registra un evento de auditoria (grupo `connect`, accion `update`, objetivo `ia_route`, canal `cli`). `laim chat` muestra «Ruta IA: <nombre — host:puerto>» al empezar, y `laim connect` / `laim config` → Connect muestran «Ruta IA:», «Perfiles Share:» y «Puerto share_api:» en el idioma del CLI.
- Heartbeat (8 s) y la inferencia usan el **slot de esa ruta**, no el perfil que este abierto en el formulario Config.
- No se puede eliminar el ultimo perfil. Un perfil nuevo copia el live como plantilla. Configuraciones antiguas (un solo host) migran a un perfil llamado `Share`.

En un nodo Connect, el menu de configuracion queda en modo protegido (`connect_only`). Un **administrador** puede abrir **Ver configuracion Connect** y usar el interruptor **LAIM Connect (esta sesion)**:

- **ON** (por defecto si hay perfiles y un Share responde): solo el menu Connect; el resto de `/config` responde 403.
- **OFF**: menu de config local completo (tiers, Sonido, usuarios…) para reconfigurar este LAIM. No se guarda en `laim.dat`.
- Los usuarios no-admin no ven el interruptor y siguen en modo protegido.

Si la ruta IA es un Share, la transcripcion de voz y el juez de firma vocal usan el tier Sonido del **master**. El enrollment (`voice.dat`) sigue en este equipo. Configure Sonido local como fallback si el master no esta disponible (TCP caido o ruta 404).

#### 8.4.2 Las credenciales Connect son de solo escritura (pkg88, Connect 0.4.73)

El cliente Connect nunca devuelve sus credenciales en claro por la API web:

- **`GET /api/v1/status`** (sin iniciar sesión), **`PUT /api/v1/ia-route`** y el cambio de perfil activo de un usuario no administrador muestran cada perfil Share solo como resumen: nombre, host, puerto, dirección, etiqueta, si responde y los indicadores `has_user_connection` / `has_password_connection` / `has_session`. Sin `user_connection`, `password_connection`, `id_session` ni la cuenta remota.
- **Configuración › Connect** (administrador) muestra `user_connection` como `••••••` más sus 4 últimos caracteres, y `password_connection` e `id_session` como `••••••`. Si deja un campo enmascarado como está (o vacío), se conserva el valor guardado; para cambiarlo, pegue el valor nuevo con 📥. La máscara nunca se guarda. Cada guardado queda en la auditoría con el nombre de las credenciales cambiadas (nunca sus valores).
- `laim connect` y `laim config` › Connect también muestran y piden estos valores enmascarados; pulse Intro para conservarlos.
- La pantalla de administración **Share** (Configuración › Share) sigue mostrando `user_connection` y `password_connection` en claro, porque desde ahí se copian a cada cliente Connect. Es solo para administradores, y cada vez que se abre queda en la auditoría (grupo Share, acción `credentials_view`).

Otras correcciones del mismo paquete:

- `GET /api/v1/local/sessions` solo lista sus propias consolas locales, y `DELETE` solo cierra las suyas (un administrador ve todas).
- Las rutas del plugin SentFileToRemote exigen iniciar sesión en LAIM.

**Después de actualizar, rote las credenciales.** Antes de pkg88, cualquier proceso local o cualquier usuario de LAIM podía leer el handoff y el `id_session` de un cliente Connect. Esos valores pueden haber acabado en informes de QA, capturas o logs. En cada master Share:

1. Abra Configuración › Share y pulse **Regenerar credenciales** (o, en `laim config` › Share, responda que sí a regenerar la clave). El `id_session` de todos los clientes deja de valer.
2. En cada cliente Connect, abra Configuración › Connect, elija cada perfil que apunta a ese Share, pegue el `user_connection` y el `password_connection` nuevos con 📥 y pulse **Guardar y probar conexión**.

#### 8.4.3 Pegar el handoff y mantener el canal (pkg90, Connect 0.4.74)

**Pegar.** Configuración › Connect limpia lo que pega antes de guardar: quita espacios, tabuladores y saltos de línea (también en medio del valor, como cuando un chat o un PDF lo parte), comillas alrededor y las etiquetas `user_connection:` / `password_connection:`. También puede pegar la **clave de conexión completa** (44 caracteres, las dos mitades juntas) en cualquiera de los dos campos: LAIM la divide. Si los dos valores están intercambiados, LAIM los coloca en su sitio (la clave siempre termina en `=`, que es el final de `user_connection`). Si los valores no pueden formar una clave Share (demasiado cortos, caracteres que una clave nunca tiene), no se guarda y el mensaje dice qué volver a copiar. Un valor de **otro** Share no se puede detectar sin conectar: lo indica **Guardar y probar conexión**.

**Clave equivocada o antigua.** Cuando el Share no puede descifrar una petición (credenciales regeneradas en el Share, valores intercambiados o copiados de otro Share), el cliente ahora lo dice en el idioma de la interfaz — «El Share no acepta esta clave de conexión…» — y qué hacer (copiar de nuevo los dos valores en Configuración › Share, pegarlos con 📥, **Guardar y probar conexión**). El aviso de chat/Directo lo trata como un problema de credenciales, no como una caída de red.

**Recuperación automática.** Si el Share ya no conoce la sesión de este cliente (caducada, cerrada por el administrador del Share o tras una rotación con la misma clave), el cliente vuelve a autenticarse **una vez** y reenvía la petición, así que el heartbeat y la siguiente petición se recuperan sin que el usuario haga nada. Un Share que sigue rechazando se informa, nunca se reintenta en bucle. La sesión nueva se guarda en el perfil que usó el cliente (la ruta IA), no en el perfil abierto en el formulario de Configuración.

**Disponibilidad en el selector.** Los selectores del chat web, Directo y Acceso remoto y la CLI (`--ia-route`, `/route`, `laim connect route`) muestran Localhost y los Share que responden. Cada dirección `share_api` se sondea como mucho una vez cada 3 s (una sola conexión TCP para todas las pestañas y sondeos), y un Share que respondió sigue en la lista 8 s después de un sondeo fallido, para que una sola conexión perdida no cambie la ruta a Localhost entre dos turnos. Un Share realmente caído desaparece pasado ese margen: la ruta muestra Localhost y `GET /api/v1/status` devuelve `ia_route_unavailable` con un aviso («El Share «silicon» no responde…»). Su elección se conserva y vuelve sola cuando el Share responde de nuevo.

**A mitad de turno.** Si el Share cae durante una respuesta, el cliente reintenta el stream (turno reanudable) y, si no lo alcanza, termina con «se perdió la conexión con Share… — vuelve a intentarlo (el turno no se ha repetido en Localhost)». Un turno nunca pasa en silencio a los modelos locales.

### 8.5 Seguridad de claves

| Clave | Ambito | Donde vive |
|---|---|---|
| `master_key_cipher` | Solo local — cifra `laim.dat` y sesiones | `identity.dat` de cada equipo (cifrado con clave global de identidad) |
| `connection_key_cipher` | Compartida — cifra mensajes Share conectado Connect | `laim.dat` del master |

Para rotar la clave compartida: **share → Regenerar clave**. Despues actualiza cada cliente Connect con el nuevo handoff.

### 8.6 Sesiones remotas

Cuando un cliente Connect se autentica contra un Share, se crea una sesion de canal **remote** en el registro de sesiones de **ese** master (`laim.sessions`). Los comandos F6 de estado local se ejecutan en el equipo del cliente (no en el master).

### 8.7 LAIM Share Network Monitor

El widget del master muestra los clientes Connect que **estan usando este Share como ruta IA**, no todos los que pueden alcanzar el puerto 4322.

| Regla | Detalle |
|---|---|
| Heartbeat | Cada **8 s** solo hacia el Share de la ruta IA |
| TTL | El cliente desaparece a los **12 s** sin pulso |
| No registra presencia | Auth, «Probar conexion», probe TCP del selector |
| Etiqueta del master | SO real del equipo (`MAC` / `LINUX` / `WINDOWS`), no un WINDOWS fijo |

Al cambiar la ruta IA a Localhost u otro Share, el heartbeat anterior se detiene y este cliente deja el monitor del Share que ya no usa.

---

## 9. Gestion de equipos remotos

Accede desde **config → 8. Gestion de equipos remotos**.

### 9.1 Equipos

Desde **config → 8 → 1. Equipos** puedes:
- Ver la lista de equipos registrados
- Crear, editar y eliminar equipos

| Campo | Descripcion |
|---|---|
| `name` | Nombre unico del equipo (insensible a mayusculas) |
| `description` | Descripcion libre |
| `host` | Hostname o FQDN (primera opcion de conexion por DNS) |
| `host_ip` | IP directa (fallback cuando DNS falla) |
| `port` | Puerto SSH (por defecto 22) |
| `remote_user` | Usuario SSH en el equipo remoto |
| Contrasena o clave RSA | Credenciales SSH (cifradas en `laim.dat`). Pegue el PEM **privado** (ver [9.1.1](#911-clave-ssh-privada-en-laim-publica-en-el-servidor)). |
| `protocol` | `ssh` (por defecto) o `winrm` |
| `connection_mode` | `direct` o `tailscale` |
| `tailscale_ip` | IP de la red mesh (si el equipo esta en Headscale) |

### 9.1.1 Clave SSH: privada en LAIM, publica en el servidor

LAIM autentica por **clave publica** (o por contrasena). El campo RSA del equipo debe ser el PEM **privado**. En el servidor, `sshd` **no** lee `~/.ssh/id_rsa.pub`: solo `~/.ssh/authorized_keys` del `remote_user`.

**Error tipico:** la pestana SSH se cierra con `unable to authenticate` / `publickey`. LAIM si envio la privada; esa clave **no** esta en `authorized_keys` de esa cuenta.

#### En LAIM (cliente)

1. En el equipo que abre la sesion, tome el PEM privado (`id_rsa` o `id_ed25519`, **sin** `.pub`): bloque `BEGIN OPENSSH PRIVATE KEY` o `BEGIN RSA PRIVATE KEY`.
2. Config → Equipos → editar el equipo → pegue la clave privada. No pegue la linea `ssh-rsa …` del `.pub`.
3. `remote_user` debe ser la cuenta del servidor (p. ej. `ansible`), no la cuenta con la que hace `sudo`.

#### En el servidor (imprescindible)

La linea del fichero `.pub` (una sola linea `ssh-rsa` / `ssh-ed25519` …) debe anadirse a `/home/<remote_user>/.ssh/authorized_keys`.

Copiar solo el fichero a `/home/<remote_user>/.ssh/id_rsa.pub` **no** autoriza el login.

Opcion A — desde el equipo que tiene el par de claves, si el usuario remoto acepta contrasena o ya hay otra clave:

```bash
ssh-copy-id -i ~/.ssh/id_rsa.pub usuario@servidor
```

Opcion B — saltando por un usuario con sudo (p. ej. `admin` en Linux), cuando el `.pub` ya esta en el servidor. Sustituya `ansible`, `admin` y las rutas por el `remote_user` y el administrador del host:

```bash
ssh admin@servidor 'sudo bash -c "
  cat /home/ansible/.ssh/id_rsa.pub >> /home/ansible/.ssh/authorized_keys
  chown ansible:ansible /home/ansible/.ssh/id_rsa.pub /home/ansible/.ssh/authorized_keys
  chmod 700 /home/ansible/.ssh
  chmod 600 /home/ansible/.ssh/authorized_keys /home/ansible/.ssh/id_rsa.pub
"'
```

Eso **anade** la linea; no borre otras claves ya presentes en `authorized_keys`.

#### Permisos (`StrictModes`)

| Ruta | Modo | Propietario |
|------|------|-------------|
| `/home/<user>` | `750` o `700` (no escribible por others) | el usuario remoto |
| `~/.ssh` | `700` | el usuario remoto |
| `~/.ssh/authorized_keys` | `600` | el usuario remoto |
| `~/.ssh/id_rsa.pub` (si existe) | `644` o `600`, propietario el usuario | no lo usa sshd para entrar |

Comprobacion: `ssh-keygen -lf` sobre el `.pub` y sobre `authorized_keys` deben mostrar la **misma huella SHA256** para esa clave.

### 9.1.2 Credenciales guardadas: el administrador las introduce una sola vez (0.58.30)

- El administrador registra la contraseña SSH o la clave privada de un equipo **una sola vez** (**config → 8 → 1** o Config > Equipos en la web). Se guardan cifradas (AES-256-GCM con la clave maestra de la instalación en `laim.dat`).
- Todos los usuarios de LAIM con acceso a ese equipo (9.4) se conectan con ellas de forma transparente — terminal, chat, Suggestions y despliegue de herramientas. Los usuarios nunca necesitan conocerlas.
- Si cambian en el equipo, el administrador las actualiza una vez y el cambio vale para todos.
- LAIM nunca pide a un usuario las credenciales de un equipo. El terminal web solo las pide a un **administrador**, y solo cuando el equipo rechazó de verdad la contraseña guardada (se llegó a probar un método) o el equipo no tiene ninguna guardada; un usuario no administrador ve "SSH rechazó las credenciales guardadas de este equipo. Solo un administrador puede actualizarlas (Config > Equipos)".
- Si LAIM no puede cargar las credenciales guardadas (fallo al descifrar), muestra: **"LAIM no pudo cargar las credenciales guardadas de este equipo; un administrador debe revisarlas"** y registra `credential_load_failed computer=… kind=password|rsa_key` en `console.log` (nunca el secreto). Revise el equipo en Config > Equipos e introduzca de nuevo la credencial.
- `attempted methods [none]` significa que el equipo no aceptó **ninguno** de los métodos que LAIM ofreció — no se llegó a probar ninguna credencial, así que no es una contraseña incorrecta y no se pide a nadie. `console.log` muestra `auth_no_method_accepted computer=… offered=password,keyboard-interactive` (o `publickey`): revise los métodos que permite el `sshd` del equipo (`PasswordAuthentication`, `PubkeyAuthentication`, bloques `Match`) o guarde la credencial correspondiente.

### 9.2 Resolución de host SSH: primero la red local, Headscale con permiso (pkg39)

LAIM llega igual a todos los equipos:

1. **Primero la red local.**
   - `Host`, tal cual si es una IP o si su nombre resuelve.
   - `HostIP` si el nombre no resuelve.
   - LAIM espera 3 segundos a que la red local responda.
2. **Headscale como alternativa.** Si la red local no responde y el equipo tiene `TailscaleIP`, LAIM pregunta: «No se llega a «server1» por la red local (…). ¿Intento la conexión por Headscale (100.x)?»
   - **Sí:** el permiso se recuerda **para ese equipo y ese usuario durante una hora**. Se olvida cuando la red local vuelve a responder, así que el siguiente fallo vuelve a preguntar.
   - **No:** no se intenta nada más.
3. **Sin nadie a quien preguntar** (tareas programadas, llamadas a la API como las de University): la malla solo se usa si quien llama lo autorizó antes (`allow_mesh: true` en la petición). Si no, la conexión falla con un mensaje que dice qué se intentó y cómo autorizarlo.
4. **Un equipo cuya única ruta es la malla** (`Host` vacío o igual a su IP `100.x`) la usa sin preguntar.

Otras reglas:
- `ConnectionMode="tailscale"`, que LAIM pone al unir un equipo a Headscale, solo indica que el equipo tiene ruta de malla. Ya no se salta la red local.
- Un inicio de sesión rechazado en la red local nunca lleva a probar la malla: solo un fallo de red.
- `console.log` anota la ruta usada: `connected … route=lan|mesh addr=…`, `mesh_fallback needs_consent …`, `mesh_fallback use …`.

**Ejemplo.** `server1` tiene `Host=server1.example.com` y `TailscaleIP=100.64.0.4`, y Tailscale está parado en el equipo de LAIM. LAIM conecta a `192.0.2.198:22` (red local). Antes de pkg39 solo probaba `100.64.0.4` y fallaba con `i/o timeout`.

### 9.3 Grupos de equipos

Desde **config → 8 → 2. Grupos de equipos**:
- Crea grupos para organizar los equipos (por departamento, SO, funcion, etc.)
- Un equipo puede pertenecer a varios grupos

### 9.4 Acceso de usuarios a equipos

Desde **config → 8 → 3. Acceso de usuarios**:
- Los admins ven todos los equipos por defecto
- Para los usuarios con rol `user`, debes conceder explicitamente acceso a cada equipo o grupo
- El usuario solo vera en `remote` los equipos que le hayas asignado

### 9.5 Chat con un equipo remoto

Una vez que has configurado los equipos y sus accesos, los usuarios pueden usar el **selector de equipo en el chat** para dirigir las preguntas de sistema hacia un equipo remoto especifico (ver manual de usuario, seccion 6).

---

## 10. Headscale — Red mesh WireGuard

Accede desde **config → 8 → 8. Red mesh WireGuard (Headscale)**.

Headscale es un servidor de control WireGuard open-source que permite crear una **red privada segura entre equipos**, util cuando los equipos no estan en la misma red local.

### 10.1 Estado del servidor Headscale

Desde **config → 8 → 8 → 1. Estado del servidor**:
- Ver si Headscale esta instalado y en que version
- Descargar el binario de Headscale desde GitHub Releases
- Configurar la URL del servidor (`https://mi-laim.empresa.com:8080`)
- Arrancar o detener el servicio Headscale
- Ver y gestionar la API key

### 10.2 Nodos conectados

Desde **config → 8 → 8 → 2. Ver nodos conectados**:
- Lista todos los equipos registrados en la red mesh
- Muestra la IP de Tailscale (100.x.x.x) de cada nodo
- Indicador de estado **online**: 🟢 (activo) / ⚪ (inactivo). Combina el campo `online` de Headscale con la recencia de `last_seen` (visto en los ultimos ~3 minutos)
- El nodo de **este equipo** (donde corre Headscale) se marca siempre online cuando su IP Tailscale coincide con la local; en la UI aparece la etiqueta `(este equipo)`
- Cada nodo muestra la marca de tiempo **visto:** (`last_seen`) para diagnostico
- Tras **Activar** o **Desactivar subnet routing**, la lista de nodos se refresca automaticamente
- Opcion de sincronizar las IPs de Tailscale en los equipos registrados

> **Headscale v0.29+:** el campo `last_seen` puede llegar como string RFC3339 o como objeto protobuf `{seconds, nanos}`. LAIM acepta ambos formatos.

### 10.3 Registrar un equipo en la red mesh

Hay **dos caminos**:

**A — Cliente LAIM (recomendado).** En el equipo que se une (p. ej. `mac1.example.com`): Config → Equipos → Red mesh → **Cliente Tailscale (este equipo)**.

1. LAIM comprueba si el cliente Tailscale existe (mac Intel / Apple Silicon, Linux o Windows), si corre como servicio y si ya es funcional. El probe es de **unos segundos** (`pgrep` / `tailscale status`, sin `brew services list`) para que el menú Config no se quede congelado.
2. Si no está instalado, **Instalar** abre un **modal de progreso** (pasos: detectar, descargar, instalador, servicio, verificar) con el log de lo que ejecuta LAIM. Recetas oficiales ([Install Tailscale](https://tailscale.com/docs/install)): Linux `install.sh` + `systemd`; macOS paquete **`.pkg` standalone** (Homebrew solo si falla el pkg); Windows MSI silencioso (`TS_UNATTENDEDMODE=always`). El interruptor «Ejecutar como servicio» **no** cambia a `brew install`.
3. Selector **Ejecutar como servicio** (solo preferencia) y controles ▶️ Ejecutar / ⏹ Parar / 🔄 Reiniciar.
4. Indique la URL del coordinador `http://<host-laim>:4324` (p. ej. `http://server1.example.com:4324`) y **Solicitar unirse**. Otro modal muestra cifrado `KeyMeshEnrollment` y el POST a `mesh_api`. *Connection refused* en el 4324 significa que en el coordinador no corre `mesh_api`: hace falta `laim web` + interruptor **Este LAIM es el coordinador de la malla** (Headscale en `:8080` no abre este puerto). El cuerpo va cifrado con **`KeyMeshEnrollment`** (clave global del major; **no** es `KeyInternalTranslator` ni la clave Share). El **mismo equipo coordinador** puede ser también cliente/nodo (`tailscale up` contra su Headscale). No pulse **Solicitar unirse** otra vez si ya hay una solicitud *aprobada*: reutiliza el mismo `request_id`. Si se creó otra fila *solicitada*, **Aplicar unión** recupera la hermana aprobada del mismo host.
5. En el LAIM coordinador: **Solicitudes de unión** — estado *Solicitado* y botones ✅ aprobar / ❌ rechazar / ⏸ suspender / ▶️ reanudar. Tras decidir, el panel muestra el resultado y **instrucciones para el cliente** (qué pulsar en el otro LAIM). No copie claves preauth por chat: el cliente las obtiene cifradas al aplicar.
   **Aprobación sellada (pkg90, Remote 0.17.9):** `KeyMeshEnrollment` está en todos los binarios LAIM, así que solo oculta el tráfico. Cada solicitud de unión lleva ahora su propia clave pública X25519 (`enroll_pub`; la privada se queda en el cliente, cifrada con su clave maestra) y el coordinador sella la clave preauth de Headscale con ella (ECDH + HKDF-SHA256 + AES-256-GCM). Solo el equipo que la pidió puede abrir la aprobación; quien la capture en la LAN o conozca el id de la solicitud, no. Los dos paneles muestran una **huella de la clave** (`abcd-1234-…`): antes de aprobar, pida al usuario del cliente que lea la de su pantalla y compruebe que coincide con la de la solicitud. Una solicitud de un LAIM antiguo muestra «Solicitud de un LAIM antiguo sin clave de unión»: sigue recibiendo la clave en claro hasta el **31-01-2027**; después se le pide actualizar LAIM. Los nodos ya unidos no se ven afectados.
6. De vuelta en el cliente: **Actualizar estado** muestra la fase de enrollment **y** el plano de datos (dirección Tailscale `100.x` y backend). El ACK a `mesh_api` **no** es lo mismo que aparecer en Headscale. **Aplicar unión** si hay clave pendiente ejecuta `tailscale up`; si el daemon ya apuntaba a otro login-server, reintenta con `--force-reauth` y la preauth. Si la solicitud ya está *validada*, **no** relanza el up: comprueba si hay IP `100.x` y muestra el estado de la conexión. Solo hay unión real con esa IP. Si no hay dirección, pida **Aprobar de nuevo** en el coordinador (clave nueva) y vuelva a Aplicar. En el coordinador: **Headscale en marcha** → **Nodos conectados → Actualizar**. Luego **Sincronizar IPs con equipos LAIM**. Si el servidor suspende, el cliente muestra **Interrumpida temporalmente** y el mismo botón hace `tailscale down`.

**B — Preauth clásica (manual).** Desde **Registrar equipo**: genera una clave 24 h y ejecuta `tailscale up --login-server=… --authkey=…` en el destino. Sigue siendo válida para nodos sin LAIM.

El puerto **`mesh_api` 4324/tcp** es LAN (`0.0.0.0`), distinto de Share **4322**, web **4320/4321** y Headscale **8080**. Abra el firewall (`LAIM mesh_api`) con Reparar en Internal › Local cuando el coordinador esté activo.

### 10.4 Conectar equipos via Headscale

Una vez registrado, **Sincronizar IPs** escribe `tailscale_ip` (100.x). SSH usa esa dirección si `connection_mode=tailscale` **o** si **este** host ya está en la malla. Marcar `connection_mode=tailscale` sigue siendo lo más claro en fichas permanentes.

LAIM usara automaticamente esta IP cuando conecte al equipo, sin necesidad de que los equipos esten en la misma red local.

**Nodos conectados** = `headscale nodes list` (plano WireGuard, IP `100.x`). **No** es el ACK de `mesh_api` (`validated`). Sin `100.x` el nodo no esta en la malla: **Aprobar de nuevo** y en el cliente **Aplicar union**.

El mismo cliente Tailscale oficial sirve para Headscale (LAIM) o para el SaaS de Tailscale Inc. No mezcle ambos `login-server` en el mismo daemon. Detalle de planos de control/datos, NAT/DERP y equipos sin LAIM: Ayuda › **Red Mesh WireGuard con Headscale**.

**Ejemplo.** Ficha aún `direct` + `tailscale_ip` relleno + este Mac con `100.x` → chat y Suggestions SSH por malla (University internet-only).

### 10.5 Windows OpenSSH y malla

En el Windows **destino**: Ayuda › Configurar Windows › **Activar automaticamente usando LAIM** (UAC). Instala OpenSSH Server, arranca `sshd`, firewall TCP 22 perfil **Any**, y muestra host/IP/usuario para registrarlo en otro LAIM. Cuentas Administrators: `C:\ProgramData\ssh\administrators_authorized_keys`.

Para llegar desde otra red: una el Windows a Headscale (cliente LAIM o `tailscale up` sin LAIM). Si **este** host ya tiene `100.x`, SSH usa `tailscale_ip` aunque el Computer siga en `direct`. Manual: *Configurar Windows para laim remote*.

### 10.6 Chat y Suggestions sobre SSH

Con `tailscale_ip` sincronizada, el **selector de equipo del chat** y **`laim remote`** usan SSH a `100.x` si el modo es `tailscale` **o** este host ya está en la malla. Suggestions reutiliza los orquestadores del chat (`remotesystem`, inventario). Python solo pinta Markdown. Equipos **sin** LAIM: mismo registro SSH; la malla solo aporta el camino.

**Ejemplo.** Equipo destino `server1`, «¿cuánto disco libre?»: F6 corre en Ubuntu por SSH, no en el Mac que abre el chat. La ruta IA (Localhost vs Share) es independiente.

---

## 11. Internal — Configuracion avanzada

Accede desde **config → 9. Internal**.

### 11.0a Gestor de colas

Pagina a pantalla completa (**Internal › Gestor de colas**). Carga los trabajos al abrirla; **⟳ Actualizar** los vuelve a pedir.

- **Quien ve que:** el administrador ve y gestiona todos los trabajos: los de todos los usuarios y los del sistema (instalacion, actualizaciones, programador, descargas encadenadas; no tienen sesion web). Un usuario ve solo los suyos, desde cualquiera de sus sesiones. El **📋 Listado de trabajos (N)** del chat muestra siempre solo los tuyos.
- **Cancelar:** un trabajo en cola o esperando respuesta lo puede cancelar siempre su dueno o el administrador. Uno en ejecucion solo se cancela si su trabajo se detiene de verdad (chat, Direct, teacher, sugerencias remotas, comprobar actualizacion, descarga de parche). Una descarga de modelo, una tarea programada, la instalacion de Ollama o la aplicacion de un parche en marcha terminan su paso; para parar la cola, usa la pausa global. Un trabajo cancelado sigue cancelado aunque su ejecucion termine despues.
- **Orden y prioridad:** prioridad 1 (alta), 2 (media), 3 (baja); despues, el mas antiguo. Un trabajo nuevo de prioridad 1 es el siguiente, pero nunca detiene el que esta en marcha. El dueno (los suyos) o el administrador (cualquiera) pueden subir o bajar la prioridad de un trabajo en cola: `POST /api/v1/queue/jobs/{id}/priority` con `{"priority": 1}`. El valor explicito gana al del tipo (teacher 3, sugerencias remotas 1).
- **Pausa global (administrador):** `PUT /api/v1/queue/state` con `{"state": "paused", "reason": "…"}` impide que empiecen trabajos nuevos; los que estan en marcha terminan su paso (estado «pausing» y despues «paused»). `{"state": "running"}` la reanuda. Lo que se encola mientras tanto, tambien tareas programadas, instalacion y actualizaciones, espera en la cola; no se descarta nada. La pausa se conserva al reiniciar: si el administrador la dejo en pausa, vuelve en pausa; si no, arranca. Cualquier usuario consulta el estado con `GET /api/v1/queue/state`.
- **Reintentar:** una descarga de modelo, un teacher, unas sugerencias remotas, una tarea programada, la instalacion de Ollama, una comprobacion de actualizacion o una descarga de parche fallidos o cancelados los puede volver a encolar su dueno o el administrador: `POST /api/v1/queue/jobs/{id}/retry`. Chat y Direct no se reintentan (se vuelve a enviar el mensaje) y la aplicacion de un parche nunca se repite desde la cola. No hay reintento automatico.
- **Ficha:** `GET /api/v1/queue/jobs/{id}` devuelve el trabajo con su origen (chat, direct, ui, scheduler, install, update, connect, agent:…), trabajo padre, numero de intento, ultimo progreso y linea de tiempo (en cola, iniciado, esperando respuesta, reanudado, cambios de prioridad, reintentos, terminado, fallido con su error, cancelado y por quien). `GET /api/v1/queue/overview` devuelve los recuentos por estado, tipo, grupo de recursos y origen, y un texto resumen.
- **Que se puede encolar por la API:** `POST /api/v1/queue/submit` admite chat, direct, teacher y sugerencias remotas para cualquier usuario, y descargas de modelos para el administrador. Instalacion, actualizaciones, tareas programadas y auto-correccion las encola LAIM (sus pantallas y tickers); enviarlas devuelve 403.
- **API:** `GET /api/v1/queue/jobs` lista tus trabajos; `?scope=all` (administrador) lista todos. La respuesta nunca incluye ids de sesion. El flujo de eventos (`/api/v1/queue/events`) envia a cada uno solo lo que puede ver: los tokens de un trabajo en marcha van solo a su sesion.
- **Auditoria:** encolar, cancelar, responder, reintentar, cambiar la prioridad, pausar y reanudar quedan en **Audit Log**, grupo **Cola de trabajos**.

### 11.0 Tareas programadas

Pagina a pantalla completa (**Configuracion › Asistente de configuracion › Interno › 7. Tareas programadas 🗓️**), justo debajo del Gestor de colas. Sustituye al antiguo «Programador de tareas» (pkg38). El acceso directo «Tareas programadas» del Asistente abre la misma pagina y su **Volver** regresa al Asistente; la barra de titulo es la ruta de navegacion clicable.

Un solo programador: toda accion con hora de LAIM es una tarea de `scheduler.dat` (cifrado, con bloqueo de fichero y escritura atomica; un fichero por instalacion) y solo se ejecuta por la cola, con la prioridad de su origen.

- **Quien ve que (D1):** cada tarea pertenece al usuario que la creo. Un usuario ve y gestiona solo las suyas (en la pagina, la API, el chat y el CLI). Un administrador ve el calendario de todos, con el propietario en cada tarea, y puede actuar sobre cualquiera. Las tareas del sistema y las del sistema operativo son solo de administradores.
- **Mes:** selectores de **Ano** y **Mes** (por defecto, el mes actual), **Hoy**, **Nueva tarea** y **Actualizar**. Columnas de lunes a domingo; el dia de hoy marcado, fines de semana sombreados y los dias de otros meses atenuados. Cada ejecucion es una ficha con un punto de color, la hora en **24 horas** (nunca am/pm), un icono (💬 prompt, 🔀 flujo, 🤖 agente, 📦 trabajo, ⚙️ sistema) y el titulo; caben 4 por dia y luego «+N mas». Una tarea que se repite mas de 4 veces en un dia sale como una franja «Titulo ×N». Las fichas pasadas toman el color del registro (correcta, fallida, no realizada, en pausa, en cola, en curso, cancelada); las futuras, el de la tarea (activa o en pausa). Todos los colores son variables del tema (`--crt-cal-*`) en los cinco temas, con contraste WCAG AA.
- **Clic en un dia:** si esta vacio abre **Nueva tarea** con esa fecha; si tiene tareas, la lista del dia (tambien las de «+N mas»).
- **Detalle de una tarea:** resumen, propietario, origen, que ejecuta, programacion en palabras, zona horaria, proximas 5 ejecuciones, prioridad, informe, privilegios avanzados, estado y las 10 ultimas ejecuciones (estado, retraso, trabajo de la cola, informe). Acciones: **Ejecutar ahora** (a la cola con la prioridad de su origen), **Pausar / Reanudar**, **Editar**, **Clonar** (otra fecha y hora, por ejemplo para corregir los privilegios), **Borrar** (con confirmacion; el historial se conserva) y **Ver en Gestor de colas**.
- **Editor:** titulo, resumen corto (sale en los avisos), que ejecuta (un prompt de chat, un flujo avanzado o un agente, elegidos entre los que existen), se repite (una vez, cada dia, cada semana, cada mes), hora `HH:MM` de 24 horas, fecha, dia de la semana o del mes, zona horaria IANA (vacia = la de este equipo), **informe tras cada ejecucion** y **privilegios avanzados**. La prioridad no se pide: la da el origen (pagina, chat, CLI y Asesor P2; Sugerencias por SSH P1; informes y tareas del sistema P3). El Core valida en el idioma del usuario (una hora «9pm» o «25:00», un dia 32, una fecha o una zona invalidas, falta el prompt, el flujo o el agente). Apagar o reiniciar el ordenador nunca es una tarea programada (regla CMD-FBD-010).
- **Pausa:** una tarea en pausa no se ejecuta; al reanudarla espera a su siguiente hora (lo pausado no se recupera).
- **Privilegios avanzados (D17):** si al disenar la tarea das tu consentimiento, cuando un paso desatendido pide autorizacion LAIM la concede en tu nombre con tus privilegios (auditado). Sin ese consentimiento el paso hace fallar la ejecucion y llega «Tarea programada sin privilegios», desde donde puedes clonarla.
- **Avisos:** al crear una tarea y en cada ejecucion (correcta, fallida o no realizada) reciben un aviso el propietario y los administradores, en el idioma del propietario. Si la tarea tiene informe, un trabajo hijo P3 lo escribe cifrado (`reports/scheduler_<fecha>_<id>.md.enc`, 0600) y llega «Informe disponible»; en **Informes › Tareas programadas** cada usuario ve solo los suyos.
- **Ejecuciones no realizadas:** si el equipo estaba apagado o dormido o LAIM parado, una ejecucion que no ocurre a su hora ni en los 60 minutos siguientes queda como «no realizada» y se avisa; nunca se recupera.
- **LAIM parado:** el binario `scheduler`, junto a `laim`, se instala solo al arrancar `laim web` (crontab en Linux, LaunchAgent en macOS, schtasks en Windows, en un bloque propio que nunca toca otras lineas). Cada hora revisa las tareas y, a su minuto, despierta a LAIM: si `laim web` responde se lo encarga; si no, ejecuta las tareas del sistema que tocan y, si hay una tarea de usuario pendiente, arranca `laim worker`, que ejecuta la tarea, deja registro, avisos e informe, y termina. Al arrancar `laim web` todo eso aparece en la pagina. `laim scheduler uninstall` la retira y se respeta; `laim scheduler status` y `laim version` muestran su estado.
- **Tareas del sistema (D13, solo administradores):** **Comprobacion de actualizaciones** (cada 15 minutos), **Rotacion de logs** (cada 6 horas) y **Sesiones caducadas** (cada noche a las 04:00). No se pueden borrar; si pausar, reanudar, reprogramar y ejecutar ahora. Corren a su hora tambien con LAIM parado (pkg100): tienen despertador del sistema como cualquier tarea y, si `laim web` no responde, el propio binario `scheduler` las ejecuta en su proceso, rapido y sin arrancar `laim worker` (la comprobacion de actualizaciones solo consulta el canal cuando toca segun su intervalo, con 10 s de limite y sin reintentos: reintenta el siguiente turno de 15 minutos). Con `laim web` arrancado van por la cola, como antes; un turno nunca se ejecuta dos veces. Nunca quedan como «no realizadas» y solo avisan si fallan.
- **Agentes programados:** un agente con automatizacion «programada» y su cron activo tiene su tarea «agent-<id>». Se aceptan `M H * * *`, `M H * * D`, `M H * * MON-FRI` y `M H D * *`; otro cron se rechaza al guardar el agente.
- **Tareas del sistema operativo (solo administradores, D12):** casilla **Mostrar tareas del sistema** y selector de equipo (Localhost o un equipo remoto). Las entradas del crontab o de schtasks salen como franjas (nunca el bloque propio de LAIM). Su detalle permite **Ejecutar**, **Editar**, **Borrar** y **Anadir tarea del sistema**: primero se muestra la diferencia y LAIM emite una confirmacion de un solo uso (10 minutos, mismo usuario); al aplicar se hace antes una copia del crontab o de la entrada de schtasks y no se escribe si el crontab cambio entretanto o su lectura llego cortada. En Windows solo tareas diarias o semanales, con su hora real.
- **Consentimiento de los comandos de riesgo (pkg62):** antes del plan, LAIM lista cada comando de riesgo — el de la tarea y el propio registro (crontab / schtasks, CMD-RSK-023) — con su regla y su motivo en el idioma del usuario en el dialogo **«Consentimiento de comandos de riesgo»**; sin ese consentimiento no hay plan. El consentimiento del comando se guarda (equipo, comando exacto, regla, quien, cuando) y se audita (`scheduler:risky_consent`); un comando editado u otro equipo vuelven a preguntar. Una ejecucion programada de un comando de riesgo solo corre con un consentimiento guardado que coincida; si no, se rechaza y se registra (`scheduler:risky_refused`) — nunca pregunta. **Ejecutar** con el usuario delante acepta ademas su exencion verificada o una confirmacion explicita de esa ejecucion (auditada, no guardada). Lo prohibido se rechaza siempre.
- **Desde el chat:** «¿que tareas tengo manana?», «calendario de noviembre», «¿se ejecuto la tarea copia?», «pausa la tarea copia», «muevela a las 06:00», «programa una comprobacion del disco cada lunes a las 09:00». Antes de cambiar o crear, LAIM pregunta lo que falta (nunca usa valores de ejemplo; «a las 5» pregunta 05:00 o 17:00), lee la tarea y pide un si.
- **CLI:** `laim scheduler list|show|calendar|history|create|edit|pause|resume|run|delete` (las propias; un administrador, todas) e `install|uninstall|status` (administrador).
- **Descargas de modelos programadas:** el catalogo y el Asesor (**Programar**) crean una tarea de una vez `Descarga del modelo: {modelo}` (`invoke_kind=job`, pool network), recomendada en horas valle.
- **API:** `GET /api/v1/scheduler/month?year=&month=&lang=&system=1&computer_id=`, `POST /api/v1/scheduler/task`, `GET|PUT|DELETE /api/v1/scheduler/task/{id}`, `POST /api/v1/scheduler/task/{id}/run|pause|resume|clone`, `GET /api/v1/scheduler/os`, `POST /api/v1/scheduler/os/install|uninstall` (administrador) y `POST /api/v1/scheduler/request` (agente: `history`, `draft`, `system_apply`, `system_run`…). Toda modificacion queda en **Audit Log**.

**Ejemplo.** En el chat: «programa una comprobacion del espacio libre cada lunes a las 9». LAIM pregunta «¿A las 09:00 o a las 21:00?», si quieres informe y si puede usar privilegios avanzados; lee la tarea («Cada lunes a las 09:00, P2») y, con tu si, la crea y te avisa. Aparece en el calendario de todos los lunes; un administrador la ve con tu nombre.

### 11.1 Import/Export

Desde **config → 9 → 1. Import/Export**:

**Export**: exporta la configuracion a `config/laim_config_clear.json` sin secretos locales.
- Selecciona que familias exportar (ver tabla). Incluye Share, Connect (con perfiles), Headscale, Direct, tareas programadas, alertas MRTG y catalogo DevOps.
- Las contrasenas de usuario y las credenciales SSH de equipos se exportan vacias.
- **Share:** solo los ajustes. El handoff (`user_connection` + `password_connection`, es decir, la clave de conexión completa) y `connection_key_cipher` **no** se exportan (pkg90): `laim_config_clear.json` es un fichero en claro (0600). El import conserva la clave propia de este Share.
- **Connect:** host, puerto y **perfiles Share**; el handoff, `password_cipher` e `id_session` van vacios. El import conserva el handoff y la contraseña ya guardados para el mismo id de perfil; en un equipo nuevo pegue el handoff con 📥.
- Las **herramientas** se exportan sin `api_key_cipher` y los **equipos** sin `tailscale_node_key` (y, como antes, sin contraseñas ni claves SSH). Un import con *overwrite* nunca borra las credenciales ya guardadas aquí.
- Para llevar secretos a otro equipo use **Backup/Restore** (§11.2): va cifrado e incluye `identity.dat`. Export no tiene opción «incluir secretos».
- **Headscale:** se exporta URL/puerto/opciones de servidor; `api_key_cipher` y `binary_path` van vacios (la API key es local; los nodos van en `computers`).
- **Direct:** modelo/prompt/umbral; sin estados de conversacion.

**Import**: importa desde `config/laim_config_clear.json`.
- El modal lista **solo las familias que hay en el JSON**. Los recuentos «N en JSON» salen de ese fichero; «M aquí» es lo que ya hay en **esta** instalación (no es lo que se exportó).
- Vista previa de conflictos antes de importar
- Opciones: `overwrite` (sobrescribe el registro local) o `skip` (por defecto, conserva el local)
- Si una contrasena de usuario estaba vacia, solicita un nuevo valor durante la importacion
- Si el JSON trae Share y Connect a la vez, el import **no borra** el otro bloque: solo apaga `enabled` del rol que no corresponde a este equipo (`reconcileShareConnectEnabled`).

**Siempre excluidos** (no son familias): `identity.dat` / clave maestra, `JobQueue`, serial, `WebAPIEnabled`. Esos van solo en Backup/Restore de instalacion.

### 11.2 Backup y Restore

**Backup** no es por familias (eso es Export/Import). Crea un **tar.gz de instalacion** `config/laim_install_YYYY-MM-DD_HH-MM.bak` con: `laim.dat` (incluye Share, Connect y perfiles, Headscale, Direct, equipos, tareas, alertas MRTG, catalogo DevOps), `identity.dat`, `laim.md`, `soul.dat`, `soulmachine.dat`, `voice.dat`, `notifications.dat`, `audit.dat`, `prompts.dat`, `plugins.dat`, `laim.sessions` y `notes/`. Los `*.dat` se leen y restauran desde `data/` (junto al binario). No incluye `library.dat` ni `translate.dat` (semillas comunes). Los backups legacy `laim.dat_*.bak` (solo gzip de `laim.dat`) siguen restaurables.

**Restore**: lista los `.bak` de `config/`; antes de restaurar, crea automaticamente un backup de seguridad del estado actual. Restaurar `identity.dat` + `laim.dat` recupera la clave maestra y todo el almacén local.

### 11.3 Local — Configuracion de instalacion

Desde **config → 9 → 2. Local** (o **Internal › Local** en la web):

| Variable / seccion | Tipo | Default | Descripcion |
|---|---|---|---|
| `max_session_hours` | int | 0 | Horas maximas por sesion (0 = infinito) |
| Configuracion del agente Teacher | varios | - | Tier del modelo, prompt del teacher, limite de feedback |
| **Firewall y puertos LAIM** | monitor + reparar | — | Catalogo de puertos/reglas OS y hardening (ver [11.3.0](#1130-firewall-y-puertos-laim)) |
| **Seguridad de inferencia** | reglas + mensajes | seed `security_by_default` | Restricciones REJECT globales (ver [11.3.1](#1131-seguridad-de-inferencia-security-by-design)) |
| Proteccion anti proxy | bool | activo | Bloqueo de cabeceras proxy sospechosas |
| **Ventana de Contexto y Cache** | objeto | ver abajo | Limites de historial y KV cache aplicativo |
| **Paralelismo Ollama** | objeto | adaptador del host (x64: 2/2; Silicon: segun RAM) | Concurrencia LAIM vs `OLLAMA_NUM_PARALLEL` (ver [11.3.2](#1132-paralelismo-ollama)) |
| **Configuracion MLX** | objeto `mlx` | context 16384, max_tokens 2048, temp 0.7, top_p 0.95, guardrail `balanced`, max_concurrent 1 | Direct MLX nativo en Apple Silicon (ver [11.3.3](#1133-configuracion-mlx-apple-silicon)). Distinto de la ventana Ollama. |
| **Registro en laim.app** | boton Registrar | — | Asocia esta instalacion a su cuenta del portal (ver [1.5](#15-registro-de-la-instalacion-en-laimapp)) |
| **Editor IA** | objeto | - | Modelos Ollama para acciones inline y chat del Editor |
| **Accesos directos** (pkg81) | 5 posiciones | Nuevo usuario, Nuevo equipo, Acceso de usuarios, Modelos Ollama, Listar agentes | Botones de «Accesos directos» del Asistente de configuración. Cada posición tiene un selector con las 9 opciones o **— Vacía —** (esa posición no muestra botón). Una opción solo puede elegirse una vez: si se repite, se rechaza indicando la posición. **Guardar accesos directos** guarda la elección en `laim.dat` (`local_settings.config_shortcuts`); **Restaurar por defecto** la borra y vuelven los de por defecto (revertir). Solo admin; API `GET`/`PUT /api/v1/config/internal/shortcuts`, `POST …/shortcuts/restore`. |
| **TTS (Orpheus)** | objeto `tts` | voces EN/ES (`tara` / `maria`) | Modelos en Tiers **TTS EN** y **TTS ES**. Direct: espanol si la UI o la respuesta lo son (el default `en` de ficha de usuario no anglifica). University fuerza `lang=es`. Distinto del tier Sonido (STT). |

#### 11.3.2 Paralelismo Ollama

Panel **Internal › Local → Paralelismo Ollama**. Controla cuantas inferencias locales pueden correr a la vez en LAIM y cuantos workers GPU arranca la cola de jobs.

| Campo | Default | Rango | Notas |
|-------|---------|-------|-------|
| Activar control de concurrencia | si | — | Semaforo `OllamaSlotManager` |
| Slots Ollama | **2** | 1–8 | Capacidad compartida: cola GPU + editor + informes + STT |
| Workers GPU | **2** | 1–8 | Reiniciar `laim web` para aplicar el nuevo N |
| `OLLAMA_NUM_PARALLEL` recomendado | **2** | 1–8 | Hint; hay que exportarlo en el demonio Ollama |
| `OLLAMA_MAX_LOADED_MODELS` recomendado | **2** | 1–8 | Hint para warmup multi-tier |

**Regla:** capacidad LAIM (slots) ≤ `OLLAMA_NUM_PARALLEL` del demonio. Si el demonio tiene `NUM_PARALLEL=1`, LAIM encolara aunque haya 2 workers.

**Adaptador por hardware** (`GET /api/v1/config/internal/local-settings` → `inference_runtime`): LAIM no sustituye Ollama por MLX. En todos los hosts el contrato sigue siendo HTTP `localhost:11434`. Lo que cambia es el perfil de concurrencia y las variables del demonio. El botón **MLX** de Inferencia directa es un camino aparte (`mlx_lm.server` en `127.0.0.1:4325`); no modifica Ollama.

| Kind | Host | Backend | Memoria | Parallelismo de fabrica (si slots=0) |
|------|------|---------|---------|--------------------------------------|
| `apple_silicon` | macOS ARM (`bin/silicon`) | llama.cpp + **Metal** (no MLX) | RAM **unificada** | 8 GB → 1; 16 GB → 2/2; 24 GB → 2 slots / 3 modelos; 64 GB → 3. `FLASH_ATTENTION=1`, KV `q8_0`, `keep_alive=-1` (≥16 GB) |
| `apple_intel` | macOS x64 | CPU | unificada | 1 slot |
| `discrete_x64` | Windows / Linux x64 | CUDA/ROCm o CPU | VRAM dedicada | 2 slots / 2 workers; FA opt-in; `keep_alive=5m` |

Los comandos concretos (`launchctl setenv` en Silicon, `$env:` en Windows, `export` en Linux) los genera el Core y el panel Internal › Local solo los muestra. En macOS, `.zshrc` **no** llega a `Ollama.app`: hay que usar `launchctl` y **salir y reabrir** la app.

El `keep_alive` de fabrica en la UI sigue siendo 5 minutos (no se persiste `-1` en `laim.dat`). En Apple Silicon ≥16 GB el runtime envia `keep_alive=-1` a Ollama para no recargar el modelo entre turnos.

Linux con systemd (unidad tipica `ollama.service`): anadir `Environment=OLLAMA_NUM_PARALLEL=…` y `systemctl restart ollama`.

Sintomas tipicos:

| Sintoma | Accion |
|---------|--------|
| Latencia alta con GPU infrautilizada | Subir slots/workers y `OLLAMA_NUM_PARALLEL` (con margen VRAM) |
| OOM / descarga frecuente de modelos | Bajar slots y `NUM_PARALLEL`; modelos cuantizados; menos `num_ctx` |
| Segunda peticion espera siempre | Comprobar que el demonio no tiene `OLLAMA_NUM_PARALLEL=1` |

Referencia: [Como Ollama maneja las solicitudes paralelas](https://www.glukhov.org/es/llm-performance/ollama/how-ollama-handles-parallel-requests/).

#### 11.3.3 Configuracion MLX (Apple Silicon)

Panel **Internal › Local → Configuracion MLX**. Solo aplica al motor nativo **mlx-lm** de Inferencia directa (boton **MLX**) en equipos **Apple Silicon** (`darwin` + `arm64`). En Windows, Linux o Mac Intel el panel se muestra con aviso: Direct MLX esta desactivado; los valores se guardan por si se usa un host Silicon.

**No es LM Studio.** LAIM no instala packs de runtime ni el selector «LM Studio MLX». El runtime es `mlx-lm` en `.venv_314` (el mismo Python de Reflex), enlace `127.0.0.1:4325` (`LAIM_MLX_PORT` si se cambia). El boton **LMStudio** sigue siendo GGUF en `:1234`. Ollama en Silicon permanece llama.cpp + Metal (`:11434`); esta seccion **no** sustituye la [ventana de contexto Ollama](#26-ventana-de-contexto-y-cache) ni el paralelismo de [11.3.2](#1132-paralelismo-ollama).

Al guardar, LAIM detiene `mlx_lm.server` para reaplicar flags en el siguiente turno Direct MLX. Los logs van a `logs/mlx_lm.server.log`.

| Campo (`local_settings.mlx`) | Default | Rango | Que controla en LAIM |
|------------------------------|---------|-------|----------------------|
| `context_tokens` | **16384** | 1024–131072 (paso 1024) | Presupuesto de prompt + historial. `mlx_lm.server` no tiene flag max-kv; LAIM compacta el historial Direct con este tope (`MLXContextWindowManagerFromStore`), **no** con la ventana Ollama. |
| `max_tokens` | **2048** | 64–32768 | `--max-tokens` del servidor y `max_tokens` OpenAI por respuesta. |
| `temperature` | **0.7** | 0–2 (0 = greedy, valido) | `--temp` y muestreo de turnos Direct MLX. Independiente de la temperatura de tiers Ollama. |
| `top_p` | **0.95** | 0.01–1 | `--top-p` (nucleus) del servidor nativo. |
| `guardrail` | **balanced** | `off` / `relaxed` / `balanced` / `strict` / `custom` | Tope de carga de `*.safetensors` frente a la RAM unificada. |
| `custom_max_model_gib` | — | ≥ 1 | Solo si `guardrail=custom`. |
| `log_level` | **INFO** | DEBUG, INFO, WARNING, ERROR, CRITICAL | `--log-level` → `logs/mlx_lm.server.log`. |
| `max_concurrent` | **1** | 1–2 | Semáforo de generaciones nativas (`MLXSlotManager`). Direct MLX y University (si reusa `:4325`) lo adquieren. **1** es el valor de producción: `mlx_lm.server` serializa GPU. **2** queda documentado para un sidecar de lote futuro (fase 2); no arranca un segundo servidor 72B. |

**Guardrails (RAM unificada).** En Apple Silicon la misma memoria sirve al SO, a Ollama Metal, a Reflex (`.venv_314`) y a `mlx_lm.server`. LAIM reserva `MLXLAIMOverheadGiB` (3 GiB) para web + Core y aplica una fraccion de la RAM usable:

| Nivel | Fraccion de RAM usable | Uso tipico |
|-------|------------------------|------------|
| OFF | 95 % | Casi sin margen (no recomendado: riesgo de freeze) |
| Relaxed | 70 % | Precauciones suaves |
| Balanced (recomendado) | 50 % | Margen para Ollama Metal y la UI web |
| Strict | 35 % | Precauciones fuertes |
| Custom | tope en GiB | El administrador fija el maximo |

Formula: `(RAM − reserva SO − 3 GiB LAIM) × fraccion`. El panel muestra el tope de carga actual y la RAM detectada. Si el modelo elegido supera el tope, Direct MLX no arranca el servidor.

`prompt_cache_bytes` (0 = auto) se calcula en Go a partir de la RAM sobrante; no hay control en la UI.

API: el objeto `mlx` viaja en `GET/PUT /api/v1/config/internal/local-settings` (admin). Persistencia: `laim.dat` → `LocalSettings.MLX`.

#### 11.3.0 Firewall y puertos LAIM

Esta seccion explica el panel **Firewall y puertos LAIM** de la configuracion web (**Internal › Local**) y el mismo catalogo que aparece en **`laim init`**. El objetivo es que el administrador entienda **que significa cada icono**, **que reglas toca LAIM** y **como reparar** bloqueos tipicos (Connect con timeout, Share inaccesible en LAN, Headscale sin puerto).

##### Donde se configura

| Via | Como |
|-----|------|
| **Web (recomendada)** | Configuracion → **Internal › Local** → bloque «Firewall y puertos LAIM» (solo rol **admin**) |
| **CLI init** | Tras la fase Ollama, `laim init` lista el catalogo y pregunta `s/n` para aplicar reglas |
| **CLI Share** | Menu Share → «Abrir firewall» (regla TCP entrante de `share_api`) |
| **API** | `GET /api/v1/config/internal/firewall-status` · `POST /api/v1/config/internal/firewall-repair` (sesion admin) |

> **Principio:** LAIM solo abre o verifica puertos que **necesita**. No desactiva Windows Defender, AppArmor, SELinux, SIP ni Gatekeeper. La seccion de hardening del panel es **solo informativa**.

##### Como leer el panel (representacion)

Al abrir Internal › Local, LAIM carga un informe (`CollectLAIMFirewallReport`) y pinta:

1. **Titulo + badge**
   - Badge **OK** — ninguna regla critica pendiente (`needs_repair = false`).
   - Badge **Requiere atencion** — hay al menos un puerto con estado 🔧 / ❌ o un fallo reparable.

2. **Resumen (`summary`)**
   - Correcto: *«Firewall y puertos LAIM en estado correcto.»*
   - Con anomalias: *«Hay anomalias: use Reparar para aplicar las reglas LAIM pendientes.»*

3. **Cabecera de contexto**
   - **Plataforma:** `windows` / `mac` / `linux` (segmento del binario).
   - **Firewall:** `enabled` / `disabled` / `unknown` (estado del firewall del SO).
   - **Backend:** motor detectado (`windows`, `ufw`, `firewalld`, `iptables`, Application Firewall de macOS, etc.).

4. **Lista «Puertos y conexiones»** — una fila por servicio del catalogo:

| Columna visual | Significado |
|----------------|-------------|
| Icono de **estado** (izquierda) | Resultado de la comprobacion (ver tabla de estados abajo) |
| Emoji del **servicio** | Identifica el rol (Share, Ollama, Headscale…) |
| **Nombre + detalle** | Nombre humano y texto tecnico (regla presente, falta regla, solo localhost…) |
| **Puerto/proto** | Ej. `4322/tcp`, `41641/udp` |
| Badge 🔧 (derecha) | Solo si `can_repair = true` — LAIM puede intentar crear/verificar esa regla |

5. **Lista «Seguridad de aplicacion del SO»** — Defender / AppArmor / SELinux / SIP / Gatekeeper. Mismos iconos de estado; **LAIM no repara ni desactiva** estos controles.

6. **Botones**
   - **Actualizar estado** — vuelve a consultar el SO y refresca el panel (no cambia reglas). Muestra mensaje de progreso/resultado bajo los botones.
   - **Reparar reglas LAIM** — visible cuando el badge es «Requiere atencion». Aplica las reglas pendientes (puede pedir **UAC** en Windows o **sudo/pkexec** en Linux/macOS).
   - **Aplicar / verificar reglas** — misma accion cuando el estado es OK: re-verifica e intenta dejar las reglas LAIM coherentes (idempotente).

##### Leyenda de estados (emoji)

| Emoji | Codigo interno | Significado | Accion tipica del admin |
|-------|----------------|-------------|-------------------------|
| ✅ | `ok` | Regla presente o puerto permitido | Ninguna |
| 🔧 | `repair` | Falta regla OS que LAIM puede crear | Pulsar **Reparar** (aceptar UAC/sudo) |
| ❌ | `fail` | Comprobacion fallo de forma grave | Revisar permisos / politica de dominio; reintentar Reparar |
| ⚠️ | `warn` | Estado indeterminado o aviso | Actualizar estado; si persiste, revisar firewall del SO a mano |
| ℹ️ | `info` | Trafico **saliente** (SSH/WinRM); no abre puerto local | Comprobar que el host no bloquea la **salida** de LAIM |
| ➖ | `skip` | No aplica (loopback o Headscale deshabilitado) | Ninguna — es informativo |

##### Catalogo de puertos (no los elimine sin causa)

| Emoji | Servicio | Puerto | Direccion | Bind | ¿Regla OS? | Notas |
|-------|----------|--------|-----------|------|------------|-------|
| 🌐 | Web API | 4320/tcp | inbound | localhost | No | Solo `127.0.0.1` — no abre LAN |
| 🖥️ | Web UI Reflex | 4321/tcp | inbound | localhost | No | Solo local |
| 🔗 | Share API (Connect) | **4322/tcp** (o `Share.Port`) | inbound | LAN `0.0.0.0` | **Si** — nombre `LAIM share_api` | **Puerto critico** para clientes Connect |
| 🧠 | Ollama | 11434/tcp | outbound | localhost | No | LAIM → Ollama en el mismo equipo |
| 📡 | Headscale control | 8080/tcp | inbound | LAN | Si, **solo si** Headscale enabled | Plano de control mesh |
| 🔒 | WireGuard data | 41641/udp | inbound | any | Si, **solo si** Headscale enabled | Plano de datos |
| 🔑 | mesh_api (enrollment) | **4324/tcp** | inbound | LAN | Si, **si Headscale o Mesh.ServerEnabled** | Solicitudes cifradas `KeyMeshEnrollment` |
| 💻 | SSH remoto (cliente) | 22/tcp | outbound | remoto | No | Salida hacia equipos `laim remote` |
| 🖥️ | OpenSSH Server (este host) | **22/tcp** | inbound | LAN | **Si, solo si `sshd` esta activo** — nombre `OpenSSH-Server-In-TCP` | Para que **otros** LAIM remote se conecten a este Windows. Activar con Ayuda › Windows remoto → **Activar automaticamente usando LAIM**. Perfil **Any** (no solo Dominio) |
| 🖥️ | WinRM HTTPS | 5986/tcp | outbound | remoto | No | Salida WinRM si se usa |

> Si cambia el puerto de Share en `laim.dat`, el panel usa ese puerto. Tras cambiarlo: reinicie `share_api` y pulse **Reparar** (o «Abrir firewall» en Share) para recrear la regla con el **mismo** `LocalPort`.

##### Que hace «Reparar» / «Aplicar» (mecanismo)

1. Lee la configuracion actual (`Share.Port`, `Headscale.Enabled`).
2. Asegura la regla entrante TCP de **Share** (`EnsureShareInboundFirewall`): en Windows elimina y recrea la regla si el puerto no coincide; en Linux/macOS usa el backend detectado.
3. Si Headscale esta habilitado, intenta permitir **8080/tcp** (`LAIM headscale`) y **41641/udp** (`LAIM wireguard`).
4. Si `mesh_api` debe escuchar (Headscale o coordinador mesh), permite **4324/tcp** (`LAIM mesh_api`).
5. Si el servicio **sshd** esta en marcha (este Windows es servidor OpenSSH), asegura la regla entrante TCP **22** (`OpenSSH-Server-In-TCP`, todos los perfiles). No abre el 22 en `laim init` si sshd no esta activo.
6. Vuelve a generar el informe y actualiza el panel; el mensaje bajo los botones lista cada accion (`Aplicada regla Share…`, `ya permitido`, o el hint manual si fallo).
7. Registra auditoria en `audit.dat` (grupo Internal, accion update, target `firewall`).

**No hace:**

- No desactiva antivirus, AppArmor, SELinux, SIP ni Gatekeeper.
- No abre 4320/4321 a la LAN (siguen en loopback).
- No modifica reglas ajenas a LAIM (otras apps / politicas de dominio), salvo recrear la regla nombrada de Share cuando el puerto no coincide.

##### Problemas frecuentes y resolucion

| Sintoma | Lectura del panel | Que hacer |
|---------|-------------------|-----------|
| Cliente Connect hace **timeout** hacia el master | Share 🔗 con 🔧 «Falta regla entrante TCP 4322» | **Reparar reglas LAIM** en el **master**; aceptar UAC. Verificar que la regla OS usa el mismo puerto que `Share.Port` (no 4320/4321). |
| Badge OK pero Connect sigue fallando | Share ✅ | Comprobar IP LAN, que Share este enabled, handoff `user_connection`/`password_connection`, y NAT/router si hay hops. En macOS cliente: binario firmado (`compile_core.sh` + `codesign`). |
| Headscale no enlaza nodos | 📡/🔒 en 🔧 o ➖ | Si Headscale esta enabled y aparecen 🔧 → Reparar. Si ➖ → Headscale no esta habilitado en Local/config. Abrir tambien NAT del router hacia 8080 si los nodos estan fuera de la LAN. |
| Boton Reparar «no hace nada» o pide elevacion | Mensaje de progreso / UAC | En Windows debe aparecer el dialogo UAC; sin aceptarlo la regla no se escribe. Espere el mensaje ✅/⚠️ bajo los botones. |
| Firewall del SO desactivado (`Firewall: disabled`) | Cabecera `disabled` | LAIM puede marcar puertos como OK sin regla; el riesgo es otro. Reactive el firewall del SO y use **Actualizar estado** + **Reparar**. |
| Politica de dominio impide crear reglas | Fallo en el mensaje de Reparar | Pida a IT una excepcion para TCP `Share.Port` (default 4322) con nombre `LAIM share_api`, o cree la regla GPO equivalente. |
| Omitio el firewall en `laim init` (`n`) | Cualquier 🔧 en Share | Entre en Internal › Local y pulse **Reparar**, o use Share → Abrir firewall. |
| Otro LAIM no entra por SSH a este Windows | OpenSSH 🖥️ en ➖ o 🔧 | En **este** Windows: Ayuda › Windows remoto → **Activar automaticamente usando LAIM**. Windows muestra UAC: pulse **Si**. Luego **Reparar** si el panel marca 🔧 en TCP 22. No use solo el perfil Dominio (timeout en LAN domestica). |

##### Seguridad de aplicacion del SO (solo lectura)

| SO | Controles mostrados en el panel |
|----|----------------------------------|
| Windows | Windows Defender Firewall, Microsoft Defender Antivirus (tiempo real, etc.) |
| Linux | Backend firewall (ufw/firewalld/iptables), AppArmor, SELinux |
| macOS | Application Firewall (`socketfilterfw`), SIP, Gatekeeper |

Si un control aparece ⚠️ o ❌, actue con las herramientas del SO (Defender, `aa-status`, `getenforce`, Preferencias del Sistema). **No** use el boton Reparar de LAIM para eso: no esta disenado para desactivar protecciones.

##### Referencia rapida API (admin)

```http
GET  /api/v1/config/internal/firewall-status
POST /api/v1/config/internal/firewall-repair
GET  /api/v1/config/internal/windows-openssh/status
POST /api/v1/config/internal/windows-openssh/enable?lang=es
```

Requieren cabecera `X-LAIM-Session-ID` de sesion web **admin**. La respuesta de firewall-status incluye `platform`, `firewall_on`, `backend`, `endpoints[]`, `hardening[]`, `needs_repair`, `summary`. Repair incluye `success`, `messages[]` y un `report` actualizado. `windows-openssh/enable` devuelve 202 y un snapshot de pasos; `…/status` se consulta hasta `done`/`error` y entonces trae `facts` / `facts_markdown` para registrar el equipo en otro LAIM remote.

#### 11.3.1 Seguridad de inferencia (security by design)

LAIM protege **todas las inferencias** con reglas REJECT gestionables por el administrador. El enfoque es **security by design**: las limitaciones forman parte del flujo (solicitud y respuesta), no un parche opcional.

**Donde viven las reglas por defecto**

| Almacen | Contenido | Alcance |
|---------|-----------|---------|
| **`library.dat`** | Catalogo **canonico de fabrica** (13 reglas `DEF-*` / `DES-*`, categoria `security`, keyword `inference_security`) | Igual en **todas** las instalaciones de la misma version mayor (`KeyLibraryfiles`); se distribuye con `scripts/distribute_common_files.ps1` |
| **`laim.dat`** (`LocalSettings.InferenceSecurity`) | Copia operativa + mensajes EN/ES + interruptor + reglas **custom** y **overrides** que el admin edite | Solo esta instalacion |

Al arrancar (`laim init` / `laim web`), LAIM hace merge por ID: anade builtins ausentes desde `library.dat` (fallback al seed Go) **sin pisar** edits locales del admin.

Referencias de modelado: [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/), [Ironhackers CyberH2O](https://ironhackers.es/cyberh2o-llm-security/), [GTFOBins](https://gtfobins.org/).

**Catalogo por defecto (proteccion que reciben chat, Direct y Suggestions SSH)**

| ID | Origen | Scope | Que bloquea |
|----|--------|-------|-------------|
| `DEF-DISK-WIPE` | default | both | Borrado destructivo de disco / FS (`rm -rf /`, `format c:`, `dd if=/dev/zero`, etc.) |
| `DEF-FORK-BOMB` | default | both | Fork bombs y bombas de procesos |
| `DEF-PRIVILEGE` | default | both | Destruccion masiva de fronteras de privilegio OS (**no** `sudo`/UAC planos) |
| `DES-WEAPONS` | design | both | Fabricacion de armas / dano violento |
| `DES-INTRUSION` | design | both | Malware, ransomware, intrusion no autorizada |
| `DES-FRAUD` | design | request | Phishing / fraude con tarjetas |
| `DES-LLM01-PROMPT-INJECTION` | design | request | Prompt injection / jailbreak (OWASP LLM01; Proofpoint directa) |
| `DES-LLM01-SYSTEM-ROLE` | design | request | Inyeccion de rol `system` y extraccion de system prompt |
| `DES-LLM01-INDIRECT` | design | both | Inyeccion indirecta / no-click / infeccion multiagente (Proofpoint + taxonomia PAT) |
| `DES-LLM06-SENSITIVE` | design | both | Exfiltracion de secretos LAIM / claves privadas (OWASP LLM06) |
| `DES-LLM02-INSECURE-OUTPUT` | design | response | Salidas que pipan codigo remoto a shell (OWASP LLM02) |
| `DES-LLM08-AGENCY` | design | request | Intentos de desactivar controles LAIM (OWASP LLM08) |
| `DES-GTFO-SHELL` | design | both | Patrones reverse/bind shell tipo GTFOBins |
| `DES-GTFO-PRIVESC` | design | both | Abuso SUID / LOL / `docker --privileged` (GTFOBins; **no** `sudo` plano) |

**Excepcion:** elevacion con `sudo` (Linux/macOS) o UAC/`runas` (Windows) **no** se rechaza aqui; queda a criterio del usuario en F6 (RISKY + consentimiento).

**Comandos que LAIM nunca ejecuta o que siempre preguntan (F6, 0.58.32):** un comando con un hueco sin rellenar (`<PID>`, `<interfaz>`) o con un valor de documentación (`YourProcessName`, `/path/to/…`, `example.com`) y los programas interactivos (editores, `htop`, `top` sin modo batch) se rechazan (FORBIDDEN): no hay nada que consentir, LAIM primero averigua el valor real. Cambiar la prioridad, la clase de E/S o la afinidad de procesos (`renice`, `ionice -c`, `chrt`, `taskset -p` con valor, `.PriorityClass =`, `wmic … setpriority`) pide siempre consentimiento (RISKY, CMD-RSK-025). Desde 0.58.33 tambien liberar espacio borrando datos (`apt-get clean`, `journalctl --vacuum-*`, `docker … prune`, `Clear-RecycleBin`, `truncate -s`…) y crear swap (`fallocate`, `mkswap`) piden consentimiento (RISKY, CMD-RSK-026). Desde 0.58.35 **LAIM nunca reinicia el equipo**: CMD-FBD-010 (FORBIDDEN) cubre tambien `softwareupdate -R/--restart` y `Install-WindowsUpdate … -AutoReboot/-ForceReboot`, ademas de `shutdown`, `reboot`, `systemctl reboot` y `Restart-Computer`. Las actualizaciones se instalan sin reiniciar y LAIM avisa cuando hace falta un reinicio (`Action: restart`, `RebootRequired`, `needrestart -b`). Desde 0.58.37 todo cambio de red pide consentimiento y nunca se ejecuta como lectura (RISKY, CMD-RSK-021):
- `nmcli` en todas sus formas: `con mod`/`m`/`add`/`del`/`up`/`reload`, `device set`/`reapply`/`connect`, `wifi connect`, `general hostname <nombre>`, `radio … on`;
- `nmtui`, `resolvectl dns <interfaz> <servidores>`, `netplan apply`;
- `ifconfig <interfaz>` con dirección, `up`, `mtu` o `alias`.

Leerlos (`nmcli … show`, `resolvectl status`, `ifconfig en0`) sigue siendo una lectura. Un `Remove-Item` recursivo sobre la raíz de una unidad o una ruta del sistema (`C:`, `$Disk.DeviceID`, `$env:SystemDrive`, `$env:SystemRoot`), con los flags en cualquier orden, está prohibido (FORBIDDEN, CMD-FBD-008).

**Desde 0.58.42 (pkg34m):**

- **Texto entre comillas:** LAIM nunca ejecuta como orden lo que el usuario escribe entre comillas. Lo que va tras `;`, `&&`, `||`, `$(` o una comilla invertida dentro de un nombre entre comillas, y cualquier `$(…)` de la pregunta, está prohibido (FORBIDDEN, CMD-INJ-001), aunque sea una lectura como `id`. Un cambio sobre un nombre así (`instala 'htop; id'`) se responde diciendo que el nombre no es válido, sin proponer nada.
- **Herramientas de macOS en Linux:** `vm_stat`, `diskutil`, `launchctl`, `networksetup` y otras están prohibidas en Linux (FORBIDDEN, CMD-PLT-007).
- **Cambios de red:** usan solo los valores de la pregunta. Una puerta de enlace, unos DNS o una conexión de NetworkManager que el usuario no dio se le preguntan; si no los da, el comando no se propone.
- **Reiniciar el equipo:** «Reinicia el equipo» se responde con la regla CMD-FBD-010 (LAIM nunca reinicia ni apaga el equipo), sin proponer comandos.

**Desde 0.58.43 (pkg34n):**

- **Escribir en un fichero:** una redirección a un fichero (`>`, `>>`, `&>`) pide consentimiento (RISKY, CMD-RSK-027), sea cual sea la ruta. `2>/dev/null`, `>$null`, `> NUL` y `2>&1` no escriben nada y siguen siendo lecturas.
- **Valores de ejemplo:** las etiquetas de launchd de la documentación (`com.example.…`, `com.yourcompany.…`) están prohibidas igual que los dominios de ejemplo (FORBIDDEN, CMD-FBD-020).
- **Salida de ejemplo:** una línea de salida de `sysctl` (`kern.ostype = Darwin`) o una ruta suelta a un fichero de datos (`/Users/…/script.log`) que escriba el modelo nunca se ejecuta.
- **Lecturas que se hicieron:** ese bloque de una petición de cambio lista solo los comandos que se ejecutaron, nunca los que rechazó una regla o denegó el usuario.
- **Windows:** cada comando va en su propia sesión de PowerShell. Se quitan las líneas que solo asignan una variable y los comandos que usan una variable que no asignan ellos mismos.

**Desde 0.58.44 (pkg36a):**

- **Comandos que no terminan:** `journalctl -f`, `tail -f`, `watch`, `log stream`, `ping` sin `-c` (en Windows, `ping -t`), `tcpdump` sin `-c` y `Get-Content -Wait` están prohibidos (FORBIDDEN, CMD-FBD-023): LAIM espera a que cada comando acabe. En macOS `top` necesita `-l` (`-n` es el número de procesos); si no, es interactivo (CMD-FBD-022).
- **Órdenes inventadas:** un `systemctl` o `launchctl` con una orden que el programa no tiene (`systemctl set-rp-expensive-journal`) está prohibido (FORBIDDEN, CMD-FBD-024).
- **No son lecturas:** `source <fichero>` / `. <fichero>` ejecuta el código del fichero (RISKY, CMD-RSK-028); `open`, `xdg-open`, `Start-Process`, `Invoke-Item`, `explorer` y `start` abren una ventana en el escritorio del equipo (RISKY, CMD-RSK-029).
- **Herramientas de Linux en macOS:** `systemctl`, `journalctl`, `apt`, `dnf`, `nmcli`, `ufw`, `ip addr`, `ss`, `free`, `lsblk`, `useradd` y `ps --sort` de GNU están prohibidos en macOS (FORBIDDEN, CMD-PLT-008).
- **Opciones que el programa no tiene (pkg96):** en macOS una opción larga (`--…`) de `df` (salvo `--libxo`), `du`, `stat`, `date` o `ps` de BSD, y `stat -c` / `date -d`, están prohibidas (FORBIDDEN, CMD-PLT-009: use `df -h`, `du -d N`, `stat -f`, `date -v`); en Linux una opción larga que `df` / `du` de GNU no tienen (`df --output-size`, `du --show-size`; un prefijo no ambiguo como `du --summ` es válido) está prohibida (FORBIDDEN, CMD-PLT-010). Solo cuenta el programa que empieza un comando (también tras `;`, `&&`, `|`, `(`, `sudo` o `env`); el texto entre comillas nunca. Las respuestas y las Sugerencias remotas nunca proponen esos comandos; en macOS `du --max-depth=N` se reescribe como `du -d N`.
- **Opciones cortas de BSD y editores (pkg98):** en macOS cada opción corta de `df`, `du`, `stat` y `date` se comprueba con el uso de macOS (`df -B` y `du -b` son solo de GNU), y `top` con el suyo (`top -b` no existe; use `top -l 1`): prohibidas (FORBIDDEN, CMD-PLT-009). `crontab -e`, `visudo` y `vipw` abren un editor y son interactivos (FORBIDDEN, CMD-FBD-022); `visudo -c` solo comprueba y está permitido. Las respuestas y las Sugerencias remotas ya no proponen comandos que necesitan un terminal (como `top` sin `-l` en macOS).
- **Valores de ejemplo y salidas de otro sistema (pkg99):** las respuestas y las Sugerencias remotas ya no proponen un comando con un valor copiado de la documentación (`/path/to/…`, `YourProcessName`, `example.com`; CMD-FBD-020); un comando con un hueco `<…>` sin rellenar se queda, porque LAIM pregunta el valor real. Un bloque de salida que nombra un proceso que el sistema del equipo no ejecuta (`systemd` en macOS, `launchd` o `WindowServer` en Linux) se quita como salida inventada.
- **sw_vers y sysctl en macOS (pkg101):** `sw_vers` solo admite `--productName`, `--productVersion`, `--productVersionExtra`, `--buildVersion` y `--help` (o un prefijo único; `sw_vers -p` es ambiguo), y `sysctl` solo nombres de un nivel superior de macOS (`kern.boottime`, `hw.memsize`; `sysctl NVRAM` falla): lo demás está prohibido (CMD-PLT-009) y nunca se propone, tampoco cuando una frase pide ejecutarlo.
- **Orden y lecturas dependientes:** los comandos se ejecutan en el orden propuesto, así que una comprobación va después de su cambio. Una lectura que usa un fichero o carpeta que solo habría creado un cambio que no se ejecutó (una copia de seguridad, una carpeta nueva) se deja fuera y se lista con CMD-DEP-001.

**Desde 0.58.45 (pkg36bc):**

- **Comprobaciones de un cambio que no se hizo:** una lectura posterior que nombra el mismo fichero, unidad o PID que un cambio denegado (su comprobación) también se deja fuera (CMD-DEP-001), y la respuesta del chat no la informa.
- **Abrir una ventana nunca es un cambio verificado:** una propuesta cuyo único cambio abre una ventana (`Start-Process ncpa.cpl`) no se ofrece como procedimiento verificado de LAIM.
- **El proceso con más CPU:** terminar o cambiar la prioridad de «el proceso que más CPU usa» nunca apunta a un proceso que el sistema necesita (`System`, `csrss`, `lsass`, `svchost`, `kernel_task`, `launchd`, `WindowServer`, `opendirectoryd`, `systemd`, hilos del kernel); la respuesta dice cuáles se dejaron fuera.
- **Los cambios de red y de cortafuegos** usan solo valores reales: los de la pregunta o una lectura del equipo (la interfaz de la ruta por defecto, su conexión de NetworkManager o su servicio de red de macOS, el cortafuegos activo). Una dirección de documentación (RFC 5737) recibe una explicación, no una regla.

**Desde 0.58.47 (pkg37):**

- **Peticiones de cambio en el chat sin procedimiento verificado:** responde LAIM (el aviso, o el dato que falta, y las lecturas); el modelo ya no propone sus propios comandos de cambio, ni en este equipo ni en un equipo remoto.
- **Indicios de un minero de criptomonedas oculto** (`crypto_miner_check`, solo lectura): los procesos con más CPU, las líneas de órdenes que nombran un minero o un pool stratum, las conexiones establecidas a los puertos habituales de pools (3333, 4444, 5555, 7777, 14444) y, en Linux, los programas que se ejecutan desde una carpeta temporal o borrados del disco. Un programa del sistema (`/usr`, `/opt`, `/snap`…) que una actualización reemplazó mientras se ejecutaba no es un indicio: se dice aparte, como un reinicio pendiente. La tabla de CPU deja fuera los procesos de la propia lectura. No se para ni se borra nada.

**Desde 0.58.46 (pkg36def):**

- **Nueva regla CMD-RSK-030 (RISKY):** las escrituras CIM (`Set-CimInstance`, `New-CimInstance`, `Invoke-CimMethod`), `Rename-Computer`, las tareas programadas (`Register-ScheduledTask`…), el entorno de máquina (`[Environment]::SetEnvironmentVariable`), `Copy-Item`/`Move-Item`, `docker`/`podman` `restart`/`stop`/`rm`… y `Dism /Cleanup-Image` piden consentimiento.
- **Claves del kernel:** una escritura de `sysctl` sobre una clave que la pregunta no nombra no se propone nunca; una clave nombrada se lee antes (`sysctl -n`), y si no existe se dice.
- **Procedimientos verificados:** PATH para todos los usuarios, tamaño de journald, sysctl persistente, fichero de swap, archivo de paginación, nombre del equipo, zona horaria, servicio systemd, tareas programadas (Windows `Register-ScheduledTask` como SYSTEM, `/etc/cron.d`, LaunchAgent), grupo de administradores (en Windows por SID S-1-5-32-544), deshabilitar una cuenta, endurecer SSH (`sshd_config.d`, `sshd -t`; nunca sin una clave en `authorized_keys`), copia de un fichero de configuración, limpieza, reiniciar el contenedor que más memoria usa. Los valores salen de la pregunta o de una lectura; si falta uno (la ruta de un script), LAIM lo pide en vez de inventarlo. Crear una cuenta con contraseña no se propone desde Suggestions: la contraseña se teclea en la ventana de contraseña de LAIM.
- **Solo actualizaciones de seguridad:** en Linux con `unattended-upgrade` (apt) o `dnf --security` hay una «Opción S».

**Desde 0.58.86 (pkg64d, decisión del usuario 2026-10-28: cambiar la zona horaria cuenta como «cambiar la hora»):**

- **Todo cambio de zona horaria es RISKY** con la regla de reloj de su plataforma, motivo «cambio de la zona horaria del sistema»: **CMD-RSK-011** (macOS) `systemsetup -settimezone`; **CMD-RSK-010** (Linux) `dpkg-reconfigure tzdata`, `setup-timezone`, `zic -l`; en ambas, cualquier escritura en `/etc/localtime` o `/etc/timezone` (`ln -s[f] … /etc/localtime`, `cp`/`mv`/`install` sobre él, `rm`/`unlink`/`truncate`, `tee`, `>`/`>>`, `sed -i`, `dd of=`); **CMD-RSK-009** (Windows) `tzutil /s` y `Set-TimeZone`. Antes `systemsetup -settimezone` sin sudo, `dpkg-reconfigure tzdata`, `unlink /etc/localtime` y `tzutil /s` se permitían; `Set-TimeZone` era CMD-RSK-021 y las escrituras de ficheros CMD-RSK-016. `timedatectl set-timezone` conserva CMD-RSK-010; `rm -f /etc/localtime` en macOS sigue Prohibido (CMD-FBD-001); `sudo …` sigue siendo CMD-RSK-001.
- **Siguen siendo lecturas:** `systemsetup -gettimezone`, `readlink /etc/localtime`, `ls -l /etc/localtime`, `cat /etc/timezone`, `timedatectl` / `show` / `list-timezones`, `tzutil /g`, `Get-TimeZone`, `date +%Z` y un prefijo `TZ=… orden` (solo afecta a ese proceso). Un único analizador (`IsTimeZoneSetCommand`, `internal/inference/timezone_set_pkg64d.go`) decide la regla y la vista de solo lectura.
- **Reversión en la pregunta:** los agentes local y remoto leen antes la zona actual (`readlink /etc/localtime`, `timedatectl show -p Timezone --value`, `tzutil /g`; solo lectura) y la pregunta dice «La zona actual es Europe/Madrid. Para deshacerlo: `sudo timedatectl set-timezone Europe/Madrid`.»; en macOS también Ajustes del Sistema › General › Fecha y hora › «Establecer la zona horaria automáticamente según tu ubicación», en Windows Configuración › Hora e idioma › Fecha y hora › «Establecer la zona horaria automáticamente» o `tzutil /s "<zona>"`. Si no se leyó nada (tareas programadas) dice «<zona anterior>» y nombra la lectura. El `remote-exec` de University rechaza estas órdenes como cualquier comando de riesgo.

**Desde 0.58.84 (pkg64c, decisión del usuario 2026-10-28: «en caso de querer cambiar la hora en un sistema necesitamos el consentimiento del usuario»):**

- **Todo comando que pone la hora del sistema es RISKY** con la regla de reloj de su plataforma: **CMD-RSK-010** (Linux), **CMD-RSK-011** (macOS) y **CMD-RSK-009** (Windows, motivo «cambio del reloj del sistema»). Cubre `date` / `gdate` / `busybox date` con un operando de hora (`date 102812002026`, `date -u 1028`), con `-s` / `--set`, o BSD `date -f formato 'fecha'` (sin `-j`); `rdate` (salvo `-p` solo), `ntpd -q`, `hwclock --set`; en Windows `Set-Date`, `net time … /set` y `date <valor>` / `time <valor>` de cmd. Antes `date 102812002026` y `date -s '…'` sin sudo se permitían y contaban como lectura. Ya eran RISKY `timedatectl set-time`, `systemsetup -settime`, `sntp -s`, `w32tm /config` y cualquier `sudo …`.
- **Siguen siendo lecturas:** `date`, `date -u`, `date +%s` (cualquier `+FORMATO`), `date -R`, `date -I…`, `date -r fichero`, `date -v-1d`, `date -j -f "%Y" 2026 +%s` (`-j` = no poner la hora), GNU `date -d yesterday`, `date /t`, `time /t`, `Get-Date`. Un único analizador (`IsClockSetCommand`, `internal/inference/clock_set_pkg64c.go`) decide la regla y la vista de solo lectura (`IsReadOnlyCommand` es falso para esas formas); el filtro «must_not» de pkg64b lo usa en lugar de su expresión propia.
- **Reversión en la pregunta:** la pregunta de consentimiento de un cambio de reloj añade bajo el motivo cómo volver a la hora automática: macOS «Ajustes del Sistema › General › Fecha y hora › Ajustar la hora automáticamente» o `sudo systemsetup -setusingnetworktime on`; Linux `sudo timedatectl set-ntp true`; Windows «Configuración › Hora e idioma › Fecha y hora › Establecer la hora automáticamente» o `w32tm /resync` (en inglés si el usuario usa inglés). El `remote-exec` de University rechaza estas órdenes como cualquier comando de riesgo.

**Desde 0.58.79 (pkg62, decision del usuario 2026-10-27: «Toda orden arriesgada debe de llevar consentimiento por parte del usuario, salvo que en algunas ocasiones esto lo pueda cambiar el usuario con la opción "Sugerir mejora" de LAIM»):**

- **El camino de laboratorio de University rechaza los comandos de riesgo.** `POST /api/v1/university/remote-exec` (loopback) solo bloqueaba los Prohibidos, asi que uno De riesgo se ejecutaba sin el consentimiento de nadie. University nunca consiente un cambio en un equipo del laboratorio, asi que un comando De riesgo tiene ahora el mismo resultado que un consentimiento denegado: 400 «remotesystem: comando de riesgo (CMD-RSK-xxx: motivo): University nunca autoriza cambios en los equipos del laboratorio; no se ejecuta», registrado en `console.log` (`remote_exec refused risky …`, y `refused forbidden` para los Prohibidos). Las lecturas se siguen ejecutando. University envuelve cada comando (`bash -lc '…'`, PowerShell `-EncodedCommand`); command_security clasifica ahora la **carga** (`UniversityExecPayload`), porque a traves del envoltorio un `Restart-Service` codificado o `bash -lc 'sudo apt install htop'` parecian permitidos y `bash -lc 'diskutil list'` parecia de riesgo. Una consulta de existencia de un programa (`command -v ifconfig`, `Get-Command winget`, la sonda de University) nunca dispara una regla por el nombre de ese programa.
- **Las tareas programadas necesitan el consentimiento de sus comandos de riesgo** (§11.0) y **una exencion de consentimiento verificada de soul.dat** es la unica excepcion a «un comando de riesgo pregunta cada vez» (§13.3.2). Lo prohibido sigue prohibido en todas partes.

**Desde 0.58.78 (pkg60b):**

- **La pregunta de consentimiento de un comando de riesgo sigue el idioma del usuario.** A un usuario en inglés la pregunta de los agentes localsystem y remotesystem le dice «⚠️ Risky command [ID] on <equipo>: …», «Reason: …», «Do you authorize running it (remotely)? (y/n)», y el detalle de CMD-RSK-033 «Current value (read with …)», «New value», «To revert it», «From the graphical interface». El idioma es el del turno (el mismo que el bloque «Cómo deshacer este cambio»); si no se conoce (Connect, pipelines) la pregunta sigue en español. La tabla de reglas conserva sus motivos en español: el motivo en inglés se genera solo para la pregunta, por ID de regla. Las respuestas no cambian: s / si / sí / y / yes son sí. El diálogo ▶ Ejecutar de Sugerencias envía su idioma y el texto 409, el motivo y la reversión lo siguen.

**Desde 0.58.77 (pkg60):**

- **Nueva regla CMD-RSK-033 (RISKY): los ajustes del escritorio y de las aplicaciones del usuario piden consentimiento**, como las escrituras HKCU del registro de Windows (CMD-RSK-017). Cubre `gsettings set` / `reset` / `reset-recursively`, `dconf write` / `reset` / `load`, `defaults write` / `delete` (macOS), `kwriteconfig5` / `kwriteconfig6` y `xfconf-query` con `-s` / `--set`, `-r` / `--reset`, `-n` / `--create` o `-T` / `--toggle`. Antes de esta regla se ejecutaban como lecturas: en el caso #1191 de University el modelo ejecutó `dconf write /org/gnome/desktop/notifications/enabled false` en el equipo del laboratorio sin preguntar. Las lecturas mantienen su veredicto y siguen ejecutándose en la autoejecución de solo lectura: `gsettings get` / `list-*` / `range` / `describe` / `monitor`, `dconf read` / `list` / `dump` / `watch`, `defaults read` / `read-type` / `domains` / `find`, `kreadconfig5/6`, `xfconf-query` sin fijar ni restablecer; una mención dentro de una cadena de `echo` o `grep` no es una escritura (vista sin comillas).
- **Reversión en colaboración con el usuario.** Antes de la pregunta de consentimiento de una de estas escrituras LAIM ejecuta la lectura de solo lectura correspondiente en el mismo equipo (`gsettings get`, `dconf read` / `dconf dump`, `defaults read-type` + `defaults read`, `kreadconfig … --default LAIM_SIN_VALOR`, `xfconf-query -c … -p …`), que aparece entre los comandos ejecutados, y la pregunta muestra el valor actual, el valor nuevo y la reversión exacta: la escritura con el valor anterior, o `dconf reset` / `defaults delete` / `kwriteconfig --delete` / `xfconf-query -r` si la clave no tenía valor propio (`gsettings` no lo distingue: muestra el valor anterior y `gsettings reset` para el valor por defecto), y la ruta en la interfaz gráfica cuando una guía de LAIM cubre la petición. Tras un cambio aprobado, la respuesta (chat) o el resultado de ▶ Ejecutar (Sugerencias) repite cómo deshacerlo. Una lectura que necesitaría su propio consentimiento (`sudo -u …`) no se ejecuta: la pregunta dice que no se pudo leer el valor. Solo cambia el consentimiento de esta regla; el resto de comandos de riesgo se preguntan como antes.

**Desde 0.58.69 (pkg56):**

- **CMD-FBD-021 prohíbe también un hueco entre comillas.** Un `<hueco>` entre comillas dobles o simples o dentro de una ruta (`Get-ChildItem -Path "<ruta>"`, `'<host>'`, `C:\Users\<usuario>`, `/proc/<pid>/fd`) es un valor sin rellenar: Prohibido, nunca ejecución automática, ▶ Ejecutar lo deniega aunque se confirme, y todo ejecutor (local, SSH, el bosque remoto y la puerta de solo lectura de Sugerencias) lo veta justo antes del shell. No son huecos: los literales regex de un programa entre comillas (`awk '/<GROUP>/'`), una carga XML entre comillas (`'<?xml …>'`), el marcado con su etiqueta de cierre (`echo "<b>…</b>"`) y los comentarios. Tanda 9 de University, caso #963: el carril disk_usage de Windows ejecutó `-Path "<ruta>"` en un equipo de laboratorio.
- **Las letras de unidad son rutas reales.** «disco C», «unidad D:», «partición E», "drive C", "C: drive", "the E drive", `D:\` (es/en, sin acentos; las palabras de una letra como «a», «y», "I" solo con dos puntos o escritas en mayúscula) se convierten en la raíz de la unidad en el carril disk_usage de Windows; si no se nombra unidad ni ruta, el hueco se mantiene y LAIM lo pide.
- **Nueva regla CMD-RSK-032 (RISKY): llamadas estáticas de .NET en PowerShell.** `[Tipo]::Método(…)`, `[Tipo]::new(…)`, un miembro con nombre de verbo que cambia algo (`[Win32API]::PostMessage`, caso #917) y cualquier miembro de los tipos del registro, interop, carga de ensamblados, WebClient/HttpClient, ZipFile, SendKeys o Clipboard piden consentimiento. Una lista de permitidos conservadora sigue siendo de solo lectura: tipos puros (`[math]`, `[datetime]`, `[timespan]`, `[convert]`, `[regex]`, `[guid]`, `[IO.Path]`, `[Text.Encoding]`, `[Console]`, enumeraciones como `[IO.FileMode]`), lecturas de `[Environment]` (`OSVersion`, `MachineName`, `GetEnvironmentVariable(s)`, `GetFolderPath`…), lecturas de `[IO.File]`/`[IO.Directory]` (`Exists`, `ReadAllText`, `GetFiles`…), `[IO.DriveInfo]::GetDrives`, `[WindowsIdentity]::GetCurrent`, `[Diagnostics.Process]::GetProcesses`, `[Net.Dns]::GetHostName`. Cualquier otra llamada `[Tipo]::Método(` es RISKY; el único `[System.Diagnostics.Process]::Start($psi)` que sigue siendo lectura es la lectura verificada de WSL de LAIM (`System32\wsl.exe --list --verbose / --status / --version`, ese tramo exacto).

**Desde 0.58.66 (pkg50c):**

- **Nueva regla CMD-RSK-031 (RISKY): los editores de administración de Windows piden consentimiento.** El editor del registro (`regedit`, `regedt32`), las directivas de grupo y de seguridad local (`gpedit.msc`, `secpol.msc`), toda consola MMC (`mmc`, cualquier `*.msc`: `services.msc`, `compmgmt.msc`, `lusrmgr.msc`…), Configuración del sistema (`msconfig`), las cuentas de usuario (`netplwiz`, `control userpasswords2`), el Panel de control y sus applets (`control`, cualquier `*.cpl`) y `rundll32` no son lecturas: lanzados por su nombre estaban permitidos y la ejecución automática de Sugerencias podía abrirlos en un equipo del laboratorio. Ahora cada uno se pregunta aparte, también por `.exe`, por ruta, con `&` o tras `cmd /c`; la ejecución automática de solo lectura los salta y los informa y, en un equipo remoto, nada se ejecuta sin tu sí. Las lecturas que solo los nombran (`Get-Process regedit`) siguen siendo lecturas. Las guías gráficas siguen proponiendo sus órdenes de apertura, sin ejecutarlas nunca.

**Desde remote 0.16.80 (pkg36-build): compilación nativa de todas las plataformas**

- `laim remote list` lista los equipos a los que puedes acceder (nombre, SO, dirección; nunca credenciales).
- `laim remote exec <equipo> [--timeout <s>] [--ps] -- <comando>` (administradores) ejecuta un comando en un equipo registrado con las credenciales que guarda LAIM, muestra su salida y devuelve su código de salida. `--ps` lo envuelve para PowerShell. El registro de auditoría guarda el equipo y un hash del comando.
- `bash scripts/compile_core_multiplatform.sh --yes` (en el Mac Apple Silicon, con sesión de administrador): en este Mac y luego en cada equipo del laboratorio, uno tras otro, para LAIM y lo que escucha en sus puertos, hace `git pull --ff-only`, compila con su script nativo, arranca `laim web` hasta que responde y lo para, y hace commit de `bin/<plataforma>/` y push. Escribe los nombres LAIM de los equipos en `scripts/compile_core_multiplatform.conf` (copia `.conf.example`; no se versiona) o pásalos con `--mac`, `--linux`, `--windows`. `--only`, `--no-push` y `--dry-run` lo limitan. Se para si un equipo tiene cambios locales fuera de su `bin/<plataforma>/`.

**Donde configurarlo (web):**

```
Configuracion › Asistente de configuracion › Internal › Local
→ panel «Seguridad de inferencia (security by design)»
```

**Que puede hacer el admin:**

| Accion | Detalle |
|--------|---------|
| Activar / desactivar | Interruptor global de la proteccion (en `laim.dat`) |
| Mensaje de denegacion EN/ES | Texto mostrado al usuario; placeholders `{rule_id}`, `{category}`, `{scope}` |
| CRUD de reglas | Crear, editar, borrar en `laim.dat`; ambito `request`, `response` o `both`; keywords separadas por coma |
| Ver seed | Las 14 reglas de `library.dat` aparecen en la lista; IDs builtin nuevos se anaden al arrancar sin pisar edits |

**Donde se aplica (obligatorio):**

| Modo | Solicitud | Respuesta del modelo |
|------|-----------|----------------------|
| Chat (8 fases) | F4.3 + fast-path | F5.4 |
| Inferencia directa | Antes de enviar a Ollama | Antes de mostrar/guardar la respuesta |
| Suggestions SSH | Antes del stream LLM | Tras el Presenter, antes de entregar al usuario |

**Ejemplo:** si una keyword incluye `rm -rf /`, LAIM impide la solicitud y tambien bloquea una respuesta del modelo que proponga ese comando.

**Trazas y notificaciones:** cada denegacion escribe `logs/secure.log` (`kind=inference_denied`), `audit.dat` (grupo `secure`, accion `threat_blocked`), una notificacion admin y un evento al agente Secure (posible `block_session`). Complementa (no sustituye) la seguridad de comandos F6 (`command_security`).

**API (admin):** `GET/PUT /api/v1/config/internal/inference-security`, `POST/PUT/DELETE …/rules[/{id}]`.

#### Ventana de Contexto y Cache

| Parametro | Default | Descripcion |
|---|---|---|
| `max_context_tokens` | 8192 | Maximo de tokens de historial enviados al modelo (`num_ctx`) |
| `compaction_trigger_ratio` | 85 | % del limite al que se dispara "Chat Context Summarized" |
| `min_turns_after_compaction` | 3 | Turnos recientes que se conservan tras comprimir |
| `keep_alive_minutes` | 5 | Minutos que Ollama mantiene el modelo cargado. En Apple Silicon ≥16 GB el runtime envia `-1` (no descargar) si el valor de fabrica no se ha cambiado |

Aplica a **chat**, **direct** y **sugerencias IA en SSH**. Detalles y tabla de VRAM: manual **Ventana de contexto** en Ayuda, o seccion [26](#26-ventana-de-contexto-y-cache) mas abajo.

#### Editor IA

| Parametro | Descripcion |
|---|---|
| Modelo acciones inline | Usado por Mejorar / Reescribir / Continuar / Resumir / Traducir |
| Modelo chat del documento | Usado por el panel lateral de chat del Editor (SSE) |
| Auto-guardado | Opcional; retardo en ms (por defecto ~2000) |

Los selectores se rellenan con la lista de modelos de `ollama list` (endpoint `/api/v1/config/ollama/models`).

### 11.4 API Info — Panel de endpoints REST

Desde **config → 9 → 3. API Info**:

Este panel muestra la **documentacion interactiva** de todos los endpoints REST que expone LAIM Core (`:4320`), similar a una interfaz Swagger UI:

- Lista todos los endpoints con su metodo HTTP y descripcion
- Agrupa los endpoints por modulo (users, chat, config, remote, teacher, etc.)
- Permite consultar el esquema de peticion y respuesta de cada endpoint
- Util para desarrolladores que integren LAIM con otras herramientas

La especificacion OpenAPI se almacena cifrada en `laim.dat` y se actualiza automaticamente.

---

## 12. Seguridad y cifrado

### 12.1 Arquitectura de ficheros cifrados

LAIM usa multiples ficheros cifrados con distintas claves segun su ambito:

| Fichero | Clave de cifrado | Ambito | Contenido |
|---|---|---|---|
| `identity.dat` | `KeyLocalIdentity` (global, exclusiva) | Por instalacion | Hostname, SO, serial, clave maestra local |
| `laim.dat` | `master_key_cipher` (local, en identity.dat) | Por instalacion | Usuarios, agentes, equipos, configuracion |
| `laim.session` | `master_key_cipher` (local) | Por sesion CLI | session_id, username, role |
| `laim.sessions` | `master_key_cipher` (local) | Global | Registro de todas las sesiones |
| `laim.memory.<id>` | `master_key_cipher` (local) | Por sesion | Historial de chat cifrado |
| `soul.dat` | `master_key_cipher` (local) | Por instalacion | Conocimiento dinamico del teacher |
| `library.dat` | `KeyLibraryfiles` (global) | Todas las instalaciones | Base de conocimiento global de IA |
| `translate.dat` | `KeyInternalTranslator` (global) | Todas las instalaciones | Traducciones de la interfaz |
| `plugins.dat` | `KeyLibraryfiles` (global) | Todas las instalaciones | Registro de plugins LAIM (cifrado AES-256-GCM, igual que library.dat) |
| `prompts.dat` | `KeyLibraryfiles` (global) | Todas las instalaciones | Prompts por defecto editables de las 8 fases |

### 12.2 Cifrado AES-256-GCM

Todo el cifrado usa **AES-256-GCM** con clave derivada via **PBKDF2** (SHA-256, 100.000 iteraciones). La implementacion esta en `internal/utils/security/cipher.go`.

### 12.3 Claves globales vs. clave maestra

| Tipo | Alcance | Cuando rotar |
|---|---|---|
| **Clave maestra** (`master_key_cipher`) | Una por instalacion, generada en `laim init` | Nunca (es la clave de la instalacion) |
| **Claves globales** (`GlobalInstallationKeys`) | Iguales en todas las instalaciones de la misma version mayor | Al publicar una nueva version mayor (0.x → 1.0) |

### 12.4 Reglas de seguridad obligatorias

- **Nunca** copies `laim.dat` entre equipos — solo funciona con la clave maestra de su instalacion
- **Nunca** compartas `master_key_cipher` ni copies `identity.dat` entre instalaciones
- **Si** para compartir claves entre Share y Connect usa el **handoff** (`user_connection` + `password_connection`)
- **Nunca** se expone contenido descifrado de `laim.dat` a traves de la API ni en logs
- Las contrasenas de usuario se almacenan como hash **bcrypt** dentro del JSON cifrado de `laim.dat`

### 12.5 library.dat — Base de conocimiento global

`library.dat` contiene heuristicas verificadas de hardware IA, inferencia LLM y conceptos tecnicos que la IA usa como referencia. Se inicializa automaticamente en `laim init` y se cifra con `KeyLibraryfiles` (identica en todas las instalaciones).

### 12.5.1 prompts.dat — Prompts por defecto editables

`prompts.dat` almacena los prompts de las 8 fases del workflow que el administrador puede personalizar. A diferencia de los defaults hardcoded en Go, estos son **editables desde la UI** y persisten en la instalacion.

**Caracteristicas:**

- Se crea automaticamente en `laim init` y al arrancar `laim web` (si no existe)
- Se cifra con `KeyLibraryfiles` — misma clave que `library.dat` (clave global de instalacion)
- Es un **fichero comun**: identico en todas las instalaciones del mismo major-version
- Puede distribuirse entre plataformas con `scripts/distribute_common_files.ps1`

**Como editar los prompts:**

Accede desde **Config → 2. Tiers de modelos → botón Prompts** en cualquier fila de fase. El modal muestra el contenido actual ya relleno y editable. Al guardar, los cambios se persisten en `prompts.dat`.

**Prioridad de resolucion:**

```
1. Override de perfil activo (laim.dat)    ← maxima prioridad
2. prompts.dat                             ← editable por el administrador
3. Defaults hardcoded en Go               ← fallback inmutable
```

**Distribucion de prompts mejorados:**

Cuando el equipo de LAIM mejora los prompts base de una version, distribuye el nuevo `prompts.dat` preconfigurado. Para adoptar estos cambios sin perder tus personalizaciones:

1. Haz backup: copia `prompts.dat` a un lugar seguro
2. Ejecuta `scripts/distribute_common_files.sh` o `.ps1` desde el nodo de estudio para copiar el nuevo `prompts.dat`
3. Si quieres recuperar alguna personalizacion anterior, edita manualmente los campos correspondientes en la UI

> **Nota de seguridad:** `prompts.dat` no contiene credenciales ni secretos de usuario. Puedes copiarlo entre equipos con la misma version mayor de LAIM sin riesgo.

### 12.6 soul.dat — Conocimiento dinamico

`soul.dat` contiene el conocimiento aprendido por el agente Teacher de los feedbacks de usuarios. Se cifra con la `master_key_cipher` local. Es especifico de cada instalacion y no debe copiarse entre equipos.

### 12.7 Proteccion activa de ficheros (Tier 1 / Tier 2 / Tier 3)

A partir de la version 0.48.1 LAIM implementa un sistema de proteccion de ficheros en **tres capas** que se aplica automaticamente en cada `laim init` y en cada arranque de `laim web`.

#### 12.7.1 Tier 1 — Endurecimiento de permisos

LAIM restringe el acceso a sus ficheros sensibles a nivel de sistema operativo:

| Fichero / directorio | Permisos Unix | Windows |
|---|---|---|
| Directorio raiz de instalacion (`bin/*/`) | `0700` — solo el propietario | DACL owner-only via `icacls` |
| `laim.md` / `identity.dat` (clave maestra en identity) | `0600` — solo el propietario | DACL owner-only |
| `laim.dat`, `soul.dat`, `soulmachine.dat`, `library.dat`, etc. | `0600` — solo el propietario | DACL owner-only |
| `laim.session`, `laim.sessions` | `0600` — solo el propietario | DACL owner-only |
| Directorio `logs/` | `0750` — owner escribe, grupo lee | DACL owner-only |
| Ficheros `*.log` | `0640` — owner escribe, grupo lee | DACL owner-only |
| Directorio `memory/` y `config/` | `0700` — solo el propietario | DACL owner-only |

Funcion central: `ProtectLAIMInstall()` en `internal/utils/file_protect.go`.

**En Windows** se ejecuta `icacls <path> /inheritance:r /grant:r "<usuario>:(F)"` para eliminar herencias de ACL y otorgar control total solo al usuario actual.

#### 12.7.2 Tier 2 — Verificacion de integridad HMAC-SHA256

Cada vez que LAIM escribe un fichero cifrado genera un fichero de firma companero `<nombre>.sig` que contiene el HMAC-SHA256 del contenido, derivado de la `master_key_cipher`.

| Fichero protegido | Fichero de firma | Momento de firma | Momento de verificacion |
|---|---|---|---|
| `laim.dat` | `laim.dat.sig` | `SaveDataStore` | `LoadDataStore` |
| `soul.dat` | `soul.dat.sig` | `SaveSoulStore` | `LoadSoulStore` |
| `soulmachine.dat` | `soulmachine.dat.sig` | `SaveSoulMachineStore` | `LoadSoulMachineStore` |
| `library.dat` | `library.dat.sig` | `SaveLibraryStore` | _(verificacion futura)_ |
| `translate.dat` | `translate.dat.sig` | `SaveTranslateStore` | _(verificacion futura)_ |
| `laim.sessions` | `laim.sessions.sig` | `SaveSessionRegistry` | _(verificacion futura)_ |
| `notifications.dat` | `notifications.dat.sig` | `SaveNotificationStore` | _(verificacion futura)_ |

**Comportamiento ante manipulacion detectada:**

- LAIM registra un evento `INTEGRITY_VIOLATION` en `console.log`.
- La operacion de carga se cancela con error `ErrTampered`.
- El usuario ve un mensaje de error generico (sin detalles tecnicos internos).

**Retrocompatibilidad:** si no existe fichero `.sig` (instalacion anterior al Tier 2), la verificacion se omite silenciosamente la primera vez. Tras el primer guardado se genera la firma.

Los ficheros `.sig` se excluyen de Git (`.gitignore`) ya que son especificos de cada instalacion.

#### 12.7.3 Tier 3 — Inmutabilidad selectiva (Linux y macOS, opcional)

Para los ficheros que raramente cambian tras la instalacion (`laim.md`, `library.dat`, `translate.dat`) es posible activar un flag de inmutabilidad a nivel de sistema operativo:

| Plataforma | Mecanismo | Efecto |
|---|---|---|
| Linux | `chattr +i` | El fichero no puede borrarse ni modificarse, ni siquiera por el propietario, hasta ejecutar `chattr -i` |
| macOS | `chflags uchg` | Flag "user immutable" — protege del borrado sin requerir root |
| Windows | No soportado | `ErrImmutableNotSupported` |

**Patron de escritura con inmutabilidad** (cuando se actualiza un fichero inmutable):

```
1. chattr -i / chflags nouchg  (quitar inmutabilidad)
2. os.WriteFile(path, data, 0o600)
3. ProtectFile(path)                (restringir permisos)
4. chattr +i / chflags uchg         (re-aplicar inmutabilidad)
```

Funciones disponibles en `internal/utils/file_immutable.go`: `MakeImmutable`, `MakeWritable`, `WriteWithImmutability`.

> **Nota:** `chattr +i` en Linux requiere el privilegio `CAP_LINUX_IMMUTABLE` o root. Si LAIM no se ejecuta con esos permisos, la operacion fallara con un aviso en `console.log` pero no abortara el arranque.

#### 12.7.4 Limites del modelo de proteccion

Ningun mecanismo de proteccion de ficheros puede resistir:

- Acceso por **root** o **Administrator** del sistema operativo.
- Capturas de **RAM** si el atacante tiene acceso fisico al sistema.
- Volcados de proceso (ej. `/proc/<pid>/mem` en Linux).

La proteccion esta disenada para usuarios del mismo sistema sin privilegios de superusuario.

#### 12.7.5 Comprobacion del estado de proteccion

Despues de `laim init` o `laim web`, LAIM registra en `console.log` el resultado de la aplicacion de permisos:

```
[init] file-protect applied to installation directory
```

Si hay errores parciales (ej. fichero no existia todavia):

```
[init] file-protect partial: logs/console.log: chmod: ...
```

Los errores parciales no bloquean el arranque; son informativos.

---

## 13. Agente Teacher y soul.dat

El agente **teacher** aprende del feedback de los usuarios sobre comandos incorrectos, sugerencias o advertencias y guarda el nuevo conocimiento en `soul.dat`.

> **Agent Box:** el Teacher usa por defecto el perfil `sandbox_code` (§5.7). Antes de persistir en `soul.dat`, el middleware de privacy redacta secretos tipicos en los campos de texto. Evita pegar contrasenas o claves en el feedback aunque el filtro exista.

### 13.1 Como funciona

```
Usuario → "Sugerir mejora" → trabajo de cola «teacher» (P3) → Teacher Agent
                                               ↓
                         Extrae primero la leccion (bloque de cierre)
                                               ↓
                Pregunta al usuario solo si no hay leccion (max. 2)
                — el trabajo se aparca: no ocupa un worker GPU mientras espera
                                               ↓
                                    Almacena en soul.dat (cifrado)
                                               ↓
          Prompts al instante; caminos deterministas solo verificada (§13.3)
```

**Desde pkg54a (VersionAgent 0.58.67, VersionWeb 0.64.10):**

- **Bloque de cierre.** `teacher.md` pide exactamente `summary:` / `keywords:` / `category:` / `wrong:` / `correct:` / `repair_cmds:` (separados por `;;`) / `interest_tokens:`, con palabras clave y tokens de interes en espanol e ingles, y prohibe las preguntas de cortesia al final. El parser lee tambien las claves en espanol (`resumen:`, `palabras clave:`, `categoría:`, `incorrecto:`, `correcto:`, `comandos:`, `tokens de interés:`). Un prompt de administrador sin el bloque recibe el contrato anadido. El prompt de sistema (teacher.md, plataforma, contexto de soul.dat) llega de verdad al modelo — antes de pkg54a se perdia.
- **Primero la leccion.** Una respuesta con `summary:` o un par `wrong:`→`correct:` se guarda aunque termine en «?». Solo una respuesta sin leccion es una pregunta; tras **2** preguntas se guarda lo que dijo el usuario con confianza ≤ 0,4.
- **Pregunta aparcada.** Una pregunta deja el trabajo en `paused_input` y libera su worker GPU y su slot de Ollama; la conversacion vive en el payload del trabajo. La respuesta (`POST /api/v1/queue/jobs/{id}/respond`, el modal, la respuesta a la notificacion, la pagina SSH) lo vuelve a encolar. La pregunta caduca a las **2 h**: el trabajo falla con «pregunta caducada, no se guardó nada / question expired, nothing was saved». Un teacher en marcha ahora **se puede cancelar** (atiende el contexto del trabajo); cancelar avisa «no se guardo nada». Tras un reinicio la pregunta pendiente se vuelve a aparcar con el tiempo que le quedaba.
- **Contexto y plataforma.** El primer turno lleva el contexto del chat (o de la pagina SSH); la plataforma de la leccion es la del equipo destino de la conversacion (`computer_id`), nunca la de la maquina que pinta la web.
- **Connect.** El esclavo es dueno de la conversacion (pregunta, respuesta, caducidad, cancelacion, notificacion); cada turno corre en el master Share con la historia (`/api/v1/share/remote/teacher/feedback`, sin estado). El `learn_action` del master lleva la `entry` guardada, el esclavo la sincroniza en su `soul.dat`, y su `created_by` es el usuario del esclavo, no la credencial Connect.

**Como se usa soul.dat (pkg54b, VersionAgent 0.58.70):**

- **Prompts del modelo — toda entrada, al instante.** Las entradas relevantes para la pregunta del usuario (BM25 con acentos plegados, equivalentes en espanol e ingles, incluidos los `interest_tokens` del teacher) y para la **plataforma del equipo destino** llegan a los prompts del modelo del chat: la via rapida y F3 (junto a la *Knowledge reference* de library.dat, seccion `## Learned from users (soul.dat)`), el enriquecimiento F6 de los agentes local y remoto, F7 y las Sugerencias remotas (ordenadas por el mensaje del usuario o, en el primer turno, por la pantalla). Como maximo **3 entradas / ~1500 bytes** por prompt, cada una marcada `verified` o `pending admin review`; si ninguna es relevante no se inyecta nada. Una entrada nunca autoriza un comando: command_security y el consentimiento siguen aplicando. La unica excepcion (pkg62) es una exencion de consentimiento verificada (§13.3.2): sustituye el consentimiento de un usuario a un comando de riesgo exacto en un equipo y nunca cambia el veredicto de command_security.
- **Caminos deterministas — solo entradas verificadas (D2).** Marca `"verified": true` (y, si hace falta, `"priority"`, `"keywords"`, `"repair_cmds"`) con `PUT /api/v1/teacher/soul/{id}` tras revisar la entrada, o desde la pagina **Revision del alma** (§13.3, pkg54c). Solo entonces cambia: el filtro de comandos conocidos como malos (CMD-SOUL-001 tambien toma el comando `wrong:` del teacher) y el orden de reparacion. Una entrada sin verificar solo llega al texto que escribe el modelo. **Desde pkg54d ninguna leccion cambia un presentador determinista** (decision del usuario 2026-10-25: «el caso del tamaño en MB es solo un ejemplo de solicitud de un usuario, no hemos de tocar el código de LAIM por este ejemplo»): el caso especial de la unidad de memoria de pkg54b/pkg54c ya no existe y el carril de memoria vuelve a ser `free -h` / CIM en GB, mostrado tal cual lo imprimio el comando (la fila de intercambio en español `Inter:` se sigue leyendo y un valor redondeado nunca se reconvierte). Una leccion como «la memoria muestramela en MB» abre ahora el **modal de contradiccion** (§13.3.1).
- **Prioridad (D3).** Una entrada **verificada** con prioridad **> 7** va **antes** de la guia/reparacion estatica del caso (comandos de la primera pasada y F6.3R). Las no verificadas mantienen la guia estatica primero y solo se usan si no hay reparacion estatica. Las correcciones del teacher (`wrong:` + `correct:`) se guardan con prioridad 8 y los consejos con 5.
- Las plataformas se comparan normalizadas (`darwin`/`macos` → `mac`, `win*` → `windows`), las escrituras de soul.dat se serializan en el proceso y F6.3R remoto cuenta el uso/exito de las entradas que ejecuto.

### 13.2 Configuracion del agente Teacher

Desde **Configuracion → 9. Internal → 2. Local** (seccion «Agente Teacher») puedes configurar:

- **Teacher activo** (`Teacher.Enabled`, desde pkg54c **se aplica**): desactivado, el boton **«Sugerir mejora»** desaparece del chat, de la pagina del terminal SSH y de un esclavo Connect, y `POST /api/v1/queue/submit {type:"teacher"}` (y el SSE heredado `/api/v1/teacher/feedback`) se rechazan con el codigo `teacher_disabled` y un mensaje en el idioma del usuario. En un master Share desactivado, la «Sugerir mejora» de sus esclavos tambien se rechaza («desactivado en el master Share»). Una instalacion que nunca guardo este valor lo tiene **activo** (antes de pkg54c la casilla desmarcada no se guardaba); solo un «desactivado» guardado explicitamente lo apaga.
- **Desactivar no borra ni oculta nada**: las entradas de `soul.dat` se siguen usando en los prompts y en los caminos deterministas (decision conservadora: lo aprendido sigue valiendo) y siguen en la pagina de revision. Un trabajo «Sugerir mejora» que ya estaba en cola o esperando tu respuesta termina normalmente.
- **Tier del modelo**: que tier usa el teacher (por defecto `medium`).
- **Prompt del teacher**: el prompt de sistema del agente (editable por admin).

### 13.3 Revision del alma (soul.dat) — pagina de administrador

**Configuracion → 9. Internal → 10. Revision del alma (soul.dat)** (solo administradores: el menu no la muestra a otros roles y la API responde 403). El menu muestra entre parentesis cuantas entradas estan **pendientes de revision**, en este elemento y en «Internal». No hay notificacion por cada entrada nueva (decision conservadora: el contador basta).

- **Filtros:** pendientes / verificadas, plataforma, categoria, origen (`user_feedback`, `teacher`, `auto_correct`, `contrastive_learn`, `presenter_learn`, `connect_sync`, …) y texto (sin distinguir mayusculas ni acentos: «servício» encuentra «servicio»). Primero las pendientes, despues las mas recientes.
- **Cada entrada** muestra resumen, palabras clave, `wrong` / `correct`, comandos de reparacion con el veredicto de **command_security** (`CheckCommand`: permitido, de riesgo, prohibido, con regla y motivo; para `all` el peor de Windows, macOS y Linux), tokens de interes, prioridad, confianza, origen, autor (`created_by`), plataforma, fechas, usos / exitos, quien la verifico y cuando, y **«Al verificarla»**: los efectos deterministas que activa.
- **Que significa verificar.** Una entrada sin verificar ya llega a los prompts del modelo (marcada `pending admin review`) y **no cambia nada determinista**. **Verificarla** activa sus efectos deterministas: su comando `wrong:` entra en el filtro de comandos conocidos como malos (CMD-SOUL-001), sus comandos de reparacion entran en el orden de reparacion (con prioridad **> 7**, **antes** de la guia/reparacion estatica del caso: la pagina lo avisa). Ninguna leccion cambia como presenta LAIM un valor (pkg54d). **Volver a pendiente** los quita al instante. Los comandos de reparacion siguen pasando por command_security y por el consentimiento del usuario al ejecutarse.
- **Contraste con Ecosystem antes de verificar** («contrastar todo con ecosystem»). Verificar (o editar una entrada ya verificada) ejecuta primero una comprobacion **de solo lectura**: `validate` y `consistency` de Ecosystem (nunca `apply` ni `propose`) y command_security sobre `repair_cmds`, `wrong` y `correct`. Se **rechaza** (422 `ecosystem_refused`, mensaje es/en) si aparece un error o aviso **nuevo**, es decir causado por la entrada: un comando de reparacion o `correct` prohibido (error), un `wrong` que filtraria una lectura propia de LAIM (aviso), o un error/aviso de Ecosystem sobre el agente dueño del alma (`agent:teacher`). **Desde pkg54d un comando de reparacion o `correct` de riesgo ya no lo impide** (decision del usuario 2026-10-25: «permitir verificarlo, y asegurarse de que está en el log»): es un aviso visible en la pagina (`risky_commands` en el contraste, categoria `command_risk`), la verificacion sigue adelante y queda en el registro de auditoria con los comandos de riesgo y sus reglas; al ejecutarse sigue pidiendo consentimiento **cada vez** (la unica excepcion es una exencion de consentimiento verificada de ese comando exacto, usuario y equipo, §13.3.2). Lo prohibido sigue impidiendolo. Los demas hallazgos de Ecosystem no dependen de soul.dat: se muestran como contexto y no bloquean. El boton **Contrastar con Ecosystem** de cada entrada lo ejecuta sin verificar (`POST /api/v1/teacher/soul/{id}/ecosystem`).
- **Editar:** resumen, palabras clave, categoria, `wrong`, `correct`, comandos de reparacion (uno por linea), tokens de interes, prioridad 1–10 y plataforma. Un campo vacio lo borra. **Comprobar comandos** muestra el veredicto antes de guardar; al guardar se vuelve a comprobar en Go. Un comando **prohibido** impide guardar comandos nuevos y verificar la entrada (422 con todos los veredictos); uno **de riesgo** se acepta y se avisa (pedira consentimiento).
- **Borrar** pide confirmacion en la misma pagina («¿Borrar esta entrada definitivamente?»), nunca un dialogo del navegador.
- **Registro de auditoria (pkg54d).** Cada **verificacion, vuelta a pendiente, edicion y borrado** (y el alta manual, que queda verificada) se escribe en el registro de auditoria de LAIM (`audit.dat`, `laim audit` y Configuracion › Auditoria, grupo **«Alma (soul.dat)»**, acciones `soul_verify` / `soul_unverify` / `soul_edit` / `soul_delete`): quien y cuando, el id de la entrada, su prioridad y plataforma, sus comandos de riesgo con sus reglas y los hallazgos de Ecosystem del contraste. Las contradicciones detectadas (`soul_contradiction`) y lo que eligen los usuarios (`soul_choice`) van al mismo grupo.
- **Marca de contradiccion (pkg54d).** Una entrada que el detector encontro muestra **«⚡ Contradiccion ×N»** con los tipos vistos, cuantas veces los usuarios la **rechazaron** (mantuvieron la respuesta de LAIM o eligieron la otra leccion), la **aplicaron** en un turno o la **enviaron a revision**, y la ultima fecha. El filtro de estado tiene **«contradiction»**. Enviarla a revision no cambia si esta verificada: decides tu.
- **Connect / Share.** Un esclavo guarda de cada leccion que le llega del master el id y la fecha de creacion de la entrada del master. Cada 10 minutos (desde el latido Connect) pregunta al master por esas entradas (`POST /api/v1/share/teacher/soul/review`, cifrado; el master solo contesta si coinciden id **y** fecha) y aplica la revision del master: **verificar, editar y borrar** en el master llegan a las copias de sus esclavos. Una edicion local en el esclavo se mantiene hasta que el master vuelva a cambiar la entrada. Una copia verificada (`connect_sync`) cuenta como correccion del teacher en CMD-SOUL-001.

### 13.3.1 Contradicciones (pkg54d)

Decision del usuario 2026-10-25: «si LAIM detecta alguna contradicción, avisar en un modal proponiendo alternativas para que el usuario elija». Con la respuesta ya entregada, LAIM compara el turno con sus lecciones **relevantes** y, si una lo contradice, el usuario ve un modal. Go detecta y construye las alternativas (`internal/utils/soul_contradiction_pkg54d.go`); Reflex y la pagina SSH solo las presentan.

**Que lecciones.** Las entradas que enseñan los usuarios (`user_feedback`, `teacher`, `connect_sync`; las medidas `auto_correct` / `contrastive_learn` no son lecciones) que el BM25 de soul.dat devuelve para la pregunta en la plataforma del equipo destino (las 10 primeras) **y** que comparten su tema: al menos una palabra no generica de la pregunta (sin acentos, con su equivalente en español/ingles) es una de sus palabras clave / tokens de interes, o dos estan en cualquier parte de la entrada. Las palabras genericas («equipo», «computer», «sistema», «servidor», «cuánta», «how», «show»…) nunca cuentan solas. Verificada o no: la deteccion solo **muestra**; una leccion sin verificar sigue sin cambiar ningun camino determinista.

**Reglas de deteccion** (deterministas; campos estructurados + palabras clave sin acentos; nunca un modelo; en caso de duda no se avisa):

| Tipo | Regla | Se avisa cuando |
|---|---|---|
| 1 leccion vs respuesta | `unit` | respondio un carril determinista (su caso, o el caso heuristico cuyas lecturas se ejecutaron) **y** la leccion pide una unidad de bytes (un verbo de mostrar o «en/in/a/to» antes de MB/MiB/GB/GiB/KB/KiB/TB/TiB, es/en; una unidad tras «no», «not», «instead of», «en lugar de», «en vez de», «rather than» es rechazada, no pedida) **y** la respuesta muestra una cantidad en otra escala (una que la leccion rechaza, o cualquier otra si no rechaza ninguna) |
| 1 | `wrong_ran` | un comando que se ejecuto en el turno es el `wrong` de la leccion (el comparador de CMD-SOUL-001: mismo comando; mismo binario en una leccion «not found»; patrones de metodo) |
| 1 | `other_form` | el comando de la leccion (`correct` si es una linea de comando, `repair_cmds`) ejecuta el mismo programa que uno que se ejecuto, con otros argumentos, y no esta entre ellos |
| 2 leccion vs leccion | `wrong_is_correct` | el `wrong` de A coincide con un comando de B |
| 2 | `opposing_correct` | las dos tienen el mismo `wrong` y distinto `correct` |
| 2 | `opposing_unit` | las dos piden una unidad de bytes de distinta escala, o una rechaza la de la otra |
| 3 leccion vs guia/reparacion estatica (cualquier prioridad) | `wrong_static` | el `wrong` de la leccion coincide con un comando de la reparacion estatica del caso (`HeuristicStaticRepairCommands`) |
| 3 | `static_other` | un comando de la leccion ejecuta un programa de la reparacion estatica con otros argumentos |
| 3 | `wrong_guide` | el `wrong` de la leccion coincide con el comando de apertura o la alternativa CLI de la guia grafica certificada (la del carril de cambios, si no la de detras de una lectura) |
| 3 | `guide_must_not` | el programa de un comando de la leccion (≥ 3 letras, sin `.exe`/`.cpl`) es una palabra completa de una linea «no hacer» de la guia |
| 4 leccion vs seguridad | `forbidden` / `risky` | un comando de la leccion es Prohibido / De riesgo para command_security en la plataforma del turno |

**`risky` se avisa una sola vez por leccion y usuario (pkg54e, agent 0.58.74).** Decision del usuario 2026-10-25: «avisar solo una vez». El primer turno que avisa `risky` de una leccion avisa al usuario y queda registrado en la entrada de soul.dat (`risky_warned`, cifrado con el resto de la entrada, escrito bajo el bloqueo de escritura de soul.dat; sobrevive a un reinicio y nunca se envia a un esclavo Connect). Los turnos siguientes del mismo usuario no avisan nada de esa leccion; un turno cuyos unicos conflictos eran esas repeticiones no abre ningun modal. Se avisa **otra vez** cuando cambia el conjunto de comandos de riesgo de la leccion en esa plataforma (SHA-256 de la evidencia «comando (id de regla)» ordenada: una edicion del administrador de `correct` / `repair_cmds`, o un cambio de reglas de command_security) o cuando la leccion se ha verificado desde entonces (sin verificar → verificada, o verificada de nuevo por el administrador). Claves (`SoulRiskyWarnKey`, nombre de usuario en minusculas, mas la plataforma del turno): `user:<usuario>@<plataforma>` para el chat web y la pagina de Sugerencias SSH (la misma cuenta se avisa una vez en cualquiera de las dos); `connect:<usuario>@<plataforma>` para el turno de un esclavo Connect en el master Share (la cuenta de la sesion remota; su aviso se muestra en otra instalacion, por eso se cuenta aparte); un turno anonimo con solo id de sesion: `session:<id>@<plataforma>`, solo en memoria; sin usuario ni sesion: sin clave, se avisa siempre. **No cambia:** todos los demas tipos y reglas (`forbidden` incluida) avisan en cada turno como antes, y un comando de riesgo sigue pidiendo consentimiento **cada vez que se ejecuta** (salvo con una exencion de consentimiento verificada, §13.3.2) — «una vez» es solo el aviso del modal. **Auditoria:** el primer aviso (`soul_contradiction`) y la eleccion del usuario (`soul_choice`) se registran como antes; una repeticion suprimida **no** se escribe en el registro de auditoria, solo se cuenta en el registro del usuario (`repeats`, `last_repeat`). La pagina **Revision del alma** añade «usuarios avisados una vez (riesgo): N» al marcador de contradiccion de la entrada (solo el numero; quien fue avisado se queda en soul.dat).

**El modal** muestra lo que hizo LAIM (su caso determinista y los comandos ejecutados), lo que dice cada leccion (verificada o pendiente), por que chocan y las alternativas, en el idioma del usuario:

- **Mantener la respuesta de LAIM** — siempre.
- **Usar la leccion X en este turno (con tu consentimiento)** — solo si la leccion tiene comandos y **ninguno es Prohibido** (un comando prohibido nunca se ofrece como ejecutable; con dos lecciones se ofrecen A y B por separado). En el chat encola un trabajo de chat de seguimiento que ejecuta los comandos por el flujo normal: command_security, la pregunta de consentimiento de cada comando de riesgo y la del lote (`Workflow.RunSoulLessonTurn`); no se ejecuta nada donde LAIM no puede ejecutar comandos. El trabajo solo nombra la contradiccion: los comandos se quedan en el servidor para ese usuario. En la pagina de Sugerencias SSH cada comando abre el dialogo de ejecucion de la pagina (la confirmacion de riesgo del Core y el rechazo de lo prohibido).
- **Enviar al administrador para revision** — siempre; se cuenta en la entrada.
- Una leccion sin comandos (p. ej. una preferencia de presentacion) solo ofrece mantener / revision (conservador: LAIM no reescribe una respuesta medida).

**Transporte.** Evento SSE `soul_contradiction` en el flujo del trabajo **despues** de «done» (el worker GPU nunca espera la eleccion); `POST /api/v1/teacher/contradictions/{id}/respond {choice}` (solo su dueño, una vez, una de las alternativas; 2 h). Conectado en el chat Reflex (ruta de la cola), la pagina de Sugerencias SSH (respuestas deterministas y del modelo) y un esclavo Connect: el turno del esclavo corre en el master Share, que registra la contradiccion y envia un **aviso no modal** (`notice_only`) que se muestra en el chat del esclavo, sin alternativas (no se pueden aplicar desde el esclavo). La ruta SSE directa `/api/v1/chat/stream` no lo avisa.

**Registro.** Cada deteccion (`soul_contradiction`: superficie, plataforma, trabajo, equipo, pregunta, cada conflicto con su tipo, regla, entradas y evidencia literal) y cada eleccion (`soul_choice`: quien, la eleccion, las lecciones, los comandos y cuales son de riesgo) va al registro de auditoria; las entradas reciben `contradiction_count`, `contradiction_kinds`, `last_contradiction`, `rejected_count`, `applied_count`, `review_requests`.

### 13.3.2 Exenciones de consentimiento (pkg62)

Decision del usuario 2026-10-27: «Toda orden arriesgada debe de llevar consentimiento por parte del usuario, salvo que en algunas ocasiones esto lo pueda cambiar el usuario con la opción "Sugerir mejora" de LAIM.» Una **exencion de consentimiento** es la unica excepcion a «un comando de riesgo pide consentimiento cada vez que se ejecuta». Es de Go (`internal/utils/soul_consent_waiver_pkg62.go`, `internal/inference/consent_waiver_pkg62.go`); Reflex solo la presenta.

- **Solicitud (usuario).** Solo desde **Sugerir mejora**, solo para un comando de riesgo que el usuario **aprobo** en su ultimo turno (cada punto de consentimiento informa de la respuesta del usuario; un turno es la pregunta hecha, una pausa de 30 minutos empieza otro, la opcion desaparece a las 2 h). La ventana muestra **«🔓 No volver a preguntarme por este comando»** con una casilla por comando (`GET /api/v1/teacher/waiver/candidates`); marcarla guarda una entrada **pendiente** de soul.dat (`POST /api/v1/teacher/waiver`, origen `consent_waiver`, auditoria `soul_waiver_request`). El texto de la sugerencia nunca se analiza para esto (conservador: una opcion explicita, no NLP). La entrada no tiene palabras clave ni comandos y nunca llega a los prompts del modelo ni a los caminos deterministas.
- **Verificacion (administrador).** La entrada muestra **🔓 Exencion de consentimiento** en esta pagina: comando, usuario, equipo y plataforma, la regla al pedirla, command_security ahora y si esta activa. Solo **Verificar** la activa, tras el mismo contraste de solo lectura con Ecosystem (añade un aviso visible `command_risk`) y la auditoria (`soul_verify` + `soul_waiver_verify`); guarda la regla en ese momento. Verificar se **rechaza** si el comando ahora es **prohibido** («un comando prohibido nunca se exime»), ya no es de riesgo, o su regla ha cambiado desde la solicitud (el usuario debe volver a pedirla).
- **Alcance.** Ese comando exacto (espacios colapsados, mayusculas respetadas), ese usuario (sin distinguir mayusculas) y ese equipo (id de `laim.dat`, o `localhost` para esta maquina), en esa plataforma, con la regla verificada. Todo lo demas sigue preguntando. El agente local del turno de un cliente Connect (localsystem en el cliente) y un nodo de inferencia Share nunca usan una exencion.
- **Uso.** Solo se comprueba donde LAIM preguntaria: localsystem, remotesystem, el carril de cambios, ▶ Ejecutar de Sugerencias SSH y el «Ejecutar» del programador con el usuario delante. command_security clasifica primero; lo Prohibido nunca llega a un punto de consentimiento. Cada uso se registra (registro de decisiones `soul_consent_waiver`, `console.log`) y se audita (`soul_consent_waiver`: entrada, usuario, equipo, comando, regla, carril); la respuesta del chat termina con «🔓 Exencion de consentimiento aplicada» y el resultado de ▶ Ejecutar muestra la misma linea. Una ejecucion programada desatendida nunca usa una exencion.
- **Revocacion, al instante.** **Volver a pendiente** la desactiva (una nueva verificacion la activa otra vez con la regla de ese momento); **editar** la entrada le quita la exencion; **Borrar** la elimina; cualquier otra escritura la desactiva. Cada una se audita (`soul_waiver_revoke`, con el motivo). Un cambio de regla la anula sin hacer nada.

### 13.4 Gestion de soul.dat desde la API

Todas solo admin, salvo `status`:

| Metodo | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/teacher/status` | `{enabled}` para cualquier sesion; los admin reciben tambien `pending_review` |
| GET | `/api/v1/teacher/soul?status=&platform=&category=&source=&q=` | Lista de revision con efectos, aviso «antes de la estatica» y veredictos |
| GET | `/api/v1/teacher/soul/summary` | `{total, pending, verified}` |
| POST | `/api/v1/teacher/soul` | Alta manual (verificada; 422 si un comando esta prohibido) |
| POST | `/api/v1/teacher/soul/check` | Veredicto de `{platform, repair_cmds}` |
| POST | `/api/v1/teacher/soul/{id}/verify` · `/unverify` | Verificar (tras el contraste con Ecosystem) / volver a pendiente |
| POST | `/api/v1/teacher/soul/{id}/ecosystem` | Contraste de solo lectura con Ecosystem |
| PUT | `/api/v1/teacher/soul/{id}` | Edicion validada (prioridad 1–10, categoria y plataforma conocidas, CheckCommand) |
| DELETE | `/api/v1/teacher/soul/{id}` | Borrar |
| POST | `/api/v1/teacher/contradictions/{id}/respond` | Eleccion del usuario en el modal de contradiccion (cualquier sesion, solo su dueño; pkg54d) |
| GET | `/api/v1/teacher/waiver/candidates` | Los comandos de riesgo que el usuario de la sesion aprobo en su ultimo turno (cualquier sesion; pkg62) |
| POST | `/api/v1/teacher/waiver` | `{candidate_id}` → una exencion de consentimiento pendiente (cualquier sesion, solo sus candidatos; 404 si no; pkg62) |

`GET /api/v1/teacher/soul?status=contradiction` lista las entradas con marca de contradiccion.

### 13.5 Integracion con la heuristica

Desde pkg54b la guia estatica de `heuristic_guide.go` ya no gana siempre: una entrada **verificada** con prioridad > 7 y comandos de reparacion va **antes** de la reparacion estatica del caso; las no verificadas solo se usan despues de la estatica (o si no hay). Auto-correct, contrastive_learn y presenter_learn tambien escriben entradas (sin HITL) con su propio `source`; las de auto_correct / contrastive_learn alimentan CMD-SOUL-001 siempre (se midieron), las del teacher solo verificadas.

---

## 13bis. soulmachine.dat — inventario del equipo local

`soulmachine.dat` es el **alma de la maquina** donde corre esta instalacion LAIM: un inventario cifrado del hardware y del sistema operativo de **este** host. No confundirlo con `soul.dat` (conocimiento aprendido por el agente Teacher) ni con `library.dat` (base de conocimiento global compartida entre instalaciones).

### 13bis.1 Para que sirve

| Uso | Comportamiento |
|---|---|
| Chat sobre el localhost | Cuando la pregunta apunta a **este equipo** (`LocalHostQuery`), el workflow inyecta el bloque `## Local machine (soulmachine.dat)` en F3 y en el fast-path |
| Heuristica `local_machine` | Caso registrado en las tres guias (Windows / macOS / Linux) para consultas del tipo «que hardware tiene este equipo», «specs de esta maquina», etc. |
| Adaptacion futura | Base para reglas de adaptacion a VRAM/RAM/GPU (tiers, prompts); por ahora solo aporta contexto al LLM |

### 13bis.2 Ubicacion y cifrado

| Propiedad | Valor |
|---|---|
| Ruta | Mismo directorio que el binario (`LAIMConfigDir()/soulmachine.dat`) |
| Cifrado | AES-256-GCM con `master_key_cipher` de `laim.md` (igual que `laim.dat` / `soul.dat`) |
| Firma de integridad | `soulmachine.dat.sig` (HMAC-SHA256) |
| Portabilidad | **No** — un fichero por instalacion; no copiar entre equipos |

El cuerpo de `laim.md` se guarda **scrubbed**: se elimina la seccion `## Encryption Keys` y cualquier linea que mencione `master_key_cipher`. Nunca se persiste la clave maestra dentro de `soulmachine.dat`.

### 13bis.3 Contenido del almacen

```
SoulMachineStore
├── Platform          (windows | mac | linux)
├── Info              ← snapshot estructurado equivalente a `laim info`
│   ├── OS, Arch, Kernel, Hostname, HostModel, Uptime, Shell, LocalIP
│   ├── CPU, GPU, GPUDriver, GPUVRAM, RAM, Disk
│   ├── OllamaVersion, OllamaModels[]
│   └── CollectedAt
├── LaimMDBody        ← laim.md sin master_key_cipher
├── InfoLoaded / LaimMDLoaded
├── UpdatedAt
└── Diffs[]           ← historial de cambios (max. 20) en re-init
```

### 13bis.4 Ciclo de vida

```
laim init (fresh)
  → CollectSoulMachineInfo + ReadLaimMD (scrubbed)
  → crea soulmachine.dat

laim init (re-init, ya existe)
  → compara snapshot anterior vs nuevo
  → guarda Diffs + actualiza Info / LaimMDBody
  → puede anexar el informe CompareSpecs de laim.md

Arranque / comando (info, chat, web, config, monitor, localmodels)
  → si soulmachine.dat no existe y hay master_key → EnsureSoulMachine (bootstrap)
  → si ya existe → no re-sondea (evita I/O; datos vivos siguen en `laim info` / F6)
```

| Evento | Accion |
|---|---|
| Primera `laim init` | Crea el fichero con info + `laim.md` scrubbed |
| `laim init` posterior | Actualiza snapshot y registra diferencias (hasta 20 entradas) |
| Falta el fichero | Bootstrap automatico al usar comandos que asumen instalacion |
| `laim chat` / web | Solo lectura bajo demanda; inyeccion si `LocalHostQuery` |

### 13bis.5 Share / Connect

Cada nodo (master o slave) tiene su propio `soulmachine.dat`, cifrado con la clave maestra **local** de ese equipo. En modo Connect, cuando el usuario pregunta por el host de ejecucion (el cliente), se usa el inventario del **slave**, no el del Share.

### 13bis.6 Operaciones de administrador

| Accion | Como |
|---|---|
| Forzar regeneracion | Borrar `soulmachine.dat` (+ `.sig`) y ejecutar `laim init` o `laim info` |
| Ver datos vivos actuales | `laim info` (no lee el fichero; sondea el sistema) |
| Ver diffs historicos | Descifrar en memoria via API Go (`LoadSoulMachineStore`); no hay panel UI dedicado aun |
| Backup | Incluir `soulmachine.dat` y `soulmachine.dat.sig` en copias locales de la carpeta del binario (misma maquina) |

### 13bis.7 Reglas de seguridad

- **Nunca** exportar `soulmachine.dat` con `master_key_cipher` dentro (el scrub es obligatorio en codigo).
- **Nunca** copiar el fichero a otra instalacion o equipo.
- **Nunca** volcar el contenido descifrado a disco ni a logs (`console.log` solo registra eventos `read`/`write`).
- Tratarlo como dato sensible de instalacion, al mismo nivel que `laim.dat` y `soul.dat`.

### 13bis.8 Diferencias con soul.dat y library.dat

| Fichero | Contenido | Clave | Ambito |
|---|---|---|---|
| `soulmachine.dat` | Inventario HW/OS de **esta** maquina | `master_key_cipher` local | Una instalacion |
| `soul.dat` | Conocimiento heuristico aprendido (Teacher) | `master_key_cipher` local | Una instalacion |
| `library.dat` | Base de conocimiento tecnica global | `KeyLibraryfiles` (global) | Todas las instalaciones del same major-version |

---

## 14. Sistema de plugins

LAIM soporta plugins opcionales que extienden funcionalidades sin crear dependencias duras en el core. Cada plugin es un **ejecutable nativo independiente por plataforma** (no una librería `.so`/`.dll` cargada en proceso — ese enfoque se descartó por ser incompatible con Windows), acompañado de un manifiesto declarativo.

### 14.1 Estructura de un plugin instalado

```
plugins/<nombre>/
├── manifest.json              # nombre, version, tier, capacidades declaradas
└── <nombre>_mac | _silicon | _linux | _windows.exe   # binario para este host
```

Al arrancar, LAIM escanea `plugins/<nombre>/manifest.json` de cada carpeta y fusiona esos metadatos (descripción, versión, tier, capacidades) con el registro `plugins.dat`. La llamada real a la funcionalidad del plugin se hace como **subproceso** (el mismo patrón que usa la conversión de voz `tts_snac`): LAIM lanza el binario, le pasa los datos necesarios por `stdin` en JSON (nunca por línea de comandos ni variables de entorno) y lee el resultado de `stdout`. Si el binario del plugin no está presente en esta instalación o falla al arrancar, LAIM degrada automáticamente al camino interno equivalente cuando existe uno — sin interrumpir la funcionalidad.

### 14.2 Fichero plugins.dat

- **Ubicacion**: mismo directorio que el binario (junto a `laim.md` y `laim.dat`)
- **Formato**: binario cifrado AES-256-GCM con `KeyLibraryfiles` (igual que `library.dat`)
- **Creacion automatica**: se genera cifrado con los plugins basicos al arrancar si no existe
- **Distribucion**: fichero comun a todas las instalaciones del mismo major-version; usar `scripts/distribute_common_files.ps1` tras anadir o actualizar plugins
- **Migracion automatica**: si existe un `plugins.dat` en formato plano (version anterior), LAIM lo detecta, lo parsea y lo re-persiste cifrado de forma transparente en el primer arranque

> **Nota de seguridad**: `plugins.dat` no contiene secretos en texto plano. Las `ActivationKey` de plugins licensed se almacenan en el campo correspondiente dentro del fichero cifrado, nunca en texto plano en disco. **Un `manifest.json` nunca puede activar un plugin ni asignarle una clave de licencia por sí mismo** — los campos `Active`/`ActivationKey` viven exclusivamente en `plugins.dat` y solo el administrador los controla (desde la UI/CLI de gestión de plugins). Esto evita que colocar una carpeta en `plugins/` sea suficiente para autoactivar funcionalidad de pago.

### 14.3 Tipos de plugin

| Tipo | Etiqueta | Descripcion |
|---|---|---|
| **basic** | `(Basic)` | Viene con LAIM Core; no requiere licencia |
| **licensed** | `(Advance)` | Plugin premium; requiere clave de activación ligada al número de serie de la instalación |

> El esquema criptográfico de verificación de licencia para plugins `(Advance)` está en diseño — todavía no hay plugins licenciados publicados.

### 14.4 Plugins basicos incluidos

| Nombre | Version | Descripcion |
|---|---|---|
| SentFileToRemote | 0.8.6 | Envía ficheros a equipos remotos registrados. La transferencia real corre como subproceso (`cmd/sentfiletoremote`); si el binario no está compilado en esta instalación, se degrada automáticamente al envío en proceso sin interrupción para el usuario. |

### 14.5 Ver plugins instalados

```bash
laim version
```

La salida incluye una seccion **Plugins** con los plugins activos, su tier, versión, y si se cargaron desde `plugins/<nombre>/` (con binario encontrado para esta plataforma o no) o siguen compilados directamente en el binario principal (variante heredada, sin carpeta propia).

### 14.6 Qué no está implementado todavía

- Comando `laim plugin install` para dar de alta un plugin nuevo detectado en `plugins/` que no tuviera ya una entrada en `plugins.dat`. Hoy la incorporación de plugins nuevos es un paso de mantenimiento.
- Verificación criptográfica de licencia para plugins `(Advance)`.

---

## 15. Sistema de traduccion i18n

LAIM soporta multiples idiomas en su interfaz. Las traducciones se almacenan en `translate.dat` (cifrado con `KeyInternalTranslator`).

### 15.1 Idiomas soportados

| Codigo | Nombre | Bandera |
|---|---|---|
| `en` | English | Bandera inglesa |
| `es` | Espanol | Bandera espanola |

### 15.2 Como cambia el idioma el usuario

1. En la pantalla de login, haz clic en la bandera del idioma deseado
2. O desde la cabecera de la aplicacion una vez autenticado
3. La preferencia se guarda en el perfil de usuario (`UserRecord.Language` en `laim.dat`)

### 15.3 translate.dat

El fichero `translate.dat` contiene las cadenas de la **interfaz** (botones, menus, mensajes cortos) organizadas por modulo (login, chat, config, remote, etc.). Se inicializa automaticamente en `laim init`. **No** almacena el cuerpo de los manuales ni de los informes.

### 15.4 Traduccion visual de manuales e informes

En **Ayuda** (manuales), **Informes** y el modal **Info** del catálogo de skills/tools, las banderas flotantes 🇬🇧 / 🇪🇸 traducen el **texto** del Markdown al idioma pedido si difiere del idioma del documento. La estructura GFM (titulos, tablas, listas, fences) la reconstruye Go (`ContentTranslatorAgent`); el tier **Traductor** solo traduce unidades de texto.

| Aspecto | Detalle |
|---------|---------|
| API | `POST /api/v1/content/view`, `GET /api/v1/content/job/{id}`, `GET /api/v1/content/meta` |
| Cache | `LAIMConfigDir()/content_i18n/{manuals,reports,ecosystem}/` (hash + `format_version`). Inspect de skill/tool: `kind=ecosystem`, id `skill.<id>` / `tool.<id>` |
| Documentos largos | Job async con progreso «Pagina N/M»; slot Ollama por pagina. **Excepcion:** los manuales `admin`, `user`, `headscale` y `windows_remote` no se traducen en Connect (horas via Share); ambas lenguas van de fabrica en Ayuda. |
| Calidad | No se persiste una traduccion incompleta (soft-fail / cuerpo aun en el idioma origen). Si falla la calidad pero ya hay fichero bueno en el idioma pedido, se sirve ese fichero |
| Informes de sesion de chat | Boton 📋 en el composer → `POST /api/v1/chat/report` → `reports/` (grupo UI **Inferencias**) |
| Copia de conversacion Direct | Boton 📋 en Inferencia directa → `POST /api/v1/direct/conversations/{id}/report` → `reports/` (grupo UI **Direct**). Permite borrar el historial sin perder el contenido |

### 15.5 Manuales por idioma (`spanish` / `english`)

Los manuales de Ayuda viven en el arbol de fuentes (y se embeben en el binario):

| Carpeta | Uso |
|---------|-----|
| `internal/manuals/spanish/` | Fuente canónica en espanol (admin, user, recommendations, headscale, context_window, windows_remote) |
| `internal/manuals/english/` | Ingles (traduccion persistida o fuente EN) |

**Comportamiento en runtime:**

1. Manuales `admin`, `user`, `headscale` y `windows_remote`: bilingües de fabrica (ES+EN). En Connect, si falta una lengua se sirve la disponible (sin aviso tecnico). Las banderas 🇬🇧/🇪🇸 permanecen visibles.
2. Si existe el fichero del idioma pedido → se sirve **sin** llamar al LLM.
3. Si no existe (resto de manuales) → se traduce una vez (tier Traductor) y, tras pasar el gate de calidad, `WriteManualTranslation` escribe en `LAIMConfigDir()/manuals/{english|spanish}/` y, en checkout de desarrollo, tambien en `internal/manuals/{lang}/` para versionar en git.
4. Override local: `LAIMConfigDir()/manuals/{spanish|english}/` tiene prioridad sobre el embed.

**Paridad obligatoria (MVP `es` + `en`):** cualquier mejora, correccion o seccion nueva en un manual debe aplicarse a **todas las versiones de idioma que ya existan** para ese manual (como minimo espanol e ingles cuando ambos ficheros esten presentes). No dejar un idioma desactualizado respecto al otro. Detalle para agentes: `AGENTS.md` § Traduccion visual / Manuales — paridad multi-idioma.

---

## 16. Sesiones y seguridad

### 16.1 Tipos de sesion

| Canal | Quien lo crea | Donde se almacena |
|---|---|---|
| `cli` | `laim login` | `laim.session` cifrado en disco |
| `web` | Login en la interfaz web | Cookie HTTP (sesion independiente) |
| `remote` | Cliente Connect autenticado | Registro en master (`laim.sessions`) |

### 16.2 Ciclo de vida de una sesion

| Evento | Accion obligatoria |
|---|---|
| `laim login` (CLI) | `RegisterSession` con `state=active`, `channel=cli`, `created_at=now` |
| Login web | `CreateWebSession` con `channel=web`; no escribe `laim.session` |
| `laim salir` | Solo sale de la consola. Sesion y Share API siguen activos |
| `laim terminar` | Escribe `ClosedAt=now`, `state=closed`; para Share API; sale del proceso |
| Web **Salir** | Solo cierra la pestana. Cookies intactas; sesion activa |
| Web **Terminar** | Llama `POST /api/v1/session/close`, limpia cookies, llama `/api/v1/shutdown` |
| Admin cierra sesion de otro usuario | `CloseManagedSession` registra `ClosedAt=now`, `state=closed` |
| Admin reanuda sesion | `ResumeManagedSession` pone `state=active`, `ClosedAt=nil` |
| Expiracion automatica | `ExpireSessionsIfConfigured` verifica `max_session_hours` |
| University (loopback) | `MintLoopbackUniversitySession` — sin contraseña; **ámbito University** (§16.5) |

### 16.3 Panel de sesiones activas

Desde **config → 1 → 2. Gestionar sesiones → 1. Sesiones activas**:
- Lista todas las sesiones activas con usuario, hora de inicio, canal y titulo
- Permite cerrar remotamente una sesion de cualquier usuario

### 16.4 Tiempo maximo de sesion

Desde **config → 9 → 2. Local**:
- `max_session_hours`: numero de horas maximas por sesion (0 = infinito)
- Se aplica a todas las sesiones del sistema
- Se verifica en cada carga de sesion y en cada login web

### 16.5 Ámbito de la sesión University (pkg90, Web 0.64.32)

`POST /api/v1/session/university` da a cualquier proceso de este equipo una sesión con la identidad del usuario LAIM activo (así habla con LAIM, sin contraseña, la herramienta de entrenamiento University). Esa sesión tiene ahora el **ámbito University**: solo puede llamar a lo que usa University — estado, su propia sesión, chat (inicio, stream, respuesta a avisos, equipos), Sugerencias remotas, relevancia heurística, el agente Ecosystem en modo de solo lectura (`inspect`, `validate`, `consistency`; nunca aprobado, sin parches, sin fichero de informe), voz (grabar, TTS), el panel del cliente mesh local y `/api/v1/university/*`. Todo lo demás — configuración, usuarios, sesiones, credenciales, ajustes Share/Connect, consola local, Import/Export — responde **403** con código `university_scope`. Los endpoints de esa lista que necesitan administrador se conceden de forma explícita: la relevancia heurística y las acciones de solo lectura de Ecosystem funcionan para el ámbito sea cual sea el rol del usuario; el cliente mesh local sigue necesitando un administrador, como antes. Una sesión duplicada a partir de ella conserva el ámbito.

`/api/v1/university/remote-exec` ahora exige una sesión web (la de University o una de operador), solo ejecuta en los equipos a los que esa sesión tiene acceso y sigue rechazando comandos de riesgo (de cambio). Cada sesión University queda en el log y en la auditoría (grupo `sessions`, objetivo `university_session`) con referencias `sr-` cortas, nunca el token.

### 16.6 Protección de la API web local (pkg90)

La API web (`127.0.0.1:4320`) solo responde a peticiones cuyo `Host` es `127.0.0.1`, `localhost` o `[::1]` en su propio puerto (o la dirección de escucha configurada), y cuyo `Origin`, si lo hay, es una página servida desde este equipo (la interfaz web en `:4321`, el editor). Lo demás — una web que usa DNS rebinding o la petición CORS previa de una página ajena — recibe **403**. `share_api` (4322), los servicios de voz/Directo del Share y `mesh_api` (4324) son servicios de LAN y siguen autenticando con sus propias credenciales.

Los monitores de red **Share** y **Remoto** identifican también cada cliente Connect y cada sesión remota por su referencia `sr-`; ningún token de sesión llega al navegador.

---

## 17. Import/Export y Backup

Ver seccion **11.1 y 11.2** para detalles completos.

### Resumen rapido

```bash
# Desde CLI
laim config → 9. Internal → 1. Import/Export

# Rutas de ficheros
config/laim_config_clear.json           # Export/Import (familias, sin identity.dat)
config/laim_install_YYYY-MM-DD_HH-MM.bak  # Backup de instalacion (tar.gz)
# legado: config/laim.dat_YYYY-MM-DD_HH-MM.bak  (gzip solo de laim.dat)
```

### Familias exportables

`users`, `model_tiers`, `tier_families`, `agents`, `computers`, `computer_groups`, `computer_access`, `skills`, `tools`, `pipelines`, `profiles`, `flows`, `flow_skills`, `local_settings`, `model_warmup`, `share`, `connect`, `headscale`, `direct`, `scheduled_tasks`, `mrtg_alerts`, `devops_catalog`

**Siempre excluidos**: `identity.dat`, `JobQueue`, serial, `WebAPIEnabled` (Backup/Restore). Los ciphers locales (`connection_key_cipher`, `password_cipher` Connect, `api_key_cipher` Headscale y de herramientas, `tailscale_node_key`, hashes de usuario, SSH) se exportan vacios, y desde pkg90 tampoco viaja el handoff Share/Connect.

---

## 17bis. Registro de Auditoria (laim audit)

LAIM mantiene un registro inmutable en `audit.dat` (cifrado como `laim.dat`) con dos familias de eventos:

1. **Cambios de configuracion** (CRUD) realizados por administradores desde CLI o web.
2. **Actividad de usuario** espejada desde `logs/activity.log` (login, chat, inferencias, decisiones de agentes, remoto, editor/voz), agrupada por naturaleza para consultarla con `laim audit` o el panel web de Auditoria.

### 17bis.1 Que se registra

Cada evento de auditoria incluye los siguientes campos:

| Campo | Descripcion |
|-------|-------------|
| `id` | Identificador unico del evento (hex) |
| `ts` | Fecha y hora UTC en formato RFC3339 |
| `user` | Usuario LAIM que realizo la accion (`bootstrap` para el primer administrador, `system` para operaciones automaticas) |
| `group` | Seccion de configuracion afectada (ver tabla de grupos) |
| `action` | Tipo de operacion: `create`, `update`, `delete`, `export`, `import`, `backup`, `restore` |
| `target` | Nombre o identificador del elemento afectado |
| `detail` | Descripcion corta de la operacion |
| `channel` | Origen de la accion: `cli` o `web` |

**Grupos de auditoria:**

| Grupo | Secciones cubiertas |
|-------|---------------------|
| `users` | Crear, modificar y eliminar usuarios LAIM |
| `agents` | Crear, modificar y eliminar agentes |
| `skills` | Crear, modificar y eliminar skills |
| `tools` | Crear, modificar y eliminar tools |
| `flows` | Crear, modificar y eliminar flujos avanzados |
| `profiles` | Crear, modificar y eliminar perfiles de inferencia |
| `models` | Cambios en tiers de modelos y mapa fases->tiers |
| `computers` | Crear, modificar y eliminar equipos remotos |
| `computer_groups` | Crear, modificar y eliminar grupos de equipos |
| `share` | Cambios Share; rotacion de clave; restart share_api; abrir firewall |
| `connect` | Cambios en la configuracion Connect |
| `headscale` | Download, configure, start/stop, preauth, sync, import-nodes, subnet |
| `internal` | Ajustes locales, log rotation, firewall LAIM |
| `import_export` | Export / import / backup / restore (web y CLI) |
| `activity_session` | Login, cierre/expiracion de sesion, access_denied (desde `activity.log`) |
| `activity_chat` | Inferencias (prompt truncado), flow_answer, inicio/fin de chat, informes |
| `activity_agents` | Consentimientos y decisiones de agentes (risky_command, forbidden_command) |
| `activity_remote` | Conexiones Share/Connect, SSH remoto (CLI y web), suggestions |
| `activity_editor` | Editor IA y speech (voz→texto) |
| `activity_other` | Otras acciones de usuario no clasificadas |
| `secure` | Amenazas bloqueadas, auth fallida, integridad, sandbox violation, anti-proxy |

### 17bis.1bis Modelo de canales (logs / audit / notificaciones)

| Canal | Uso | Anti-spam |
|-------|-----|-----------|
| `logs/console.log` | Arranques, bridges, restart, tests Connect, sandbox exec OK | Si |
| `logs/activity.log` | Inferencias, consentimientos F6 (RISKY/FORBIDDEN), SSH, expire con username | Si; espeja a `activity_*` en audit |
| `logs/secure.log` | Auth, middleware Secure, REJECT, sandbox violation, anti-proxy | Si |
| `audit.dat` | CRUD config, rotaciones, ACL, RSA view, export/import, Headscale, firewall open | Append-only; sin secretos |
| `notifications.dat` | Amenazas, fallos de servicio (Share/Headscale/firewall), jobs del usuario | **No** cada click, chat OK ni sandbox OK |

Notificaciones de sistema (`NotifySystemEvent`) solo para: Share API no escucha / firewall Share fallido / repair firewall fallido / Headscale start-stop fallido / clave Share regenerada / sandbox violation / anti-proxy (con throttle 5 min por IP).

**Que no se registra en audit:**

- Respuestas completas de la IA (siguen solo en `laim.memory` cifrado)
- Consultas de solo lectura (listar usuarios, ver configuracion, etc.)
- Secretos, contraseñas o tokens

**Nota:** `activity.log` sigue siendo el fichero de texto rotado; `audit.dat` es la vista agrupada (puente automatico al escribir actividad).

### 17bis.2 Inmutabilidad

Los eventos de auditoria **nunca se modifican ni se borran**. `audit.dat` es un fichero de solo crecimiento (append-only). No existe ningun mecanismo de purga o modificacion de eventos en el API ni en el CLI.

### 17bis.3 Acceso desde el CLI

```bash
laim audit
```

Requiere sesion activa con rol `admin`. Muestra los eventos agrupados por seccion con una tabla de columnas: Fecha/Hora, Usuario, Accion, Destino, Detalle.

Ejemplo de salida:

```
  LAIM — Registro de Auditoría  (15 eventos totales)
  ——————————————————————————————————————————————————————————————————

  ► Usuarios  (4)
  ——————————————————————————————————————————————————————————————————
  Fecha/Hora             Usuario       Acción     Destino               Detalle
  ——————————————————————————————————————————————————————————————————
  2026-07-29 09:15:33    bootstrap     create     admin                 Usuario creado (rol: admin)
  2026-07-29 09:18:44    admin         create     maria                 Usuario creado (rol: user)
  ...
```

### 17bis.4 Acceso desde la interfaz web

En la interfaz web, la auditoria esta disponible en:

```
Configuracion > Asistente de configuracion > Internal > Registro de Auditoria
```

El visor agrupa los eventos por seccion. Cada grupo muestra un contador de eventos y una tabla expandida con todos los detalles. El boton "Actualizar" recarga los datos del backend.

### 17bis.5 Seguridad y cifrado

- `audit.dat` se almacena en el mismo directorio que el binario LAIM (`LAIMConfigDir()`).
- Se cifra con la misma clave maestra (`master_key_cipher`) que `laim.dat`.
- Solo el binario LAIM de esa instalacion puede leer y escribir `audit.dat`.
- No copiar `audit.dat` entre equipos (cada instalacion tiene su propia clave maestra).
- Si `audit.dat` no existe, se crea automaticamente en el primer evento registrado.

### 17bis.5bis Robustez, copias, registros apartados y recuperación (pkg97)

**Por qué.** Hasta LAIM 0.66.5 cada evento reescribía `audit.dat` entero en su sitio (truncar y escribir) sin bloqueo entre procesos. Cuando `laim web`, un comando de la CLI y un trabajo de Ecosystem registraban eventos a la vez, el fichero podía quedar con bytes de dos escritores: dejaba de autenticarse («audit: decrypt: decrypt failed: cipher: message authentication failed») y todos los eventos posteriores se perdían.

**Ahora (`audit.dat`, `identity.dat`, `laim.dat`):**

- **Bloqueo entre procesos.** Cada escritura mantiene `<almacén>.lock` (junto al almacén, en `data/`) desde que carga hasta que guarda; los lectores lo toman compartido. Se escribe en un fichero temporal que se renombra sobre el almacén: un lector ve el fichero anterior o el nuevo, nunca uno a medias. Los `.lock` están vacíos y pueden quedarse.
- **Los cambios simultáneos en `laim.dat` ya no se pierden (pkg102).** Un cambio hecho a la vez por varios procesos (`laim web`, un comando de la CLI, el programador / `laim worker`, Ecosystem) o por dos peticiones conservaba solo el último que se guardaba. Los cambios de equipos y grupos, inscripciones de la malla y Headscale, la API de Configuración (agentes, skills, tools, pipelines, perfiles, tiers de modelos), flujos, notas, la cola de trabajos, los consentimientos del programador, la cadena de actualización y las alertas MRTG se aplican ahora sobre el `laim.dat` actual uno detrás de otro bajo `laim.dat.update.lock` (junto a `laim.dat`; guarda el pid y la operación del cambio en curso y puede quedarse). Leer `laim.dat` nunca lo espera. Si un cambio no puede empezar en 15 s la acción falla con «laim.dat is busy: another change is still being saved (held by pid …, op …)»: repítala; nada queda guardado a medias.
- **Todos los cambios de `laim.dat` van ya uno detrás de otro (pkg103, fase 2 de pkg102).** El resto de cambios —los menús de `laim config` (perfiles, tiers y familias de modelos, temperaturas, agentes, skills, tools, pipelines, Share y Connect), el resto de la API de Configuración (temperaturas, familias, Share/Connect, ajustes locales, idioma, profesor, especificación de la API), usuarios, reglas de seguridad de inferencia, rotación de logs, apps generadas y su gobierno, Direct, Headscale, el número de serie, el «apply» de Ecosystem, el constructor de agentes, la importación y los valores de fábrica— se aplican también sobre el `laim.dat` actual bajo `laim.dat.update.lock`. Un menú interactivo o un flujo largo (un modelo, Ecosystem) guarda solo los valores que cambió, así que se conserva lo que otro proceso guardó mientras tanto; si dos cambian a la vez la misma lista, gana el último. Se aplican el mismo mensaje «laim.dat is busy…» y la misma espera de 15 s.
- **Última copia buena.** `audit.dat.bak` es la versión anterior del registro, `laim.dat.bak` + `laim.dat.bak.sig` el `laim.dat` anterior con su firma e `identity.dat.bak` la identidad actual. Son el propio cifrado del almacén (misma clave maestra, permisos 0600). Si el fichero principal no se puede leer, LAIM lee la copia y lo anota en `logs/secure.log`. Las instalaciones anteriores a pkg97 obtienen sus copias en el primer guardado (identity.dat y laim.dat también al leerlos).
- **laim.dat y su firma.** La firma nueva se escribe antes como `laim.dat.sig.pending`, después `laim.dat`, y por último la firma se renombra sobre `laim.dat.sig`: tras un corte entre los dos pasos la firma pendiente sigue verificando el fichero nuevo. Un `laim.dat` que descifra pero no casa con su firma se sigue informando como manipulado; solo uno que no se puede autenticar ni descifrar pasa a la copia.
- **La clave maestra nunca se sustituye.** Si `identity.dat` falta o no se puede leer, LAIM lo restaura desde `identity.dat.bak` (apartando el ilegible). Sin copia legible, LAIM se detiene con un error explícito en lugar de crear una clave maestra nueva (una clave nueva dejaría ilegibles todos los almacenes cifrados). `laim init` sin `laim.md` conserva la clave de un `identity.dat` existente. Si ocurre, restaure `identity.dat` desde una copia de la instalación (§ Backup).

**Registro de auditoría ilegible (se aparta, nunca se borra).** El primer evento tras volverse ilegible `audit.dat` lo renombra `audit.dat.unreadable-<AAAAMMDDThhmmssZ>` (UTC), empieza un registro nuevo desde `audit.dat.bak` si descifra y registra primero un evento de **Seguridad** (`store_quarantined`) con el nombre del fichero, su tamaño, la clase de error (`authentication_failed`, `too_short`, `parse`) y cuántos eventos vinieron de la copia. El registro continúa. Los visores (`laim audit`, la página web) nunca mueven nada: muestran la copia y explican la situación.

**Página web.** Interno › Registro de auditoría muestra, en su idioma, «El registro de auditoría anterior no se pudo leer y se apartó como <fichero>; los eventos nuevos se están registrando» (o que está mostrando la última copia buena), lista los ficheros apartados con **Recuperar eventos** y los recuperados con **Ver**, y **Volver al registro actual**.

**CLI (administrador):**

```bash
laim audit                    # el registro; explica un almacén ilegible o apartado
laim audit status             # audit.dat, audit.dat.bak, apartados y recuperados: tamaño, fecha, si descifra, eventos
laim audit recover <fichero>  # p. ej. laim audit recover audit.dat.unreadable-20261013T004300Z
laim audit show <fichero>     # los eventos de un fichero del registro (p. ej. audit.dat.recovered-…)
```

**Recuperación y qué significa «SIN VERIFICAR».** `recover` nunca modifica el fichero de origen. Escribe un almacén **nuevo** cifrado `audit.dat.recovered-<UTC>` y anota la recuperación en el registro actual (`store_recovered`) y en `secure.log`. Si el fichero aún se autentica, la copia es exacta (verificada). Si no, LAIM lo descifra sin la etiqueta de autenticación (el flujo de contador de AES-GCM, con la clave de la instalación) y conserva cada evento completo que encuentra; las zonas escritas por otro escritor o dañadas salen como basura y se descartan. Esos eventos quedan marcados **SIN VERIFICAR** (`recovered`, `*` en la CLI, una etiqueta en la web): nada prueba que no se alteraran, así que úselos como indicio a contrastar (con `logs/activity.log` y `logs/secure.log`), no como registro de auditoría. Los eventos que un segundo escritor sobrescribió en la cabecera del fichero no se pueden recuperar. Con una clave errónea no se recupera nada.

### 17bis.6 Integracion con laim config (CLI)

Las operaciones realizadas mediante `laim config` (gestion interactiva de usuarios) tambien generan eventos de auditoria:

- Crear primer administrador (bootstrap): usuario `bootstrap`, canal `cli`
- Crear usuario adicional: usuario administrador activo, canal `cli`
- Modificar usuario: usuario administrador activo, canal `cli`
- Eliminar usuario: usuario administrador activo, canal `cli`

---

## 18. Mantenimiento y actualizacion

### 18.1 Actualizar LAIM

```bash
laim update
```

O desde el acceso directo en la interfaz web.

### 18.2 Recompilar desde fuentes

```bash
# Windows
powershell -File scripts/compile_core.ps1

# macOS / Linux
bash scripts/compile_core.sh
```

Los binarios se generan en `bin/{windows,mac,linux}/laim[.exe]`.

### 18.3 Distribuir ficheros comunes

Tras `EnsureLibrarySeed` (`laim web`) en el nodo donde se estudio (p. ej. Apple Silicon + University), replica `library.dat`, `translate.dat`, `plugins.dat` y `prompts.dat` a las demas carpetas `bin/*/data/`. Estan cifrados con claves globales y son identicos en todas las instalaciones del mismo major-version. El script **nunca** copia `laim.dat`, `identity.dat` ni `soul.dat`.

```bash
# Apple Silicon (origen por defecto) → Windows, Linux, macOS Intel
./scripts/distribute_common_files.sh --dry-run
./scripts/distribute_common_files.sh --from silicon
```

```powershell
# Windows (origen por defecto) → mac, silicon, linux
powershell -File scripts\distribute_common_files.ps1 -DryRun
powershell -File scripts\distribute_common_files.ps1
powershell -File scripts\distribute_common_files.ps1 -From silicon
```

### 18.3bis Datos de producto sin datos del laboratorio (pkg104)

Las versiones que se publican («Generar versión» de laim_maintenance, instaladores y parches) llevan `library.dat`, `translate.dat`, `plugins.dat`, `prompts.dat` y `default.dat` **sin ningún nombre, dominio, usuario ni dirección del laboratorio** donde se construyen. Los ejemplos de la Ayuda y de la biblioteca usan valores reservados: `server1` / `server1.example.com`, `mac1.example.com`, `example.com`, `192.0.2.x` / `198.51.100.x` (rangos de documentación) y los usuarios `admin` / `maria`. LAIM nunca ejecuta un comando con ellos (CMD-FBD-020): pide el valor real.

- **Lista de exclusión del laboratorio:** `internal/utils/security/lab_denylist.txt` (carpeta `security/`, fuera de git; se copia a mano a cada equipo de compilación como `cipher.go`). Una regla por línea: `nombre = sustituto` (literal, sin distinguir mayúsculas, nombre completo; el más largo primero) o `red IPv4 = red IPv4` con el mismo prefijo (se conserva la parte de host). Una dirección seguida de un prefijo más ancho (`192.168.0.0/16`, un rango que se describe) no se toca.
- **Comprobar** (solo lectura): `laim release check-dat bin/<plataforma>/data --denylist internal/utils/security/lab_denylist.txt` — sale con 0 si está limpio y con 1 nombrando cada fichero, regla y valor encontrado. Siempre busca además secretos (claves de Headscale/Tailscale, tokens de GitHub/OpenAI/AWS/Slack, claves privadas).
- **Sanear** (copias nuevas): `laim release sanitize-dat --in bin/<plataforma>/data --out <dir> --denylist …` — escribe en `<dir>` las copias con los sustitutos (fichero temporal + renombrado, firma `.sig` nueva si el original la tenía); un fichero sin hallazgos se copia byte a byte. Nunca modifica la carpeta de entrada.
- **laim_maintenance:** «Generar versión» ejecuta `check-dat` sobre el `data/` de cada payload con el `laim` del equipo de compilación; un hallazgo, la falta de la lista o un `laim` anterior a pkg104 detienen la versión.
- **Dominio de búsqueda:** el producto no supone ninguno (`DefaultDNSSearchDomains` vacío); sale del FQDN de los equipos registrados o LAIM lo pregunta.

### 18.4 Logs

| Fichero | Contenido |
|---|---|
| `logs/console.log` | Interacciones tecnicas generales del CLI |
| `logs/activity.log` | Actividad auditada de usuarios autenticados: inferencias, respuestas al flujo, consentimientos |
| `logs/secure.log` | **Log principal de seguridad**: autenticaciones (exito y fallo), detecciones OWASP, decisiones del agente Secure, alertas de integridad. Los fallos de login tambien generan entrada en Audit (grupo Seguridad) y notificacion `security_alert` |
| `logs/performance_local_ai.log` | Muestras de rendimiento por fase |

> Las respuestas completas de la IA **NO** se escriben en `activity.log`; van al `laim.memory` cifrado de cada sesion.

> **Seguridad:** para investigar incidentes o intentos de acceso, consulte primero `logs/secure.log` (junto a Audit → grupo Seguridad). La rotacion builtin de `secure.log` es la misma que `activity.log` (semanal, 12 copias, comprimido).

### 18.5 Entorno Python

LAIM usa `.venv_314` (entorno Python 3.14) para la interfaz web. Si se corrompe:

```bash
laim web   # Lo detecta y reinstala automaticamente
```

O manualmente:

```bash
# Unix
source .venv_314/bin/activate
pip install -r requirements.txt

# Windows
.\.venv_314\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Apple Silicon:** el mismo `laim web` instala `mlx-lm` en `.venv_314` (Direct → botón MLX / `mlx_lm.server` en `:4325`). El paquete está en `requirements.txt` con un marker PEP 508 (`darwin` + `arm64`); en Windows, Linux y Mac Intel `pip` lo omite. No hace falta un `pip install mlx-lm` aparte. Parametros de contexto, muestreo y RAM: [11.3.3 Configuracion MLX](#1133-configuracion-mlx-apple-silicon).

---

## 19. Interfaz web y API REST

### 19.1 Puertos

| Puerto | Servicio | Alcance de red |
|---|---|---|
| **4320** | API REST LAIM Core | Solo localhost (127.0.0.1) |
| **4321** | Interfaz web Reflex | Solo localhost |
| **4322** | Share API (trafico cifrado Share conectado Connect) | Red local (0.0.0.0) |

### 19.2 Autenticacion web

Las sesiones web usan cookies HTTP. La cabecera `X-LAIM-Session-ID` autentica las llamadas a la API.

### 19.3 Documentacion de endpoints

Consulta la documentacion completa de la API en:
- **Panel API Info** en la interfaz web: `config → 9. Internal → 3. API Info`
- Fichero `docs/web_api.md` en el repositorio del proyecto

### 19.4 Seguridad de la API

- La API web escucha solo en `127.0.0.1:4320` (no expuesta a la red)
- Todos los endpoints que acceden a datos sensibles requieren autenticacion
- Los endpoints de admin verifican rol `admin`
- `laim.dat` nunca se expone en texto plano a traves de la API

---

## 20. Referencia de comandos CLI

```bash
# Todos los usuarios
laim help           # Ayuda
laim version        # Version (global + por funcionalidad + plugins)
laim info           # Hardware y sistema local
laim language       # Idioma del CLI (EN o ES)
laim login          # Autenticacion (crea laim.session)
laim chat           # Chat interactivo (tier mode)
laim chat <modelo>  # Chat con override de modelo global
laim chat --ruta-ia <localhost|n|nombre|id>  # Fija antes la ruta IA (/ruta dentro del chat)
laim connect ruta [<n|nombre|id>]            # Muestra o cambia la ruta IA (usuario con sesion)
laim remote         # Gestion SSH remota
laim web            # Arrancar interfaz web (API + Reflex)

# Solo administrador
laim config         # Configuracion completa
laim init           # Inicializar workspace
laim localmodels    # Listar modelos Ollama
laim catalog        # Catalogo publico Ollama
laim connect        # Cliente Connect
laim share          # Master Share
laim agents         # Modo agente autonomo
laim update         # Actualizar LAIM
```

**Idioma de `laim info`, `laim version` y `laim agents`:** todas las etiquetas, unidades, «N/D» y sí/no siguen el idioma del CLI (español por defecto, inglés tras `laim language EN`): p. ej. «Tiempo activo │ 1 día, 2 horas, 5 minutos» / «Uptime │ 1 day, 2 hours, 5 mins», «Versiones por funcionalidad:» / «Feature versions:», «Habilitado: sí» / «Enabled: yes». Los nombres de producto y funcionalidad (LAIM Core, Chat, Connect, Share, Direct, CPU, GPU, RAM, Ollama) no se traducen. `soulmachine.dat` guarda sus valores en inglés.

**`laim info` en Windows:** el hardware se lee con PowerShell `Get-CimInstance` (solo lectura: `Win32_Processor`, `Win32_ComputerSystem`, `Win32_LogicalDisk` discos fijos, `Win32_VideoController`; `laim init` también `Win32_PnPEntity` y `Win32_DiskDrive`). `wmic`, que Windows 11 24H2 y posteriores ya no instalan, solo se usa como respaldo cuando la consulta CIM no devuelve nada y `wmic.exe` sigue presente.


### Ejemplos avanzados

```bash
# Chat con un modelo especifico (override global de tiers)
laim chat llama3.2:3b

# Ver todas las versiones por funcionalidad
laim version

# Inicializar de nuevo (crea nuevo laim.md/laim.dat — borra todo!)
laim init
```

---

## 21. Temperatura de modelos LLM

La **temperatura** es el parametro que controla el nivel de aleatoriedad en la generacion de texto de un LLM. Es posiblemente el parametro mas influyente que un administrador puede ajustar para obtener respuestas mas precisas o mas creativas segun el caso de uso.

### 21.1 Efecto de la temperatura sobre las respuestas

| Rango | Efecto | Casos de uso tipicos |
|-------|--------|---------------------|
| `0.0` | Completamente deterministico — siempre la misma respuesta | Codigo, calculo, respuestas factuales, modelos *thinking* |
| `0.1 – 0.3` | Muy consistente, minima variacion | Analisis tecnico, extraccion de datos, traduccion, CLI |
| `0.4 – 0.6` | Equilibrio precision/creatividad | Chat general, resumen, explicaciones paso a paso |
| `0.7 – 0.9` | Creativo, respuestas variadas | Brainstorming, redaccion creativa, generacion de ideas |
| `1.0 – 1.5` | Alta variabilidad, respuestas menos predecibles | Generacion artistica, exploracion de hipotesis |
| `> 1.5` | Incoherente para la mayoria de modelos | **No recomendado en produccion** |

> **Regla de oro:** cuanto mayor es la temperatura, mas "sorprendente" pero potencialmente menos preciso el resultado. Para sistemas de gestion y administracion de infraestructura como LAIM, lo habitual es mantener temperaturas bajas (0.1-0.4) para analisis tecnicos y permitir valores mas altos (0.6-0.8) solo en el tier `slow` / `alternative` para tareas de razonamiento amplio.

### 21.2 Modelos thinking — temperatura forzada a 0.0

Los modelos con razonamiento interno (*thinking*) — como `deepseek-r1`, `qwen3` con modo think activado, o cualquier modelo con `thinking_template` en su Modelfile — **requieren temperatura 0.0** para que el bloque de razonamiento interno sea coherente. Con temperatura > 0 el modelo puede entrar en bucles de razonamiento incoherentes o generar pasos intermedios contradictorios.

LAIM detecta automaticamente estos modelos y:

1. Fuerza `temperature = 0.0` en el override.
2. Marca el override como `locked = true` (bloqueado).
3. Impide subir la temperatura por encima de 0.1 en cualquier interfaz.

Para verificar si un modelo es thinking antes de asignarlo a un tier:

```
Web: config → Tiers de modelos → panel derecho → Gestionar overrides → Auto-detect
CLI: laim config → 2. Modelos IA → 15. Temperatura → 4. Auto-detect
```

### 21.3 Jerarquia de temperatura — que prevalece sobre que

LAIM resuelve la temperatura efectiva para cada llamada LLM siguiendo esta cadena de prioridad (de mayor a menor):

```
NIVEL 1 — Override por modelo (maxima prioridad)
  Ejemplo: llama3.2:3b → 0.25 (configurado manualmente por admin)
  Ejemplo: qwen3:8b   → 0.0  (auto-detected thinking, locked)

NIVEL 2 — Temperatura del tier activo
  Ejemplo: tier "medio" → 0.4
  (configurada en Modelos IA > Tiers de modelos > panel derecho > Lambda Temperatura por tier)

NIVEL 3 — Temperatura del Modelfile de Ollama
  Si el Modelfile del modelo tiene "PARAMETER temperature X", se usa ese valor.
  LAIM lo lee con Auto-detect y lo registra como override con source=modelfile.

NIVEL 4 — Default interno de LAIM por tier
  traductor: 0.2  |  rapido: 0.3  |  medio: 0.4  |  lento: 0.5
  alternativo: 0.4 | imagenes/video/sonido: 0.6  | desarrollo: 0.2
```

**Regla critica:** un valor `0.0` en cualquier nivel significa **"no configurado — ir al nivel siguiente"**, NO "forzar temperatura deterministico". La unica excepcion son los overrides `locked` de modelos thinking, donde `0.0` es el valor real forzado.

#### Resumen visual de prioridades

```
¿Hay override para este modelo? → SI  → usar override (aunque sea 0.0 si esta locked)
                                 → NO  ↓
¿Tier tiene temperatura > 0.0?  → SI  → usar temperatura del tier
                                 → NO  ↓
¿Modelfile tiene temperatura?   → SI  → usar temperatura del Modelfile
                                 → NO  ↓
Usar default del tier segun LAIM (tabla anterior)
```

### 21.4 Tres mecanismos de configuracion de temperatura

LAIM ofrece tres capas independientes de configuracion de temperatura, cada una con su proposito:

| Mecanismo | Alcance | Cuando usarlo |
|-----------|---------|---------------|
| **Temperatura por tier** | Todos los modelos asignados a ese tier | Politica uniforme para un grupo de modelos |
| **Override por modelo** | Un modelo especifico en cualquier tier | Modelo con caracter propio distinto al tier |
| **Override auto-detectado** | Un modelo especifico (automatico) | Modelos thinking o con temperatura en Modelfile |

---

### 21.5 Configurar temperatura por tier

Establece la temperatura que usaran **todos los modelos de ese tier** salvo que tengan override propio.

#### Desde la interfaz web

1. Ir a **Configuracion > Modelos IA por tier > Tiers de modelos**.
2. En el **panel derecho** aparece la seccion **Lambda Temperatura por tier**.
3. Cada tier (Traductor, Rapido, Medio, Lento, Alternativo, Imagenes, Video, Sonido, TTS EN, TTS ES, Desarrollo) tiene un campo numerico.
4. Valor `0.0` = usar el default interno de LAIM para ese tier.
5. Rango util: `0.1` (muy preciso) a `1.0` (muy creativo). Valores > 1.0 no recomendados.
6. Pulsar **Guardar tiers** (boton izquierdo) para persistir.

#### Desde CLI

```
laim config
  → 2. Modelos IA
    → 15. Temperatura de modelos
      → 7. Configurar temperatura de un tier especifico
```

#### Valores recomendados por tier

| Tier | Valor recomendado | Justificacion |
|------|------------------|---------------|
| **Traductor** | `0.1 – 0.2` | Traduccion debe ser literal y consistente |
| **Rapido** | `0.2 – 0.3` | Clasificacion y deteccion de idioma — precision ante todo |
| **Medio** | `0.3 – 0.5` | Analisis tecnico con cierta flexibilidad narrativa |
| **Lento** | `0.4 – 0.6` | Reprocessing — razonamiento profundo con algo de variacion |
| **Alternativo** | `0.5 – 0.8` | Slot de pruebas — probar valores fuera del estandar |
| **Imagenes** | `0.4 – 0.6` | Descripcion de imagen — equilibrio |
| **Video** | `0.4 – 0.6` | Analisis de fotogramas — equilibrio |
| **Sonido** | `0.2 – 0.4` | Transcripcion — preferir consistencia |
| **TTS EN** | `0.5 – 0.7` | Sintesis inglesa Orpheus (default 0.6) |
| **TTS ES** | `0.5 – 0.7` | Sintesis espanola Orpheus (default 0.6) |
| **Desarrollo** | `0.1 – 0.3` | Generacion de codigo — maxima precision |

---

### 21.6 Configurar overrides de temperatura por modelo

Un **override** asigna una temperatura especifica a un modelo concreto con independencia del tier al que este asignado. Es el mecanismo de maxima prioridad.

#### Cuando crear un override

- El modelo tiene un caracter muy diferente al tier donde esta asignado (ej. modelo creativo en tier tecnico).
- El Modelfile del modelo ya especifica su temperatura optima y quieres que LAIM la respete.
- El modelo es thinking y necesita `0.0` (LAIM puede hacerlo automaticamente).
- Has ejecutado un sweep y quieres fijar la temperatura recomendada.

#### Desde la interfaz web — modal de gestion

1. Ir a **Configuracion > Modelos IA por tier > Tiers de modelos**.
2. En el panel derecho, seccion **Override por modelo**, pulsar **🌡️ Gestionar overrides →**.
3. Se abre el **modal de gestion** con:

| Zona del modal | Descripcion |
|----------------|-------------|
| **Lista de overrides** | Modelos con override activo, su temperatura y origen |
| **Auto** (por fila) | Auto-detecta la temperatura optima desde el Modelfile |
| **Sweep** (por fila) | Lanza benchmark de 8 temperaturas en segundo plano |
| **🗑 Eliminar** (por fila) | Elimina el override (no disponible en modelos thinking locked) |
| **Selector de modelo** | Lista de modelos Ollama instalados |
| **Input de temperatura** | Valor entre 0.0 y 2.0 |
| **Guardar** | Persiste el override en `laim.dat` |
| **Auto-detect** | Detecta temperatura para el modelo seleccionado |

4. Para anadir: seleccionar modelo → introducir temperatura → pulsar **Guardar**.
5. Para auto-detectar: seleccionar modelo → pulsar **Auto-detect**.
6. El modal se cierra pulsando **✕** o haciendo click fuera.

#### Desde CLI

```
laim config
  → 2. Modelos IA
    → 15. Temperatura de modelos
      → 2. Establecer override para un modelo concreto
      → 3. Eliminar override de un modelo
      → 4. Auto-detect (lee Modelfile + detecta thinking)
```

#### Estructura del override almacenado

| Campo | Descripcion |
|-------|-------------|
| `model` | Nombre exacto del modelo en Ollama (ej. `llama3.2:3b`) |
| `temperature` | Valor float `[0.0, 2.0]` |
| `source` | `admin` (manual) / `modelfile` (leido del Modelfile) / `auto_thinking` (forzado) |
| `locked` | `true` si el modelo es thinking — temperatura fijada, no modificable |

Los overrides `locked = true` no pueden aumentarse por encima de 0.1 desde ninguna interfaz (API, CLI o web).

---

### 21.7 Auto-detect de temperatura

La funcion **auto-detect** examina un modelo especifico y registra automaticamente su temperatura optima si puede determinarse. Realiza dos comprobaciones en orden:

1. **Lectura del Modelfile**: llama a `ollama show <modelo>` y extrae `PARAMETER temperature X` si existe. Registra override con `source = modelfile`.
2. **Deteccion thinking**: analiza el nombre del modelo y el contenido del Modelfile buscando indicadores como `thinking_template`, `<think>`, nombre `deepseek-r1`, `qwen3` con think activado. Si detecta thinking, registra override `temperature = 0.0`, `locked = true`.

**Cuando ejecutar auto-detect:**
- Al instalar un modelo nuevo antes de asignarlo a un tier.
- Despues de actualizar un modelo (`ollama pull`).
- Cuando sospechas que un modelo es thinking y no estas seguro.

---

### 21.8 Benchmark de temperatura (sweep)

El **sweep** es una prueba automatica que evalua un modelo a 8 valores de temperatura distintos y recomienda el optimo para tu hardware especifico.

#### Como funciona

Se envian al modelo 4 prompts por cada temperatura probada (0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.1, 1.3):
- **3 prompts de precision** (preguntas con respuesta conocida) → mide coherencia y consistencia de respuestas.
- **1 prompt de creatividad** (tarea abierta) → mide varianza y riqueza de expresion.

Al finalizar se almacena en `laim.dat` un `ModelTemperatureEval` con:
- Tabla de puntuaciones precision/creatividad por temperatura.
- **Temperatura recomendada** = mejor equilibrio entre ambas dimensiones.

#### Desde la web

En el modal de gestion de overrides, boton **Sweep** en la fila del modelo. El benchmark se ejecuta en segundo plano (202 Accepted). Resultado disponible en unos minutos en la misma lista de overrides.

#### Desde CLI

```
laim config → 2. Modelos IA → 15. Temperatura → 5. Ejecutar sweep
                                              → 6. Ver resultados del ultimo sweep
```

> **Nota:** el sweep puede tardar varios minutos segun el tamano del modelo y el hardware. No bloquea el uso de LAIM durante la ejecucion.

---

### 21.9 Familias de tiers y temperatura

Las **Familias de tiers** (seccion 4.10 de este manual) almacenan conjuntos completos de asignaciones `tier → modelo`. Cuando activas una familia, **no se cambia la temperatura por tier** — la temperatura permanece tal como esta configurada independientemente de que familia este activa.

Si quieres que una familia incluya tambien una configuracion de temperatura especifica:
1. Activa la familia deseada.
2. Ajusta las temperaturas por tier en el panel derecho.
3. Pulsa **Guardar tiers**.

Esto es por diseno: separar la asignacion de modelos de la politica de temperatura permite ajustar cada dimension de forma independiente.

---

### 21.10 Endpoints REST de temperatura

Todos requieren sesion de administrador (`X-LAIM-Session-ID`).

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/v1/config/temperature/overrides` | Listar todos los overrides activos |
| GET | `/api/v1/config/temperature/overrides/{model}` | Override de un modelo especifico |
| PUT | `/api/v1/config/temperature/overrides/{model}` | Crear o actualizar override |
| DELETE | `/api/v1/config/temperature/overrides/{model}` | Eliminar override |
| POST | `/api/v1/config/temperature/auto-detect` | Auto-detect para un modelo |
| GET | `/api/v1/config/temperature/evals` | Listar resultados de sweeps anteriores |
| POST | `/api/v1/config/temperature/sweep` | Lanzar sweep (responde 202 Accepted, async) |

Ejemplo — crear override manual:

```http
PUT /api/v1/config/temperature/overrides/llama3.2%3A3b
X-LAIM-Session-ID: <session_id>
Content-Type: application/json

{"temperature": 0.3}
```

Ejemplo — auto-detect:

```http
POST /api/v1/config/temperature/auto-detect
X-LAIM-Session-ID: <session_id>
Content-Type: application/json

{"model": "qwen3:8b"}
```

---

### 21.11 Guia rapida — que configurar y cuando

#### Escenario 1: Instalacion nueva, modelos recien descargados

1. Ejecuta **Auto-detect** para cada modelo (detecta thinking y Modelfile).
2. Revisa la lista de overrides creados automaticamente.
3. Deja las temperaturas por tier en `0.0` (usaran los defaults internos de LAIM).
4. Empieza a usar LAIM. Si las respuestas son demasiado repetitivas, sube ligeramente el tier Medio (ej. 0.4 → 0.5).

#### Escenario 2: Quieres afinar para un caso de uso tecnico (sysadmin, codigo)

```
Tier Rapido:      0.2  (clasificacion precisa de consultas)
Tier Medio:       0.3  (analisis tecnico sin aleatoriedad)
Tier Lento:       0.4  (reprocessing — algo de variacion es util)
Tier Desarrollo:  0.1  (generacion de codigo — maxima precision)
```

#### Escenario 3: Quieres respuestas mas creativas y variadas en chat

```
Tier Medio:       0.6  (explicaciones mas ricas y narrativas)
Tier Lento:       0.7  (razonamiento mas exploratorio)
Tier Alternativo: 0.8  (pruebas de modelos en modo creativo)
```

#### Escenario 4: Tienes modelos mixtos en el mismo tier

Ej: el tier Medio tiene `llama3.1:8b` (tecnico) pero a veces lo sustituyes por `mistral:7b` (mas creativo). En este caso:

- Temperatura del tier Medio: `0.4` (valor intermedio)
- Override `llama3.1:8b`: `0.3` (lo hace mas preciso cuando esta activo)
- Override `mistral:7b`: `0.6` (aprovecha su caracter creativo)

Esto es exactamente el caso de uso ideal para los **overrides por modelo**: cada modelo funciona con su temperatura optima independientemente del tier al que este asignado.

#### Escenario 5: Experimentacion con familias de tiers

```
Familia blue (produccion):
  Medio = qwen3-fable:4b  → override: 0.4 (tecnico con algo de expresividad)
  Lento = qwen3.5:9b      → override: 0.0 (thinking, locked automatico)

Familia green (experimental):
  Medio = llama3.1:8b     → override: 0.5
  Lento = deepseek-r1:7b  → override: 0.0 (thinking, locked)

Alternancia: activar familia green, probar, volver a blue si no convence.
Los overrides por modelo se mantienen en ambas familias porque son independientes.
```

---

### 21.12 Resumen de decisiones

| Situacion | Solucion recomendada |
|-----------|---------------------|
| Modelo thinking instalado | Auto-detect → se crea override `0.0 locked` automaticamente |
| Politica uniforme para un tier | Configurar temperatura del tier (panel derecho Tiers de modelos) |
| Modelo con comportamiento distinto al del tier | Crear override especifico para ese modelo |
| Quiero saber la temperatura optima para un modelo | Ejecutar sweep → revisar recomendacion |
| Modelo con temperatura en su Modelfile | Auto-detect → LAIM la lee y la registra como override |
| Configuracion de produccion vs experimental | Familias de tiers + overrides por modelo (independientes entre si) |
| Modelos thinking en tier Lento | Normal y recomendado — `0.0` locked es correcto para reprocessing |
| Temperatura > 1.0 | Solo en tier Alternativo para experimentos — no en produccion |

---

## Exportar e Importar Modelos Ollama (redes sin internet)

LAIM permite descargar un modelo en una maquina con conexion a internet, exportarlo a un archivo `.tar.gz` y luego importarlo en cualquier otra instalacion LAIM que **no tenga acceso a internet**. Esto hace posible trabajar con IA local en redes corporativas securizadas, entornos de laboratorio, plantas industriales o cualquier infraestructura air-gap.

**No requiere ninguna version especifica de Ollama.** LAIM accede directamente al directorio de modelos (`~/.ollama/models/`) sin usar el CLI de Ollama para la exportacion.

---

### Caso de uso: despliegue en redes sin internet

```
[Maquina A — con internet]          [Dispositivo USB / disco externo]     [Maquina B — sin internet]
        |                                        |                                    |
  1. ollama pull modelo                          |                                    |
  2. LAIM: Exportar modelo  ──► modelo.tar.gz ──► copiar al USB ──► conectar USB ──► LAIM: Importar modelo
                                                                                     3. ollama list ► modelo disponible
                                                                                     4. LAIM: Asignar al tier
```

Este flujo ha sido verificado funcionalmente: el modelo importado es identico al original y responde a inferencias correctamente.

---

### Donde encontrar los botones

En la interfaz web, abre el panel **Herramientas** (barra superior, icono de llave inglesa). Encontraras un selector de modelo y, debajo de los botones de analisis, dos botones adicionales:

- **📤 Exportar modelo** — crea un archivo `.tar.gz` del modelo seleccionado
- **📥 Importar modelo** — importa un modelo desde un archivo `.tar.gz` exportado por LAIM

---

### Paso 1 — Descargar el modelo (maquina con internet)

En la maquina conectada a internet, instala el modelo normalmente desde LAIM:

- **Via interfaz web:** panel **Herramientas** > selector de modelo > campo de busqueda > pulsa **Instalar**
- **Via terminal:** `ollama pull nombre_del_modelo`

Verifica que el modelo esta disponible con `ollama list` antes de exportar.

---

### Paso 2 — Exportar a archivo (maquina con internet)

1. En el panel **Herramientas**, selecciona el modelo a exportar en el selector.
2. Pulsa **📤 Exportar modelo**. Se abrira el modal de exportacion.
3. Introduce la ruta de destino en el campo **Ruta de destino**:
   - Escribe directamente la ruta, por ejemplo: `C:\usb\modelos\llama3.2_3b`
   - O usa el boton **📁** para navegar por el almacenamiento y seleccionar la carpeta
4. Pulsa **📤 Exportar modelo**. El log mostrara el progreso en tiempo real:
   ```
   Directorio de modelos Ollama: C:\Users\usuario\.ollama\models
   Leyendo manifiesto: ...manifests\registry.ollama.ai\library\llama3.2\3b
   Archivando sha256-... (2048.0 MB)
   Archivando sha256-... (0.0 MB)
   Exportacion completada ✔  C:\usb\modelos\llama3.2_3b.tar.gz  (2048.0 MB sin comprimir)
   ```
5. LAIM agrega la extension `.tar.gz` automaticamente si no la escribiste.
6. Copia el archivo `.tar.gz` al dispositivo de almacenamiento externo (USB, disco, NAS interno).

> **Formato del archivo:** `.tar.gz` que contiene el manifiesto del modelo y todos sus blobs tal como los almacena Ollama internamente. No es un archivo GGUF independiente — es una copia exacta de la estructura de Ollama, comprimida.

---

### Paso 3 — Transferir al entorno sin internet

Copia el archivo `.tar.gz` al dispositivo externo y transportalo a la maquina de destino (red securizada). No se requiere conexion a internet en ningun momento a partir de este paso.

**Espacio necesario:** el archivo `.tar.gz` ocupa aproximadamente el mismo espacio que el modelo en Ollama (los blobs ya estan en formato binario optimizado; la compresion gzip tiene efecto minimo).

---

### Paso 4 — Importar en la maquina de destino (sin internet)

1. Conecta el dispositivo externo a la maquina de destino.
2. En el panel **Herramientas** de LAIM, pulsa **📥 Importar modelo**.
3. Usa el boton **📁** para navegar hasta el archivo `.tar.gz` y seleccionarlo, o escribe la ruta directamente.
4. Pulsa **📥 Importar modelo**. El log mostrara el progreso:
   ```
   Directorio de modelos Ollama: C:\Users\usuario\.ollama\models
   Abriendo archivo: D:\usb\modelos\llama3.2_3b.tar.gz
   Extraido: sha256-...
   Extraido: sha256-...
   Importacion completada ✔  3 fichero(s) → C:\Users\usuario\.ollama\models
   Reinicia Ollama si el modelo no aparece en 'ollama list'.
   ```
5. El modelo queda disponible en Ollama inmediatamente.

> **Si el modelo no aparece en `ollama list` tras importar:** reinicia el servicio Ollama. En Windows: cierra y vuelve a abrir la aplicacion Ollama desde la bandeja del sistema, o ejecuta en PowerShell:
> ```powershell
> Stop-Process -Name "ollama" -Force -ErrorAction SilentlyContinue
> Start-Process "ollama" -ArgumentList "serve"
> ```

---

### Paso 5 — Asignar el modelo a los tiers en LAIM

Una vez importado y visible en `ollama list`:

1. Ve a **Configuracion > Modelos IA > Tiers de modelos**.
2. Selecciona la familia de tiers activa (blue/green).
3. Asigna el modelo importado al tier deseado (rapido, medio, lento o traductor).
4. Pulsa **Guardar tiers** para confirmar.
5. El modelo estara listo para usarse en el chat y en todos los flujos de inferencia.

---

### Verificacion del ciclo completo

Para confirmar que un modelo importado funciona correctamente:

```powershell
# 1. Verificar que aparece en Ollama
ollama list

# 2. Hacer una inferencia de prueba rapida
echo "Di hola en una frase" | ollama run nombre_del_modelo

# 3. Verificar los blobs en disco (PowerShell)
$base = "$env:USERPROFILE\.ollama\models"
$manifest = "$base\manifests\registry.ollama.ai\library\nombre_modelo\tag"
if (Test-Path $manifest) { Write-Host "Manifiesto OK" } else { Write-Host "Manifiesto NO encontrado" }
```

---

### Errores frecuentes

| Error | Causa probable | Solucion |
|-------|----------------|----------|
| `modelo 'X' no encontrado. Asegurate de que esta instalado` | El modelo no esta en `ollama list` en la maquina origen | Ejecuta `ollama pull nombre_modelo` antes de exportar |
| `no se pudo crear el archivo` | Ruta de destino no existe o sin permisos de escritura | Crea la carpeta manualmente o elige otra ruta |
| `El archivo no es un gzip valido` | Archivo corrupto o no es un `.tar.gz` exportado por LAIM | Verifica la integridad del archivo (MD5/SHA256); re-exporta si es necesario |
| `no se pudo abrir el archivo` | Ruta incorrecta en la importacion | Usa el explorador de ficheros para seleccionar el archivo correcto |
| `no se pudo crear directorio` | Sin permisos de escritura en `~/.ollama/models/` | Ejecuta LAIM con permisos de administrador o ajusta los permisos de la carpeta |
| El modelo no aparece en `ollama list` tras importar | El servicio Ollama necesita reiniciarse | Reinicia Ollama (ver Paso 4) |

---

### Directorio de modelos Ollama por plataforma

| Sistema operativo | Ubicacion por defecto | Variable de entorno para sobreescribir |
|-------------------|----------------------|----------------------------------------|
| Windows | `%USERPROFILE%\.ollama\models` | `OLLAMA_MODELS` |
| macOS | `~/.ollama/models` | `OLLAMA_MODELS` |
| Linux | `~/.ollama/models` | `OLLAMA_MODELS` |

Si tu instalacion de Ollama usa una ruta personalizada (por ejemplo en un volumen con mas espacio), asegúrate de que la variable de entorno `OLLAMA_MODELS` este definida en el sistema antes de iniciar LAIM. LAIM la detecta automaticamente.

---

### Notas de seguridad

- Los archivos `.tar.gz` exportados **no estan cifrados**. Tratalos con el mismo nivel de proteccion que el modelo original (pueden contener pesos de redes neuronales potencialmente sensibles).
- LAIM verifica la integridad estructural del archivo al importar (gzip valido, entradas tar correctas, rutas sin traversal), pero **no verifica los hashes SHA256 de los blobs**. Si tu politica de seguridad lo requiere, calcula y compara los hashes SHA256 manualmente:
  ```powershell
  # Calcular hash del archivo exportado (en maquina origen)
  Get-FileHash "C:\usb\modelos\llama3.2_3b.tar.gz" -Algorithm SHA256

  # Verificar en maquina destino (debe coincidir)
  Get-FileHash "D:\modelos\llama3.2_3b.tar.gz" -Algorithm SHA256
  ```
- No compartas archivos `.tar.gz` de modelos a traves de canales no seguros sin cifrado adicional.

---

## Escenario complejo de uso de IA local desde redes externas

Este escenario describe como un usuario puede utilizar LAIM Chat con acceso a la IA local del servidor Share **desde Internet** usando una malla VPN WireGuard (Headscale) y el subnet routing de LAIM.

### Descripcion del escenario

```
┌──────────────────────────────────────────────────────┐
│  Red LAN de la oficina / casa (p. ej. 192.168.1.0/24) │
│                                                        │
│  ┌─────────────────────────────────────────────┐      │
│  │   Servidor Linux (server1.example.com)           │      │
│  │   · Headscale (control Tailscale, :8080)     │      │
│  │   · LAIM Share (Ollama + API, :4322)         │      │
│  │   · IP local: 192.168.1.50                   │      │
│  │   · Tailscale IP (malla): 100.64.0.1         │      │
│  └─────────────────────────────────────────────┘      │
│                                                        │
│  ┌───────────────────┐                                 │
│  │ PC Windows (dev)  │                                 │
│  │ · LAIM Share (UI) │                                 │
│  │ · Administra      │                                 │
│  │   Headscale       │                                 │
│  └───────────────────┘                                 │
└──────────────────────────────────────────────────────┘
              ▲ Internet
              │  WireGuard/Tailscale
              ▼
┌──────────────────────────────────────────────────────┐
│  Red externa (cafeteria, hotel, 4G, etc.)             │
│                                                        │
│  ┌────────────────────────────────────┐               │
│  │  MacBook / portatil               │               │
│  │  · LAIM Connect                   │               │
│  │  · Tailscale (cliente)            │               │
│  │  · Tailscale IP: 100.64.0.2       │               │
│  └────────────────────────────────────┘               │
└──────────────────────────────────────────────────────┘
```

El **Mac** esta en una red publica (sin acceso directo a `192.168.1.x`). Con Headscale + subnet routing, la malla WireGuard hace que el Mac pueda alcanzar todos los equipos de la subred `192.168.1.0/24` a traves del tunel cifrado, incluido el servidor LAIM Share.

### Componentes requeridos

| Componente | Maquina | Funcion |
|------------|---------|---------|
| **Headscale** (servidor control) | Linux (server1.example.com) | Controla la malla WireGuard, registra y autoriza nodos |
| **Tailscale** (cliente) | Linux + Mac | Cliente WireGuard que forma la malla |
| **LAIM Share** | Linux (o Windows) | Servidor de IA, Ollama, share_api :4322 |
| **LAIM Connect** | MacBook | Cliente fino que usa la IA del Share |
| **Subnet routing** | Linux (activado en LAIM) | Anuncia 192.168.1.0/24 a la malla |

### Requisitos previos

1. **Headscale instalado y configurado** en el servidor Linux (ver seccion "WireGuard mesh (Headscale)").
2. **Tailscale instalado** en Linux y en el MacBook.
3. Ambos nodos registrados en la malla Headscale.
4. Puerto del servidor Headscale (**8080** por defecto) accesible desde Internet (regla de firewall / NAT en el router).
5. Puerto LAIM Share (**4322**) accesible en la LAN (no necesita ser publico si se usa subnet routing).

### Paso 1 — Configurar Headscale en el servidor Linux

```bash
# En server1.example.com
laim web   # arranca la UI de administracion
# Navega a: Config > Acceso remoto > WireGuard mesh (Headscale)
# → Estado del servidor > Configurar con:
#     Server URL: https://mi-dominio-publico.com:8080
#     Puerto:     8080
# → Descargar binario Headscale
# → Arrancar
```

Alternativamente desde CLI:
```bash
laim config   # menu > Acceso remoto > Headscale
```

### Paso 2 — Registrar el servidor Linux en la malla como nodo subnet router

```bash
# En server1.example.com
tailscale up --login-server=https://mi-dominio-publico.com:8080 \
             --advertise-routes=192.168.1.0/24 \
             --accept-routes
```

Aprobar las rutas en Headscale:
```bash
headscale routes list
headscale routes enable -r <ID_de_la_ruta>
```

O desde la UI de LAIM: **Config > Acceso remoto > WireGuard mesh > Estado del servidor > Enrutamiento de subred**.

### Paso 3 — Activar el enrutamiento de subred desde la UI de LAIM (metodo recomendado)

1. Navega a: **Config > Acceso remoto > WireGuard mesh (Headscale) > Estado del servidor**.
2. Desplazate hasta la seccion **"Enrutamiento de subred"**.
3. Lee el aviso de seguridad: al activar esta opcion, **todos los miembros autenticados** de la malla podran alcanzar cualquier equipo de tu LAN.
4. El campo CIDR se pre-rellena con la subred detectada automaticamente (p. ej. `192.168.1.0/24`). Verificalo o escribe el CIDR correcto.
5. Pulsa **"▶ Activar enrutamiento de subred"**.
6. Comprueba en los logs que aparece `✅ Subnet routing activado`.

> **Seguridad:** Desactiva esta opcion cuando no necesites acceso remoto desde el exterior. Solo debe estar activo mientras el escenario de red externa este en uso.

### Paso 4 — Registrar el MacBook en la malla

Desde la UI de LAIM (en el servidor Linux):

1. **Config > Acceso remoto > WireGuard mesh > Registrar equipo en la red mesh**.
2. Selecciona el equipo Mac de la lista y genera una PreAuth Key.
3. En el Mac, ejecuta el comando mostrado:
   ```bash
   tailscale up --login-server=https://mi-dominio-publico.com:8080 \
                --authkey=<preauth-key> \
                --accept-routes
   ```
4. El Mac obtiene una IP en la malla (p. ej. `100.64.0.2`).
5. Desde el Mac puede alcanzar `192.168.1.50:4322` (LAIM Share).

### Paso 5 — Configurar LAIM Connect en el MacBook

```bash
# En el MacBook
laim config  # menu > Share/Connect > Configurar Connect
# Introduce:
#   Host del master Share: 192.168.1.50  (IP LAN del Linux)
#   Puerto:                4322
#   Usuario:               <usuario_laim>
#   Contrasena:            <contrasena_laim>
laim connect  # arranca el cliente
laim chat     # usa la IA del servidor Share
```

O desde la UI web del Mac: **Config > Share/Connect > Connect**.

### Paso 6 — Verificar conectividad

```bash
# Desde el MacBook (en red externa, con Tailscale activo)
ping 192.168.1.50         # debe responder (subnet routing activo)
curl http://192.168.1.50:4322/api/v1/share/health  # debe devolver {"status":"ok"}
```

Si el ping no responde:
- Verifica que Tailscale esta conectado en ambos nodos: `tailscale status`.
- Verifica que la ruta esta aprobada: `headscale routes list`.
- Verifica que la opcion `--accept-routes` esta activa en el cliente Mac.

### Diagrama de trafico del chat

```
MacBook (100.64.0.2)
  └─► Tailscale tunel cifrado (WireGuard)
        └─► Linux 192.168.1.50:4322  (share_api)
              └─► Ollama localhost:11434
                    └─► Respuesta SSE cifrada
                          └─► LAIM Connect (Mac)
                                └─► Chat en pantalla
```

### Resumen de puertos y reglas de firewall

| Puerto | Protocolo | Donde abrir | Para que |
|--------|-----------|-------------|---------|
| 8080 | TCP | Router (NAT publico → Linux) | Headscale control (registro de nodos) |
| 41641 | UDP | Router (NAT publico → Linux) | WireGuard data plane (Tailscale) |
| 4322 | TCP | Solo LAN (no publico) | LAIM Share API (acceso via subnet routing) |
| 4320-4321 | TCP | Solo LAN | LAIM Web API y Reflex UI |

> **Nota:** Los puertos 4322, 4320 y 4321 **no necesitan abrirse en el router publico** si el acceso se realiza exclusivamente a traves de la malla WireGuard con subnet routing.

### Consideraciones de seguridad

| Riesgo | Mitigacion |
|--------|-----------|
| Exposicion de toda la LAN a la malla | Activar el enrutamiento de subred solo cuando sea necesario; desactivarlo al terminar |
| Acceso no autorizado al servidor Share | Mantener `user_connection` y `password_connection` seguros; usar contrasenas fuertes |
| Exposicion del puerto Headscale (8080) | Considerar HTTPS con certificado; restringir acceso por IP si el conjunto de usuarios es fijo |
| Nodos no autorizados en la malla | Usar PreAuth Keys de un solo uso y caducidad corta (24h) |
| Intercepcion del trafico de chat | El trafico share_api usa cifrado AES-256-GCM de extremo a extremo ademas del tunel WireGuard |

---

## Protección anti proxy

### Qué es y por qué existe

LAIM está diseñado para funcionar **exclusivamente en el equipo local** donde está instalado. Su API REST escucha en `127.0.0.1:4320` y su interfaz web Reflex en `http://localhost:4321`. Ninguno de estos endpoints está pensado para ser accesible desde Internet ni desde la red local a través de un proxy inverso.

Si un administrador configura un proxy inverso (nginx, Caddy, HAProxy, Apache mod_proxy…) para publicar LAIM hacia el exterior, se abren vectores de ataque significativos:

- **Exposición de sesiones de usuarios** a la red pública.
- **Acceso a `laim.dat`** (configuración cifrada con credenciales y tokens).
- **Ejecución de comandos del sistema** (función F6 / agente `localsystem`) desde redes externas.
- **Acceso a la gestión de equipos remotos** (SSH/WinRM) y a modelos de IA locales.

La protección anti proxy detecta este tipo de tráfico y lo bloquea automáticamente antes de que llegue a cualquier handler de la API.

### Cómo funciona la detección

Cuando la protección está **activa** (por defecto), cada solicitud entrante se inspecciona en busca de señales de proxy inverso. Si se detecta alguna, la solicitud es rechazada con `403 Forbidden`.

**Señales que se detectan:**

| Señal | Descripción |
|-------|-------------|
| `RemoteAddr` no es loopback | La API escucha en `127.0.0.1:4320`; toda conexión legítima llega desde `127.0.0.1` o `[::1]`. Si el origen no es loopback, la solicitud no viene del navegador local. |
| `X-Forwarded-For` | Cabecera que los proxies añaden para indicar la IP real del cliente original. |
| `X-Forwarded-Host` | Nombre de host que el proxy reenvía al backend. |
| `X-Forwarded-Proto` | Protocolo original (`http`/`https`) añadido por el proxy. |
| `X-Forwarded-Server` | Nombre del servidor proxy que procesó la solicitud. |
| `X-Real-IP` | IP del cliente real, usada por nginx y otros proxies. |
| `Via` | Protocolo y versión del proxy o pasarela por donde transitó la solicitud (RFC 7230). |
| `Forwarded` | Cabecera estándar RFC 7239 que engloba los campos anteriores. |
| `Proxy-Connection` | Cabecera propietaria de algunos clientes/proxies HTTP. |
| `X-Proxy-ID` | Identificador de proxy añadido por algunos sistemas. |
| `CDN-Loop` | Cabecera de Cloudflare para detectar bucles de CDN. |
| `CF-Connecting-IP` | IP real del cliente según Cloudflare. |
| `True-Client-IP` | IP real del cliente según Akamai y Cloudflare Enterprise. |
| `X-Cluster-Client-IP` | IP del cliente en entornos de balanceo de carga en clúster. |

> **Nota:** la comprobación se realiza en cada solicitud, por lo que un cambio en la configuración (activar/desactivar) tiene efecto inmediato sin reiniciar LAIM.

### Cómo activar o desactivar la protección

**Desde la interfaz web:**

1. Navega a **Configuración › Asistente de configuración › Internal › Local — Configuración de instalación**.
2. Localiza la sección **Protección anti proxy**.
3. Usa el interruptor para activar (posición ON, por defecto) o desactivar la protección.
4. Pulsa el botón **Guardar** al final de la página para persistir el cambio.

El cambio se almacena en `laim.dat` (cifrado) y toma efecto inmediatamente.

**Desde el CLI:**

No existe comando específico; el campo se modifica a través de la API REST cuando se llama `laim config` (en futuras versiones). Actualmente el canal habitual es la web.

### Cuándo desactivar la protección (no recomendado)

Existen escenarios legítimos donde puede ser necesario deshabilitar la protección, siempre bajo responsabilidad del administrador:

- **Acceso corporativo controlado**: cuando LAIM debe ser accesible desde varias máquinas de la misma red de confianza y se dispone de un proxy inverso con autenticación robusta (mTLS, VPN interna, restricciones de IP).
- **Entornos de desarrollo**: cuando se prueba LAIM detrás de un proxy local en un entorno de desarrollo aislado sin acceso a Internet.
- **Integración con sistemas de monitorización**: cuando una herramienta de monitorización legítima añade cabeceras de seguimiento a las solicitudes.

> ⚠️ **Advertencia:** al desactivar esta protección, la seguridad de la instalación LAIM depende enteramente de los controles externos que el administrador implemente (firewall, autenticación en el proxy, restricciones de red). LAIM no puede garantizar la seguridad en este modo.

### Comportamiento ante tráfico bloqueado

Cuando la protección está activa y se detecta una solicitud de proxy, LAIM devuelve:

```json
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "error": "acceso denegado: tráfico a través de proxy inverso no permitido. Desactiva la protección anti-proxy en Configuración › Internal › Local si deseas publicar LAIM a través de un proxy (no recomendado)."
}
```

El evento **no** se registra en `activity.log` ni en `audit.dat` para no inundar los logs con solicitudes de escaneo automatizado. Los errores técnicos relacionados sí aparecen en `console.log`.

### Resumen de seguridad

| Escenario | Estado protección | Resultado |
|-----------|------------------|-----------|
| Acceso desde `http://localhost:4321` (normal) | Activa | ✅ Permitido |
| Acceso desde `http://localhost:4320` (API directa) | Activa | ✅ Permitido |
| Nginx en la misma máquina haciendo proxy a 4320 | Activa | ⛔ Bloqueado (cabecera `X-Forwarded-For`) |
| Acceso desde otra máquina de la red sin proxy | Activa | ⛔ Bloqueado (RemoteAddr no es loopback) |
| Nginx en la misma máquina haciendo proxy a 4320 | Desactiva | ⚠️ Permitido (responsabilidad del admin) |

---

---

## Agente Secure (protección continua OWASP)

### Qué es el agente Secure

El **agente Secure** es un componente de seguridad autónomo que arranca automáticamente con `laim web` y se ejecuta en segundo plano de forma continua. Su misión es detectar, verificar y bloquear comportamientos maliciosos que afecten a la API REST de LAIM, los recursos del sistema y la integridad de sus ficheros.

El agente trabaja en tres capas coordinadas:

| Capa | Componente | Rol |
|------|-----------|-----|
| **Detección rápida** | `SecurityMiddleware` | Intercepta cada petición HTTP antes de que llegue a los handlers; comprueba bloqueos activos, inyección SQL/OS/XSS y path traversal. |
| **Monitoreo continuo** | `SecureMonitor` | Goroutine de fondo que cada 30 s verifica la integridad del binario LAIM, de los ficheros clave del entorno virtual Python y los contadores de fallos de autenticación. |
| **Verificación y acción** | `SecureAgent` | Consume la cola de eventos, verifica con el LLM tier medio si se trata de un ataque real y, si lo confirma, bloquea en tiempo real, escribe en `logs/secure.log` e inscribe el incidente en `audit.dat`. |
| **Log de seguridad** | `logs/secure.log` | Fichero principal de eventos de seguridad (auth, detecciones, bloqueos). Complementa Audit y las notificaciones. |

### Flujo de eventos simplificado

```
Petición HTTP
    |
    ▼
SecurityMiddleware → SecureBlockList (IP/sesión bloqueada → 403 inmediato)
    |
    ├─ Rate-limit excedido
    ├─ Inyección SQL/OS/XSS detectada
    └─ Path traversal detectado
                             |
                    canal SecurityEvent (buffer 256)
                             |
SecureMonitor ──────────────┤
  hash binario              |
  checksums .venv_314       |
  fallos auth               |
                             ▼
                     SecureAgent.Listen()
                             |
              ┌──────────────┴─────────────┐
              ▼                             ▼
       LLM tier medio                Modo determinista
       (verifica amenaza)            (si LLM no config.)
              |                             |
       ┌──────┴──────┐              CRITICAL/HIGH → bloqueo automático
       │             │              como "amenaza presunta"
      YES            NO
       |
┌──────┴──────┐
▼             ▼
SecureBlockList  audit.dat
AddIP/Session    grupo "secure"
```

### Categorías de amenaza detectadas

| Código | Categoría OWASP | Descripción |
|--------|----------------|-------------|
| `owasp_injection` | A03 / API8 | SQL, OS, LDAP, XPath injection; XSS |
| `owasp_auth` | A07 / API2 | Brute force, credential stuffing |
| `owasp_api_abuse` | API1 / API4 | BOLA, BFLA, consumo excesivo |
| `owasp_misconfig` | A05 / API8 | Cabeceras proxy sospechosas, configs inseguras |
| `owasp_path_traversal` | A01 | `../`, null byte, codificaciones dobles |
| `owasp_rate_limit` | API4 | Tasa de peticiones >200/60s por IP |
| `owasp_session` | A07 | Session hijacking, token anómalo |
| `integrity_binary` | A08 | Hash SHA-256 del binario modificado |
| `integrity_venv` | A08 | Checksums de `.venv_314` modificados |
| `integrity_config` | A08 | Ficheros de configuración alterados |

### Severidades y comportamiento

| Severidad | Sin LLM (modo determinista) | Con LLM tier medio |
|-----------|---------------------------|-------------------|
| `critical` | Bloqueo automático como "amenaza presunta" | LLM verifica; bloqueo si confirma |
| `high` | Bloqueo automático como "amenaza presunta" | LLM verifica; bloqueo si confirma |
| `medium` | Sin acción | LLM verifica; bloqueo si confirma |
| `low` | Sin acción | Sin acción |

### Log principal: `logs/secure.log`

Todo evento de seguridad se anota en **`logs/secure.log`** (directorio de instalación, junto a `console.log` / `activity.log`):

- Autenticación correcta y fallida (CLI, web, Connect/Share)
- Eventos emitidos por el middleware y `SecureMonitor`
- Decisiones del SecureAgent (`event_received`, `threat_blocked`, `event_dismissed`, errores)
- Eventos descartados por cola llena (`event_dropped`)

La rotación programada de `secure.log` es **igual que `activity.log`**: semanal, conservar 12 copias, compresión gzip (configurable en Internal → rotación de logs).

### Registro de amenazas en auditoría

Cada incidente confirmado se registra automáticamente en `audit.dat` bajo el grupo **Seguridad**:

- **Acción `threat_blocked`**: amenaza verificada por el LLM y bloqueada.
- **Acción `threat_detected`**: evento bloqueado en modo determinista sin LLM ("amenaza presunta").
- **Acción `auth_failed`**: intento de autenticación fallido (también en `secure.log` + notificación).

Para revisar los eventos:

1. Revisar `logs/secure.log` (cronología completa de seguridad).
2. Acceder a `Configuración › Asistente de configuración › Internal › Registro de Auditoría`.
3. Expandir el grupo **Seguridad**.
4. Cada entrada muestra: timestamp, acción, IP origen, categoría OWASP y detalle del evento.

Los eventos de seguridad **no se pueden modificar ni borrar** (propiedad inmutable de `audit.dat`).

### Notificaciones en tiempo real (panel Notificaciones)

Además del registro en Audit y en `secure.log`, cada amenaza bloqueada y cada **login fallido** generan una **notificación** de tipo `security_alert` visible en el panel **Notificaciones** (sidebar, badge de no leídas). El mensaje sintetizado incluye:

- IP de origen
- Categoría legible y severidad (amenazas) o canal/usuario/motivo (auth fallida)
- Clasificación OWASP (si aplica)
- Acciones aplicadas y estado **BLOQUEADO** (amenazas)
- Referencia a `logs/secure.log` y Audit → grupo `secure`
- **Amenazas bloqueadas por SecureAgent:** un informe Markdown en Informes → **Incidencias** (`secure_*.md`) con hechos medidos, cómo LAIM lo bloqueó y un análisis (IA si el tier medio está configurado; si no, determinista, p. ej. falso positivo de «Probar conexión»). El cuerpo de la notificación cita el fichero. Los login fallidos y el REJECT de inferencia no generan este informe (otro texto de aviso).

El destinatario vacío implica **todos los administradores**. Así el admin recibe el aviso sin tener que abrir Audit en ese momento; el informe de Incidencias es la fuente de detalle para distinguir ataque real vs falso positivo. `secure.log` y Audit siguen siendo el trail inmutable.

### Skill OWASP

El agente Secure usa la skill builtin `owasp` como base de conocimiento para la verificación LLM. Incluye 7 capacidades: `detect_injection`, `detect_auth_abuse`, `detect_api_abuse`, `detect_path_traversal`, `detect_rate_abuse`, `classify_owasp_category` y `recommend_remediation`. La skill no se puede eliminar desde la UI.

### Modo determinista (sin LLM)

Si el tier medio no está configurado (`laim config → Modelos IA → Modelo medio` vacío), el agente Secure opera en **modo determinista**: bloquea automáticamente eventos `CRITICAL` y `HIGH` sin verificación LLM y los documenta como "amenaza presunta". Los eventos de severidad media o baja se descartan silenciosamente. Este comportamiento garantiza protección básica en instalaciones sin modelo de IA.

### Consideraciones de rendimiento

- El canal de eventos tiene buffer de 256 entradas. Los envíos son **no bloqueantes**: el middleware continúa sin esperar, preservando la capacidad de respuesta HTTP.
- `SecureMonitor` comprueba cada 30 segundos con consumo de CPU mínimo.
- Las llamadas LLM de verificación son asíncronas y no añaden latencia a las peticiones web.

---

## Monitor de sistema (`laim monitor`)

El **Monitor de sistema** es una utilidad de consola interactiva que proporciona visibilidad en tiempo real del estado del equipo donde se ejecuta LAIM: CPU por núcleo, memoria, disco, red y tabla de procesos. Está disponible en dos modos:

- **Modo CLI (`laim monitor`)**: ocupa el terminal completo con una interfaz TUI (Terminal User Interface) de pantalla completa.
- **Modo web**: accesible desde `Configuración › Asistente de configuración › Internal › Monitor de sistema`, que muestra los mismos datos en un panel de ancho completo dentro de la interfaz Reflex.

### Lanzar el monitor en modo CLI

```bash
# Windows
laim.exe monitor

# macOS / Linux
laim monitor
```

### Interfaz TUI — descripción de secciones

| Sección | Descripción |
|---------|-------------|
| **Cabecera** | Nombre de host, plataforma, versión LAIM, número de procesos, tiempo activo del sistema |
| **CPU** | Barra total + barra por núcleo con etiqueta de porcentaje. Color: verde (<50 %), ámbar (50–80 %), rojo (>80 %) |
| **Recursos** | Barras de MEM, SWAP, DISK con valores legibles (GB/MB). IO de red y disco en KB/s o MB/s |
| **Tabla de procesos** | Columnas: PID, NOMBRE, CPU%, MEM%, RSS, ESTADO, USUARIO, COMANDO |
| **Barra de estado** | Modo de ordenación activo, filtro activo, tasa de refresco, mensaje de acción |

### Atajos de teclado completos

#### General

| Tecla | Acción |
|-------|--------|
| `q` / `Ctrl+C` | Salir del monitor |
| `?` | Mostrar/ocultar ayuda superpuesta (*overlay*) |
| `s` / `/` | Activar modo búsqueda (filtro de texto) |
| `Esc` | Cerrar overlay o limpiar búsqueda |
| `Space` | Pausar / reanudar la actualización |
| `r` | Ciclar la tasa de refresco: 1s → 2s → 3s → 5s → 0,5s → 1s |

#### Navegación

| Tecla | Acción |
|-------|--------|
| `↑` / `k` | Mover selección hacia arriba |
| `↓` / `j` | Mover selección hacia abajo |
| `PgUp` | Subir una página en la lista |
| `PgDn` | Bajar una página en la lista |
| `Home` / `g` | Ir al principio de la lista |
| `End` / `G` | Ir al final de la lista |

#### Gestión de procesos

| Tecla | Acción |
|-------|--------|
| `K` / `x` / `Delete` | Solicitar confirmación para matar el proceso seleccionado |
| `p` | Anclar (*pin*) el proceso seleccionado al principio de la lista |
| `y` | Confirmar la eliminación del proceso (tras `K`/`x`/`Delete`) |
| `n` | Cancelar la eliminación del proceso |

#### Ordenación de columnas

| Tecla | Columna |
|-------|---------|
| `0` | CPU% (por defecto) |
| `1` | Memoria |
| `2` | PID |
| `3` | Nombre |
| `4` | Estado |

#### Búsqueda

Pulsa `s` o `/` para entrar en modo búsqueda. El texto introducido filtra la lista de procesos en tiempo real por nombre. Pulsa `Enter` para confirmar o `Esc` para cancelar y limpiar el filtro.

### Modos de refresco

La tasa de refresco se cicla con `r`:

| Tasa | Descripción |
|------|-------------|
| 1s | Por defecto — buen balance rendimiento/reactividad |
| 2s | Bajo impacto en sistemas con muchos procesos |
| 3s | Muy bajo impacto |
| 5s | Monitorización pasiva |
| 0,5s | Máxima reactividad (mayor consumo de CPU) |

### Pantalla de ayuda (`?`)

Al pulsar `?` se superpone un panel con todos los atajos disponibles. Se cierra con cualquier tecla o `Esc`.

### Monitor de sistema en la interfaz web

En la interfaz web (`Configuración › Asistente de configuración › Internal › Monitor de sistema`) se obtiene la misma información en un panel de ancho completo:

- **Auto-refresco automático**: al abrir la pantalla se inicia un ciclo de actualización cada **5 segundos** en segundo plano. Los datos se renuevan sin intervención del usuario mientras la pantalla esté abierta. Al navegar fuera, el ciclo se detiene automáticamente.
- **Botón `↻ Actualizar`**: fuerza una actualización inmediata y reinicia el ciclo de 5 s desde cero.
- **Selector de ordenación**: permite ordenar la tabla de procesos por `cpu`, `mem`, `pid`, `name` o `status`.
- **Campo de filtro**: filtra la tabla de procesos en tiempo real por nombre o PID.

### API REST del monitor

Los endpoints son de solo lectura y requieren sesión web activa:

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/monitor/stats` | Estadísticas del sistema: CPU (por núcleo y total), MEM, SWAP, DISK, IO de red y disco |
| GET | `/api/v1/monitor/processes` | Lista de procesos. Parámetros opcionales: `sort` (cpu/mem/pid/name/status), `max` (número máximo, defecto 200), `filter` (texto libre) |

**Ejemplo de consulta:**

```bash
# Procesos ordenados por CPU, máximo 20, filtrados por "python"
curl -s "http://localhost:4320/api/v1/monitor/processes?sort=cpu&max=20&filter=python" \
  -H "X-LAIM-Session-ID: <session_id>" | jq .
```

### Notas de compatibilidad multiplataforma

| Plataforma | Notas |
|-----------|-------|
| **Windows** | Requiere PowerShell o `cmd`. `gopsutil` usa WMI/Win32 para CPU y procesos. Ejecutar como administrador para ver procesos de sistema. |
| **macOS** | La tabla de procesos se obtiene con `ps(1)` (una sola invocación: `pid/pcpu/pmem/rss/state/user/args`), no con el camino gopsutil por PID (demasiado costoso y podía dejar `PROCESSES (0)` con CPU al 100%). CPU por núcleo usa `host_processor_info`. No suele hacer falta `sudo` para listar procesos. |
| **Linux** | Lee `/proc`. Sin dependencias adicionales. Compatible con distribuciones estándar. |

> Inventario del host: ver [seccion 13bis — soulmachine.dat](#13bis-soulmachinedat--inventario-del-equipo-local).

---

## Seguridad de la Share API (puerto 4322)

El puerto **4322** es la única superficie de red externamente accesible de LAIM (escucha en `0.0.0.0`). Desde la versión `VersionShare 0.5.2`, la Share API dispone de su propia capa de seguridad (`ShareSecurityMiddleware`):

### Protecciones activas en el puerto 4322

| Protección | Detalle |
|-----------|---------|
| **Block list** | `GlobalSecureBlockList` compartida con puerto 4320 — las IPs bloqueadas por el SecureAgent se rechazan también en Share API. La respuesta es **JSON** `{"error":"…"}` (no texto plano): si Connect muestra «el master Share ha bloqueado esta IP», desbloquee la IP en **Config › Share → IPs bloqueadas → Desbloquear**. El detalle del bloqueo (ataque vs falso positivo) está en Informes → **Incidencias**. Reiniciar `laim web` también vacía la lista (solo memoria). Un 403 en texto plano lo interpretaba Connect como «respuesta inválida del servidor». |
| **Rate-limit en `/auth`** | 60 peticiones en 60 segundos desde una misma IP → bloqueo inmediato (hard block con `AddIP`) + respuesta **429 JSON** |
| **Rate-limit general** | 300 peticiones en 60 segundos → evento `SecurityEvent` emitido al SecureAgent (soft, sin bloqueo inmediato) |
| **Límite de body** | `MaxBytesReader` de 2 MB — peticiones mayores son rechazadas (protege contra DoS por payload) |
| **Detección de inyección** | URL/query string escaneada con los mismos regex de `secure_detector.go` (SQL, OS, path traversal, XSS) |
| **Timeouts HTTP** | `ReadHeaderTimeout: 15s`, `ReadTimeout: 30s`, `WriteTimeout: 180s` (SSE largas toleradas), `IdleTimeout: 120s` |

> Los payloads de Share API están **cifrados** con `connection_key_cipher` — la detección de inyección opera sobre la URL y query string (capa HTTP pre-descifrado). El SecureAgent verifica los eventos emitidos usando el mismo LLM y skill `owasp` que para el puerto 4320.

### Porta 4320 (API REST local)

El puerto **4320** escucha únicamente en `127.0.0.1` y **no es accesible remotamente**. Sus protecciones adicionales incluyen:

- `MaxBytesReader` de 4 MB (límite más generoso para payloads de configuración)
- `AntiProxyMiddleware` — rechaza cabeceras de proxy inverso
- CORS restringido a la interfaz web, `http://localhost:4321` (también `http://127.0.0.1:4321`)

---

## Protección contra Prompt Injection (OWASP LLM01:2025)

El **prompt injection** es el ataque más crítico en aplicaciones LLM (OWASP LLM01; taxonomía Proofpoint: directa, indirecta/no-click, infección multiagente). Un atacante puede pegar overrides en el chat **o** ocultar instrucciones en documentos/HTML/API que el modelo procesa después.

LAIM dispone de: (1) REJECT `DES-LLM01-*` en InferenceSecurity; (2) detección determinista en `DetectPromptInjectionInText()` (`secure_detector.go`) → `SecurityEvent` `owasp_prompt_injection` severidad `HIGH`; (3) conocimiento defensivo en `library.dat` (`sec-proofpoint-*`, taxonomía PAT **sin** payloads).

**Patrones detectados:**
- `ignore previous instructions` / `ignore all instructions`
- `you are now [persona]` / `pretend you are`
- `override instructions` / `disregard all rules`
- `reveal system prompt` / `what are your instructions`
- `jailbreak` / `DAN mode` / `do anything now`
- Bloques `[SYSTEM]`, `<system>`, `## instructions ##`

**Flujo de respuesta:**
1. Detección determinista → `SecurityEvent` con categoría `owasp_prompt_injection`
2. SecureAgent verifica via LLM (skill `owasp.detect_prompt_injection`)
3. Si se confirma: bloqueo de sesión + registro en `audit.dat` grupo "Seguridad"
4. En modo determinista (sin LLM): bloqueo automático por severidad HIGH

---

## Superficie de ataque externo — resumen ejecutivo

| Vector | Puerto | Riesgo | Mitigación en LAIM |
|--------|--------|--------|-------------------|
| Brute force en auth | 4322 | Alto | Rate-limit 60/60s + hard block automático |
| Inyección HTTP (SQL/OS/XSS/Path) | 4320, 4322 | Alto | Detección regex en ambos middleware |
| Prompt injection (LLM01) | 4320 | Alto | `DetectPromptInjectionInText` + skill owasp |
| DoS por payload enorme | 4320, 4322 | Medio | `MaxBytesReader` 4MB/2MB + rate-limit |
| CSRF | 4320 | Bajo | Custom header `X-LAIM-Session-ID` (no cookies) + CORS restringido |
| Proxy inverso (exposición web) | 4320 | Bajo | `AntiProxyMiddleware` + `AntiProxyEnabled` configurable |
| Acceso remoto no autorizado | 4322 | Alto | `connection_key_cipher` + payload cifrado + block list |
| Integridad de binario/venv | Sistema | Alto | `SecureMonitor` (SHA-256, cada 30s) |
| OWASP Top 10 general | Ambos | Variable | Skill `owasp` (10 capabilities) + SecureAgent LLM |

---

---

## 22. Sandbox de Agentes LAIM

El **Sandbox de Agentes** es un entorno de ejecucion aislado que permite a los agentes internos de LAIM generar, probar y ejecutar codigo (Python, PowerShell, Bash, **Go**) sin acceder a datos de produccion ni al sistema de ficheros del host fuera de la frontera del sandbox.

> **Relacion con la Agent Box (§5.7):** el sandbox es la *habitacion* donde corre el codigo. La Agent Box decide *si* un agente concreto puede entrar (perfil `sandbox_code` o `localsystem_host`) y, ademas, filtra secretos al guardar resultados en memoria, soul o auditoria. Configura primero el perfil del agente; luego ajusta permisos de este sandbox.

Se crea automaticamente durante `laim init` en todas las plataformas.

---

### 22.1 Estructura de directorios

```
bin/<plataforma>/
└── sandbox/
    ├── sandbox.json              ← Configuracion: permisos, limites, rutas
    ├── .sandbox_ignore           ← Paths que los agentes NO pueden tocar
    ├── SANDBOX_CAPABILITIES.md   ← Documentacion para los agentes
    ├── requirements_sandbox.txt  ← Paquetes Python del venv dedicado
    ├── scripts/                  ← Scripts de ejecucion (INMUTABLES)
    │   ├── run_python.ps1 / .sh
    │   ├── run_powershell.ps1 / run_bash.sh
    │   ├── run_go.ps1 / .sh      ← compile+run (go run, modulo aislado)
    │   └── sandbox_status.ps1 / .sh
    ├── workspace/
    │   ├── scripts/              ← Scripts generados por agentes
    │   ├── output/               ← Resultados de ejecucion
    │   └── temp/                 ← Ficheros temporales
    └── logs/                     ← sandbox.log
```

Los subdirectorios se crean con `EnsureSandbox()` (llamado desde `EnsureInstallDirs()` en `laim init`). Si se borran accidentalmente, se recuperan ejecutando `laim init` de nuevo.

---

### 22.2 Resolucion del interprete Python

El sandbox busca Python en el siguiente orden de prioridad:

| Prioridad | Ruta | Descripcion |
|-----------|------|-------------|
| 1 | `sandbox/.venv_sandbox/` | Venv dedicado, instalado con `POST /api/v1/sandbox/setup` |
| 2 | `<repo>/.venv_314` | Venv de la interfaz web (raíz del proyecto; también vía `../../../.venv_314`) |
| 3 | Sistema | `python` / `python3` / `py -3` en PATH, **solo si pasan probe** (`import sys`) |

> **Importante para Windows**: el stub de la Microsoft Store (`WindowsApps\python3.exe`) no se usa: se rechaza por ruta y por probe fallido (exit 9009). Preferir `python` real o el launcher `py -3`.

### 22.2.1 Runtime Go (`SandboxLangGo`)

| Aspecto | Detalle |
|---------|---------|
| Binario | Primer `go` en `PATH` (`SandboxGoPath`) |
| Ejecucion | `go run .` sobre una copia del script en `workspace/temp/go-run_*` con `go.mod` propio (`module laimsandbox`) |
| Cache | `GOCACHE`, `GOTMPDIR`, `GOMODCACHE` bajo `workspace/temp/` |
| Formato de codigo | Un solo fichero `package main` + `func main()`; preferible stdlib |
| Timeout | Suelo por defecto **60 s** (primera compilacion); maximo 120 s |
| Estado API | `GET /api/v1/sandbox/status` incluye `go_ok` y `go_path` (opcionales; `ready` sigue dependiendo de Python + workspace) |
| Runners | `scripts/run_go.ps1` (Windows) / `scripts/run_go.sh` (Unix) |

Si `go_ok=false`, el agente Developer con lenguaje `go` devolvera error de runtime (exit 4); instala el toolchain Go en el host y reinicia LAIM.

---

### 22.3 Modelo de seguridad

El sandbox aplica una politica **default-deny**:

| Aspecto | Politica |
|---------|---------|
| **Escritura** | Solo `workspace/scripts/`, `workspace/output/`, `workspace/temp/`, `logs/` |
| **Directorio `scripts/`** | Inmutable — los scripts de ejecucion no pueden ser sobreescritos por codigo de agente |
| **Escape al directorio padre** | `filepath.Clean` resuelve cualquier `../` antes de las comprobaciones |
| **Red (outbound)** | Deshabilitada por defecto; localhost permitido |
| **Ficheros LAIM sensibles** | `laim.dat`, `laim.md`, `soul.dat`, `soulmachine.dat`, `laim.session`, `laim.sessions`, memoria de sesion — listados en `.sandbox_ignore` |
| **Tiempo de ejecucion** | 30 s por defecto; el agente puede pedir hasta 120 s; kill forzoso a `timeout + 5 s` |
| **Memoria** | 512 MB por defecto |
| **Subprocesos** | Permitidos dentro del workspace |

#### Fichero `.sandbox_ignore`

Lista los paths que ningun agente puede leer ni escribir, independientemente de los permisos declarados en `sandbox.json`. Incluye todos los ficheros de configuracion criticos de LAIM, el codigo fuente y el repositorio Git.

---

### 22.4 Tokens de escalacion de permisos

Cuando un agente necesita sobrepasar los limites del sandbox, emite un token estructurado por `stdout`. El administrador o el sistema anfitrion lee `SandboxExecResult.EscalationRequests` y decide si conceder el permiso para una ejecucion posterior.

| Token | Significado |
|-------|-------------|
| `REQUEST_PERMISSION:network_outbound` | El agente necesita acceso a internet |
| `REQUEST_PERMISSION:write_outside_sandbox` | Necesita escribir fuera del workspace |
| `REQUEST_PERMISSION:system_commands` | Necesita ejecutar comandos privilegiados del SO |
| `REQUEST_PERMISSION:filesystem_write` | Necesita escritura ampliada en el sistema de ficheros |

Ejemplo en un script Python del agente:

```python
# El agente declara su necesidad antes de intentar la operacion
print("REQUEST_PERMISSION:network_outbound")
# La operacion real se implementa solo si el host concede el permiso
```

---

### 22.5 Configuracion del sandbox (`sandbox.json`)

El fichero `sandbox.json` define todos los parametros del sandbox para la plataforma actual:

```json
{
  "version": "1.0",
  "platform": "windows",
  "sandbox_id": "laim-sandbox-windows",
  "workspace_dir": "workspace",
  "venv_rel_path": "../../../.venv_314",
  "python_version": "3.14",
  "permissions": {
    "filesystem": {
      "allow_read":  ["workspace", "scripts", "logs"],
      "allow_write": ["workspace/scripts", "workspace/output", "workspace/temp", "logs"],
      "deny_read":   ["../../laim.dat", "../../soul.dat"],
      "deny_write":  ["../../laim.dat", "../../laim.md", "scripts"]
    },
    "network": {
      "outbound_enabled":  false,
      "localhost_enabled": true,
      "requires_approval": true
    },
    "process": {
      "max_execution_time_sec": 30,
      "max_memory_mb":          512,
      "allow_shell_subprocesses": true,
      "allow_file_io":           true
    }
  },
  "escalation": {
    "network_outbound":       "REQUEST_PERMISSION:network_outbound",
    "write_outside_sandbox":  "REQUEST_PERMISSION:write_outside_sandbox",
    "system_commands":        "REQUEST_PERMISSION:system_commands",
    "filesystem_write":       "REQUEST_PERMISSION:filesystem_write"
  }
}
```

Para modificar la configuracion desde la API web:

```bash
# Ver configuracion actual
curl -H "X-LAIM-Session-ID: <session>" http://localhost:4320/api/v1/sandbox/config

# Actualizar tiempo maximo de ejecucion
curl -X PUT -H "X-LAIM-Session-ID: <session>" \
     -H "Content-Type: application/json" \
     -d '{"permissions":{"process":{"max_execution_time_sec":60}}}' \
     http://localhost:4320/api/v1/sandbox/config
```

---

### 22.6 API REST del sandbox (`:4320`)

Todos los endpoints requieren sesion de administrador (`X-LAIM-Session-ID`).

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/api/v1/sandbox/status` | Estado del sandbox: listo, path Python, workspace |
| POST | `/api/v1/sandbox/run` | Ejecutar codigo en el sandbox |
| GET | `/api/v1/sandbox/files` | Listar ficheros del workspace |
| DELETE | `/api/v1/sandbox/workspace/clean` | Limpiar contenido del workspace |
| POST | `/api/v1/sandbox/setup` | Instalar `requirements_sandbox.txt` en `.venv_sandbox` |
| GET | `/api/v1/sandbox/config` | Leer `sandbox.json` |
| PUT | `/api/v1/sandbox/config` | Actualizar `sandbox.json` |

#### Ejemplo: ejecutar un script Python

```bash
curl -X POST \
     -H "X-LAIM-Session-ID: <session>" \
     -H "Content-Type: application/json" \
     -d '{
       "language": "python",
       "code": "import platform\nprint(platform.system())",
       "filename": "check_os",
       "requested_by": "admin",
       "timeout_sec": 10
     }' \
     http://localhost:4320/api/v1/sandbox/run
```

Respuesta:

```json
{
  "stdout":      "Windows\n",
  "stderr":      "",
  "exit_code":   0,
  "duration_ms": 312,
  "script_path": "...sandbox/workspace/scripts/check_os_20260730_112000.py",
  "output_path": "...sandbox/workspace/output/check_os_20260730_112000.txt",
  "escalation_requests": []
}
```

---

### 22.7 Configurar el venv dedicado del sandbox

Para instalar el venv dedicado (`sandbox/.venv_sandbox`) con todos los paquetes de desarrollo:

```bash
# Desde la API
curl -X POST -H "X-LAIM-Session-ID: <session>" \
     http://localhost:4320/api/v1/sandbox/setup

# O manualmente (Windows)
cd bin\windows\sandbox
python -m venv .venv_sandbox
.venv_sandbox\Scripts\pip install -r requirements_sandbox.txt

# Manualmente (Unix)
cd bin/linux/sandbox   # o bin/mac/sandbox
python3 -m venv .venv_sandbox
.venv_sandbox/bin/pip install -r requirements_sandbox.txt
```

Paquetes incluidos en `requirements_sandbox.txt`:

```
requests, httpx, numpy, pandas, scipy, matplotlib
pytest, black, isort, mypy
psutil, cryptography, pyyaml, toml, jinja2, rich
sh, aiohttp, aiofiles, pydantic, typing-extensions
```

---

### 22.8 Uso por agentes internos — referencia rapida

Los agentes Go usan la API publica de `internal/utils/sandbox.go` y `sandbox_executor.go`:

```go
// Ejecutar Python desde un agente
result, err := utils.ExecuteInSandbox(utils.SandboxExecRequest{
    Language:    utils.SandboxLangPython,
    Code:        `import json, sys; print(json.dumps({"ok": True}))`,
    Filename:    "mi_agente_check",
    RequestedBy: "mi_agente",
    TimeoutSec:  15,
})
if err != nil { /* manejo */ }
if result.Violation != "" { /* path-traversal bloqueado */ }
if result.TimedOut   { /* script excedio timeout */ }

// Comprobar tokens de escalacion
for _, token := range result.EscalationRequests {
    // Ejemplo: "REQUEST_PERMISSION:network_outbound"
    log.Printf("agente solicita permiso: %s", token)
}

// Verificar si un path es escribible
if ok, reason := utils.SandboxIsPathAllowed(absPath); !ok {
    return fmt.Errorf("sandbox violation: %s", reason)
}
```

#### Casos de uso tipicos para agentes

| Caso de uso | Lenguaje | Descripcion |
|-------------|----------|-------------|
| Analisis de datos de inferencia | Python | Scripts `numpy`/`pandas` sobre salidas del workflow |
| Validacion de JSON/YAML generado por LLM | Python | Verificar que la respuesta es parseable antes de persistir |
| Prototipado de heuristicas | Python | Probar nuevas reglas de `heuristic_guide` con datos reales |
| Scripts de mantenimiento del sistema | PowerShell / Bash | Limpieza de logs, compresion, checks de disco |
| Generacion de informes | Python + `jinja2` | Informes HTML o Markdown desde datos de `laim.dat` |
| Tests rapidos de modelos Ollama | Python + `httpx` | Llamadas a `http://localhost:11434` (localhost permitido) |
| Transformacion de datos de sensores | Python + `pandas` | Pre-procesado antes de persistir en `library.dat` / `soul.dat` |

---

### 22.9 Mantenimiento y diagnostico

#### Verificar estado del sandbox

```bash
# Windows CLI
.\bin\windows\sandbox\scripts\sandbox_status.ps1

# Unix CLI
./bin/linux/sandbox/scripts/sandbox_status.sh

# Via API
curl -H "X-LAIM-Session-ID: <session>" http://localhost:4320/api/v1/sandbox/status
```

#### Limpiar workspace

```bash
# Via API (recomendado — respeta los .gitkeep)
curl -X DELETE -H "X-LAIM-Session-ID: <session>" \
     http://localhost:4320/api/v1/sandbox/workspace/clean

# Manual: borrar solo el contenido, no los directorios
# Windows
Remove-Item bin\windows\sandbox\workspace\scripts\* -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item bin\windows\sandbox\workspace\output\* -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item bin\windows\sandbox\workspace\temp\* -Recurse -Force -ErrorAction SilentlyContinue
```

#### Regenerar la estructura del sandbox

Si los archivos del sandbox se danan o eliminan:

```bash
# Basta con re-ejecutar init — EnsureSandbox() es idempotente
laim.exe init   # Windows
laim init       # macOS / Linux
```

#### Ver logs de ejecucion

```bash
# Windows
Get-Content bin\windows\sandbox\logs\sandbox.log -Wait

# Unix
tail -f bin/linux/sandbox/logs/sandbox.log
```

---

### 22.10 Seguridad avanzada — consideraciones

| Riesgo | Mitigacion en LAIM |
|--------|--------------------|
| Un agente intenta leer `laim.dat` | `.sandbox_ignore` + `SandboxIsPathAllowed` → VIOLATION, exit code 3 |
| Un agente intenta sobrescribir `run_python.ps1` | `scripts/` es inmutable → VIOLATION |
| Script con bucle infinito | Timeout (default 30 s) → `TimedOut=true`, exit code 2 |
| Path traversal (`../../laim.md`) | `filepath.Clean` resuelve la ruta y `HasPrefix` la rechaza |
| Script hace peticion a internet | La peticion falla (SO bloquea) o el agente emite token de escalacion |
| Agente instala paquetes maliciosos | Requiere `POST /api/v1/sandbox/setup` con sesion admin |

> **Nota de arquitectura:** El sandbox no usa contenedores (Docker, WSL, etc.) por razones de portabilidad y simplicidad de instalacion. La seguridad se basa en comprobaciones de path en Go, timeouts de proceso y la politica `default-deny` del `sandbox.json`. Para entornos de produccion de alta seguridad se recomienda complementar con politicas de SO (AppLocker en Windows, seccomp en Linux).

---

### 22.11 Tests del sandbox

La suite de tests cubre el sandbox en `tests/test_unit_sandbox_test.go`:

```bash
go test -v -count=1 ./tests/... -run 'TestUnit_Sandbox'
```

| Test | Que verifica |
|------|-------------|
| `_Structure_AllDirsExist` | Todos los subdirectorios existen tras `EnsureSandbox` |
| `_Structure_KeyFilesExist` | `sandbox.json`, `.sandbox_ignore`, `SANDBOX_CAPABILITIES.md`, `requirements_sandbox.txt` |
| `_Structure_RunnerScriptsExist` | Scripts de ejecucion presentes y no vacios |
| `_Config_PlatformMatchesOS` | El campo `platform` en `sandbox.json` coincide con `runtime.GOOS` |
| `_Config_VenvPathThreeLevelsUp` | `venv_rel_path` empieza con `../../../` (3 niveles hasta la raiz del repositorio) |
| `_Config_SecurityDefaults` | Outbound deshabilitado, localhost habilitado, tiempo > 0, memoria > 0 |
| `_Security_PathInsideAllowed` | `workspace/scripts/` acepta escrituras |
| `_Security_ParentEscapeBlocked` | `../laim.dat` rechazado por path-traversal |
| `_Security_RunnerScriptsDirImmutable` | `scripts/` rechaza escrituras |
| `_Execute_PythonPrintHello` | Ejecucion Python basica con captura de stdout *(requiere Python)* |
| `_Execute_EscalationTokenDetected` | Tokens `REQUEST_PERMISSION:*` detectados en resultado *(requiere Python)* |
| `_Execute_PathTraversalRejected` | Script con path externo → exit code 3 (VIOLATION) |
| `_Execute_TimeoutKillsLongRunningScript` | Script que excede timeout → `TimedOut=true`, exit code 2 *(requiere Python)* |
| `_VenvPath_ThreeLevelsUpFromSandboxDir` | Regresion matematica: 3 niveles resuelve al directorio raiz correcto |

---

## 23. Agente Developer Orquestador

El agente `developer` es el **interlocutor de LAIM para tareas de desarrollo** de alto nivel. Recibe peticiones en lenguaje natural ("crea una app que calcule…", "make a tool that…", "escribe un CLI en Go…") y orquesta un ciclo completo de desarrollo interno dentro del sandbox.

> **Acceso web:** Configuracion › Asistente › **10. Tecnico** → **Developer** (solo admin). No aparece en el sidebar Comandos.

### 23.1 Arquitectura

| Componente | Rol |
|------------|-----|
| `DeveloperAgent` | Orquestador principal: coordina sub-agentes y persiste resultados |
| `dev_researcher` | Consulta `library.dat` y `soul.dat` antes de generar codigo |
| `dev_writer` | Genera el codigo delegando en `sandbox_dev` |
| `dev_reviewer` | Revision estatica y verificacion de determinismo |
| `sandbox_dev` | Motor de ejecucion de bajo nivel en el sandbox aislado (`ExecuteInSandbox`) |

### 23.2 Flujo de orquestacion

```
LAIM (heuristica spec/plan) / Panel Tecnico → POST /api/v1/developer/request → DeveloperAgent
  DEFINE  — spec (developer_spec): lenguaje go|python, acceptance, fuera de alcance
  PLAN    — ciclo DEFINE→SHIP (dev_planning)
  BUILD   — sandbox_dev generate (o Code fijo)
  VERIFY  — ExecuteInSandbox runtime_profile sandbox_code (developer_tdd / action=test)
  REVIEW  — calidad / determinismo (dev_code_quality)
  SHIP    — Go GeneratedApp + handoff DevOps HITL; Python snippet (developer_deliver)
  → DeveloperResult (spec, code, execution_output, handoff, delivery_mode, confidence)
```

**Chat F8:** la accion `chat_script` genera un artefacto para el execution host (SkipReport). El sandbox del nodo de inferencia no se hace pasar por el Mac/Windows del usuario en Connect.

**Lenguajes soportados en el selector / API:**

| Valor | Runtime sandbox | Requisitos |
|-------|-----------------|------------|
| `python` | Interprete Python del sandbox | Venv o Python de sistema (§22.2) |
| `powershell` | PowerShell (Windows) / bash fallback | Host Windows tipico |
| `bash` | Bash | Host Unix |
| **`go`** | `SandboxLangGo` → `go run` | Toolchain `go` en PATH (`go_ok` en status); programa de un fichero `package main` |

**Modos de entrega (`delivery_mode`):**

| Modo | Comportamiento |
|------|---------------|
| `execute` | LAIM ejecuta el codigo en el sandbox y muestra el resultado |
| `suggest` | LAIM presenta el codigo al usuario como sugerencia |
| `store` | LAIM almacena el snippet en soul.dat sin ejecucion inmediata |

### 23.3 Tier de modelo

El agente developer usa el tier **`development`** — un modelo Ollama dedicado a tareas de programacion. Configuralo en:

```
laim config → 2. Modelos IA → Tiers (o via web: Config > Modelos IA > Tiers)
```

Si el tier `development` no esta configurado, el agente usa `medium` / `slow` como fallback.

### 23.4 Memoria

| Tipo | Almacen | Prefijo/Filtro |
|------|---------|----------------|
| Corto plazo | `SessionMemoryStore` | `developer:request`, `developer:plan`, `developer:last_job_id`, `developer:iteration_count` |
| Largo plazo | `soul.dat` | `Source="developer"`, `Category="tip"`, `Verified=true`, `ConfidenceScore >= 0.80` |

### 23.5 API REST

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| POST | `/api/v1/developer/request` | Inicia job asincrono; body incluye `language` (`python`\|`powershell`\|`bash`\|`go`) |
| GET | `/api/v1/developer/result/{job_id}` | Sondea el resultado (`status: pending/ready/error`) |
| GET | `/api/v1/developer/snippets` | Lista snippets verificados del developer en soul.dat |
| DELETE | `/api/v1/developer/snippets/{id}` | Elimina un snippet por ID |
| GET | `/api/v1/developer/status` | Estado del agente (tier, configuracion, conteo snippets) |

### 23.6 Skills y Tools del developer

**Skills:**

| ID | Descripcion |
|----|-------------|
| `developer_spec` | DEFINE: congela objetivo, lenguaje (Go binario vs Python sandbox) y aceptacion |
| `dev_planning` | PLAN: descomposicion alineada al ciclo DEFINE→SHIP |
| `developer_tdd` | VERIFY: TDD en el Agent Sandbox (`ExecuteInSandbox`) |
| `dev_code_quality` | REVIEW: calidad y determinismo (no sustituye VERIFY) |
| `developer_deliver` | SHIP: registrar binario Go o snippet Python; handoff DevOps HITL |
| `dev_snippet_memory` | Acceso a snippets verificados en soul.dat |
| `dev_sandbox_bridge` | Capacidades del sandbox (incl. Go) y protocolo con sandbox_dev |

**Tools:**

| ID | Endpoint | Descripcion |
|----|----------|-------------|
| `developer_criteria_checklist` | `GET /api/v1/developer/status` | Checklist DEFINE (sin LLM) |
| `dev_sandbox_info` | `GET /api/v1/sandbox/status` | Capacidades actuales (Python + Go) |
| `developer_sandbox_test` | `POST /api/v1/developer/request` `action=test` | VERIFY TDD en sandbox |
| `developer_app_register` | `POST …/request` `action=deliver` | SHIP: registra GeneratedApp Go |
| `developer_devops_handoff` | `GET /api/v1/developer/status` | Metadatos deploy/run para DevOps (no despliega) |
| `dev_snippet_get` | `GET /api/v1/developer/snippets` | Recupera snippets relevantes |
| `dev_snippet_store` | `POST /api/v1/developer/snippets` | Persiste snippet verificado |

### 23.7 Heuristica `developer_request`

Detecta peticiones de alto nivel en las tres plataformas:

| Plataforma | Trigger |
|------------|---------|
| Windows | Keywords: "crear aplicacion", "make an app", "mini app", "herramienta interna", "desarrolla un script"… |
| macOS | Mismo set de keywords |
| Linux | Mismo set de keywords |

Al detectarse, el chat short-circuit ejecuta **spec/plan** (sin codigo). BUILD/VERIFY/SHIP: panel Tecnico o `POST /api/v1/developer/request`. Para forzar Go, usa el selector del panel o `language:"go"`. Keywords extra: `developer spec`, `tdd en sandbox`, `developer deliver`.

### 23.8 Diferencia con DevOps

| Usa **Developer** cuando… | Usa **DevOps** cuando… |
|---------------------------|------------------------|
| Quieres un script/app pequena (Python/Go/Shell) | Necesitas plan de despliegue, CI/CD, rollback |
| Quieres probar codigo en el sandbox | Diagnosticar servicios, firewall, SSH, incidentes |
| Quieres guardar un snippet util en soul.dat | Quieres un runbook operativo reutilizable |

### 23.9 Apps generadas y AppAssist

> **Estado actual (gobierno):** las herramientas solo se crean desde Developer, solo se ejecutan cuando un admin las aprueba y se despliegan en `/tmp/.laim/<slug>_v<versión>_<sha256[:8]>` (Windows: `%USERPROFILE%\.laim\tools\<slug>\<versión>_<sha256[:8]>\<slug>.exe`, §23bis.10). Donde esta subsección difiera (crear apps desde el chat, `/tmp/.laim/<slug>_vN`, ejecutar sin aprobación), prevalece el [§23bis](#23bis-agente-developer-y-aprobación-de-desarrollos). Desde LAIM 0.58.31 el chat ejecuta las herramientas aprobadas por la ruta rápida de herramientas (§23bis.11), no por AppAssist (solo con `LAIM_LEGACY_APPASSIST=1`).

Las apps helper en Go (p. ej. `dirsize`) se compilan a `LAIMConfigDir()/<goos>/<goarch>/<slug>`, se registran en `laim.dat` (`GeneratedApps`) y DevOps las despliega por SSH a `/tmp/.laim/<slug>_vN`.

| Capacidad | Detalle |
|-----------|---------|
| Build | Developer / `BuildGoBinary`; contrato CLI tipico: stdout JSON |
| Deploy / run | DevOps `action=deploy\|run` con `app_slug` + nombre de equipo (`server1`) |
| Chat | Heuristica `generated_app_assist`: HITL crear → desplegar → ejecutar; si rechazas, fallback a `du`/`find` |
| API | `GET/POST /api/v1/apps`, `GET /api/v1/apps/{id\|slug}` |
| UI | Configuracion › Tecnico: tabla de apps; DevOps: campos slug/computer |

#### 23.9.1 Ejemplo de uso: tamaño y ficheros de `/var/log` en `server1.example.com`

Este es el flujo de referencia de **apps generadas** de extremo a extremo (probado en E2E real). Sirve para medir, en un Linux remoto, el **tamaño recursivo** de una carpeta y el **número de ficheros** sin depender de pipelines lentos o frágiles (`du` + `find`).

**Prerrequisitos**

1. Equipo remoto registrado en LAIM (`laim remote` / Config › Computers) con nombre `server1` o host `server1.example.com`, credenciales SSH y `OSType=linux`.
2. Toolchain **Go** instalado en el host LAIM (el que construye el binario; p. ej. Windows de desarrollo).
3. Sesion autenticada (chat CLI o web). Para paneles Tecnico / DevOps / Developer: rol **admin**.

---

##### A) Pedirlo por inferencia en el chat

Escribe en `laim chat` o en el chat web una frase que combine **tamaño**, **ficheros/archivos** y **carpeta/ruta** (y, si aplica, el host remoto):

```text
¿Cuánto ocupa la carpeta /var/log y cuántos ficheros hay en ella y en todas las subcarpetas que contiene?
```

**Resolucion de equipo (nombre corto vs FQDN)**

LAIM no asume un hostname fijo. Cruza el texto del prompt (y el target remoto del chat web) con los equipos a los que tienes permiso:

| Forma | Ejemplo | Como se interpreta |
|-------|---------|-------------------|
| Nombre corto / NetBIOS | `server1` | Coincide con `Computer.Name` o la primera etiqueta de `Host` |
| FQDN | `server1.example.com` | Coincide con `Computer.Host` |
| Expansion por dominio | `server1` → `server1.example.com` | Sufijos desde Hosts del inventario + `local_settings.dns_search_domains` (p. ej. `example.com`) |

Si hay **una** coincidencia, AppAssist pregunta: *¿La consulta se refiere al equipo server1 (server1.example.com)?*  
Si hay **varias**, pide el nombre corto o FQDN exacto.  
Si el chat web ya tiene target remoto (`SetRemoteTarget`) y el texto no nombra host, pregunta: *El chat apunta a … ¿Usar ese equipo?*  
Si la ruta es Unix (`/var/log`) y no hay equipo, pide el nombre corto/FQDN antes de caer a shell.

Puedes decir solo `server1` o el FQDN completo; ambos son validos.

LAIM clasifica el turno con la heurística **`generated_app_assist`** (`isAgentTrigger`) en las tres plataformas. Antes de F4–F6, el workflow llama a **AppAssist** (`RunAppAssist`):

1. HITL: confirmar equipo (corto/FQDN / target del chat) → **s**
2. HITL: ¿crear la app helper Go `dirsize` y registrarla en `laim.dat`? → **s** (si no existe)
3. HITL: ¿desplegar `dirsize` en el equipo vía SSH? → **s**
4. HITL: ¿ejecutar `/tmp/.laim/dirsize_vN /var/log` en remoto? → **s**

Si en cualquier paso respondes **n**, AppAssist hace **fallback** al camino clasico (`du` / `find` vía localsystem o remotesystem).

---

##### B) Peticion al agente Developer (crear la herramienta)

AppAssist (o tu, desde Config › Tecnico → **Developer**) parametriza el Developer asi:

| Parametro | Valor tipico (`dirsize`) |
|-----------|--------------------------|
| `action` | `develop` |
| `language` | `go` |
| `slug` | `dirsize` |
| `target_os` / `target_arch` | `linux` / `amd64` (destino remoto) |
| `request` | CLI helper: tamaño + conteo recursivo de ficheros; stdout JSON |

**API (admin):**

```http
POST /api/v1/developer/request
Content-Type: application/json

{
  "action": "develop",
  "language": "go",
  "request": "CLI Go stdlib dirsize <path>: walk recursivo; stdout JSON {\"path\",\"bytes\",\"files\",\"error\"}"
}
```

El panel Tecnico › Developer usa el mismo contrato (selector de lenguaje **go**).

---

##### C) Parametrizacion y contrato de la herramienta `dirsize`

El codigo canónico vive en Go (`BuiltinDirsizeGoSource`). Contrato CLI:

```text
dirsize <path>
# stdout (una linea JSON):
{"path":"/var/log","bytes":5731477811,"files":214,"error":""}
```

| Campo JSON | Significado |
|------------|-------------|
| `path` | Ruta analizada |
| `bytes` | Suma de tamaños de ficheros regulares (recursivo) |
| `files` | Numero de ficheros regulares (no directorios) |
| `error` | Mensaje si el walk fallo parcialmente; vacio si OK |

Registro en `laim.dat` (`GeneratedApps`):

| Campo | Ejemplo |
|-------|---------|
| `slug` | `dirsize` |
| `keywords` | ocupa, ficheros, var/log, folder size, … |
| `cli_usage` | `dirsize <path>` |
| `output_hint` | esquema JSON anterior |
| `binary_rel` | `linux/amd64/dirsize` |
| `source_rel` | `apps/src/<app_id>/` |

Tras un build correcto, Developer llama a `BuildAndRegisterGeneratedApp` / `UpsertGeneratedApp`.

---

##### D) Donde se almacena (fuente, sandbox y binario)

| Artefacto | Ubicacion (junto al binario LAIM = `LAIMConfigDir()`) |
|-----------|------------------------------------------------------|
| Fuente | `apps/src/<app_id>/main.go` + `go.mod` minimo |
| Cache de compilacion | bajo sandbox: `sandbox/workspace/temp/go-cache` (y go-tmp / go-mod) |
| Binario persistente | `<goos>/<goarch>/<slug>` — p. ej. en Windows host: `bin/windows/linux/amd64/dirsize` (cross-compile hacia Linux) |
| Registro | slice cifrado `GeneratedApps` dentro de `laim.dat` |

La compilacion usa `go build -o …` con `GOOS`/`GOARCH` del destino (no solo `go run`). El sandbox aporta aislamiento de modulo y caches; el **binario util** queda fuera del workspace temporal, listo para deploy.

Comprobar en UI: Config › Tecnico → tabla **Apps generadas** (slug, binary, despliegues) o `GET /api/v1/apps`.

---

##### E) Despliegue con el agente DevOps

Cuando AppAssist (o el admin) confirma el deploy:

| Parametro DevOps | Valor |
|------------------|-------|
| `action` | `deploy` |
| `app_slug` | `dirsize` |
| `computer_name` | `server1` (o `server1.example.com`) |

**API:**

```http
POST /api/v1/devops/request
{
  "action": "deploy",
  "app_slug": "dirsize",
  "computer_name": "server1"
}
```

En el panel Tecnico › DevOps: accion `deploy`, campos `app_slug` y computer.

**Que hace LAIM**

1. Resuelve el `Computer` y el path absoluto local del binario (`GeneratedAppBinaryAbsPath`).
2. Transfiere por SSH a `/tmp/.laim/` (`DeployLocalBinaryToRemote` / SentFileToRemote).
3. Renombra a `/tmp/.laim/dirsize_vN` y `chmod 755` (sin root).
4. Actualiza `Deployments[]` en el registro `GeneratedApp` (`computer_id`, `host`, `remote_path`, `deployed_at`).
5. Auditoria / `console.log` sin credenciales SSH.

Para ejecutar a mano sin AppAssist: accion DevOps `run` con `app_slug=dirsize`, computer `server1` y en la peticion el argumento `/var/log` (`remote_args`).

---

##### F) Uso desde la inferencia y resultado al usuario

Tras el HITL de ejecucion, AppAssist lanza en el remoto:

```text
/tmp/.laim/dirsize_vN /var/log
```

El stdout JSON lo formatea el presentador genérico `PresentToolResult` (§23bis.11; `FormatDirsizeAssistSummary` es ahora un envoltorio obsoleto sobre él) + `PresentResults` (escalas humanas) y se devuelve como **resultado del turno de chat** (sin pasar por el camino largo F5/F6 si AppAssist completo el pipeline). Ejemplo de salida visible:

```text
Carpeta `/var/log`:
- Tamaño: 5.3 GB (5465.96 MB)
- Ficheros: 214
```

| Campo del turno | Contenido |
|-----------------|-----------|
| Analisis / `Output` | Resumen legible (MB/GB + numero de ficheros) |
| `CommandOutput` | JSON crudo del binario (trazabilidad) |

Si la app **ya** estaba registrada y desplegada en ese host, AppAssist omite crear/desplegar y solo pide confirmacion para **ejecutar**.

**Seguridad**

- HITL obligatorio en crear, deploy remoto y run remoto.
- Binario remoto solo bajo `/tmp/.laim/`.
- InferenceSecurity / command_security siguen aplicando al prompt del usuario.
- Nunca se vuelcan contraseñas SSH en logs.

---

## 23bis. Agente Developer y aprobación de desarrollos

Las herramientas propias de LAIM (binarios Go como `dirsize`) las **crea** el agente Developer y DevOps las puede **desplegar** sin aprobación, pero solo se **usan** —se ejecutan o aparecen para la inferencia— cuando un administrador las ha aprobado. Esta sección describe el ciclo tal como funciona hoy: Developer → manifest → propuesta → aprobación → despliegue por equipo → catálogo de herramientas por equipo.

> **Resumen:** crear, desarrollar y desplegar está permitido sin aprobación; ninguna herramienta se ejecuta ni entra en el catálogo hasta que un admin aprueba su versión y su sha256 exactos. Deprecar, rechazar o volver atrás surte efecto en la siguiente llamada.

### 23bis.1 Qué produce Developer (solo admin)

Developer es **solo para admins**: el panel rechaza cualquier otro rol y todas las rutas `/api/v1/developer/*` exigen sesión web de admin (401 en otro caso).

- **Web:** Configuración › **10. Técnico** → **Developer** (selector de lenguaje **go** para herramientas).
- **API:** `POST /api/v1/developer/request` (admin). Campos del body: `action` (`spec` | `plan` | `develop` | `test` | `review` | `deliver` | `research` | `recall`), `request` (la tarea en lenguaje natural), `context`, `code` (fuente fija opcional; se salta la generación), `language` (`python` | `powershell` | `bash` | `go`), `slug` (nombre del binario, opcional), `target_os` (`linux` | `mac` | `windows`) y `target_arch` (`amd64` | `arm64`). Responde `202` con `job_id`; el resultado se consulta con `GET /api/v1/developer/result/{job_id}`.

Para una herramienta Go, el flujo (`action: "develop"`, `language: "go"`) produce:

| Resultado | Detalle |
|-----------|---------|
| Fuente Go con el manifest embebido | `const laimManifest` y los flags reservados `--manifest` (imprime el JSON canónico del manifest y sale con 0) y `--json` (salida JSON); los errores salen en JSON con códigos 0 ok / 1 error / 2 uso |
| Comprobación en el build | el build nativo ejecuta `<bin> --manifest` y lo compara con el manifest registrado → `manifest_check` |
| Binarios | el `target_os`/`target_arch` pedido; el resto de plataformas declaradas en el manifest se compilan con la misma fuente al aprobar |
| Registro | una app generada en `laim.dat` (`GET /api/v1/apps`): slug, versión, sha256 por plataforma, `manifest`, `manifest_check`, `catalog` (gobierno) |
| Propuesta | el flujo **termina proponiendo** la herramienta para su aprobación (`governance_state` del resultado = `proposed`); las apps sin manifest o creadas por e2e/test quedan en `draft` con el motivo |

El resultado de Developer indica además `manifest_status` y `catalog_eligible`.

### 23bis.2 El manifest de la herramienta

El manifest es el contrato tipado de una herramienta (`schema_version` 1):

| Campo | Significado |
|-------|-------------|
| `slug`, `purpose`, `purpose_es` | nombre; una frase en inglés (se usa en los prompts) y otra en español |
| `intents` | entre 3 y 10 preguntas de ejemplo (routing) |
| `heuristic_cases` | casos heurísticos que la herramienta responde mejor (p. ej. `generated_app_assist`) |
| `params` | cada uno con `name`, `type` (`string` \| `int` \| `bool` \| `path` \| `enum` \| `host` \| `pid` \| `duration`), `required`, `pattern` (RE2 anclada, obligatoria en `string`), `enum`, `min`/`max`, `allowed_paths`/`denied_paths`, `extract` (`path` \| `host` \| `pid` \| `service` \| `int` \| `none`), `slot` (p. ej. `<ruta>`), `const`, `sensitive` |
| `argv` | plantilla: literales o exactamente `{param}` por argumento; sin metacaracteres de shell; `--manifest` está reservado |
| `output` | `format` (`json` para el catálogo; `text` solo en borrador), `fields` (`int` \| `bytes` \| `string` \| `bool` \| `duration_ms` \| `timestamp` \| `list`, con etiquetas y `primary`), `error_field`, `list_field`/`list_columns` |
| `side_effect` | `read_only` \| `writes` \| `exec` — no existe la clase `network` |
| `timeout_sec`, `max_output_bytes` | por defecto 30 s / 64 KiB; máximo 300 s / 1 MiB |
| `platforms` | `<linux\|mac\|windows>/<GOARCH>`, p. ej. `linux/amd64` |
| `privileges` | `user` (por defecto) o `root`; root exige `side_effect` ≠ `read_only` y confirmación explícita de un admin — nunca sudo implícito |
| `self_test` | datos del golden run: `args` (param → valor; `$LAIM_SANDBOX_WORKSPACE` = la carpeta del sandbox) y `expect_fields` |
| `fallback` | opcional, solo en herramientas `read_only`: por segmento de SO (`linux` \| `mac` \| `windows`) de 1 a 3 plantillas de comandos nativos de solo lectura que miden exactamente lo mismo que la herramienta; se usan cuando la herramienta no se puede usar en el equipo (23bis.10) |

**Solo valores reales.** Los valores de `path`, `host` y `pid` salen solo de la pregunta del usuario (o de su respuesta al slot); nunca pueden tener un valor por defecto en `const`. Un param obligatorio sin `extract` necesita `slot`.

**Validación.** Cada problema tiene una severidad: `error` (manifest no válido), `not_catalog_eligible` (bien formado pero aún no utilizable: `output_text`, `platform_not_built` — una plataforma declarada sin binario compilado) o `admin_required` (p. ej. `root_requires_admin`). "No apta para el catálogo" significa que la herramienta puede registrarse y quedar en borrador, pero nunca se lista ni se ejecuta. `manifest_check.status` vale `ok`, `manifest_mismatch` (el binario imprime otro manifest, falla o tarda demasiado) o `manifest_invalid`.

Los admins pueden leer y editar el manifest: `GET`/`PUT /api/v1/apps/{id}/manifest` (`PUT` reescribe `const laimManifest`, recompila y deja una versión nueva en borrador) y `POST /api/v1/apps/{id}/manifest/validate`.

### 23bis.3 Ciclo de vida y versiones

```
build (Developer) ─▶ draft ─propose─▶ proposed ─approve (admin)─▶ approved ─deprecate (admin)─▶ deprecated
                                      proposed ─reject (admin, motivo)─▶ rejected ─propose─▶ proposed
                                      approved ─rollback (admin)─▶ approved (una versión aprobada anterior)
```

- **Candidatas.** Un build nuevo de una herramienta aprobada pasa a ser su *candidata* (draft → proposed → approved | rejected); la versión aprobada sigue sirviendo hasta que se aprueba la candidata. Rechazar la candidata no afecta a la versión aprobada.
- **Historial.** La aprobación guarda una copia local de los binarios de cada plataforma de las **3** últimas versiones aprobadas. **Volver atrás** (rollback) solo lleva a una de esas versiones aprobadas antes, y solo si sus copias conservan el sha256 aprobado.
- **Deprecated** es terminal hasta recompilar (sin rollback; recompilar la devuelve a `draft`).
- Proponer: `POST /api/v1/apps/{id}/propose` (el autor o un admin).

### 23bis.4 Aprobar una herramienta (Aprobación de desarrollos)

**Web:** Configuración › Asistente de configuración › **9. Internal** › **9. 🛡️ Aprobación de desarrollos** — visible solo para admins (los demás roles no ven la opción; la página y la API los rechazan). La página lista las propuestas pendientes y las herramientas aprobadas; al elegir una se muestra su revisión:

| Bloque de la revisión | Contenido |
|-----------------------|-----------|
| Manifest | el manifest en revisión (JSON legible) |
| Problemas de validación / Requisitos de aprobación pendientes | problemas del manifest y cada requisito que falta |
| Comprobación del build (--manifest) | el resultado de `manifest_check` |
| Golden run (sandbox) | último golden run de esta versión, con **Repetir golden run** |
| Plataformas | cada plataforma declarada: compilada, versión, sha256, sha256 aprobado |
| Diff de la fuente contra la última aprobada | diff unificado de `main.go` respecto a la última versión aprobada |

**Requisitos para aprobar** (todos obligatorios; si falta alguno, `422 approval_blocked` con la lista): la versión es la propuesta pendiente (`proposed`); manifest válido con `self_test`; `manifest_check` = `ok` y vigente; la fuente en disco es la que se compiló y revisó; no es efímera ni creada por e2e/test; todas las plataformas declaradas compiladas (las que faltan se compilan en ese momento con la misma fuente, sin subir la versión); y un **golden run correcto** en el sandbox de Developer (perfil `sandbox_code`, 120 s como máximo).

**Acciones (admin):**

| Acción | API | Notas |
|--------|-----|-------|
| Aprobar | `POST /api/v1/apps/{id}/approve` `{version, ack_admin_issues}` | `version` debe ser la pendiente; `ack_admin_issues: true` (casilla en la web) confirma los avisos `admin_required`, como `privileges=root` |
| Rechazar | `POST /api/v1/apps/{id}/reject` `{reason}` | motivo obligatorio |
| Deprecar | `POST /api/v1/apps/{id}/deprecate` `{reason, replaced_by}` | motivo obligatorio; `replaced_by` opcional (otra app registrada) |
| Volver atrás | `POST /api/v1/apps/{id}/rollback` `{version}` | solo a una versión aprobada conservada |
| Revisión / golden run | `GET /api/v1/apps/{id}/review`, `POST /api/v1/apps/{id}/golden-run` | |
| Listado | `GET /api/v1/apps/proposals[?all=1]` | `all=1` incluye también las aprobadas |

Una transición no permitida responde `409 illegal_transition`; un dato que falta, `400`.

**Notificaciones y auditoría.** Cada cambio de estado notifica al autor de la herramienta (notificación de tipo `tool_governance`); una propuesta nueva notifica además al resto de admins. Cada decisión queda en el registro de auditoría, grupo **`tools`** (acciones `propose`, `approve`, `reject`, `deprecate`, `rollback`, `golden_run`, `manifest_edit`, `run_denied`) — ver Configuración › 9. Internal › 4. Audit Log.

### 23bis.5 Uso condicionado a la aprobación

- Crear, desarrollar y desplegar una herramienta está permitido sin aprobación. **Usarla** no: una herramienta solo se ejecuta (chat, DevOps `run`) y solo aparece en el catálogo mientras está aprobada.
- Cada ejecución vuelve a leer la herramienta y comprueba: estado aprobado, versión aprobada, sha256 aprobado de la plataforma, sha256 de la copia local aprobada y, en el equipo, el sha256 de la copia remota. Un rechazo se explica al usuario y se audita (`run_denied`, con los argumentos enmascarados).
- Deprecar, rechazar o volver atrás retira el permiso al instante, incluso para una ejecución que ya estaba preparada.
- Una herramienta aprobada siempre despliega su copia aprobada; un build candidato nunca se despliega para ejecutarse.
- La coincidencia heredada del chat (AppAssist) solo ofrece apps aprobadas y no efímeras.
- Las herramientas con manifest solo se ejecutan a través del ejecutor de herramientas (23bis.8), que aplica todo lo anterior y además las reglas del catálogo en cada llamada. Las apps registradas antes de que existieran los manifests (sin manifest) siguen el camino de ejecución anterior, siempre condicionado a la aprobación.

### 23bis.6 Despliegues por equipo

Cada app mantiene un registro de despliegues por equipo (`deployments` en `GET /api/v1/apps`):

| Estado | Significado |
|--------|-------------|
| `present` | sha256 remoto = el binario esperado (el aprobado, en herramientas aprobadas) |
| `missing` | el fichero remoto ya no está |
| `stale` | el fichero remoto es distinto (p. ej. una versión aprobada anterior) |
| `undeployed` | retirado por LAIM (solo historial) |
| `unknown` | nunca verificado o equipo inaccesible |

- **Web:** Configuración › 10. Técnico → **Apps generadas**: por app, sus despliegues con **Verificar** (comprobación de solo lectura de sha256 y arquitectura) y **Retirar** (borra exactamente el fichero registrado), y **×** para eliminar la app.
- **API (admin):** `POST /api/v1/apps/{id}/deployments/{computer_id}/verify`, `DELETE /api/v1/apps/{id}/deployments/{computer_id}`, `DELETE /api/v1/apps/{id}` (`409 app_has_deployments` mientras quede alguna copia desplegada) o `DELETE /api/v1/apps/{id}?undeploy=all` (retira de todos los equipos y después borra; `409 undeploy_incomplete` si algún equipo no se pudo limpiar).
- **Ruta remota:** Linux y macOS `/tmp/.laim/<slug>_v<versión>_<sha256[:8]>`; Windows `%USERPROFILE%\.laim\tools\<slug>\<versión>_<sha256[:8]>\<slug>.exe` (23bis.10). Retirar solo borra el fichero registrado: en Windows, solo una copia bajo la `tool_root` registrada (`%USERPROFILE%\.laim\tools`), comprobado otra vez en el propio equipo.
- **Antes de cada ejecución** se comprueba la copia: `present` → se ejecuta; `missing`/`stale` → LAIM pregunta si redesplegar la versión aprobada y ejecutar (HITL); sin verificar o con arquitectura distinta → no se ejecuta. Nada se despliega sin consentimiento; por la API de DevOps, ese consentimiento es `approve_deploy: true`. Las herramientas con manifest vuelven a comprobar el sha256 en la misma sesión SSH que las ejecuta y se limitan con los topes de su manifest (23bis.8); las apps sin manifest se limitan a 60 s y 1 MiB de salida.

### 23bis.7 Catálogo de herramientas por equipo

El catálogo es la lista de herramientas aprobadas que un usuario puede usar en un equipo, ordenada según una pregunta. Una herramienta aparece solo si, en este orden:

| Comprobación | Código de exclusión |
|--------------|---------------------|
| no es efímera | `ephemeral` |
| está aprobada y su versión aprobada consta en el registro (se usan la versión y el manifest aprobados, nunca una candidata pendiente) | `not_approved`, `no_approved_version` |
| el manifest aprobado existe, es válido y tiene el sha256 canónico aprobado | `manifest_missing`, `manifest_invalid`, `manifest_sha_mismatch` |
| la plataforma del equipo `<linux\|mac\|windows>/<arch>` está declarada en `platforms`, aprobada, y la copia local aprobada tiene el sha256 aprobado | `platform_not_declared`, `platform_not_approved`, `binary_missing`, `sha_mismatch` |
| no está deshabilitada para ese equipo en la política por equipo de la herramienta | `host_disabled` |
| el usuario tiene acceso al equipo (no se comprueba para el propio host de LAIM, que no tiene concesiones por equipo) | `no_access` |
| el efecto está permitido para el rol: `read_only` para cualquier usuario con acceso; `writes`/`exec` solo se listan a admins | `side_effect_admin_only` |
| con pregunta: puntuación mínima de relevancia (1 por defecto) | `below_min_score` |

Aparecer en el catálogo no da permiso para ejecutar: el ejecutor lo vuelve a comprobar todo en cada llamada, incluida la política por equipo (23bis.5, 23bis.8). La política por equipo aún no se puede cambiar desde la web ni desde la API.

Cada herramienta listada lleva el **estado de despliegue** del equipo tomado del registro de despliegues **sin SSH** (última verificación guardada): `present`, `missing`, `stale`, `undeployed`, `unknown` o `not_deployed`; una copia guardada cuya versión o sha256 no son los aprobados cuenta como `stale`. La ordenación puntúa la pregunta contra `purpose`, `purpose_es`, `intents` y los nombres de los params, con **+10** si el caso heurístico de la pregunta está en los `heuristic_cases` del manifest. El texto para el prompt lleva como mucho 5 herramientas y 1500 bytes (solo líneas completas), ordenadas por puntuación y después por slug, una línea por herramienta:

```text
tool:dirsize — Recursive folder size in bytes and regular-file count (symlinks are not followed). args: path(path, required). read_only. host status: present v<N>
```

Una herramienta que no está `present` muestra `host status: needs deploy (<estado>) v<N>`.

**Depuración (admin):** `GET /api/v1/tools/catalog?computer_id=<computer_id>&q=<pregunta>` (401 para quien no es admin). `computer_id` vacío o `localhost` = el propio equipo LAIM; un equipo desconocido → 404. Opcionales: `as_user=<usuario>` (evalúa acceso y rol como ese usuario) y `min_score=<n>`. La respuesta trae `target` (`computer_id`, `host`, `segment`, `arch`, `local`, `arch_assumed`), `query`, `user`, `role`, `min_score`, `tools` (`slug`, `app_id`, `version`, `purpose`, `side_effect`, `platform`, `approved_sha256`, `deploy_status`, `deploy_version`, `remote_path`, `last_verified_at`, `score`, `heuristic_bonus`, `line`), `excluded` (`app_id`, `slug`, `version`, `code`, `reason`), `prompt` y `prompt_bytes`.

**Próximamente:** el catálogo ya se construye y se expone, y el ejecutor (23bis.8) ya funciona para la ruta rápida de herramientas del chat con su presentador determinista (23bis.11) y DevOps; el catálogo todavía no se inyecta en los prompts del planificador del chat. Los siguientes pasos son su uso por el planificador y el uso desde Connect y Suggestions.

### 23bis.8 Ejecutar una herramienta (ejecutor)

Toda ejecución de una herramienta aprobada que tiene manifest pasa por un único ejecutor: hoy la ruta rápida de herramientas del chat (23bis.11) y DevOps `action: "run"`; más adelante el planificador del chat, Suggestions y Connect. En cada llamada hace, en este orden:

| Paso | Qué ocurre |
|------|------------|
| 1. Permiso | La herramienta se vuelve a leer de `laim.dat` y se comprueba con las reglas del catálogo de 23bis.7 para ese usuario y ese equipo: aprobación (estado, versión, sha256), plataforma, manifest aprobado, **política por equipo** (`host_disabled`), acceso al equipo y `writes`/`exec` solo para admins. Un rechazo no ejecuta nada y se audita (`run_denied`). La comprobación se repite justo antes de ejecutar, así que una retirada o un rechazo hechos mientras el usuario responde a una pregunta también detienen la ejecución. |
| 2. Argumentos | Se construyen solo con la plantilla `argv` del manifest. Cada valor se comprueba según su tipo (`pattern`, `enum`, `min`/`max`). Las rutas deben ser absolutas y sin `..`; se normalizan y deben quedar fuera de `denied_paths` (siempre también `/proc/kcore`, `/dev`, `/sys/firmware`) y dentro de `allowed_paths` si existe; las rutas de unidad de Windows (`C:\…`) solo en equipos Windows. Se rechazan NUL, saltos de línea y caracteres de control; un valor que empieza por `-` se rechaza como valor de una opción y, como posicional, lleva `--` delante cuando la plantilla lo permite. **Solo valores de la pregunta:** cada valor debe aparecer literalmente en la pregunta del usuario o en su respuesta a la pregunta del hueco (p. ej. `<ruta>`); si no, se rechaza (`not_in_question`). Un hueco vacío significa que no se ejecuta nada (`slot_unfilled`). |
| 3. Despliegue | Si la copia del equipo no está `present`, una copia `missing`/`stale`/`unknown` en caché se comprueba primero con la sonda de sha256 de solo lectura. Si sigue sin estar presente, LAIM pregunta `¿Desplegar/Redesplegar <slug> v<N> (sha256 <sha8>) en <host>? (s/n)`. No → la herramienta no se ejecuta y el turno termina con el respaldo honesto de 23bis.10 (nunca con la respuesta a otra pregunta). Nunca se despliega nada sin esa respuesta (API de DevOps: `approve_deploy: true`); el autorun de Suggestions nunca despliega. Un equipo de otra arquitectura → no se ejecuta (`arch_mismatch`). |
| 4. Consentimiento | Según la clase de efecto (tabla siguiente). |
| 5. Verificar + ejecutar | Una sola sesión SSH comprueba el sha256 del fichero remoto contra el sha256 **aprobado** y, solo si coincide, lo ejecuta (sin hueco entre la comprobación y la ejecución). |
| 6. Límites | `timeout_sec` y `max_output_bytes` del manifest. Una salida truncada nunca se presenta como medida (`truncated`). |
| 7. Salida | JSON estricto: un objeto; campos declarados con su tipo declarado; los campos no declarados se descartan; los campos `sensitive` y cualquier secreto se enmascaran. Un `{"error": …}` no vacío es una ejecución fallida (`tool_error`). |
| 8. Registro | Última ejecución en el registro de despliegues, auditoría del grupo **`tools`** con la acción `run` (destino `<slug>@<host>`, argumentos enmascarados, código de resultado) y la entrada `tool_run` del registro de decisiones. |

**Consentimiento por clase de efecto:**

| `side_effect` | Consentimiento |
|---------------|----------------|
| `read_only` | Entra en la única pregunta de solo lectura del turno como una línea más, `laim-tool <slug> <args> @<host>`; sola, es una pregunta de una línea del mismo tipo. En el autorun de Suggestions se ejecuta sin preguntar solo si la herramienta está aprobada y su copia está presente y verificada en el equipo. Una petición `run` de DevOps hecha por un admin es el consentimiento para esa llamada concreta. |
| `writes`, `exec` | Pregunta propia en cada llamada, con la clase de efecto y los argumentos exactos. Nunca va en una pregunta de lote, ni en el autorun ni en una vía rápida; solo admins. Por la API de DevOps (sin canal interactivo) la petición `run` explícita es el consentimiento para esa llamada concreta. |

**Orden de verificación + ejecución** (cada argumento entre comillas simples; los valores del usuario nunca se interpolan en un shell):

```text
Linux:   p='<ruta>'; h=$(sha256sum -- "$p" | cut -c1-64); [ "$h" = '<sha256>' ] || { echo LAIM_TOOL_HASH_MISMATCH >&2; exit 97; }; exec "$p" '--json' '--path' '/var/log'
macOS:   lo mismo con shasum -a 256
Windows: $p='<ruta>'; $h=(Get-FileHash -Algorithm SHA256 -LiteralPath $p …).Hash; if (…ne '<sha256>') { … exit 97 }; & $p '--json' '--path' 'C:\Logs'; exit $LASTEXITCODE
         enviado como powershell -NoProfile -NonInteractive -EncodedCommand <base64 UTF-16LE>, con salida UTF-8
```

**Exit 97** (`LAIM_TOOL_HASH_MISMATCH`): el binario del equipo no es el aprobado, así que no se ha ejecutado nada. El despliegue se marca `stale` (`last_verify_error`), el evento se audita (`run_hash_mismatch`) y LAIM pregunta si redesplegar la copia aprobada y volver a ejecutar (una vez). En el propio equipo de LAIM, la copia local aprobada se comprueba contra su sha256 y se ejecuta directamente, sin shell.

**Qué ve el usuario.** Una ejecución aparece como el comando `laim-tool <slug> <args>` entre los comandos ejecutados (línea de Método, lista de comandos ejecutados, University) y su salida es el JSON enmascarado.

**Las llamadas a herramientas nunca son shell.** Un bloque de código `laim-tool` o un fragmento `tool:` / `laim-tool` en línea dentro de una respuesta del modelo nunca se extrae ni se ejecuta como comando de shell en ningún sitio (agentes local y remoto, Suggestions, flujos, Connect): regla `CMD-TOOL-001`. Solo el ejecutor ejecuta herramientas.

**Códigos de resultado:** `ok`, `args_invalid`, `slot_unfilled`, `needs_deploy`, `deploy_declined`, `deploy_failed`, `arch_mismatch`, `consent_declined`, `autorun_forbidden`, `hash_mismatch`, `timeout`, `truncated`, `output_invalid`, `tool_error`, `exec_failed`, además de los códigos de permiso de 23bis.7.

### 23bis.9 Ejemplo: dirsize desde Developer hasta la primera ejecución

1. **Recompilar desde Developer.** Configuración › 10. Técnico → Developer, lenguaje **go**, o `POST /api/v1/developer/request` con `{"action":"develop","language":"go","slug":"dirsize","target_os":"linux","target_arch":"amd64","request":"dirsize: tamaño recursivo de una carpeta y número de ficheros, JSON por stdout"}`. Una petición que nombra `dirsize` usa la fuente canónica de `dirsize` de LAIM: `dirsize --manifest`, `dirsize --json --path <ruta>`, y sin `--path` sale con 2 y `{"error":"path required"}` (sin valor por defecto `.`). Su manifest declara `path` (tipo `path`, obligatorio, `extract: path`, slot `<ruta>`, prohibidas `/proc`, `/sys`, `/dev`), `side_effect: read_only`, plataformas `linux/amd64`, `mac/arm64`, `windows/amd64`, un `self_test` sobre la carpeta del sandbox y un `fallback` por segmento (23bis.10).
2. **Propuesta.** El build registra una versión nueva y el flujo la propone; los admins reciben una notificación `tool_governance`. Si `dirsize` ya estaba aprobada, el build nuevo es una candidata y la versión aprobada anterior sigue funcionando.
3. **Aprobar.** Configuración › Asistente de configuración › 9. Internal › 9. 🛡️ Aprobación de desarrollos → elegir `dirsize`, revisar manifest, comprobación del build, plataformas y diff de la fuente, y pulsar **Aprobar**. LAIM compila las plataformas que faltan, ejecuta el golden run en el sandbox y fija la versión y el sha256 de cada plataforma.
4. **Comprobar el catálogo.** `GET /api/v1/tools/catalog?computer_id=<computer_id>&q=<pregunta>` lista `dirsize` para ese equipo; si el equipo aún tiene la versión anterior, aparece `needs deploy (stale)`.
5. **La primera ejecución pide redesplegar.** En la siguiente ejecución en `<host>` (chat, o DevOps `action: "run"` con `app_slug: "dirsize"`, `computer_name: "<host>"`, `remote_args: ["<ruta>"]`), LAIM verifica la copia, la encuentra `stale` y pregunta `¿Redesplegar dirsize v<N> (sha256 <sha8>) en <host>? (s/n)` (por la API de DevOps la respuesta es `approve_deploy`; sin él no se despliega nada). Sí → despliega `/tmp/.laim/dirsize_v<N>_<sha8>` (Windows: `%USERPROFILE%\.laim\tools\dirsize\<N>_<sha8>\dirsize.exe`); en el chat pregunta después la pregunta de solo lectura con `laim-tool dirsize --json --path <ruta> @<host>` y la ejecuta con la comprobación de sha256 en la misma sesión (23bis.8). No → no se ejecuta nada.

### 23bis.10 Equipos Windows y respaldo honesto

**Dónde vive una herramienta en Windows.** `%USERPROFILE%\.laim\tools\<slug>\<versión>_<sha256[:8]>\<slug>.exe` del usuario SSH, p. ej. `C:\Users\Some User\.laim\tools\dirsize\1_d7f3bb6c\dirsize.exe`. LAIM lee `%USERPROFILE%` una vez por despliegue (solo lectura) y guarda la ruta absoluta y su `tool_root` (`%USERPROFILE%\.laim\tools`) en el registro del despliegue. Se rechaza un perfil bajo `C:\Windows` (perfil de sistema), una ruta UNC o una ruta con `..`. Linux y macOS siguen, por ahora, en `/tmp/.laim`.

**Toda orden de Windows salvo la copia del binario es un script de PowerShell codificado** — `powershell -NoProfile -NonInteractive -EncodedCommand <base64 UTF-16LE>` con salida UTF-8, el mismo envoltorio que el agente de sistemas remotos — para que funcione tanto si el shell por defecto de OpenSSH del equipo es PowerShell como si es `cmd.exe`:

| Paso | Script (decodificado) |
|------|-----------------------|
| Leer el perfil | `$env:USERPROFILE` |
| Arquitectura / sha256 | `$env:PROCESSOR_ARCHITECTURE`; `Get-FileHash -Algorithm SHA256 -LiteralPath …` |
| Crear la carpeta | `New-Item -ItemType Directory -Force -Path '<…\<versión>_<sha8>>'` |
| Transferir | receptor SCP `scp -t "C:/Users/…/<slug>.exe.<rand8>.part"` (sin PowerShell), después modo líneas y después escrituras por bloques con `-EncodedCommand` — ver *Copia del binario a Windows* y *Copia robusta y observable* más abajo |
| Instalar | ninguno desde 0.58.29: la finalización de la copia comprueba tamaño + sha256 y sustituye `<slug>.exe` en una sola llamada |
| Verificar + ejecutar | 23bis.8 (las rutas con espacios o comillas van entre comillas simples de PowerShell) |
| Retirar | `Remove-Item -LiteralPath … -Force`, solo después de comprobar en el propio equipo que el fichero está bajo el `%USERPROFILE%\.laim\tools` vigente (si no, `OUTSIDE` y no se borra nada); después, la carpeta de la versión si queda vacía |

**Copia del binario a Windows (LAIM 0.58.28).** LAIM 0.58.27 enviaba el binario por la entrada estándar a un script de PowerShell codificado que copiaba `[Console]::OpenStandardInput()` al fichero. Con OpenSSH de Windows y Windows PowerShell 5.1 el script nunca veía el final de la entrada: la copia (y con ella el turno del chat) se quedaba colgada para siempre tras `transfer_start`. Ahora la copia funciona así:

1. **Receptor SCP.** LAIM ejecuta en el equipo `scp -t "C:/Users/<usuario>/.laim/tools/<slug>/<versión>_<sha8>/<slug>.exe"` (`scp.exe` viene con OpenSSH de Windows) y habla él mismo el protocolo SCP: la cabecera lleva el tamaño exacto y el equipo confirma cada paso con un byte, así que nada depende del final de la entrada. La ruta va con barras normales entre comillas dobles, que un shell por defecto PowerShell o `cmd.exe` pasan sin cambios a `scp.exe`; una ruta con `"`, `$`, `` ` `` o `%` nunca se envía a scp (pasa directamente al paso 2).
2. **Respaldo por bloques**, automático, cuando el receptor scp no responde al saludo (`scp` no instalado — «not recognized» / exit 127 — o sin respuesta en 30 s): el binario (comprimido con gzip si así ocupa menos) se envía en trozos, cada uno con su propio `powershell -NoProfile -NonInteractive -EncodedCommand` que decodifica sus bytes en base64 y los añade a `<fichero>.part` solo si el fichero parcial tiene exactamente la longitud esperada (`LAIM_PART_OK <longitud>`). No se usa la entrada estándar. Cada línea de órdenes queda por debajo de 30.000 caracteres (límite de Windows 32.767); si el primer trozo se rechaza porque el shell por defecto es `cmd.exe` (límite de 8.191 caracteres), los trozos bajan a 8.000 caracteres. Una última orden descomprime (o renombra) el fichero parcial a `<slug>.exe` y devuelve su tamaño y su sha256 (`LAIM_DONE`), que deben coincidir con el fichero local; ante cualquier fallo se borra el fichero parcial. Los ficheros de más de 32 MiB no se copian por bloques.
3. **La comprobación del sha256 tras la copia sigue siendo obligatoria**: una copia truncada o corrupta nunca se registra como `present`.

**Toda transferencia tiene un tiempo máximo** (también `cat >` en Linux y macOS): un plazo de 60 s + 1 s por cada 100 KiB del binario, con un máximo de 10 minutos (una herramienta de 3 MB: 90 s); un vigilante que aborta cuando lleva 60 s sin ningún byte confirmado; si salta cualquiera de los dos, se cierra la sesión SSH (y la conexión unos segundos después si la sesión no termina). Los demás pasos del despliegue (perfil, mkdir, instalación, sondas de sha) tienen 30 s cada uno y el saludo SSH de la copia, 30 s. El log de consola muestra `transfer_start … size=<bytes> timeout=<plazo>` y después `transfer_done … after=<tiempo>` o `transfer_timeout` / `transfer_failed … after=<tiempo> | <motivo>`.

**Qué ve el usuario si se agota el tiempo.** El despliegue falla con `deploy_failed` y un motivo que empieza por `transfer_timeout`; no se registra nada en el equipo. El turno del chat termina con el respaldo honesto de abajo — los comandos nativos de solo lectura si el manifest los declara, si no `No se pudo usar la herramienta LAIM <slug> v<N> en <host>: no se pudo desplegar: la copia del binario al equipo superó su tiempo límite y se canceló (…).` — nunca se queda colgado ni responde otra pregunta. Volver a preguntar reintenta el despliegue.

El plugin sentfiletoremote (transferencia de ficheros desde la web, dentro del proceso y como binario propio) usa el mismo mecanismo para Windows y los mismos límites; su transferencia a Linux/macOS (`cat > '<fichero>'`) no cambia.

**Copia robusta y observable (LAIM 0.58.29).** En POWERPC (0.58.28) el receptor scp se abandonaba sin decir por qué, el respaldo por bloques tardó 6,5 minutos (≈165 arranques de PowerShell) y su último paso falló sobre `dirsize_windows@v1.exe` con un error `#< CLIXML` ilegible: ese fichero seguía abierto por el `powershell.exe` del intento colgado de 0.58.27. Desde 0.58.29:

- **Orden: receptor scp → modo líneas → por bloques.** (1) El receptor SCP de arriba. (2) **Modo líneas:** UN solo `powershell -NoProfile -NonInteractive -EncodedCommand <arranque>`; el arranque escribe `LAIM_READY`, lee de su entrada estándar líneas de texto en base64 (`[Console]::In.ReadLine()`, 3.072 bytes por línea), las añade a su propio fichero temporal, confirma el avance (`LAIM_ACK <bytes>` cada 16 líneas) y se detiene en la línea final explícita `LAIM_END <tamaño> <sha256>` — nunca espera al final de la entrada (el cuelgue de 0.58.27). Sin `LAIM_READY` en 15 s, o sin `LAIM_ACK` durante 15 s → (3) los procesos por bloques de 0.58.28. El modo líneas es el camino rápido cuando falta scp (un proceso en lugar de uno por trozo) y lo acotan el mismo plazo y el mismo vigilante.
- **Nombres temporales únicos y finalización atómica.** Cada modo escribe `<final>.<rand8>.part` (8 hexadecimales aleatorios por intento; los trozos gzip, `<final>.<rand8>.gz.part`) en la carpeta de la versión — nunca el nombre subido (`<slug>_windows@v<N>.exe`) ni el nombre final. Una orden de finalización comprueba el tamaño y el sha256 del temporal contra el binario local (`LAIM_BAD` → se descarta, `sha_mismatch`) y después sustituye `<slug>.exe` en una sola llamada (`[System.IO.File]::Replace`, o `[System.IO.File]::Move` si no había copia); ya no hay paso de instalación aparte. Si otro proceso tiene abierto `<slug>.exe`, el despliegue falla con `dest_locked` nombrando el fichero (`no se pudo desplegar: el fichero de destino está en uso en el equipo (otro proceso lo tiene abierto)`); no se escribe ni un byte en él. La sonda de sha256 tras la copia sigue siendo obligatoria antes de registrar la copia como `present`.
- **Restos.** Antes de cada copia LAIM limpia solo la carpeta de la versión `<tool_root>\<slug>\<versión>_<sha8>` (comprobada en LAIM y otra vez en el equipo contra el `%USERPROFILE%\.laim\tools` vigente, como al retirar; nada recursivo, nada fuera): ficheros `*.part` de más de 15 minutos y nombres subidos antiguos `<slug>_*.exe`; nunca `<slug>.exe`. Un resto que no se puede borrar porque un proceso lo tiene abierto se registra como `leftover_locked <nombre>` y se ignora — la copia sigue con su propio nombre temporal único.
- **Limpieza de procesos remotos colgados.** Cada orden codificada de un modo empieza con la línea de comentario `# laim-xfer <16 hexadecimales aleatorios>`; el base64 que codifica esa línea se ve en la línea de órdenes del `powershell.exe` interior y del envoltorio exterior `powershell.exe -c "…"` que añade OpenSSH cuando su DefaultShell es PowerShell (scp: la ruta temporal). Cuando un modo agota su tiempo (o se abandona el modo líneas), LAIM cierra la sesión y ejecuta una orden acotada (10 s) que detiene solo procesos `powershell.exe` / `scp.exe` cuya línea de órdenes contiene una de las marcas de esta transferencia (nunca a sí misma ni a su padre; marcas de menos de 32 caracteres se ignoran) y borra los ficheros temporales exactos de esta transferencia. Nunca detiene ningún otro proceso.
- **Log y mensajes.** El log de consola (`remote_deploy`) muestra `scp_sink ok bytes=<n> after=<t>` o `scp_sink_failed reason=<handshake timeout|error ack '<texto>'|exit <n>|not found|eof> stderr="<primer texto de error>"`, `line_mode start lines=<n>`, `line_mode ok` / `line_mode_failed reason=…`, `chunked start chunks=<n> chunk_bytes=<n> gzip=<bool>`, `chunked ok chunks=<n> … after=<t>`, `remote_cleanup markers=<n> temps=<n> stopped=<n>`, `leftover_removed` / `leftover_locked`, y `transfer_done … mechanism=<scp_sink|line|chunked>` (o `transfer_failed` / `transfer_timeout` / `dest_locked … | <motivo>`). PowerShell escribe los errores en un stderr redirigido como CLIXML (`#< CLIXML <Objs …><S S="Error">…_x000D__x000A_</S>`); LAIM lo decodifica a texto plano (solo las líneas de error, sin las de posición `At line:` / `+ …`), con el código de salida, en el log y en el mensaje honesto al usuario (recortado a una línea).

**Resolución de problemas.** Si una versión anterior de LAIM se quedó colgada durante una copia (0.58.27), puede seguir ejecutándose en el equipo un `powershell.exe` que tiene abierto un fichero de la carpeta de la versión (Administrador de tareas → Detalles, o `Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Select ProcessId,CreationDate,CommandLine`). LAIM 0.58.29 ya no necesita ese fichero: usa nombres temporales únicos, registra `leftover_locked` y sigue, y detiene sus propios procesos marcados cuando una transferencia agota el tiempo. Los procesos de LAIM 0.58.27/0.58.28 no llevan marca y LAIM nunca los detiene: termínalos a mano (o reinicia el equipo) si quieres que el fichero desaparezca.

**Registros heredados.** Un despliegue de Windows registrado en `/tmp/.laim/…` (antes de LAIM 0.58.27) es `stale`: nunca se sondea ni se ejecuta, la siguiente ejecución pide redesplegar en `%USERPROFILE%\.laim\tools` y el registro antiguo se cierra como `undeployed` sin ninguna orden en el equipo (`last_verify_error` lo explica).

**Respaldo honesto.** Cuando una herramienta elegida para una pregunta no da una medida — `deploy_failed`, fallo de verificación, `hash_mismatch` sin redespliegue, `arch_mismatch`, `deploy_declined`, permiso denegado, `exec_failed`, `timeout`, `output_invalid`, `truncated` — LAIM nunca responde a otra pregunta. O bien:

1. **Comandos nativos de solo lectura** que miden exactamente lo mismo, si el manifest aprobado declara un `fallback` para el segmento del equipo. Se construyen solo con los argumentos **validados** de la llamada (entre comillas para el shell de ese segmento), se vuelven a comprobar con el clasificador de solo lectura, se muestran en la pregunta normal de solo lectura (`🔐 Comandos propuestos para ejecutar en «<host>»`) y solo se ejecutan con un sí; la respuesta dice que la herramienta no se pudo usar y por qué, y muestra cada comando con su salida. Se audita en el grupo `tools`, acción `fallback`. O bien
2. **El mensaje honesto:** `No se pudo usar la herramienta LAIM <slug> v<N> en <host>: <motivo>.` y el turno termina ahí, sin otra medida.

El propio `{"error": …}` de la herramienta (p. ej. la carpeta no existe) y un consentimiento de lectura rechazado terminan con el mensaje honesto, sin comandos nativos.

**El campo `fallback`** (opcional, solo herramientas `read_only`):

```json
"fallback": [
  {"segment": "linux",   "commands": ["du -sb -- {path}", "find {path} -type f | wc -l"]},
  {"segment": "mac",     "commands": ["du -sk {path}", "find {path} -type f | wc -l"]},
  {"segment": "windows", "commands": ["Get-ChildItem -LiteralPath {path} -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum | Select-Object Count,Sum | Format-List"]}
]
```

Validación (severidad `error`): una entrada por segmento (`fallback_segment_invalid`, `fallback_segment_duplicate`); de 1 a 3 comandos de 400 caracteres como máximo (`fallback_commands_count`, `fallback_command_invalid`); `{param}` debe ser una palabra entera y un param declarado y no `sensitive` (`fallback_unknown_param`, `fallback_sensitive_param`); sin rutas literales (`fallback_literal_value`) ni metacaracteres de shell salvo la tubería — sin comillas, `;`, `&`, `>`, `<`, `$`, comillas invertidas, paréntesis ni llaves (`fallback_shell_metachar`); cada comando debe pasar el clasificador de solo lectura de su segmento (`fallback_not_read_only`); solo herramientas `read_only` (`fallback_requires_read_only`).

**Recompilar + volver a aprobar.** `fallback` forma parte del manifest, así que cambia el sha256 canónico del manifest. Una herramienta aprobada antes de LAIM 0.58.27 (p. ej. `dirsize` v1) no tiene `fallback`: hasta que se recompile desde Developer y se apruebe la versión nueva (23bis.9), sus fallos terminan solo con el mensaje honesto. La ubicación de Windows y las órdenes codificadas no necesitan recompilar: se aplican a todo despliegue hecho por LAIM 0.58.27 o posterior.

### 23bis.11 Ruta rápida de herramientas en el chat, presentador y «LAIM explica sus herramientas»

Desde LAIM 0.58.31 el chat ya no usa AppAssist: una herramienta aprobada se ejecuta por la **ruta rápida de herramientas**, su respuesta la construye un **presentador genérico** a partir del manifest, lleva la **línea Method** de LAIM y el comando ejecutado como cualquier turno medido, y LAIM sabe **explicar sus propias herramientas**.

**Ruta rápida de herramientas.** Se comprueba en cada turno de chat antes de los orquestadores y de la ruta rápida heurística (turnos de Connect / Share: no en v1):

1. **Equipo.** Se usa el *Equipo destino* del chat tal cual: desaparece la pregunta «El chat apunta a X. ¿Usar ese equipo para AppAssist? (s/n)». Con *Localhost* (sin equipo remoto) la herramienta se ejecuta en el equipo LAIM. LAIM solo pregunta si hay ambigüedad: la pregunta nombra otro equipo distinto del destino del chat («La pregunta menciona X y el chat apunta a Y. ¿Ejecutar en X?»), o nombra uno sin que el chat tenga destino remoto («¿La consulta se refiere al equipo X?»).
2. **Selección.** El catálogo por equipo de 23bis.7 de ese equipo, ordenado para la pregunta. Su primera herramienta solo se usa si es `read_only` **y** el `heuristic_cases` de su manifest contiene el caso heurístico de la pregunta —`dirsize` declara `generated_app_assist`: tamaño y número de ficheros de una carpeta nombrada con una palabra («carpeta», «folder») o por su ruta (`/var/log`, `C:\Windows\Logs`)— o si la pregunta la nombra por su slug con una relevancia de al menos 20. Las herramientas `writes` / `exec` nunca entran en esta ruta.
3. **Argumentos solo de la pregunta** (`extract` del manifest: `path` → la primera ruta absoluta, `int` / `pid` → el primer número, `host` → el primer nombre de equipo). Un valor obligatorio que falte se pregunta una vez como su slot (`LAIM necesita un dato real para ejecutar <slug> … ¿Valor de <ruta>?`); una respuesta vacía no ejecuta nada y el turno sigue por el camino normal.
4. **Ejecución.** El ejecutor de 23bis.8: la pregunta de despliegue si el equipo no tiene la copia aprobada verificada y después la pregunta de consentimiento de solo lectura con la línea `laim-tool <slug> <args> @<equipo>`. Las reglas del autorun de Suggestions no cambian.
5. **Respuesta.** Determinista: sin modelos de F2–F7 ni traducción por modelo (`DeterministicCaseID` = `tool:<slug>`); F8 como siempre. Una llamada que no da medida termina con la respuesta honesta de 23bis.10.

**Presentador genérico (`PresentToolResult`).** Se construye solo con el `output` del manifest: los campos declarados no primarios encabezan la respuesta (``Carpeta `C:\Windows\Logs`:``), los `primary` son líneas `- Etiqueta: valor` y `list_field` es una tabla con `list_columns`. Etiquetas `label_es` / `label_en` (español por defecto, inglés si el turno es en inglés). Tipos: `bytes` → tamaño legible y MB exactos (`98.0 MB (98.00 MB)`), `int` (con `unit`), `duration_ms` (`2 min 5 s`), `timestamp` (RFC 3339 → `2026-10-13 08:00:00 UTC`), `bool` (sí / no). Un campo `sensitive` sale siempre como `********`. JSON no válido, un campo de error relleno o una salida truncada **no** dan respuesta determinista (mensaje honesto en su lugar); nunca se responde con la salida cruda. Sustituye al formateador exclusivo de dirsize `FormatDirsizeAssistSummary` (queda como envoltorio obsoleto con las mismas cifras).

```text
Carpeta `C:\Windows\Logs`:
- Tamaño: 98.0 MB (98.00 MB)
- Ficheros: 379

**Method:** ran `laim-tool dirsize --json --path 'C:\Windows\Logs'` (heuristic case `tool:dirsize`). LAIM tool `dirsize` v1 (sha256 d7f3bb6c) on POWERPC.
```

**Línea Method y comandos ejecutados.** Una ejecución de herramienta se informa como cualquier ejecución heurística: la línea Method estándar de LAIM (`` **Method:** ran `<comando>` (heuristic case `tool:<slug>`). ``, en inglés como todas las líneas Method) seguida de la procedencia (herramienta, versión aprobada, prefijo del sha256, equipo). La salida de comandos del turno —SSE `command_output` y `done.command_output`— es `$ laim-tool <slug> <args>` más el JSON enmascarado, y la web la muestra como bloque de comando. Una llamada que no se ejecutó nunca lleva línea Method; tras una llamada fallida, la línea Method solo lista los comandos nativos del respaldo que sí se ejecutaron.

**Nota de medición para University.** University lee la línea Method (`ExtractLaimExecutedCommands`) y las líneas `$ ` de la salida de comandos, así que una ejecución de herramienta cuenta como ejecución medida de `laim-tool <slug> …`. `laim-tool` no es un programa del equipo: University no debe volver a ejecutarlo como sonda por SSH; comprueba la medida con comandos nativos de solo lectura (pkg33i).

**LAIM explica sus herramientas (`laim_tool_info`).** «¿qué es dirsize?», «¿para qué sirve dirsize?», «¿cómo se usa dirsize?», «what is dirsize», «explain dirsize», «¿qué herramientas tiene LAIM?», «what LAIM tools are available?». La respuesta es determinista y sale del manifest **aprobado**: qué es (`purpose_es` / `purpose`), para qué sirve (los intents como preguntas de ejemplo, `heuristic_cases`), cómo se usa (parámetros con tipo, obligatorio y slot; una pregunta de ejemplo; la orden que ejecuta LAIM, p. ej. `laim-tool dirsize --json --path <ruta>`), la clase de efecto y el consentimiento que pide, las plataformas, su estado en cada equipo al que el usuario tiene acceso (y en el equipo LAIM), la versión aprobada, el autor, quién la aprobó y cuándo. Termina con `**Método:** catálogo de herramientas LAIM (manifest aprobado).` (en inglés: `**Method:** LAIM tool catalog (approved manifest).`): sin comando, no se ejecutó nada. Una pregunta sobre una herramienta nunca la ejecuta.

| Quién | Ve |
|-------|----|
| Usuario | Herramientas aprobadas, no efímeras y `read_only`; los equipos a los que tiene acceso |
| Admin | Además las herramientas `writes` / `exec`, borradores, propuestas, rechazadas y retiradas, marcadas como tales (estado y versión pendiente) |

Las herramientas efímeras (de test) nunca se muestran. Un nombre desconocido recibe «No hay ninguna herramienta LAIM llamada X» solo si la pregunta nombra explícitamente una herramienta LAIM («¿qué es la herramienta LAIM X?»); un «¿qué es X?» sin más cuya X no es una herramienta visible para el usuario —o «¿qué es el uso de disco?»— sigue por el camino normal.

**`manifest_check.catalog_eligible`.** Se recalcula al aprobar (para entonces todas las plataformas declaradas están compiladas) y en cada lectura: una herramienta aprobada y apta ya no muestra `catalog_eligible: false` en `GET /api/v1/apps`.

**Opción de compatibilidad.** `LAIM_LEGACY_APPASSIST=1` en el entorno de LAIM recupera el bloque AppAssist (sin línea Method); por defecto se usa la ruta rápida de herramientas. AppAssist tampoco pregunta ya «El chat apunta a X…».

---

## 24. Editor Markdown con IA

El **LAIM Editor** es una aplicación web embebida (`go:embed` en `internal/editor/`) servida en `http://localhost:4320/editor/`. Los usuarios la abren desde **Ayuda → Editor**.

### 24.1 Capacidades

- Notas Markdown por usuario, contenido cifrado en `LAIMConfigDir()/notes/<id>.enc`
- Metadatos en `laim.dat` → `Notes[]` (aislamiento por `username`)
- Acciones IA inline: polish, rewrite, continue, summarize, translate (16 idiomas)
- Panel de chat SSE con el documento como contexto
- Preview con marked.js, highlight.js y Mermaid
- Exportación Markdown, HTML y PDF (solo contenido del preview)

### 24.2 Configuración admin

**Internal › Local → Editor IA** (ver [§11.3](#113-local--configuracion-de-instalacion)):

| Campo | Uso |
|-------|-----|
| `inline_ai_model` | Modelo Ollama para acciones sobre texto seleccionado |
| `chat_model` | Modelo Ollama para el panel lateral |
| `auto_save` / `auto_save_delay_ms` | Persistencia automática del borrador |

### 24.3 API REST (`:4320`, sesión web requerida)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET/POST | `/api/v1/editor/notes` | Listar / crear notas |
| GET/PUT/DELETE | `/api/v1/editor/notes/{id}` | Leer / actualizar / eliminar |
| POST | `/api/v1/editor/notes/{id}/export` | Exportar HTML |
| POST | `/api/v1/editor/ai/inline` | Acción inline (JSON: action, text, language) |
| POST | `/api/v1/editor/ai/chat` | Chat SSE con documento |

La autenticación usa el mismo `X-LAIM-Session-ID` (el editor recibe `?sid=` al abrirse).

### 24.4 Modo Connect → Share

En un nodo Connect:

| Recurso | Donde vive |
|---------|------------|
| Notas (`.enc` + metadatos) | **Local** (slave), cifrado con `master_key_cipher` del slave |
| Modelos Editor / tiers / ventana de contexto | **Share master** |
| Inferencia inline / chat | Proxy cifrado `POST /api/v1/share/editor/ai/inline` y `…/chat` |

No hay UI de config del Editor en Connect (Internal no se muestra). Si el Share no responde, el slave intenta Ollama local como fallback. El master registra `remote_editor_inline` / `remote_editor_chat` en `activity.log`.

---

## 25. Sistema de Notificaciones

Canal bidireccional persistente entre LAIM («interno») y el usuario («cliente»).

### 25.1 Almacenamiento

- Fichero `notifications.dat` cifrado con `master_key_cipher` (mismas reglas que `laim.dat`)
- Tipos: teacher, download, chat, system, update, **security_alert** (agente Secure)

### 25.2 Superficies

| Superficie | Uso |
|------------|-----|
| Web — sidebar **Notificaciones** | Badge de no leídas, hilos estilo chat, reply con IA (tier medium) |
| CLI `laim notifications` | Listar, marcar leídas, responder |
| Connect | Proxy al Share master; no leer el `notifications.dat` local vacío |

### 25.3 API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/notifications` | Lista (usuario / admin ve más) |
| POST | `/api/v1/notifications/{id}/read` | Marcar leída |
| POST | `/api/v1/notifications/{id}/reply` | Respuesta → inferencia → hilo |
| DELETE | `/api/v1/notifications/{id}` | Eliminar |
| GET | `/api/v1/notifications/events` | SSE de nuevas notificaciones |

### 25.4 Origenes tipicos

| Evento | Tipo de notificacion |
|--------|----------------------|
| Job teacher terminado | teacher |
| Descarga de modelo | download |
| Amenaza bloqueada por Secure / REJECT | security_alert (admins). SecureAgent además escribe `reports/secure_*.md` (Informes → Incidencias) y lo cita en el mensaje |
| Sandbox violation (path-traversal) | system (admins) |
| Anti-proxy 403 (throttle 5 min/IP) | system (admins) |
| Share API no escucha / firewall Share fallido | system (admins) |
| Firewall LAIM repair fallido | system (admins) |
| Headscale start/stop fallido | system (admins) |
| Clave Share regenerada | system (admins) |
| Otros jobs relevantes | chat / system |

En modo Connect, el teacher y las notificaciones se crean en el **master** para que el panel del esclavo las vea via proxy.

---

## 26. Ventana de contexto y cache

Resumen operativo. El manual completo esta en Ayuda → **Ventana de contexto** (`context_window_manual.md`).

### 26.1 Objetivo

Controlar `num_ctx` y `keep_alive` de Ollama, y comprimir historial largo con el proceso **Chat Context Summarized** (tier medio) antes de saturar VRAM.

### 26.2 Ambito

| Funcionalidad | Historial |
|---------------|-----------|
| Chat (8 fases) | `laim.memory` |
| Direct | Mensajes de la conversacion en RAM |
| Sugerencias IA SSH | Historial de la sesion de sugerencias |

### 26.3 Configuracion

Ver parametros en [§11.3](#113-local--configuracion-de-instalacion). El usuario ve el aviso de contexto comprimido en el chat; no necesita configurar nada.

### 26.4 Recomendacion

No subir `max_context_tokens` por encima de lo que permite la VRAM (tabla en el manual dedicado). En hardware basico preferir 4096–8192.

---

*Manual de administrador — LAIM Core v0.3.14 · Actualizado 2026-09-09 (ejemplos por seccion, agentes mlx/scheduler, ficha Direct en cache, TTS EN/ES)*
