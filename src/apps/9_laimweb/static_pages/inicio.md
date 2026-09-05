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
grande que, por dentro, enciende «expertos» especializados según el trozo de la tarea.

En LAIM hacemos algo parecido… pero a otra escala. Lo llamamos **MOM** (*Mixture of Models*).

En lugar de activar expertos internos de **un** modelo, **activamos modelos distintos**
según el caso: uno más ágil para una respuesta rápida, otro más capaz para razonar,
otro afinado en un dominio o entrenado con tu información. Cada petición puede
encender la mezcla que mejor encaja: funcionalidad, contenido y contexto.

| Idea | MoE (Mixture of Experts) | MOM (Mixture of Models) en LAIM |
|------|--------------------------|----------------------------------|
| ¿Qué se enciende? | Expertos *dentro* de un mismo modelo | **Modelos enteros**, elegidos para la ocasión |
| ¿Para qué? | Especializar capas internas | Adaptar *qué cerebro* usa cada tarea |
| ¿Quién decide? | El propio modelo, en tiempo de inferencia | LAIM, según el caso, el hardware y tu configuración |

No hace falta memorizar la tabla. Quédate con esta imagen:

> MoE es un equipo de especialistas **dentro de una misma cabeza**.
> MOM es un **estante de cabezas distintas**: LAIM acerca la que conviene
> a cada conversación, cada sistema y cada tipo de contenido.

Así la IA no es «un modelo para todo». Es una **orquesta de modelos** que se
activa de forma adaptada: diagnóstico del equipo, redacción, código, seguridad,
documentos o una pregunta rápida.

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
- **Enseñar correcciones**: si la IA se equivoca en un comando, puedes decirle
  cómo hacerlo bien para la próxima vez.

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
capacidad de combinar esas familias** según lo que estés haciendo.

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

Ahí MOM elige cabezas distintas según la pestaña, y tú no eres un cuello
de botella: orquestas. Eso es acariciar al jerbo de verdad —no un atajo
de ratón, sino **varios frentes de LAIM a la vez**, bajo tu criterio.

> *Doble clic en el logo: otra pestaña, otra sesión, el mismo tú.*

---

## Una última idea para llevarte

La inteligencia artificial no sustituye tu criterio. **LAIM** solo intenta que
esa inteligencia esté **cerca, comprensible y bien elegida**: el modelo adecuado,
en el momento adecuado, sobre tus datos y tus sistemas.

Si algo no está claro, pasa a Documentación o escribe en **Contacto**.
Estamos para que esta puerta de entrada se sienta tan cómoda como el resto del proyecto.

> *Bienvenido. Aquí la IA trabaja a tu lado, no por encima de ti.*
