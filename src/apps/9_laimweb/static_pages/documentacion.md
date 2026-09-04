# Documentación

## Una brújula, no un manual interminable

Esta página es la **referencia pública** del cliente **LAIM** (*Local Artificial Intelligence Management*).
Está pensada para que sepas *dónde está cada cosa* y *qué comando usar*, sin ahogarte
en detalle interno.

Si buscas el porqué del proyecto, empieza por **Inicio** y **Presentación**.
Si quieres instalar o descargar, ve a **Servicios**.
Si ya tienes cuenta, los **Manuales** del área privada te llevan paso a paso.

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

Ahí encaja **MOM** (*Mixture of Models*): según la pregunta, el hardware y el
perfil, LAIM puede **activar el modelo adecuado** —uno ágil, uno más capaz,
uno de dominio— en lugar de forzar un único cerebro para todo. Es la idea
hermana de MoE (*Mixture of Experts*), pero a escala de **modelos enteros**.
Más detalle en **Inicio**.

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

Verás un panel de **comandos** y un área de **terminal**: misma semántica que la CLI,
con la estética CRT. Además tienes chat, inferencia directa, equipos remotos,
informes y configuración —según tu rol.

| Quieres… | Usa… |
|----------|------|
| Scripts y automatización | CLI |
| Trabajar con ratón y visores | `laim web` |
| Descargar, leer esto o abrir un ticket | este portal |

---

## Dónde seguir leyendo

Tras iniciar sesión en el portal o en el cliente:

- **Manuales** — instalación, uso diario, voz, SSH, privacidad y preguntas frecuentes.
- **Manual de administrador** — usuarios, red, firewall, Share y endurecimiento.
- **`laim help`** — la lista oficial de comandos de *tu* versión instalada.

Enlaces que suelen hacer falta:

- [Ollama](https://ollama.com/) — motor de modelos locales
- [getmylllm.com](https://www.getmylllm.com/) — modelos a medida y el ciclo de entrenamiento
- [Reflex](https://reflex.dev/docs/) — base técnica de la web local del cliente

Si un comando no aparece en tu `laim help`, tu instalación es más antigua o más
nueva que esta página: **confía en la ayuda del binario**. Esta documentación
explica el mapa; el cliente dice la verdad de lo que tienes delante.

> *Documentar es acompañar. Si te pierdes, Contacto está a un clic.*
