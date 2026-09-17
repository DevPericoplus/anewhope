# Bienvenido a LAIM

## Local Artificial Intelligence Management

**LAIM** es una forma cercana de trabajar con inteligencia artificial **en tu propio equipo**.
No hace falta enviar tus conversaciones, documentos o contraseñas a un servicio lejano:
la IA puede quedarse contigo, en casa o en la red de tu organización.

Piensa en LAIM como un compañero técnico que entiende lo que pides en lenguaje natural
y te ayuda a **gestionar sistemas, servicios y aplicaciones**. Habla con él desde la
línea de comandos o desde una web local. Tú decides el ritmo; la herramienta acompaña.

> Si es tu primera visita, respira: no necesitas ser experto en modelos.
> Esta página te cuenta, con calma, qué es LAIM y por qué existe.

---

## ¿Qué problema resuelve?

Durante años, usar IA ha significado elegir entre dos extremos: un chat en la nube
(cómodo, pero lejos de tus datos) o un modelo suelto en el ordenador (privado, pero
difícil de orquestar).

LAIM ocupa el espacio de en medio. Te ofrece:

- **Privacidad por defecto.** El trabajo cotidiano puede ejecutarse en local con [Ollama](https://ollama.com/).
- **Control.** Tú eliges el modelo, el equipo y si compartes la IA con compañeros de la red.
- **Utilidad real.** No solo «preguntar a un chat»: también administrar el sistema,
  conectar por SSH, generar informes o pedir que te escriba un script.

La misión es sencilla: **gestionar tecnología con el apoyo de la inteligencia artificial**,
sin perder de vista quién manda (tú) y dónde viven los datos (donde tú elijas).

---

## MOM: Mixture of Models

En el mundo de la IA se habla mucho de **MoE** (*Mixture of Experts*): un solo modelo
grande que, por dentro, enciende «expertos» según el trozo de la tarea. **Quién decide**
ahí es el propio modelo, en tiempo de inferencia.

En LAIM hacemos algo distinto. Lo llamamos **MOM** (*Mixture of Models*): un grupo de
**modelos pequeños de IA local**, cada uno con una capacidad concreta, que trabajan
juntos. No es un único cerebro para todo. Es un **estante de cabezas** que tú —o el
administrador de esa instalación— organizas.

> MoE es un equipo de especialistas **dentro de una misma cabeza**.
> MOM es un **estante de cabezas distintas**: los administradores eligen cuál
> usa cada función, y LAIM se encarga de tenerlas listas, en paralelo y a
> medida del hardware.

### ¿Quién decide?

**Los administradores de cada LAIM.** No el modelo. No un algoritmo opaco que
«adivina» el caso.

Lo hacen con **familias de tiers**. De serie vienen dos: **blue** y **green**.
Cada familia es un conjunto de casillas (tiers). En cada casilla se asigna
**un modelo**. Luego, cada funcionalidad de LAIM apunta a un tier. Así el
sistema sabe qué modelo usar en cada momento: traducir, responder rápido,
razonar, ver una imagen, escuchar, sintetizar voz o escribir código.

Puedes tener, por ejemplo, una familia **estable** (blue) para el día a día y
otra **experimental** (green) para probar candidatos. O una familia para
**monopuesto** y otra para un **LAIM Share** que presta GPU a nodos ligeros
en Connect. Cambiar de familia activa es cambiar de receta completa, sin
perder la anterior.

| Idea | MoE (Mixture of Experts) | MOM (Mixture of Models) en LAIM |
|------|--------------------------|----------------------------------|
| ¿Qué se enciende? | Expertos *dentro* de un mismo modelo | **Modelos enteros**, uno por cada necesidad |
| ¿Para qué? | Especializar capas internas | Cubrir cada función con el modelo adecuado |
| ¿Quién decide? | El propio modelo, en tiempo de inferencia | **Los administradores**, con familias de tiers |

### Adaptar MOM al hardware y al uso

LAIM no elige solo «según el hardware». **Tú eliges modelos que quepan** en
esa máquina. Los billones de parámetros (un 4B, un 8B, un 27B…) piden
memoria para cargarse. En un flujo o *pipeline* es normal querer **varios
modelos a la vez** en VRAM, de forma predictiva, para no esperar a que se
carguen entre fases.

Como orientación de partida (GPU):

| Perfil | Memoria GPU | Ejemplo en el tier medio |
|--------|-------------|--------------------------|
| **Mínima** | 6 GB | un modelo ~4B |
| **Base** | 12 GB | un modelo ~8B |
| **Recomendada** | 16–64 GB | hasta un ~27B en 64 GB |
| **Óptima** | 128 GB | más margen para varios modelos en paralelo |

No es lo mismo un LAIM de **un solo puesto** que un **LAIM Share** al que se
conectan otros LAIM en modo ligero (sin GPU local). En el segundo caso hay
que reservar memoria y *slots* para varias inferencias a la vez. MOM se
parametriza para ese uso.

### Lo que LAIM aporta cuando los modelos ya están elegidos

Una vez el administrador ha asignado los modelos, LAIM pone en marcha
mecanismos que otras IAs locales suelen dejar sueltos:

- **Warmup predictivo.** Precarga en VRAM los modelos que van a hacer falta
  (por ejemplo el rápido y el medio al abrir el chat; el lento cuando se
  acerca un reprocesamiento). Menos espera al primer token.
- **Paralelismo de inferencias.** Cola GPU, *slots* y workers acordes a
  `OLLAMA_NUM_PARALLEL` y a la potencia de la máquina.
- **KV-cache y ventana de contexto.** Controla `num_ctx` y `keep_alive` para
  no saturar VRAM y mantener el modelo caliente entre turnos.
- **Cola de trabajos.** Chat, descargas y otras tareas no se pisan: se
  ordenan y se pueden seguir desde la interfaz.

El valor frente a «un Ollama y un modelo» es este: **varios modelos locales
a la vez**, cada uno en su sitio, con carga anticipada y uso ordenado de la
GPU.

### Evolucionar sin empezar de cero

MOM está vivo. Hoy un tier puede usar la versión 3.2 de un modelo; mañana
sale la 4.0. El camino es sencillo:

1. Descargar la versión nueva.
2. Evaluarla con las herramientas de LAIM (¿sigue cubriendo la función?
   ¿cabe en memoria?).
3. Cambiar la asignación del tier al modelo nuevo.

Heredas las mejoras del modelo **sin rehacer** el mapa de funcionalidades.

### Herramientas en Configuración › Tiers de modelos

Todo esto se gestiona en **Configuración › Asistente de configuración ›
Modelos IA por tier › Tiers de modelos**. Ahí el administrador dispone de:

| Qué hay en esa pantalla | Para qué sirve, en una frase |
|-------------------------|------------------------------|
| **Tiers de texto** | Traductor, Rápido, Medio, Lento y Alternativo: el flujo de chat (fases F1–F8) y un hueco para probar un candidato sin tocar lo productivo. |
| **Tiers especializados** | Imágenes, Vídeo, Sonido, TTS EN, TTS ES y Desarrollo: visión, voz (escuchar y hablar) y código. |
| **Familias de tiers** | Blue y green de serie; crear, activar o eliminar recetas (estable / experimental, monopuesto / Share). |
| **Temperatura por tier** | Un valor por casilla (0.0 = el defecto del modelo). Rango habitual 0.1–0.7. Los modelos *thinking* se fuerzan a 0.0. |
| **Override por modelo** | Temperatura de un modelo concreto, por encima del tier. Auto-detección y *sweep* para hallar el punto estable. |
| **Herramientas** | Capacidades (visión, tools, thinking…), uso de RAM/VRAM de lo que está cargado, puntuación de idoneidad por tier. |
| **Verificación** | Batería de pruebas alineada a las fases reales de LAIM (idioma, comandos, JSON, Markdown, traducción…). |
| **Asesor** | Recomienda modelos del catálogo según el hardware **y** el hueco de tier que estés rellenando. |
| **Recomendaciones** | Guía práctica de Ollama: cuantización, `keep_alive`, diagnóstico si algo no cabe. |
| **Comparar / evaluar** | Métricas reales en *tu* máquina (tok/s, carga, duración), no las del folleto del fabricante. |

La idea de fondo: **hay herramientas para elegir bien**, no un botón mágico.
Tú adaptas MOM a la GPU, al número de personas y a si este LAIM es el
cerebro de la red o solo un cliente ligero.

---

## El Alma de LAIM

MOM decide **qué modelo** habla en cada función. El **alma** decide **cómo**
debe comportarse *este* LAIM: las costumbres de vuestra casa, no las de un
manual genérico.

En varias funcionalidades —el chat, el trabajo con el sistema, la
administración…— verás **💡 Sugerir mejora**. No es un buzón que se pierde.
Es la forma de **educar** a LAIM: le cuentas, en tu idioma, cómo deberían
ser las respuestas o qué no debe proponer nunca.

### De una frase tuya a conocimiento compartido

1. Escribes la mejora o la corrección.
2. Un mecanismo de **aprendizaje automático** (el agente Teacher) traduce
   ese texto en conocimiento para la heurística: qué hacer, qué evitar,
   en qué contexto.
3. Antes de guardarlo, revisa si **choca** con reglas que ya existen o si
   **duplicaría** algo que LAIM ya sabe. Así el alma no se contradice ni
   se llena de ecos.
4. Si encaja, se **persiste** en esta instalación. A partir de ahí,
   **todos los usuarios** de ese LAIM lo heredan.

No viaja a otras máquinas. Es el carácter de *este* LAIM: la política de
*este* dominio, oficina o laboratorio.

### Un ejemplo: parches y reinicios

Pides revisar **parches pendientes**. LAIM te asiste al aplicarlos. Si
detecta un parche de **kernel**, pregunta si quieres **reiniciar**. Tú
respondes que no.

Luego, en **Sugerir mejora**, dejas escrito algo así:

> Las máquinas de este dominio son de producción. Nunca propongas
> reiniciarlas. Limítate a informar a los administradores de la situación
> y de que esas mejoras se aplicarán después del reinicio programado de
> ese servidor.

Eso entra en el **alma** de ese LAIM. En el próximo caso parecido —tú u
otra persona— LAIM **no propondrá reiniciar**. Explicará cómo se opera
con esos servidores en ese entorno y avisará a quien corresponda.

### Una heurística que crece con vosotros

La heurística de fábrica es el punto de partida. El alma la **adapta** a
vuestra política: usuarios y administradores colaboran, caso a caso. Un
LAIM de laboratorio puede ser más atrevido; uno de producción, más
prudente. No hace falta reescribir el producto: se **enseña**.

> MOM elige **qué cabeza** habla.
> El alma enseña **con qué criterio** debe hablar en vuestra casa.

---

## Qué puedes hacer con LAIM

Cuando instales el cliente en tu ordenador, estas son las puertas más usadas:

- **Conversar** con la IA en tu idioma, también por voz si lo prefieres.
- **Preguntar al sistema**: memoria, discos, procesos, red… con respuestas ancladas
  a lo que realmente hay en la máquina.
- **Administrar equipos remotos** por SSH, desde la web o desde la terminal.
- **Compartir la IA en la red local** (modo Share) o **conectarte** a un servidor
  de tu organización (modo Connect) sin convertir tu portátil en el único cerebro.
- **Generar informes** de una sesión, editar Markdown con ayuda de IA y pedir
  scripts o pequeñas aplicaciones.
- **Enseñar correcciones**: con **💡 Sugerir mejora** educas el **alma** de
  esa instalación (políticas, hábitos, «nunca hagas esto»). Lo aprendido
  queda para todos los que usen ese LAIM.

Todo eso vive en **dos formas de uso**, según te sientas más cómodo:

| Modalidad | Cuándo te encaja |
|-----------|------------------|
| **CLI** | Automatizar, administrar y trabajar desde la terminal (`laim chat`, `laim remote`…) |
| **Web local** | Una interfaz amable en tu equipo para el día a día, sin renunciar al control local |

---

## En qué equipos funciona

LAIM está pensado para el escritorio de verdad, no solo para un laboratorio:

- **Linux** — distribuciones tipo Debian/Ubuntu y Red Hat.
- **macOS** — portátiles y equipos de escritorio Apple (Intel y Apple Silicon).
- **Windows** — con PowerShell; también puedes apoyarte en WSL si lo necesitas.

La IA local se apoya en **Ollama** cuando quieres modelos en tu hardware.
Si el equipo es más ligero, puedes usar LAIM como **cliente** conectado a otro
nodo de tu red que sí tenga GPU o más memoria. Y, si un día lo necesitas,
puedes configurar proveedores externos (por ejemplo Gemini, Mistral o Kimi):
siempre como **opción**, nunca como obligación.

Los **modelos** se organizan en tres familias que irás conociendo al registrarte:

1. **Base** — punto de partida adaptado a tu hardware.
2. **Especializados** — enriquecidos para un dominio concreto.
3. **Personalizados** — creados a medida con información privada, en el ecosistema
   [getmylllm.com](https://www.getmylllm.com/).

MOM encaja aquí de forma natural: no es un único fichero mágico, sino **la
capacidad de asignar, por tiers, el modelo local que cada función necesita**.

---

## Cómo te proponemos empezar

1. Lee **Presentación** si quieres el porqué (la visión humana + IA).
2. Mira **Servicios** para el catálogo práctico: instaladores, manuales y modelos.
3. Consulta **Documentación** cuando necesites la referencia de comandos.
4. Crea tu cuenta y, cuando estés listo, descarga el cliente e inicia con calma.

No hay que hacerlo todo el primer día. LAIM está diseñado para crecer contigo:
primero una conversación local, después un equipo remoto, más adelante una red
compartida o un modelo personalizado.

---

## Acaricia al jerbo

En la web local (`laim web`), el logo de la barra lateral **es el jerbo**.
Cuando ya has iniciado sesión, un **doble clic** sobre él abre **otra
pestaña** del navegador: misma persona, mismo rol, sin volver a escribir
la contraseña. LAIM crea una **sesión web nueva** para esa pestaña; la
original sigue viva. Cada pestaña tiene su propia conversación, así que
puedes hacer dos (o más) cosas a la vez sin que se mezclen los hilos.

Si el navegador bloquea la ventana, permite ventanas emergentes para
`http://127.0.0.1:4321`. El interruptor de **Connect** (si lo tenías
fijado) se copia a la pestaña nueva.

Cuatro usos que suelen importar de verdad:

1. **Conversar y vigilar el equipo.** En una pestaña dejas el chat. En la
   otra abres el monitor o preguntas por memoria, disco o un proceso.
   Mientras la IA razona, tú no pierdes de vista lo que ocurre en la
   máquina.
2. **Este ordenador y un servidor, a la vez.** Una pestaña te ayuda con
   *este* equipo. Tras otro doble clic, en la nueva entras por **acceso
   remoto** (SSH) a un servidor de la red. Diagnosticar el portátil y
   tocar el servidor deja de ser «primero uno, luego el otro».
3. **Informe sin pausar el trabajo.** En una pestaña pides o revisas un
   Markdown de la sesión (conclusiones, pasos, capturas). En la otra
   sigues el hilo operativo: comandos, comprobaciones, «qué queda». El
   documento no te obliga a cerrar el chat.
4. **Modelos y configuración, sin soltar el chat.** Una pestaña sigue
   hablando con la IA. En la otra ajustas tiers, instalas un modelo del
   catálogo o miras Share/Connect. Cuando vuelves al chat, el otro frente
   no se ha perdido.

### Hasta dónde se puede llegar

Un laboratorio pequeño —casa u oficina— con **un solo login** y varias
pestañas nacidas del jerbo: chat pidiendo un diagnóstico de logs (parsers
en paralelo, hallazgos correlacionados); otra pestaña dentro de un
servidor remoto; otra con el mapa de la red o el Share sirviendo modelos
a un compañero en **Connect**; y, si lo tienes activado, un **agente**
siguiendo un flujo mientras tú confirmas solo lo delicado.

Ahí cada pestaña usa los modelos que el administrador asignó a cada
función (traducir, razonar, hablar…), en paralelo, sin que tú seas un
cuello de botella: orquestas. Eso es acariciar al jerbo de verdad —no un
atajo de ratón, sino **varios frentes de LAIM a la vez**, bajo tu criterio.

> *Doble clic en el logo: otra pestaña, otra sesión, el mismo tú.*

---

## Una última idea para llevarte

La inteligencia artificial no sustituye tu criterio. **LAIM** solo intenta que
esa inteligencia esté **cerca, comprensible y bien elegida**: el modelo adecuado,
en el momento adecuado, sobre tus datos y tus sistemas.

Si algo no está claro, pasa a Documentación o escribe en **Contacto**.
Estamos para que esta puerta de entrada se sienta tan cómoda como el resto del proyecto.

> *Bienvenido. Aquí la IA trabaja a tu lado, no por encima de ti.*
