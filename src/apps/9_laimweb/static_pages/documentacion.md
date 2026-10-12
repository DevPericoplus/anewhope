# Documentación

## Una brújula, no un manual interminable

Esta página es la **referencia pública** del cliente **LAIM** (*Local Artificial Intelligence Management*).
Está pensada para que sepas *dónde está cada cosa* y *qué comando usar*, sin ahogarte
en detalle interno.

Si buscas el porqué del proyecto, empieza por **Inicio** y **Presentación**.
Si quieres instalar o descargar, ve a **Servicios**.
Los textos largos —instalación, chat, red, avisos legales— viven en el
cliente: **`laim web` → Ayuda**. Tras iniciar sesión aquí, **Manuales**
apunta al mismo material de uso diario.

> No hace falta memorizar nada. Léelo como un mapa: primero el paisaje, después las calles.

---

## Tres sitios, una misma LAIM

LAIM se usa de tres maneras. Las tres hablan con el mismo núcleo; cambia solo la puerta.

| Dónde | Qué es | Cuándo te encaja |
|-------|--------|------------------|
| **CLI** (`laim …`) | El binario en tu terminal | Automatizar, administrar, trabajar por SSH |
| **Web local** (`laim web`) | Interfaz en tu equipo (`http://localhost:4321`) | Día a día con pantallas, sin salir de tu máquina |
| **Este portal** | Catálogo, cuenta e instaladores | Conocer el proyecto, descargar y volver cuando lo necesites |

La web local **no sustituye** a la consola: la complementa. Un clic en un comando
hace lo mismo que escribirlo en la terminal. El cerebro sigue siendo LAIM Core.

---

## Cómo empezar (sin prisa)

En un equipo nuevo el camino habitual es este:

