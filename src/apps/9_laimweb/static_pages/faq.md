# Preguntas frecuentes (FAQ)

## Respuestas rápidas con transparencia

### ¿Mis datos salen de mi equipo?

En el **modo local** estándar, el procesamiento puede realizarse íntegramente en su infraestructura. Las integraciones en la nube o con terceros son **opcionales** y usted las configura explícitamente.

### ¿LAIM es gratuito?

El cliente y los recursos incluidos en su cuenta de portal están sujetos a las condiciones de su organización o plan. Los modelos personalizados y proyectos avanzados se gestionan a través de [getmylllm.com](https://www.getmylllm.com/).

### ¿Qué diferencia hay entre modelos base, especializados y personalizados?

- **Base** — Punto de partida general, adaptable a su hardware
- **Especializados** — Enriquecidos con dominio concreto
- **Personalizados** — Entrenados con su información privada para uso interno

### ¿Puedo usar LAIM sin conexión a Internet?

Sí, para operación local una vez descargados el cliente y los modelos necesarios. Este portal requiere conexión para **autenticación** y **descargas** actualizadas.

### ¿Cómo mantengo un entorno seguro?

Utilice contraseñas robustas, mantenga el sistema actualizado, limite los complementos a fuentes de confianza y consulte el manual de **Configuración segura** en la sección Manuales.

### ¿Dónde obtengo ayuda humana?

En **Soporte** puede abrir un ticket o escribirnos. Preferimos acompañarle con claridad antes que dejarle con un error críptico.

---

## Cómo usar la CLI

La CLI es el binario en su terminal: `laim <comando> [opciones]`.
En Windows el ejecutable se llama **`laim.exe`**; en macOS y Linux, **`laim`**.
La ayuda canónica, siempre al día en *su* instalación, es:

```bash
# macOS y Linux
laim help

# Microsoft Windows
laim.exe help
```

Hay dos grupos: comandos **generales** (cualquier usuario con sesión) y de
**administración** (solo el administrador, cuando ya hay usuarios dados de alta).

### ¿Cómo empiezo en un equipo recién instalado?

El administrador deja el espacio de trabajo listo y luego cada persona entra
con su usuario.

```bash
laim init
laim login
laim chat
```

`init` pregunta si quiere IA local (Ollama) y crea la configuración de esa
máquina. Después suele abrir la web local; si está automatizando o no quiere
el navegador:

```bash
laim init --no-web
```

`--install-path` cambia dónde se guardan los datos (por defecto `~/laimapp`).

### ¿Cómo inicio y cierro la sesión?

`login` abre una sesión cifrada (`laim.session`). `logout` la cierra y vuelve
al prompt; **LAIM sigue en marcha**.

```bash
laim login
laim logout
```

Si el equipo ya tiene usuarios, casi todo lo demás (chat, web, administración)
pide esa sesión.

### ¿Cómo converso desde la terminal?

Sin modelo, `chat` usa los **tiers** que el administrador asignó en
`laim config` (rápido, medio, lento…). Con un nombre, fuerza ese modelo de
Ollama.

```bash
# Flujo normal, con los tiers configurados
laim chat

# Forzar un modelo concreto
laim chat llama3.2:1b

# Sin el flujo de varias fases: va directo al modelo
laim chat --perfil direct

# Ver sesiones anteriores o métricas, sin abrir un chat nuevo
laim chat --list
laim chat --perf
```

Usted confirma lo delicado (comandos sobre su máquina). Si no hay tiers y no
indica modelo, LAIM le dirá cómo completar `laim config` → Modelos IA.

### ¿Qué diferencia hay entre `web` y `webdebug`?

Las dos arrancan la interfaz local (`http://localhost:4321`).
`web` solo muestra una barra de progreso. `webdebug` escribe el detalle técnico
en la terminal: úselo si la web no abre o se queda a medias.

```bash
laim web
laim webdebug
```

### ¿Cómo veo la versión y qué hardware tengo?

```bash
laim version
laim info
```

`info` resume sistema, CPU, memoria y GPU. Es lo primero que pedimos en un
ticket de Soporte si algo «no arranca».

### ¿Cómo me conecto a otro equipo de la red?

`remote` abre el cliente de equipos (SSH y, en Windows, también WinRM):
grupos, credenciales y terminal remota.

```bash
laim remote
```

### ¿Qué puedo hacer solo si soy administrador?

Estos comandos piden rol administrador cuando ya hay usuarios. Sirven para
preparar el equipo, no para el día a día de todo el mundo.

```bash
laim config          # asistente: usuarios, tiers, Share/Connect…
laim localmodels     # modelos Ollama ya instalados, por tamaño
laim catalog         # catálogo público; instala con una guía
laim catalog gemma   # empieza filtrando por «gemma»
laim eval            # elige el modelo en un menú
laim eval llama3.2:1b
laim compare llama3.2:1b gemma3:1b
laim connect         # este equipo usa la IA de un Share de la LAN
laim share           # este equipo ofrece IA a otros nodos
laim agents          # modo de agentes autónomos de la sesión
laim audit           # cambios de config y actividad por grupo
laim notifications   # avisos: descargas, sugerencias, eventos
laim monitor         # CPU, memoria, disco, red y procesos en vivo
```

`eval` guarda 9 pruebas (3 categorías) en `laim.dat`. `compare` solo funciona
si **ambos** modelos ya se evaluaron. `catalog` necesita Internet; `localmodels` no.

### ¿Cómo actualizo LAIM?

Cada subcomando es un paso explícito. Sin argumento es lo mismo que `check`.

```bash
laim update              # ¿hay versión nueva?
laim update check
laim update download     # baja el parche
laim update apply        # lo deja listo
laim update restart      # aplica el binario y reinicia ahora
```

Para un complemento concreto: `laim update check --plugin NombreDelPlugin`
(también en `download` y `apply`; `restart` no admite `--plugin`).

### ¿Share y Connect son lo mismo?

No. **Share** convierte *este* equipo en maestro de IA para la red (API, por
defecto el puerto 4322). **Connect** hace que *este* equipo use la IA de un
Share. Las acciones sobre el sistema vivo se ejecutan donde usted está sentado;
lo que viaja es la inferencia, cifrada.

```bash
# En el equipo que ofrece la IA
laim share

# En el equipo que la consume
laim connect
```

### Escribí un comando mal. ¿Qué ocurre?

LAIM responde `Unrecognized command`, vuelve a pintar `laim help` y no cambia
nada. Pruebe otra vez, o abra **Documentación** para el mapa de comandos y
**Manuales** para el detalle de *su* versión.

> ¿No encuentra su respuesta? Use el botón **Ir a Soporte** o explore la documentación en **Manuales**.
