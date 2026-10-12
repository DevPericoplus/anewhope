# Instaladores LAIM

## El cliente en su equipo

Desde aquí descarga **LAIM community_edition** para **Windows** (`.exe`), **macOS** (`.dmg`, Apple Silicon e Intel) y **Linux** (`.deb` / `.rpm`). El paquete lleva el binario, los `.dat` comunes de producto y los plugins Basic.

Esta página es solo **instaladores**. Las actualizaciones posteriores las detecta el propio cliente (`laim update`), no este portal.

### Plataformas

| Sistema | Formato | Notas |
|---------|---------|-------|
| **Windows** | Instalador `.exe` | Sin privilegios de administrador. También puede descargarlo con `curl.exe` desde una terminal. |
| **macOS** | Disco `.dmg` o script `install.sh` | Apple Silicon e Intel. El script no pide `sudo`. |
| **Linux (Debian/Ubuntu)** | Paquete `.deb` o `install.sh` | El paquete instala en `/opt/laim`; el script, en `~/.local`. |
| **Linux (RHEL/Fedora)** | Paquete `.rpm` o `install.sh` | Mismo contrato que el `.deb`. |

Elija modalidad y plataforma más abajo. El botón muestra el fichero real publicado (por ejemplo `laim_install_2.0.1.exe`).

La edición **advance** se anunciará cuando el esquema de licencia esté listo.

---

## Tómese su tiempo: instalar no es solo copiar un fichero

El paquete deja el programa en el disco en unos minutos. **Tener LAIM listo para conversar** es otro tramo: hay que crear su espacio de trabajo, y —si quiere IA en este equipo— descargar el motor y unos modelos. Eso usa **Internet**, **disco** y **un rato de reloj**. No es un fallo: es el primer arranque.

Piense en tres capas:

1. **El cliente** — el programa que acaba de instalar.
2. **El motor** — [Ollama](https://ollama.com/), quien ejecuta los modelos en *su* máquina.
3. **Los modelos** — los «cerebros» (rápido, traductor, medio). Pesan gigas; no viajan dentro del `.exe`/`.dmg`.

Hasta que esas tres capas estén, el chat no puede ser plenamente útil. Por eso pedimos **paciencia** y mirar las **colas**.

---

## Mini guía, paso a paso

### 1. Instalar el paquete (1–5 minutos)

Abra el `.exe` o el `.dmg`, o ejecute el script. Cuando termine, abra una terminal.

Los tiempos de esta fase dependen sobre todo de si el antivirus o Gatekeeper revisan el fichero. En un portátil sencillo puede alargarse un poco; no suele pasar de unos minutos.

### 2. `laim init` — su instalación (1–3 minutos)

```text
laim init
```

En Windows, si `laim` no está en el PATH de esa ventana, ciérrela y abra otra, o use la ruta que indicó el instalador (`%LOCALAPPDATA%\LAIM\`).

`init` no descarga los modelos todavía. Prepara **esta** máquina:

| Qué crea | Para qué sirve |
|----------|----------------|
| Identidad y clave de la instalación | Cifra sus datos; no se copia a otro equipo |
| Inventario del hardware | RAM, CPU, GPU: así se eligen modelos que quepan |
| Base de conocimiento y traducciones | Vocabulario y textos de la interfaz |
| Usuario `localadmin` | Primer administrador; cambie la contraseña en `laim config` |

Si responde que sí a **IA local**, LAIM recuerda que debe instalar Ollama y el núcleo de modelos. Esas tareas **no bloquean** la terminal: las deja en las **colas** y siguen cuando abra `laim web`.

Si responde que no, puede usar LAIM como cliente ligero contra un Share de su red, o añadir Ollama más adelante.

### 3. Entre y mire las colas (aquí está la espera larga)

```text
laim login
laim web
```

La primera vez que abre la web local, LAIM puede preparar un entorno Python (unos **3–15 minutos** según el equipo y si ya hay paquetes en caché). Luego, en **Configuración → Internal → Gestor de colas**, verá el progreso.

`init` suele encolar, si pidió IA local:

| Tarea en cola | Qué descarga | Para qué | Tiempo orientativo |
|---------------|--------------|----------|--------------------|
| Instalación de Ollama | El motor oficial (ollama.com) | Hablar con los modelos **en su equipo**, sin nube | 3–15 min |
| Modelo **rápido** | Un modelo pequeño | Respuestas ágiles, fases livianas | 5–25 min |
| Modelo **traductor** | Un modelo de idioma | Entenderle y contestarle en su lengua | 5–30 min |
| Modelo **medio** | Un modelo más capaz | Razonar, redactar, el día a día del chat | 15–60 min (a veces más) |

Son **orientaciones**. Un escritorio con fibra y disco SSD está en la parte baja. Un portátil por Wi‑Fi, un antivirus que inspecciona cada mega, o un repositorio lento (Ollama, GitHub) se van a la parte alta. Si el hardware no da para un tier, LAIM **no lo encola**: no insiste en un modelo que no cabe.

Puede cambiar de pantalla: la descarga sigue. El chip «Descargando» y el gestor de colas le dicen si va bien. Si una descarga se corta, verá un aviso para **reanudar**; no hace falta empezar de cero.

### 4. Cuando las colas estén en verde

```text
laim chat
```

o siga en `laim web`. Ahí sí está plenamente funcional.

---

## Por qué hace falta Internet *solo* al principio

| Recurso | De dónde sale | Por qué no va en el instalador |
|---------|---------------|--------------------------------|
| **Ollama** | Sitio oficial del motor | Se actualiza por su cuenta; cada SO tiene su instalador |
| **Modelos** | Catálogo de Ollama | Cambian a menudo y pesan mucho; se eligen según *su* RAM/GPU |
| **Paquetes de la web local** | Índices Python | Solo la primera vez que lanza `laim web` |

El instalador de este portal **no** incluye esos gigas a propósito: así el paquete es pequeño y cada equipo descarga solo lo que puede ejecutar.

**Cuando todo haya bajado, LAIM no necesita Internet** para conversar, administrar el equipo ni usar la web local. Vuelve a hacer falta red solo si:

- actualiza el cliente (`laim update`);
- actualiza o cambia un modelo;
- quiere instalar **otros** modelos además de los propuestos en el primer arranque.

---

## Si algo se alarga

1. Abra el **Gestor de colas** y mire el estado (en cola / en curso / hecho / error).
2. Compruebe disco libre: Ollama pide margen; cada modelo son varios GB.
3. Compruebe la red hacia ollama.com. Un proxy corporativo puede frenar o bloquear la descarga.
4. No cancele a mitad sin motivo: una capa a medias se **reanuda**, no se tira.

> El primer día pide calma. Después, el trabajo se queda en su máquina.