1. **Instala** el cliente (Windows, macOS o Linux) desde **Servicios → Instaladores**.
2. Abre una terminal en la carpeta de instalación y ejecuta **`laim init`**.
   Ahí decides si quieres IA local con [Ollama](https://ollama.com/) y se crea
   el espacio de trabajo de esa máquina.
3. Entra con **`laim login`**. Así la sesión queda cifrada y las acciones
   se asocian a tu usuario.
4. Prueba **`laim chat`** para conversar, o **`laim web`** si prefieres el navegador local.
5. En la web local, abre **Ayuda**: ahí están los manuales de *tu* versión
   (español o inglés) y las herramientas Editor y Temas.

El binario se llama **`laim`** en macOS y Linux, y **`laim.exe`** en Microsoft Windows.
La ayuda canónica, siempre al día en tu instalación, es:

```bash
# macOS y Linux
laim help

# Microsoft Windows
laim.exe help
```

---

## Comandos para todo el mundo

Estos los puede usar cualquier persona autenticada. Piensa en ellos como
el día a día.

| Comando | Para qué sirve |
|---------|----------------|
| **`help`** | Muestra esta brújula en la propia terminal. |
| **`version`** | Versión instalada del cliente. |
| **`info`** | Ficha técnica del equipo: sistema, CPU, memoria, GPU… útil para diagnosticar. |
| **`login`** | Abre una sesión cifrada. Necesaria cuando ya hay usuarios en el equipo. |
| **`logout`** | Cierra la sesión y vuelve al prompt; LAIM sigue en marcha. |
| **`chat`** | Conversación interactiva. Sin argumento usa el *tier* configurado; puedes indicar un modelo. |
| **`remote`** | Equipos de tu red por SSH (y WinRM en Windows): grupos, credenciales y terminal. |
| **`web`** | Arranca la interfaz local. Solo ves una barra de progreso: pensado para el uso cotidiano. |
| **`webdebug`** | Igual que `web`, pero con trazas técnicas. Úsalo si algo no arranca. |

### El chat, en una frase

`laim chat` no es un «pregunta y olvida». Recorre un **flujo de varias fases**:
entiende el idioma, aplica reglas de seguridad, y si hablas del sistema en vivo
puede proponerte comandos, pedirte permiso y ejecutarlos en **tu** máquina
(Windows, macOS o Linux). Tú siempre confirmas lo delicado.

Ahí encaja **MOM** (*Mixture of Models*): los administradores asignan un
modelo local a cada **tier** (rápido, medio, traductor, sonido…) y cada
fase o agente usa esa casilla. No decide el modelo en caliente: decide
quien configura LAIM. Es la idea hermana de MoE (*Mixture of Experts*),
pero a escala de **modelos enteros**, con warmup, paralelismo y KV-cache.

Y encaja el **alma** de LAIM: en el chat y en otras pantallas, **💡 Sugerir
mejora** traduce tu corrección en conocimiento para la heurística
(sin chocar ni duplicar lo que ya sabe) y lo comparte con todos los
usuarios de *esa* instalación. Más detalle de MOM y del alma en **Inicio**.

---

## Comandos de administración

Estos piden rol **administrador** cuando ya existen usuarios. Sirven para
preparar el equipo, no para el uso diario de todo el mundo.

| Comando | Para qué sirve |
|---------|----------------|
| **`init`** | Primera configuración: IA local opcional, inventario del hardware, identidad de la instalación. |
| **`config`** | Asistente interactivo: usuarios, tiers, Share/Connect y el resto de ajustes cifrados. |
| **`localmodels`** | Lista los modelos Ollama ya instalados, agrupados por tamaño. |
| **`catalog`** | Recorre el catálogo público de Ollama e instala modelos con una guía. |
| **`eval`** | Evalúa un modelo local con un juego de pruebas y guarda el resultado. |
| **`compare`** | Compara, lado a lado, dos evaluaciones previas. |
| **`connect`** | Perfiles para usar la IA de un **Share** de tu red (cliente). |
| **`share`** | Convierte este equipo en **maestro** de IA para otros nodos (API de red, por defecto puerto 4322). |
| **`agents`** | Acceso al modo de **agentes** autónomos de la sesión. |
| **`update`** | Actualiza el cliente a la última versión o a una concreta. |
| **`audit`** | Registro de cambios de configuración y actividad, por grupos. |
| **`notifications`** | Avisos del sistema: descargas, sugerencias, eventos. |
| **`monitor`** | Pantalla completa en vivo: CPU, memoria, disco, red y procesos. |

> **Share y Connect, en corto.** Un equipo puede *ofrecer* la IA (Share) y otros
> pueden *usarla* (Connect) eligiendo la **ruta IA**: este ordenador (*Localhost*)
> o un Share de la LAN. Las preguntas al sistema vivo siguen ejecutándose
> **donde estás sentado**; lo que viaja es la inferencia, cifrada.

---

## La web local, sin misterio

Cuando lanzas `laim web`:

- El navegador abre **`http://localhost:4321`**.
- La API local escucha en **`127.0.0.1:4320`** (solo en tu máquina, no en la red).
- Si este equipo es Share, la puerta hacia otros nodos es **`4322`**.
- **Ayuda** (en el menú del cliente) abre los documentos y herramientas
  de las secciones siguientes.

Verás un panel de **comandos** y un área de **terminal**: misma semántica que la CLI,
con la estética CRT. Además tienes chat, inferencia directa, equipos remotos,
informes y configuración —según tu rol.

| Quieres… | Usa… |
|----------|------|
| Scripts y automatización | CLI |
| Trabajar con ratón y visores | `laim web` |
| Leer los manuales de *tu* instalación | `laim web` → **Ayuda** |
| Descargar, leer esto o abrir un ticket | este portal |

---

## En la Ayuda del cliente

La página **Ayuda** del cliente lista ocho entradas. Las seis primeras son
documentos (el texto completo de *tu* versión, en el idioma de la interfaz).
**Editor** y **Temas** son herramientas, no ficheros. Aquí va solo un
resumen para que sepas cuál abrir.

---

## Manual de administrador

Instalación, usuarios, tiers de modelos, agentes, Share/Connect, equipos
remotos, Headscale, cifrado, auditorías y mantenimiento. Es el libro de
quien prepara el equipo: el primer arranque, cómo dar de alta personas y
cómo dejar la instalación lista para el resto.

---

## Manual de usuario

Chat, inferencia directa, voz, sesiones SSH, notificaciones, editor,
privacidad y preguntas frecuentes. Empieza aquí si ya tienes LAIM
instalado y quieres usarlo día a día, sin tocar la configuración de
administrador.

---

## Red mesh WireGuard (Headscale)

Cómo LAIM monta una malla privada (Headscale + cliente Tailscale) para
que el chat, `laim remote` y las sugerencias lleguen a equipos de otras
redes sin abrir puertos a Internet. Linux o macOS pueden ser el
coordinador; Windows entra como nodo, no como servidor Headscale.

---

## Recomendaciones

Guía de uso responsable y avisos legales: el aprendizaje queda en *esa*
instalación, qué límites hay, qué usos de alto riesgo están fuera y qué
aceptas al usar LAIM. Léela antes de poner el cliente en un entorno de
producción o compartido.

---

## Ventana de contexto

Cómo LAIM recorta y resume el historial que ve el modelo (`num_ctx`,
compresión «Chat Context Summarized») y qué VRAM pide cada tamaño de
ventana. Ábrelo si el chat «olvida» el principio de la conversación o
el equipo se queda sin memoria al subir el contexto.

---

## Windows remoto (OpenSSH)

Activar el Servidor OpenSSH en Windows 10/11 o Server para que otro
LAIM se conecte con `laim remote`, sin WSL. En el propio Windows, Ayuda
lleva el botón que lo habilita con UAC y registra el equipo.

---

## Editor

Editor Markdown con acciones de IA (mejorar, reescribir, continuar,
resumir, traducir) y un chat que usa el documento como contexto. Las
notas se guardan cifradas por usuario. No es un manual: se abre desde
Ayuda → Editor.

---

## Temas

Elige el aspecto de la interfaz local (CRT, suave, relieve, metal…).
Cambia el look, no el comportamiento ni los datos. Se abre desde
Ayuda → Temas; puedes volver al predeterminado cuando quieras.

---

## Dónde seguir leyendo

Los textos completos en español están en **Manuales** (tras iniciar
sesión): la misma réplica que abre **`laim web` → Ayuda**. Editor y
Temas siguen siendo herramientas del cliente, no documentos.

- **`laim help`** — la lista oficial de comandos de *tu* versión.
- [Ollama](https://ollama.com/) — motor de modelos locales
- [getmylllm.com](https://www.getmylllm.com/) — modelos a medida y el ciclo de entrenamiento

Si un comando no aparece en tu `laim help`, tu instalación es más antigua o más
nueva que esta página: **confía en la ayuda del binario**. Esta documentación
explica el mapa; el cliente dice la verdad de lo que tienes delante.

> *Documentar es acompañar. Si te pierdes, Contacto está a un clic.*
