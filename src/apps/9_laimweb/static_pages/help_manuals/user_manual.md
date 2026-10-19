# Manual de Usuario — LAIM

**LAIM** (Local Artificial Intelligence Management) es una herramienta que te permite conversar con una inteligencia artificial directamente desde tu ordenador, **sin Internet** y sin enviar tus datos a ningún servicio externo. Todo se procesa localmente o, si tu empresa tiene un servidor LAIM compartido, en la red local de tu organización.

---

## Indice

1. [Que puedo hacer con LAIM](#1-que-puedo-hacer-con-laim)
2. [Acceso a la interfaz web](#2-acceso-a-la-interfaz-web)
3. [Navegacion en la interfaz web](#3-navegacion-en-la-interfaz-web)
4. [Idioma de la interfaz y de los manuales](#4-idioma-de-la-interfaz-y-de-los-manuales)
5. [Chat con la IA](#5-chat-con-la-ia)
   - [5.1 Memoria, contexto y compresion](#51-memoria-contexto-y-compresion)
   - [5.2 Diagramas Mermaid en el chat](#52-diagramas-mermaid-en-el-chat)
   - [5.3 Pedir desarrollo de scripts o aplicaciones](#53-pedir-desarrollo-de-scripts-o-aplicaciones)
   - [5.4 Entrada por voz en el chat](#54-entrada-por-voz-en-el-chat-)
   - [5.5 Informe de la sesion de chat](#55-informe-de-la-sesion-de-chat-)
   - [5.6 Complementos F8 (Codigo y Ejemplo)](#56-complementos-f8-codigo-y-ejemplo)
   - [5.7 Herramientas de LAIM](#57-herramientas-de-laim)
6. [Chat con equipos remotos](#6-chat-con-equipos-remotos)
7. [Inferencia directa](#7-inferencia-directa)
   - [7.1 Adjunto de fichero](#71-adjunto-de-fichero-)
   - [7.2 Entrada por voz](#72-entrada-por-voz-)
   - [7.3 Proteccion de voz (anti-suplantacion)](#73-proteccion-de-voz-anti-suplantacion)
   - [7.4 LM Studio y MLX (Apple silicon)](#74-lm-studio-y-mlx-apple-silicon)
   - [7.5 Copiar conversacion a Informes (📋)](#75-copiar-conversacion-a-informes-)
8. [Equipos remotos SSH](#8-equipos-remotos-ssh)
   - [8.1 Acceso desde la interfaz web](#81-acceso-desde-la-interfaz-web)
   - [8.2 Acceso desde la linea de comandos](#82-acceso-desde-la-linea-de-comandos-laim-remote)
   - [8.3 Panel SESIONES ACTIVAS — vista unificada](#83-panel-sesiones-activas--vista-unificada)
   - [8.4 Ejemplo practico: trabajo simultaneo web + CLI](#84-ejemplo-practico-trabajo-simultaneo-web--cli)
   - [8.5 Sugerencias de la IA en sesiones SSH](#85-sugerencias-de-la-ia-en-sesiones-ssh)
9. [Mejorar la IA con tu feedback](#9-mejorar-la-ia-con-tu-feedback)
10. [Ver el rendimiento de la IA](#10-ver-el-rendimiento-de-la-ia)
11. [Notificaciones](#11-notificaciones)
12. [Editor Markdown con IA](#12-editor-markdown-con-ia)
13. [Sesiones y privacidad](#13-sesiones-y-privacidad)
   - [Usar LAIM como cliente Connect](#usar-laim-como-cliente-connect)
   - [Elegir Localhost o un servidor Share](#elegir-localhost-o-un-servidor-share)
14. [Preguntas frecuentes](#14-preguntas-frecuentes)

---

## 1. Que puedo hacer con LAIM

| Funcion | Descripcion |
|---|---|
| Chat | Conversa con la IA en lenguaje natural; tambien puedes dictar el prompt por voz (🎤) |
| Chat en equipo remoto | Usa la IA para analizar y ejecutar comandos en otro ordenador de tu red |
| Inferencia directa | Preguntas rapidas con historial; puedes adjuntar un fichero (📄) o dictar por voz (🎤) |
| Proteccion de voz | Tu firma vocal evita que otra persona use el microfono con tu sesion abierta |
| Ruta IA (Connect) | Elige Localhost o un Share de tu red para chat, Direct y el resto de servicios IA |
| Equipos SSH (web) | Abre terminales SSH interactivas en el navegador con gestion de sesiones |
| Equipos SSH (CLI) | Conecta con `laim remote` desde tu consola sin abrir el navegador |
| SESIONES ACTIVAS | Monitoriza en tiempo real todas las sesiones SSH abiertas (web y CLI) |
| Notificaciones | Recibe avisos de LAIM (sugerencias procesadas, descargas, alertas) y responde |
| Editor | Escribe notas Markdown con acciones de IA y exportacion a PDF/HTML |
| Sugerir mejora | Envia tu feedback para que la IA aprenda de tus correcciones |
| Informe de sesion (📋) | Genera un Markdown de toda la conversacion de chat (turnos, comandos, fases) en Informes → Inferencias |
| Copia Direct → Informes (📋) | En Inferencia directa, guarda la conversacion activa como Markdown en Informes → Direct, para poder borrarla del historial sin perder el contenido |
| Ayuda bilingüe | En el visor de manuales e informes, cambia el idioma del documento con las banderas 🇬🇧 / 🇪🇸 |
| Desarrollo de scripts | Pide a LAIM que cree un script o pequena aplicacion (agente developer) |
| Rendimiento | Analiza el tiempo y la carga de cada respuesta por fases |
| Temas graficos | En Ayuda, elige el aspecto de la interfaz (CRT, Soft UI, cuero, metal) |

---

## 2. Acceso a la interfaz web

1. Abre un navegador y ve a **http://localhost:4321**
2. Introduce tu **nombre de usuario** y **contrasena** (te los proporciona tu administrador).
3. Haz clic en **Iniciar sesion**.

> Si el boton no responde al instante, espera unos segundos; LAIM puede estar iniciandose en segundo plano.

### Modos de acceso

| Modo | Cuando se usa |
|---|---|
| **Localhost** | Este ordenador ejecuta la IA (Ollama local) |
| **Share (ruta IA)** | Chat, Direct y el resto de servicios IA usan un servidor LAIM Share de tu red. Lo eliges en el selector de **ruta IA** (chat, Direct o Acceso remoto). |

En ambos casos el acceso desde el navegador es identico: `http://localhost:4321`.

**Ejemplo.** Maria (rol `user`) abre Chrome en `http://localhost:4321`, inicia sesion y ve el sidebar. En el banner de Chat elige **Localhost**. Si el administrador le ha dado un perfil Share «Windows GPU», el selector tambien muestra ese nombre **solo si el Share responde**; si no, permanece en Localhost.

---

## 3. Navegacion en la interfaz web

El panel izquierdo muestra los comandos disponibles para tu usuario. Como usuario normal veras:

| Boton | Para que sirve |
|---|---|
| `help` | Ayuda, manuales y acceso al **Editor** Markdown |
| `version` | Version instalada de LAIM |
| `info` | Informacion tecnica del sistema local |
| `chat` | Abre el chat interactivo con la IA |
| `direct` | Inferencia directa (preguntas rapidas) |
| `remote` | Acceso a equipos remotos via SSH |
| **Notificaciones** | Panel de avisos (badge con el numero de no leidas) |

Desde **help** tambien puedes abrir:

| Acceso | Que abre |
|---|---|
| Manual de usuario / administrador / Headscale / Recomendaciones | Visor de manuales Markdown |
| **Ventana de contexto** | Manual sobre limites de historial y compresion automatica |
| **Editor** | Editor Markdown con IA en una pestana nueva |

> Los botones de administracion (`config`, modelos, conexiones remotas, etc.) solo estan disponibles para usuarios con rol **admin**.

**Temas graficos.** En **help → Temas** puedes cambiar el aspecto (CRT verde, Soft UI, cuero, metal). La preferencia se guarda en tu usuario; no cambia la logica de Chat ni Direct.

**Ejemplo.** Entras en `help`, pulsas **Manual de usuario** y lees este documento. Las banderas 🇬🇧 / 🇪🇸 del visor cambian el idioma del **manual**, no el de los botones de la app (eso son las banderas de cabecera).

---

## 4. Idioma de la interfaz y de los manuales

Puedes cambiar el idioma de la **interfaz** web entre **ingles** y **espanol** con las banderas de idioma que aparecen en la parte inferior del panel de inicio de sesion o en la cabecera de la aplicacion.

- Bandera inglesa = interfaz en ingles
- Bandera espanola = interfaz en espanol

El idioma seleccionado se guarda automaticamente en tu perfil de usuario y se restaura en cada inicio de sesion.

### Idioma de la linea de comandos (`laim language`)

La terminal tiene su propio idioma. Lo cambias con:

```bash
laim language        # muestra el idioma actual (EN o ES)
laim language ES     # espanol
laim language EN     # ingles
```

El valor se guarda en tu perfil y como idioma por defecto del CLI. `laim help` muestra las descripciones en ese idioma. En la pagina **Ayuda** de la web, el recuadro «Referencia de comandos (`laim help`)» sigue las **banderas de la interfaz** (cabecera o login), no las del visor del manual.

### Idioma de los documentos (Ayuda e Informes)

Al abrir un **manual** (help) o un **informe**, veras banderas flotantes 🇬🇧 / 🇪🇸 en el visor. Sirven para leer el **contenido del documento** en otro idioma (no cambian solo los botones de la app):

1. Abre el documento en Ayuda o Informes.
2. Pulsa la bandera del idioma que quieras leer.
3. Si ese idioma ya esta preparado, el texto aparece al instante. Si hace falta traducirlo, veras un progreso («Pagina N/M») y, al terminar, la version queda guardada para la proxima vez.

Si la traduccion no supera el control de calidad, LAIM no deja un documento a medias: mantiene el idioma original o la ultima version buena, y puede mostrar un aviso. En ese caso pide ayuda a tu administrador (tier Traductor / modelo Ollama).

**Ejemplo.** El manual se abre en espanol. Pulsas 🇬🇧: si ya hay copia inglesa, cambia al instante. Si no, veras «Pagina 1/M» mientras se traduce; la proxima vez que pulses 🇬🇧 no espera.

---

## 5. Chat con la IA

El **Chat** es la funcion principal de LAIM. Puedes escribir preguntas en lenguaje natural, pedir analisis o solicitar que la IA ejecute comandos en tu ordenador.

### Como iniciar un chat

1. En el panel izquierdo, haz clic en **chat**.
2. Escribe tu pregunta en el cuadro de texto inferior.
3. Pulsa **Enter** o el boton **Enviar**.

### Ejemplos de lo que puedes preguntar

- *"Cuanto espacio libre hay en mi disco?"*
- *"Que procesos estan consumiendo mas CPU ahora mismo?"*
- *"Explicame que es una direccion IP."*
- *"Como listo los archivos de una carpeta en Windows?"*
- *"Cuanta RAM tiene este ordenador?"*
- *"Muestra los 5 procesos que mas memoria consumen."*

### Flujo de inferencia — las 8 fases

Cuando envias un mensaje, LAIM lo procesa en 8 fases internas:

| Fase | Que hace |
|---|---|
| **F1** | Detecta el idioma de tu mensaje y clasifica la intencion |
| **F2** | Determina el rol de la respuesta (informativo, ejecutivo, etc.) |
| **F3** | Recupera contexto del sistema segun el tema |
| **F4** | Analiza la peticion con detalle |
| **F5** | Genera la respuesta o los comandos necesarios |
| **F6** | Ejecuta comandos en el sistema (si aplica, con tu permiso) |
| **F7** | Formatea y traduce la respuesta a tu idioma |
| **F8** | Anade sugerencias adicionales o complementos. **Codigo / script** abre un flujo del agente Developer: script nativo del equipo (bash o PowerShell) o codigo Go/Python, con permiso para ejecutarlo aqui y la opcion de marcarlo **valido** para guardarlo en Informes. |

### Comandos del sistema — Consentimiento previo

Cuando LAIM detecta que tu pregunta esta relacionada con el estado del ordenador, puede proponer ejecutar comandos.

> **LAIM siempre pedira tu confirmacion** antes de ejecutar nada. Responde **si** o **no** en el chat.

Si el comando falla o no es compatible con tu sistema operativo, LAIM intenta alternativas automaticamente (reparacion F6.3R) y solo muestra el resultado cuando tiene exito.

Cuando preguntas por el estado de **este** equipo (disco, RAM, etc.), LAIM presenta tablas y cifras a partir de los datos reales de los comandos: unidades legibles (GB), tablas Markdown y correccion automatica si el modelo deja filas vacias o texto mezclado en las celdas. Puedes confiar en FreeGB/TotalGB y similares cuando aparecen en la respuesta.

### Comandos de riesgo

Algunas operaciones (como eliminar archivos o detener servicios) se marcan como **de riesgo** y requieren una confirmacion adicional. Tu respuesta queda registrada en el log de actividad por motivos de auditoria.

Si respondes **no**, LAIM no ejecuta nada y te lo dice tal cual: «No se ha ejecutado nada: denegaste la ejecucion de los comandos», con la lista de lo que proponia. Nunca lo presenta como un fallo ni describe una salida que no existe.

LAIM no propone comandos que no puede ejecutar tal cual: con un hueco sin rellenar (`<PID>`), con un valor de ejemplo (`/path/to/…`), interactivos (editores como `vi`) o programas que tu sistema no tiene.

### Peticiones de cambio en el chat

Si pides un **cambio** en el equipo del chat («Vacia la cache DNS», «Baja la prioridad del proceso con mas CPU», «Instala htop»):

- Si LAIM tiene comandos verificados completos para tu sistema, usa esos (no los escribe el modelo) y te pide permiso **para cada uno**. Si el cambio necesita un dato del equipo (por ejemplo, el proceso con mas CPU), primero hace esa lectura, con tu permiso, y te dice que proceso es y su PID antes de preguntarte por el cambio.
- Si no los tiene, el modelo propone los comandos y tambien te pide permiso para cada cambio. Si al final no propone ningun cambio, LAIM te lo dice («LAIM no tiene un procedimiento verificado para este cambio…») y, debajo, lo que haya leido. Una lectura (`df`, `ps`, `cat /etc/hosts`…) nunca se presenta como si fuera la respuesta al cambio.
- Si deniegas el permiso, no se ejecuta nada y te lo dice tal cual. Si se hicieron lecturas, aparecen debajo, pero LAIM nunca da por hecho un cambio que no se ejecuto.
- Todo esto vale igual si el **equipo destino** del chat es otro equipo: los comandos se ejecutan en el por SSH, con los mismos permisos uno a uno.

### Actualizaciones del sistema

Si pides instalar actualizaciones, LAIM no instala todo de golpe: primero lee la lista pendiente (con tu permiso) y te la muestra con lo que requiere reinicio y lo que es una **actualizacion mayor** (por ejemplo, pasar a una nueva version de macOS). Despues te ofrece opciones y tu eliges:

- **Opcion A:** solo las que no requieren reinicio.
- **Opcion B:** todas salvo la actualizacion mayor, sin reiniciar; LAIM te dice cuales necesitan reinicio para terminar.
- **Opcion C:** la actualizacion mayor, solo si la pides expresamente («actualiza a macOS 27»).

En Linux no se sabe antes de instalar que necesitara reinicio: LAIM instala las actualizaciones y despues consulta `needrestart` (o `/var/run/reboot-required`, `dnf needs-restarting`) para decirte si hace falta reiniciar. En Windows hace falta el modulo PSWindowsUpdate; sin el, LAIM te lo dice y no instala nada.

**LAIM nunca reinicia el equipo:** si hace falta, te lo dice y reinicias tu cuando te venga bien.

### Historial de sesiones

En el panel lateral del Chat veras tus conversaciones organizadas por fecha. Haz clic en cualquiera para **retomar desde donde la dejaste**. El historial se guarda cifrado en tu equipo.

### Perfil y modo de chat

En el panel de Chat encontraras opciones para personalizar la sesion:

- **Perfil de flujo**: selecciona un perfil de inferencia preconfigurado (si el admin ha creado varios)
- **Modo**: modo normal o modo con override de modelo especifico

### 5.1 Memoria, contexto y compresion

Tus conversaciones se guardan cifradas en `laim.memory` (solo en tu equipo, protegidas con la clave maestra de la instalacion). Esta memoria permite que la IA recuerde el contexto de turnos anteriores y puedas **iterar** sobre resultados previos (por ejemplo: listar ficheros → filtrar CSV → pedir solo los de mas de 12 registros).

Para no saturar la memoria de la GPU, LAIM limita el historial que se envia al modelo. Cuando ese limite se acerca:

1. Se activa automaticamente el proceso **Chat Context Summarized**.
2. LAIM resume los turnos mas antiguos (conservando peticiones, decisiones y datos relevantes).
3. En el chat veras un aviso del tipo: *"Contexto comprimido — el historial fue compactado para continuar la sesion."*
4. Puedes seguir preguntando con normalidad; el resumen sustituye al historial largo.

**Como empezar de cero:** abre una **nueva sesion** de chat (o una nueva conversacion en Direct). El historial comprimido pertenece a la sesion actual; no se borra al cerrar solo la pestana del navegador.

> Los limites exactos (tokens, umbral de compresion) los configura el administrador en **Internal › Local**. Si necesitas detalles tecnicos, abre en Ayuda el manual **Ventana de contexto**.

**Ejemplo.** Llevas 20 turnos preguntando por logs y CSV. Aparece «Contexto comprimido». Sigues: «filtra solo los de mas de 12 registros» y la IA recuerda el criterio porque el resumen conserva las decisiones. Si quieres un tema nuevo sin ese bagaje, abre **nueva sesion**.

### 5.2 Diagramas Mermaid en el chat

Cuando la IA genera un diagrama (flujo, secuencia, etc.) en formato Mermaid, LAIM lo **renderiza en vivo** dentro del chat:

- Veras una miniatura del diagrama con la pista *"Clic para ampliar"*.
- Al hacer clic se abre un modal a pantalla completa (cierra con Escape o el boton Cerrar).
- Si el modelo produce sintaxis incorrecta, puede aparecer un mensaje `[Diagram error: …]` en lugar del dibujo. En ese caso puedes pedir a la IA que regenere el diagrama, o usar **Sugerir mejora** si el fallo se repite.

Los mismos diagramas Mermaid tambien se pueden ver en el **Editor** (preview de notas Markdown).

**Ejemplo.** Preguntas «dibuja el flujo de un ping hasta el gateway». En el chat aparece un flowchart; haces clic, lo ves a pantalla completa y cierras con Escape. Si ves `[Diagram error:]`, pides «regenera el diagrama Mermaid».

### 5.3 Pedir desarrollo de scripts o aplicaciones

Si pides explicitamente crear una aplicacion, un script o una herramienta pequena — por ejemplo:

- *"Crea usando el agente developer una aplicacion que sume los numeros impares del 1 al 21"*
- *"Haz un script en Python que liste los CSV de esta carpeta"*

LAIM puede activar el **agente developer**. Ese agente:

1. Planifica la tarea y genera codigo (por defecto **Python**, salvo que indiques otro lenguaje).
2. Puede probarlo en un entorno aislado (sandbox) cuando corresponde.
3. Te muestra el **codigo** y, si se ejecuto, el **resultado** de la ejecucion.

No es un chat generico de sistemas: si tu peticion es solo de desarrollo, el resultado esperado es el script/aplicacion (y su salida), no un analisis de procesos o red del equipo.

**Ejemplo.** Escribes «crea usando el agente developer un script Python que sume los impares del 1 al 21». Ves el codigo, el sandbox lo ejecuta y el resultado (121) aparece debajo. No es lo mismo que F8 Codigo tras una pregunta de sistema ([seccion 5.6](#56-complementos-f8-codigo-y-ejemplo)).

### 5.4 Entrada por voz en el chat (🎤)

Debajo del cuadro de mensaje del **Chat** hay un boton **🎤** igual que en Inferencia directa:

1. Pulsa **🎤** para grabar, habla, y vuelve a pulsar para detener.
2. El texto reconocido se escribe en el prompt del chat. **Revisalo** y pulsa **Enviar**.
3. Si tu voz coincide con la firma registrada, veras un badge del tipo **«Voz reconocida: tu_usuario»**.

La captura, la transcripcion y la **proteccion anti-suplantacion** son las mismas que en Direct. Detalle completo: [seccion 7.2](#72-entrada-por-voz-) y [seccion 7.3](#73-proteccion-de-voz-anti-suplantacion).

**Ejemplo.** Pulsas 🎤, dices «cuanta RAM hay en este equipo», sueltas el boton, revisas el texto y envias. Si otra persona habla al mic con tu sesion abierta, LAIM no transcribe.

### 5.5 Informe de la sesion de chat (📋)

Junto al microfono del composer del Chat hay un boton **📋** que genera un **informe Markdown** de la sesion activa:

1. Con una conversacion abierta (uno o varios turnos), pulsa **📋**.
2. LAIM escribe el informe en la carpeta de informes de la instalacion (prefijo con fecha).
3. Abre **Informes** en la interfaz: el documento aparece en el grupo **Inferencias**.

El informe incluye los turnos de la sesion, salidas de comandos (F6), analisis, resumen de fases y datos de rendimiento utiles para revisar o compartir con el administrador. Puedes cambiar el idioma del informe con las banderas del visor ([seccion 4](#4-idioma-de-la-interfaz-y-de-los-manuales)).

**Ejemplo.** Has preguntado por disco y procesos en tres turnos. Pulsas 📋: en **Informes → Inferencias** aparece un Markdown con fecha en el nombre (no `chat_` ni `direct_`).

### 5.6 Complementos F8 (Codigo y Ejemplo)

Tras una respuesta, el chat puede ofrecer **F8** (complementos):

| Boton | Que hace |
|---|---|
| **Codigo / script** | El agente Developer propone un script nativo de **este** equipo (bash en macOS/Linux, PowerShell en Windows) o codigo Go/Python. Si aceptas, se ejecuta con el mismo consentimiento F6. Solo lo marcado **valido** se guarda en Informes (`developer_script_*`). |
| **Ejemplo** | Explica la inferencia con una analogia cotidiana (objetivo, analogia, pasos, tabla). No escribe informes en `reports/` desde el chat; el panel Tecnico Example si puede, si el admin lo pide. |

**Ejemplo.** Preguntas «cuanta RAM hay en este equipo» y obtienes una tabla. Pulsas **Ejemplo**: LAIM compara la RAM con «cajones de un armario» y mapea cada cifra. Pulsas **Codigo**: te ofrece `free -h` o `Get-CimInstance Win32_OperatingSystem` segun el SO, y pide confirmacion antes de ejecutarlo.

### 5.7 Herramientas de LAIM

LAIM tiene sus propias herramientas pequeñas — por ejemplo `dirsize`, que mide cuánto ocupa una carpeta y cuántos ficheros contiene. Las crea un administrador y las aprueba antes de que nadie pueda usarlas; hasta entonces nunca se ejecutan.

- **¿Qué herramientas hay?** Pregunta *«¿qué herramientas tiene LAIM?»* (o *"what LAIM tools are available?"*). Ves las herramientas aprobadas que puedes usar.
- **¿Qué hace una herramienta?** Pregunta *«¿qué es <herramienta>?»*, por ejemplo *«¿qué es dirsize?»*, *«¿para qué sirve dirsize?»* o *«¿cómo se usa dirsize?»*. LAIM responde con la descripción aprobada de la herramienta: qué mide, preguntas de ejemplo, los datos que necesita, la orden que ejecuta, si solo lee y su estado en los equipos que puedes usar. Si nombras una herramienta que no existe, LAIM te lo dice; nunca se inventa una.
- **Usar una herramienta.** Haz tu pregunta con el equipo seleccionado, p. ej. *«¿Cuánto ocupa la carpeta /var/log y cuántos ficheros tiene?»*. Si una herramienta aprobada la responde, LAIM pide el consentimiento de solo lectura de siempre, con una línea como `laim-tool dirsize --json --path /var/log @mi-servidor`. Si la herramienta aún no está en ese equipo, LAIM pregunta antes si la despliega. Si falta un dato (por ejemplo, qué carpeta), LAIM te lo pide; si lo dejas vacío, no se ejecuta nada y LAIM responde de la forma habitual.
- **La respuesta** muestra las cifras y termina con una línea **Method:** que nombra la orden exacta que se ejecutó (p. ej. `` **Method:** ran `laim-tool dirsize --json --path /var/log` … ``), para que siempre sepas de dónde salen los datos. Si la herramienta no se pudo usar, LAIM dice por qué y nunca responde a otra pregunta.

**Ejemplo.** Con el equipo remoto *mi-servidor* seleccionado preguntas «¿cuánto ocupa /var/log y cuántos ficheros tiene?». LAIM pide una vez permiso para ejecutar `laim-tool dirsize --json --path /var/log @mi-servidor`, respondes *s* y obtienes «Carpeta `/var/log`: Tamaño 4.9 GB, Ficheros 226» seguido de la línea Method.

---

## 6. Chat con equipos remotos

Esta funcion te permite usar la IA para analizar y ejecutar comandos **en un equipo remoto** (no en tu ordenador local), a traves de una conexion SSH automatica.

### Como usarlo

1. Abre el **chat** desde el panel izquierdo.
2. En el panel de Chat, localiza el **selector de equipo destino** (aparece junto al selector de perfil y modo).
3. Por defecto aparece **Localhost** — haz clic para desplegar la lista de equipos a los que tienes acceso.
4. Selecciona el equipo remoto deseado. Aparecera un indicador con el sistema operativo detectado: por ejemplo `[linux] mi-servidor`.
5. Escribe tu pregunta o solicitud normalmente.

### Que ocurre en el fondo

- LAIM detecta automaticamente el sistema operativo del equipo remoto (Windows, Linux o macOS).
- Las fases F5 y F6 generan y ejecutan comandos **del sistema operativo del equipo remoto**, no del tuyo.
- Los comandos se ejecutan via SSH usando las credenciales configuradas por el administrador.
- Tu confirmacion sigue siendo necesaria antes de cualquier ejecucion.

### Ejemplo

Si seleccionas un servidor Linux y preguntas *"Cuanta RAM tiene este servidor?"*, LAIM generara el comando `free -h` (adecuado para Linux) y lo ejecutara en el servidor remoto, mostrando el resultado en tu chat.

> Para que un equipo remoto aparezca en la lista, el administrador debe haberlo registrado y concederte acceso.

---

## 7. Inferencia directa

La inferencia directa es un cuadro de preguntas rapidas, mas agil que el chat de 8 fases.

1. Haz clic en **direct** en el panel izquierdo.
2. Escribe tu pregunta (o usa adjunto / voz, abajo) y pulsa **Enviar**.
3. Puedes seguir enviando mensajes en la misma conversacion: LAIM mantiene el historial para que puedas iterar sobre la respuesta anterior.
4. Mientras el modelo escribe veras tres puntos animados junto a **Generando respuesta…**. Al terminar aparece un distintivo con la velocidad de inferencia en **tok/s**.

Al abrir **Nueva conversación** o al cambiar el modelo en el selector (Ollama o **MLX**), el modelo se presenta con una ficha técnica. Esa pregunta no se muestra en el chat. La primera vez LAIM consulta al modelo y guarda la ficha; las siguientes veces reutiliza esa copia **sin volver a llamar a Ollama/MLX** (veras un estado del tipo «Cargando ficha del modelo (caché)…»). Si la ficha llega como un bloque de texto sin títulos ni tablas, LAIM la formatea (secciones, listas, bloques) igual que en el chat; si ya trae Markdown válido, se respeta.

La primera presentacion de un modelo grande puede tardar (carga en GPU + ficha larga). Si el stream se corta, LAIM puede mostrar lo ya generado y **no** cachea ese recorte, para que el siguiente intento complete la ficha.

**Ejemplo.** Eliges `qwen3.5:9b` por primera vez: aparece la ficha (identificacion, razonamiento, tools). Cierras Direct, abres **Nueva conversacion** con el mismo modelo: la ficha vuelve a pintarse, pero ya no ocupa GPU ni slot Ollama. Cambias a `gemma4:e4b`: esa combinacion motor+modelo+idioma es nueva → si se infiere y se guarda.

### 7.1 Adjunto de fichero (📄)

Puedes adjuntar un fichero del **equipo donde corre LAIM** (ruta en el servidor, no una subida desde el navegador):

1. Pulsa el boton **📄** junto al cuadro de mensaje. Se abre un explorador de carpetas (igual que al importar un modelo).
2. Selecciona el fichero; aparece un chip con el nombre debajo del composer. Puedes quitarlo con **✕**.
3. Escribe el prompt **antes o despues** de adjuntar (el orden da igual) y pulsa **Enviar**.
4. Al enviar, LAIM lee el fichero en el host:
   - **Texto** (`.txt`, `.md`, código…): se añade al mensaje como contexto.
   - **Imagen mapa de bits** (PNG, JPEG/JPG/JFIF, GIF, WebP, BMP): se envía al modelo multimodal en el campo `images` (base64), no como texto. Si no escribes prompt, se usa «Describe and analyze the following image.».

**Limites:** el texto se trunca si supera ~256 KiB; las imagenes hasta ~8 MiB. TIFF, HEIF/HEIC y RAW no se envian (conviertelos a PNG o JPEG). El adjunto vale para **ese envio**. En Connect, el fichero se lee en este equipo y la imagen viaja cifrada al Share. Si hay tier **Imagenes** configurado, Direct lo usa para el turno con foto.

**Ejemplo.** Pulsas 📄, eliges `~/Desktop/captura.png` y escribes «que ves en la captura». El modelo de vision describe la imagen. Un `.md` de 10 KB se pega como contexto de texto.

### 7.2 Entrada por voz (🎤)

En Inferencia directa (y tambien en el **Chat**, ver [§5.4](#54-entrada-por-voz-en-el-chat-)) puedes **dictar el prompt** en lugar de escribirlo. El boton **🎤** (junto a 📄 en Direct) es un **interruptor de grabacion**:

1. Pulsa **🎤** una vez: el boton se marca como activo y LAIM empieza a grabar el **microfono por defecto del host** donde corre el binario LAIM (no el microfono del navegador de otro PC).
2. Habla con claridad el texto que quieres enviar (unos segundos bastan para una frase corta).
3. Vuelve a pulsar **🎤**: se detiene la grabacion. Mientras transcribe veras un estado del tipo «Transcribiendo…».
4. El texto reconocido aparece en el cuadro de mensaje. **Revisalo o corrigelo** y pulsa **Enviar** cuando estes listo.

**Antes de la primera transcripcion** LAIM te pedira registrar tu voz (enrollment de 20 segundos). Eso protege tu sesion frente a suplantacion: ver [seccion 7.3](#73-proteccion-de-voz-anti-suplantacion).

La transcripcion usa **solo** el modelo asignado al tier **Sonido** (el administrador lo configura en **config → Modelos IA → Tiers → Sonido**). No se usa el modelo de Direct ni el tier Medio como sustituto.

**Lectura en voz alta (🔊):** junto al microfono, Direct puede leer la ultima respuesta del asistente. Si la respuesta (o la interfaz) esta en espanol, usa el tier **TTS ES**; si ambos estan en ingles, **TTS EN**. Los informes de University se leen **siempre en espanol** (TTS ES). El administrador asigna cada modelo en **config → Modelos IA → Tiers**.

#### Modelo recomendado (tier Sonido)

| Modelo Ollama | Uso |
|---|---|
| **`gemma4:e2b`** | **Recomendado.** Modelo con encoder de audio; es el que se ha **probado con exito** en LAIM para dictado en Inferencia directa. Instalacion: `ollama pull gemma4:e2b`, luego asignarlo al tier Sonido. |
| `gemma4:e4b` | Alternativa con audio (mayor consumo de VRAM). |

**No uses para voz** (fallaran o inventaran texto):

- `gemma4:12b` — solo vision, sin audio
- Modelos TTS como Orpheus — generan voz, no la transcriben
- GGUF community tipo `whisper-tiny` sin mmproj de audio en Ollama

Si el tier Sonido esta vacio o el modelo no acepta audio, veras un error pidiendo configurarlo (el administrador debe hacerlo).

#### Microfono y consejos de uso

- Se graba el **microfono por defecto del servidor LAIM** (en Windows: Configuracion → Sistema → Sonido → Entrada).
- Si abres la web desde otro equipo, la grabacion es del mic del **servidor**, no del tuyo.
- Habla cerca del mic; si el volumen de entrada esta muy bajo o silenciado, LAIM rechazara la captura en lugar de inventar texto.
- Tras detener, espera a que el texto aparezca; entonces puedes editarlo antes de enviar.

Cuando el historial crece demasiado, se aplica la misma **compresion automatica de contexto** descrita en la [seccion 5.1](#51-memoria-contexto-y-compresion). Para empezar limpio, crea una **nueva conversacion** Direct.

> Ideal para consultas puntuales o dialogos cortos que no necesitan el flujo completo de fases F1–F8.

### 7.3 Proteccion de voz (anti-suplantacion)

El microfono de LAIM **no acepta cualquier voz** solo porque tu sesion este abierta. Cada usuario registra una **firma vocal** vinculada a su cuenta. Asi, si dejas el PC desbloqueado o alguien se sienta delante con tu sesion web abierta, **otra persona no puede dictar comandos ni prompts en tu nombre**.

#### Que problema resuelve

| Situacion de riesgo | Que hace LAIM |
|---|---|
| Sesion abierta y alguien habla al microfono | Compara la voz con tu firma; si no coincide, **bloquea** la transcripcion |
| Primera vez que usas el 🎤 | Obliga a un **enrollment** de 20 segundos antes de poder transcribir |
| Intento de suplantacion detectado | No genera texto; registra el evento de seguridad (el admin puede verlo en logs / notificaciones) |

Esto complementa (no sustituye) tu contraseña y el cierre de sesion: **cierra sesion** cuando te alejes del puesto.

#### Primer uso — registrar tu voz (enrollment)

1. En **Chat** o **Inferencia directa**, pulsa **🎤**.
2. Si aun no tienes firma, aparece un modal: **Enrollment vocal (20 segundos)**.
3. Pulsa **Iniciar grabacion** y habla con naturalidad durante la cuenta atras (puedes leer un texto, presentarte, etc.; lo importante es **tu voz**, no las palabras exactas).
4. Al terminar, LAIM guarda la firma de forma **cifrada** en el equipo (fichero `voice.dat`; no se exporta en los JSON de configuracion portables).
5. Veras un mensaje del tipo **«Voz registrada. Ya puedes usar el microfono.»**

Consejos para un buen registro:

- Habla a distancia normal del microfono del **host LAIM** (el del servidor/PC donde corre `laim`, no el del navegador remoto).
- Evita ruido fuerte de fondo y el silencio total.
- Si fallas, puedes volver a abrir el enrollment (o pedir al admin que **resetee** tu firma y repetir el proceso).

#### Uso diario — verificacion antes de transcribir

Cada vez que detienes el 🎤 para dictar:

1. LAIM compara la muestra recien grabada con tu firma (juez de audio del tier **Sonido**).
2. Si es **la misma voz** → transcribe el texto al prompt y muestra el badge **«Voz reconocida: tu_usuario»**.
3. Si es **otra voz** → **no** transcribe; veras un aviso de que la voz no coincide.
4. Si el modelo de Sonido no esta disponible o no puede juzgar → **tampoco** transcribe (fallo seguro: mejor bloquear que aceptar una voz dudosa).

#### Reset de la firma (solo administrador)

Si cambias de entorno de microfono de forma permanente, o sospechas un registro incorrecto:

- El **administrador** puede resetear tu firma desde la tabla de usuarios (icono de voz) o desde el panel Tecnico → **Calibrate**.
- Tras el reset, el siguiente uso del 🎤 volvera a pedir el enrollment de 20 segundos.

Tu, como usuario normal, no borras firmas de otros usuarios.

#### Privacidad

- La muestra de enrollment se guarda **cifrada** en la instalacion local; no viaja a Internet.
- No se incluye en Export/Import de configuracion (solo en backups de instalacion que gestione el admin).
- LAIM no «escucha» en segundo plano: solo graba mientras el 🎤 esta activo o durante el enrollment.

#### Resumen rapido

| Pregunta | Respuesta |
|---|---|
| ¿Debo registrar mi voz? | Si, la primera vez que uses el microfono en Chat o Direct |
| ¿Sirve para Chat y Direct? | Si; es la misma proteccion y la misma API |
| ¿Puede otro dictar con mi sesion? | No, si su voz no coincide con tu firma |
| ¿Que hago si pierdo / cambio de mic? | Pide al admin un reset de firma y vuelve a enrollar |

### 7.4 LM Studio y MLX (Apple silicon)

Por defecto, Inferencia directa habla con **Ollama** (selector de modelo, **Ajustes**, **Evaluar** y **Comparar**). Hay dos interruptores extra, mutuamente excluyentes:

**Botón LMStudio (GGUF / llama.cpp).** A la derecha de **Comparar** verás **LMStudio** solo mientras LAIM alcanza `http://localhost:1234/v1` (servidor local de LM Studio). Direct comprueba el puerto mientras la pantalla está abierta: si arrancas LM Studio el botón aparece; si lo cierras, desaparece y el interruptor se apaga. Al encenderlo se deshabilitan el selector Ollama, **Ajustes**, **Evaluar** y **Comparar**. Carga **antes** un modelo en LM Studio (Chat o pestaña Developer). Direct usa ese modelo en memoria, no el selector de Ollama.

**Botón MLX (safetensors, Apple Silicon).** Inventaria carpetas `publisher/model` bajo `~/.lmstudio/models` (`config.json` + `*.safetensors`). Al elegir una, el modelo se presenta (ficha técnica, igual que el selector Ollama) y, al enviar, LAIM arranca **mlx-lm** nativo en `127.0.0.1:4325` con esos pesos. **No hace falta tener LM Studio abierto.** En Apple Silicon, `laim web` instala `mlx-lm` en el entorno `.venv_314` (el mismo Python de la interfaz web). Un administrador parametriza ventana de contexto, tokens de generación, muestreo y límites de RAM unificada en **Configuración › Internal › Local → Configuración MLX** (distinto de la ventana de contexto Ollama). Ollama en Silicon sigue siendo llama.cpp + Metal (`:11434`); este botón no lo sustituye. Un GGUF no se ejecuta aquí: usa **LMStudio**.

La conversación, el historial y el micrófono de Direct siguen siendo los de LAIM; solo cambia el motor de inferencia del turno.

**Ejemplo (Apple Silicon).** Enciendes **MLX**, eliges un safetensors de `~/.lmstudio/models` y envias. No hace falta LM Studio abierto. Si enciendes **LMStudio**, el selector Ollama se apaga y Direct usa el GGUF ya cargado en `:1234`.

### 7.5 Copiar conversacion a Informes (📋)

Junto al microfono del composer de **Inferencia directa** hay un boton **📋** (el mismo icono que en Chat). Sirve para **guardar una copia** de la conversacion activa antes de borrarla del historial.

1. Abre la conversacion que quieres conservar (al menos un mensaje).
2. Pulsa **📋**. LAIM escribe un fichero Markdown en la carpeta `reports/` de la instalacion.
3. Abre **Informes** en la interfaz: el documento aparece en el grupo **Direct** (el nombre empieza por `direct_`).
4. Cuando la copia este en Informes, puedes eliminar la conversacion con la **X** roja del historial sin perder el contenido.

La copia incluye titulo, mensajes de usuario y de la IA, y una tabla de indice. No pasa por el Presenter (no se reescribe el Markdown). Si la conversacion esta vacia, LAIM avisa y no crea el fichero.

El informe de **Chat** (seccion 5.5) va al grupo **Inferencias**; el de Direct va al grupo **Direct**, para distinguirlos.

---

## 8. Equipos remotos SSH

LAIM te permite conectarte a equipos remotos de **dos formas** complementarias: desde la interfaz web (con terminal interactiva en el navegador) o desde la linea de comandos con `laim remote`. Ambos modos son visibles en tiempo real en el panel **SESIONES ACTIVAS** de la web, que actua como panel de control unificado para toda la actividad SSH de la instalacion.

---

### 8.1 Acceso desde la interfaz web

1. Haz clic en **remote** en el panel izquierdo.
2. En la columna **EQUIPOS** veras la lista de maquinas a las que tienes acceso.
3. Haz clic sobre el nombre de un equipo para abrir una **terminal SSH interactiva en una nueva pestana del navegador**.
   - El titulo de la pestana identifica la sesion: `SSH · nombre-equipo · #id`.
4. Puedes abrir **multiples sesiones** contra la misma maquina o contra maquinas distintas haciendo clic tantas veces como necesites.

**Cerrar una sesion web:**

- **Con el boton X rojo** — aparece en la fila del equipo cuando hay exactamente una sesion web activa. Cierra la sesion correctamente (envia `exit` al SSH, espera y cierra la pestana del navegador).
- **Desde la pestana** — escribe `exit` en la terminal. La pestana se cierra automaticamente a los pocos segundos.

---

### 8.2 Acceso desde la linea de comandos (`laim remote`)

Puedes abrir sesiones SSH directamente desde tu terminal sin abrir el navegador:

```
laim remote
```

1. LAIM mostrara la lista de equipos disponibles para tu usuario.
2. Selecciona el numero del equipo al que quieres conectarte.
3. Se abrira una sesion SSH interactiva en la propia consola.
4. Escribe `exit` para cerrar la sesion.

Esta modalidad es identica en seguridad y acceso a la web: usa las mismas credenciales cifradas en `laim.dat` y respeta los mismos permisos por usuario.

---

### 8.3 Panel SESIONES ACTIVAS — vista unificada

El panel **SESIONES ACTIVAS** en la interfaz web muestra en tiempo real **todas las sesiones abiertas** de la instalacion LAIM, independientemente de como se abrieron.

**Layout de cada fila:**

```
[emojis web]  nombre-equipo  [iconos CLI]  ....  [Abrir sesion]  [X]
```

| Elemento | Significado |
|----------|-------------|
| Emoji de colores a la **izquierda** del nombre | Sesion abierta desde la **interfaz web** (🖥️💻⚡🔌📡...). Un emoji por sesion activa. |
| Icono de terminal a la **derecha** del nombre | Sesion abierta desde la **CLI** con `laim remote`. Un icono por sesion activa. |
| Boton **Abrir sesion** | Abre una nueva sesion web contra ese equipo en cualquier momento. |
| Boton **X rojo** | Solo aparece cuando hay exactamente **una** sesion web activa. Cierra esa sesion de forma limpia. |

**Clic en los emojis web:** enfoca la pestana del navegador correspondiente a esa sesion.

**Los iconos CLI son de solo monitorizacion:** no tienen boton de cierre en la web porque la sesion vive en tu terminal. Para cerrarla, escribe `exit` en esa consola.

**Actualizacion automatica:** el panel se refresca cada pocos segundos. Tambien puedes forzar una sincronizacion con el boton **Recuperar sesiones activas**.

---

### 8.4 Ejemplo practico: trabajo simultaneo web + CLI

Imagina que tienes un servidor `tibet` y quieres:
- Un administrador trabajando con la terminal web.
- Tu mismo usando `laim remote` desde PowerShell para tareas de mantenimiento.

El panel SESIONES ACTIVAS mostraria algo como:

```
🖥️  tibet.house.loc  [icono-cli]  ....  [Abrir sesion]
```

- El emoji `🖥️` representa la sesion web del administrador.
- El icono de terminal representa tu sesion CLI.
- Ambas son independientes y conviven sin interferencias.

---

### 8.5 Sugerencias de la IA en sesiones SSH

Durante una sesion SSH remota desde la web, puedes solicitar analisis inteligente de lo que aparece en pantalla:

1. Haz clic en el boton **IA** dentro de la terminal SSH.
2. LAIM analiza el contenido visible de la consola y actua como un **ingeniero de sistemas experto**: interpreta la salida de comandos, detecta errores, propone pasos siguientes o explica configuraciones del sistema.
3. El asistente conoce el sistema operativo del equipo remoto y adapta sus sugerencias a la plataforma (Ubuntu, CentOS, Debian, etc.).
4. Si la IA necesita ejecutar comandos adicionales para obtener mas informacion, te lo comunicara y pedira tu confirmacion antes de proceder.
   - Si le pides un **cambio** (vaciar la cache DNS, renombrar el equipo, cambiar los DNS…), LAIM propone los comandos verificados de su catalogo para ese sistema, sin ejecutarlos; si no tiene un procedimiento verificado, te lo dice («LAIM no tiene un procedimiento verificado para este cambio en Linux») en lugar de improvisar comandos. Si leyo algo del equipo, lo muestra despues de ese aviso, nunca como si fuera la respuesta al cambio.
   - Para **subir o bajar la prioridad** de un proceso, LAIM usa la direccion que pides (bajar: `renice -n 10` / `BelowNormal`; subir: `sudo renice -n -5` / `AboveNormal`) sobre un PID real: el que indiques o, si pides «el proceso con mas CPU», el que LAIM lee antes en el equipo (sin contar sus propios procesos de consulta). Te dice que proceso es antes de proponer el cambio.
5. Las respuestas se formatean con **titulos de seccion** claros y espaciado legible (listas numeradas, epigrafes) para facilitar la lectura en el panel CRT.

El historial de sugerencias de esa sesion SSH tambien esta sujeto a la **compresion de contexto** si crece demasiado (mismo mecanismo que chat y Direct).

**Ruta IA Share:** si el selector de ruta IA apunta a un Share, la **inferencia** de las sugerencias se ejecuta en ese master (GPU remota). Los **equipos SSH** siguen siendo los de **esta** instalacion (los que el administrador te ha concedido en Acceso remoto). No se listan los equipos del Share.

> **Ambito actual de SESIONES ACTIVAS:** la monitorizacion unificada cubre las sesiones abiertas desde la web y desde la CLI de la instalacion LAIM local. Las sesiones SSH abiertas desde un nodo `laim connect` se incorporaran en una fase posterior.

---

## 9. Mejorar la IA con tu feedback

El boton **Sugerir mejora** (icono de bombilla, en la parte superior del chat) permite que la IA aprenda de tus correcciones y sugerencias. Esta funcion alimenta al **agente Teacher**, que procesa tu feedback y actualiza el conocimiento de la instalacion LAIM.

### Como funciona

1. Haz clic en el boton **Sugerir mejora** en el chat.
2. Aparece un modal con un campo de texto. Describe la mejora o correccion:
   - *"El comando que generaste para listar procesos en Windows no era correcto."*
   - *"En este servidor, el comando para ver disco libre es `df -h --block-size=GB`."*
   - *"La respuesta sobre redes fue demasiado tecnica para un usuario basico."*
3. El **agente Teacher** analiza tu mensaje. Puede hacerte preguntas de aclaracion antes de guardar.
4. Cuando el agente tenga suficiente informacion, almacena el nuevo conocimiento en `soul.dat` (cifrado).

### Para que sirve

- Las correcciones se utilizan automaticamente en futuras inferencias para ese tipo de consulta.
- El conocimiento acumulado mejora la precision de los comandos generados en tu plataforma.
- El administrador puede ver y gestionar el conocimiento acumulado desde la configuracion.

> Esta funcion tiene un limite de uso por sesion para evitar saturar al agente Teacher.

**Ejemplo.** La IA propuso `free` en un Windows. Escribes «en este PC el comando nativo es Get-CimInstance Win32_OperatingSystem». El Teacher puede preguntar el SO y guarda el tip en `soul.dat`. La siguiente pregunta de RAM en Windows no insiste en `free`.

---

## 9.1 Protocolo de correccion automatica de errores

LAIM aprende de forma autonoma cuando los comandos que genera no funcionan en tu sistema. No necesitas hacer nada: el proceso es completamente transparente.

### Que hace LAIM de forma automatica

Cuando la IA genera un comando en una sesion de chat y ese comando falla al ejecutarse con un error de tipo "comando no encontrado" o "argumentos invalidos", LAIM:

1. **Detecta el fallo** al terminar la ejecucion del lote de comandos en la fase F6.
2. **Encola un job de aprendizaje** (tipo *Correccion de errores*, prioridad baja 3) para que no interfiera con tu trabajo actual.
3. **Aprende de forma determinista** (sin necesidad de conectarse a la IA): almacena en `soul.dat` que ese comando concreto no esta disponible en tu plataforma.
4. **Aplica el conocimiento** en la siguiente inferencia: el filtro de comandos rechaza el comando conocido como malo antes de pedirte confirmacion para ejecutarlo.

### Tipos de errores que corrige

| Tipo | Ejemplo en Windows | Lo que aprende LAIM |
|------|-------------------|---------------------|
| Comando no encontrado | `sysmon` no es un cmdlet conocido | "sysmon" no esta disponible en Windows como comando nativo |
| Argumento invalido | `Get-Process -BadParam` | El comando existe pero los parametros eran incorrectos |

> Los errores genericos de ejecucion (codigo de salida ≠ 0 sin patron de "no encontrado") no se aprenden, para evitar falsos positivos.

### Donde ver los jobs de correccion

En la pagina **Gestor de colas** (menu lateral) puedes ver los jobs de tipo *auto_correct*. Apareceran con prioridad **P3** y estado *done* cuando el aprendizaje haya terminado.

### Privacidad y seguridad

- El conocimiento acumulado se almacena en `soul.dat` (cifrado con la clave maestra de tu instalacion).
- Solo el binario LAIM de esa instalacion puede leer y usar ese conocimiento.
- No se envia informacion a servidores externos.

---

## 10. Ver el rendimiento de la IA

Tras usar el Chat puedes analizar cuanto tardo cada fase y que carga genero en la CPU/GPU:

1. En el Chat, haz clic en el boton **Rendimiento** (icono de grafico, sobre el area de respuesta).
2. Selecciona el **usuario**, **fecha**, **sesion** e **inferencia**.
3. El grafico mostrara el consumo por fase (F1-F8) con scroll horizontal y control de zoom.

| Fase | Significado |
|---|---|
| F1 | Deteccion de idioma y clasificacion |
| F2-F4 | Analisis del contexto y recuperacion |
| F5 | Generacion de comandos de sistema |
| F6 | Ejecucion y reparacion automatica |
| F7-F8 | Formato, traduccion y presentacion |

**Ejemplo.** Tras un chat de disco libre, pulsas **Rendimiento**, eliges tu usuario y la inferencia de hace un minuto. El grafico muestra F6 mas largo que F7 porque se ejecutaron `df`/`Get-Partition` y el modelo no tuvo que «inventar» cifras.

---

## 11. Notificaciones

El panel **Notificaciones** es el canal de avisos entre LAIM y tu usuario. Aparece en el sidebar con un **badge** que muestra cuantas tienes sin leer.

### Como abrirlo

1. En el panel izquierdo, haz clic en **Notificaciones**.
2. Veras la lista de avisos (titulo, tipo y fecha).
3. Haz clic en una notificacion para leer el hilo completo (estilo chat).

### Tipos habituales de aviso

| Tipo | Cuando aparece |
|---|---|
| Sugerencia / Teacher | Tras procesar un **"Sugerir mejora"** |
| Descarga de modelo | Cuando termina una descarga de modelo Ollama |
| Chat / sistema | Eventos relevantes de trabajos en cola |
| Alerta de seguridad | (Administradores) amenaza detectada y bloqueada por el agente Secure |

**Ejemplo.** Tras **Sugerir mejora**, el badge del sidebar pasa a `1`. Abres **Notificaciones**, lees «Sugerencia procesada» y respondes «gracias»: LAIM contesta en tu idioma. Si la ruta IA es un Share, esa respuesta de IA se genera en el master, pero la lista sigue siendo la de **este** PC.

### Responder a una notificacion

Puedes escribir una respuesta en el hilo. LAIM genera una contestacion breve con IA (en tu idioma). Cada mensaje muestra la fecha y hora bajo la burbuja.

### Ruta IA Share

El listado de notificaciones es **siempre de esta instalacion** (`notifications.dat` local). Si la ruta IA es un Share, las **respuestas de IA** del hilo se generan en el master (con los datos del panel local); no se sustituye tu bandeja por la del Share.

### Desde la linea de comandos

```
laim notifications
```

Lista las notificaciones pendientes, permite marcarlas como leidas y responder desde la terminal.

> Las notificaciones se almacenan cifradas en `notifications.dat` (misma clave maestra que `laim.dat`). No se envian fuera de tu instalacion.

---

## 12. Editor Markdown con IA

El **Editor** es una pestana independiente para escribir y gestionar notas Markdown con ayuda de la IA. Se abre desde **help → Editor**.

### Abrir el editor

1. En el sidebar, haz clic en **help**.
2. Pulsa el boton **Editor**.
3. Se abre `http://localhost:4320/editor/` en una pestana nueva (usa tu sesion web actual).

> Si el navegador bloquea la ventana emergente, permite pop-ups para `localhost` o copia la URL que muestra LAIM.

### Que puedes hacer

| Accion | Descripcion |
|---|---|
| **Notas** | Crear, abrir, guardar y eliminar notas. El contenido va cifrado por usuario. |
| **Markdown** | Escribir en fuente Markdown; el preview muestra el resultado formateado. |
| **Acciones IA inline** | Selecciona texto → barra flotante: Mejorar, Reescribir, Continuar, Resumir, Traducir. |
| **Traducir** | El boton Traducir abre un selector con 16 idiomas (ES, EN, FR, DE, IT, PT, ZH, JA, KO, RU, AR, NL, PL, TR, SV, UK). |
| **Chat del documento** | Panel lateral: pregunta a la IA usando el documento completo como contexto. |
| **Diagramas Mermaid** | Los bloques ` ```mermaid ` se renderizan en el preview. |
| **Exportar** | Markdown (descarga), HTML o **PDF** (solo el contenido del preview, sin la UI del editor). |

### Flujo tipico con IA inline

1. Selecciona un parrafo en el area de escritura.
2. Elige una accion (por ejemplo **Mejorar** o **Traducir → Français**).
3. Veras un indicador de carga mientras la IA trabaja.
4. Revisa el resultado (diff / preview) y **acepta** o **rechaza**.

### Privacidad

- Cada nota pertenece a tu usuario; otros usuarios de la misma instalacion no ven tus notas.
- El contenido se cifra en disco (`notes/<id>.enc`) con la clave maestra local.
- Los modelos de IA del editor los configura el administrador en **Internal › Local** (modelo para acciones inline y modelo para el chat del documento).

### Modo Connect

Si tu instalacion usa **laim connect**:

- Las **notas** siguen guardandose en **tu equipo** (carpeta `notes/` y asociaciones en tu `laim.dat`), con el mismo cifrado local.
- Las acciones de **IA** (inline y chat del documento) se ejecutan en el servidor **Share**, usando los modelos y la ventana de contexto configurados alli — no necesitas configurar modelos del Editor en el Connect.
- Si el Share no esta disponible y tu equipo tiene Ollama local, LAIM intenta un **fallback local** automaticamente.

**Ejemplo.** Seleccionas un parrafo, **Traducir → English**, revisas el diff y pulsas **Aceptar**. El chat del documento («resume esta nota en tres bullets») usa toda la nota como contexto. En Connect, la nota sigue en tu disco; la IA corre en el Share.

---

## 13. Sesiones y privacidad

### Ciclo de vida de tu sesion

- Tu sesion se abre cuando inicias sesion y expira segun el tiempo maximo configurado por el admin.
- Si usas el microfono (Chat o Direct), tu **firma vocal** protege la sesion frente a que otra persona dicte en tu nombre; ver [seccion 7.3](#73-proteccion-de-voz-anti-suplantacion). Aun asi, cierra sesion al dejar el puesto.
- **Cerrar sesion**: cierra la sesion activa y vuelve a la pantalla de login **sin** detener LAIM ni Share. Equivale a `laim logout` en la terminal.
- **Salir**: solo cierra la pestana del navegador. Tu sesion sigue activa en el servidor; puedes reconectarte sin hacer login de nuevo.
- **Terminar**: cierra la sesion definitivamente, detiene el servicio Share si esta activo y termina LAIM por completo.

### Cerrar sesion (web y CLI)

| Accion | Interfaz web | Terminal (CLI) |
|--------|-------------|----------------|
| Cerrar sesion y volver al login | Boton **Cerrar sesion** (sidebar, bajo "Terminar") | `laim logout` |
| Salir del navegador sin cerrar sesion | Boton **Salir** | — |
| Cerrar sesion y detener LAIM | Boton **Terminar** | `laim terminar` |
| Salir de la consola sin cerrar sesion | — | `laim salir` |

**Boton "Cerrar sesion" (web):**
Aparece en el sidebar bajo los botones "Terminar" y "Salir". Al pulsarlo:
1. Se invalida la sesion web activa en el servidor.
2. Se borran las cookies de sesion del navegador.
3. La interfaz vuelve automaticamente a la pantalla de login.
El backend de LAIM y el servicio Share permanecen en funcionamiento.

**Comando `laim logout` (CLI):**
```
laim logout
```
Cierra la sesion cifrada almacenada en `laim.session` y actualiza el registro de sesiones (marcando la sesion como cerrada con hora y fecha). A continuacion:
- LAIM sigue ejecutandose en el mismo proceso (no hay `os.Exit`).
- El servicio Share permanece activo.
- Puede iniciar una nueva sesion con `laim login`.

Ejemplo de salida:
```
✅ Sesion cerrada: abc123 (usuario: maria)
   Use `laim login` para iniciar una nueva sesion.
```

> **Nota:** si no hay sesion activa cuando ejecutas `laim logout`, LAIM lo indica con un aviso y no produce ningun error.

### Privacidad de tus datos

- Todas tus conversaciones se guardan **cifradas** en el ordenador local (o en el servidor master si usas modo Connect).
- Las conversaciones se almacenan en `laim.memory` protegidas con cifrado AES-256-GCM.
- Nadie fuera de tu instalacion LAIM puede leer tus conversaciones.
- Las respuestas de la IA **no** se envian a Internet ni a servidores de terceros.

### Usar LAIM como cliente Connect

Si tu empresa tiene uno o varios servidores LAIM (modo **Share**), el administrador guarda **perfiles** en Config › Connect (nombre, IP/puerto y credenciales de handoff). No hace falta un interruptor «activar Connect»: con perfiles guardados este equipo ya puede usar el selector.

Cuando eliges un Share en el **selector de ruta IA**:

- Tus consultas de chat, Direct, voz, editor y traduccion van al master **cifradas** por la red.
- La IA se ejecuta en ese servidor (normalmente con mas GPU).
- Los comandos de sistema F6 de «este equipo» se ejecutan en **tu propio ordenador**.
- Los equipos SSH / Acceso remoto son los de **esta** instalacion, no los del Share.

Si eliges **Localhost**, todo vuelve a Ollama de este equipo. Los perfiles no se borran.

### Elegir Localhost o un servidor Share

El selector aparece en **chat**, **Direct** e **Acceso remoto** (IA SSH). Siempre incluye **Localhost** y los Shares que **responden** en ese momento.

1. Abre chat, Direct o Acceso remoto.
2. En el banner, elige **Localhost** o el nombre de un Share (por ejemplo Windows GPU o Silicon).
3. Esa eleccion aplica a todos esos servicios hasta que la cambies en cualquiera de esas pantallas.
4. Si ningun Share esta alcanzable, LAIM usa **Localhost** (no elige un Share solo por tenerlo guardado).

El administrador crea y edita los perfiles en **config → Connect**. «Probar conexion» comprueba el handoff; no es lo que te pinta en el monitor del Share. El Share solo muestra este cliente mientras usas **su** ruta IA (unos segundos de margen si dejas de usarlo).

### Usar LAIM Connect desde una red externa (Wi-Fi de hotel, 4G, etc.)

Si el administrador ha configurado **Headscale + subnet routing**, puedes usar LAIM Connect desde **cualquier red con Internet**, incluso si el servidor Share esta en casa u oficina sin IP publica.

#### Como funciona (para el usuario)

1. Tu ordenador (Mac, Linux) tiene instalado **Tailscale** y esta registrado en la malla WireGuard del servidor.
2. Cuando enciendes Tailscale, tu ordenador obtiene una IP privada en la malla (p. ej. `100.64.0.2`).
3. Gracias al **enrutamiento de subred** activado por el administrador, puedes alcanzar el servidor Share directamente por su IP local (p. ej. `192.168.1.50:4322`), como si estuvieras en la misma red.
4. LAIM Connect funciona igual que en casa: cifrado de extremo a extremo, IA remota, comandos locales.

#### Pasos para el usuario (una vez configurado por el admin)

**Antes de salir de casa / la oficina (primera vez):**

1. Asegurate de que Tailscale esta instalado en tu portatil.
2. Unete a la malla con la PreAuth Key que te facilite el administrador:
   ```bash
   # Mac o Linux
   sudo tailscale up --login-server=http://<URL_DEL_SERVIDOR>:8080 \
                     --authkey=<tu-preauth-key> \
                     --accept-routes
   ```
3. Verifica que el servidor aparece como activo:
   ```bash
   tailscale status
   ```
4. Configura LAIM Connect apuntando a la IP LAN del servidor (te la dara el admin):
   ```bash
   laim config   # Menu > Share/Connect > Configurar Connect
   # Host: 192.168.1.50  Puerto: 4322
   # Usuario y contrasena: los que te facilite el admin
   ```

**En la red externa (hotel, 4G, cafeteria):**

1. Abre la aplicacion Tailscale (icono en la barra de herramientas) y asegurate de que esta conectado.
2. Abre LAIM normalmente:
   ```bash
   laim connect   # conecta al servidor Share
   laim chat      # usa la IA
   ```
   O abre la UI web en `http://localhost:4321`.
3. Si la conexion falla, comprueba que Tailscale esta activo con `tailscale status`.

#### Instalacion de Tailscale segun tu sistema operativo

##### macOS

LAIM usa el **cliente oficial standalone** (`Tailscale.app`), el mismo que Headscale y que Tailscale Inc. El CLI correcto es:

`/Applications/Tailscale.app/Contents/MacOS/Tailscale`

**No** uses el binario de Homebrew ni `sudo` alrededor de ese CLI: no habla con el daemon de la app y macOS pide el permiso VPN en la GUI.

> **App Store:** si solo tienes Tailscale de la App Store (`IPNExtension`), desinstálala o cierra esa app. LAIM instala el `.pkg` oficial (Config › malla › Cliente Tailscale › Instalar). Homebrew es un fallback si falla el `.pkg`, no el camino recomendado.

**Paso 1 — Instalar**

Desde LAIM (recomendado): Config › Red mesh › **Cliente Tailscale** › Instalar (descarga `Tailscale-latest-macos.pkg`).

A mano: [tailscale.com/download/mac](https://tailscale.com/download/mac) o:

```bash
open -a Tailscale   # si ya está en /Applications
```

**Paso 2 — Abrir la app**

Deja el icono en la barra de menú (Running). Acepta el perfil VPN si macOS lo pide.

**Paso 3 — Unirte a la malla Headscale**

Con LAIM: Solicitar unirse → el administrador Aprueba → **Aplicar unión** (LAIM llama al CLI de `Tailscale.app`, sin sudo).

Sin LAIM (preauth del administrador):

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale up \
  --login-server=http://<IP_O_FQDN_SERVIDOR>:8080 \
  --accept-routes \
  --hostname=<nombre-de-tu-mac> \
  --authkey=<tu-preauth-key>
```

Sustituye `<IP_O_FQDN_SERVIDOR>` por el coordinador (p. ej. `tibet.house.loc`) y `<tu-preauth-key>` por la clave que te facilite el administrador. No mezcles este `--login-server` con `login.tailscale.com` en el mismo daemon.

**Paso 4 — Verificar:**

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale status
# Debes ver tu Mac y el servidor Linux ambos como "online"
# y la ruta de subred (p. ej. 192.168.0.0/24) si el admin la anunció
ping 100.64.0.2   # ping al servidor Linux por su IP mesh
```

**Para uso diario:** Tailscale.app puede abrirse al iniciar sesión (preferencias de la app). No hace falta `brew services`.

**Para detener Tailscale temporalmente:**

```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale down
```

---

##### Linux

**Paso 1 — Instalar Tailscale:**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
# o en Ubuntu/Debian:
sudo apt install tailscale
```

**Paso 2 — Habilitar el reenvio de IP (necesario para subnet routing):**

```bash
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/99-tailscale.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.d/99-tailscale.conf
sudo sysctl -p /etc/sysctl.d/99-tailscale.conf
```

**Paso 3 — Unirte a la malla Headscale (como nodo cliente):**

Si el nodo Linux va a ser solo cliente (no el servidor Headscale):

```bash
sudo tailscale up \
  --login-server=http://<IP_SERVIDOR_HEADSCALE>:8080 \
  --accept-routes \
  --hostname=<nombre-del-equipo> \
  --authkey=<tu-preauth-key> \
  --reset
```

**Paso 3b — Si el nodo Linux es el servidor Headscale (anuncia la subred):**

Este es el caso del servidor `tibet.house.loc`. Ademas de unirse, **anuncia** su LAN local a la malla:

```bash
sudo tailscale up \
  --login-server=http://localhost:8080 \
  --accept-routes \
  --advertise-routes=192.168.0.0/24 \
  --hostname=tibet \
  --reset

# A continuacion, aprueba la ruta en Headscale:
./bin/linux/headscale nodes list-routes \
  --config bin/linux/headscale_data/config.yaml

# Obtener el ID del nodo (columna ID) y aprobar:
./bin/linux/headscale nodes approve-routes \
  --config bin/linux/headscale_data/config.yaml \
  --identifier <ID_NODO> \
  --routes 192.168.0.0/24
```

**Paso 4 — Verificar:**

```bash
tailscale status
# Todos los nodos deben aparecer como "online"
# La ruta debe aparecer en: headscale nodes list-routes
```

**Para hacer permanente el reenvio de IP en el arranque:**

```bash
# Ya incluido en /etc/sysctl.d/99-tailscale.conf (paso 2)
# Tailscale tambien lo gestiona automaticamente en versiones recientes
```

---

#### Que hace el administrador por ti

El admin es quien:
- Instala y configura Headscale en el servidor.
- Activa el **enrutamiento de subred** desde el panel de LAIM web (por defecto desactivado por seguridad).
- Te genera la PreAuth Key de registro.
- Abre los puertos necesarios en el router (8080 TCP y 41641 UDP).

Tu solo necesitas instalar Tailscale una vez y unirte a la malla con la clave que te den.

#### Privacidad y seguridad

- Todo el trafico entre tu portatil y el servidor Share viaja **cifrado por WireGuard** (protocolo militar, codigo abierto, auditado).
- Ademas, los mensajes de LAIM (prompts, respuestas) tienen **cifrado AES-256-GCM adicional** dentro del tunel.
- Nadie en la red del hotel / 4G puede ver tu contenido.
- El enrutamiento de subred solo esta activo cuando el administrador lo necesita. Cuando no se usa, se desactiva para minimizar la superficie de exposicion.

---

## 13.1 Funcion "Sugerir mejora" en modo Connect → Share

Cuando usas LAIM como cliente **Connect** (tu Mac, por ejemplo) y el servidor **Share** (Windows u otro equipo) proporciona la IA, la funcion **"Sugerir mejora"** sigue funcionando de extremo a extremo con las mismas garantias que en una instalacion local.

### Como funciona en este escenario

```
Mac (Connect)                     Windows (Share)
─────────────────────────────     ──────────────────────────────────
1. Pulsas "Sugerir mejora"
2. Job encolado localmente    →   3. RunTeacherSession (Ollama)
                              ←      SSE: chunk, learn_action, done
4. Badge progreso visible ✓   ←   soul.dat Windows actualizado ✓
5. Informe generado en Mac ✓
6. soul.dat Mac sincronizado ✓
7. Notificacion en Mac ✓
```

### Pasos desde tu punto de vista

1. Haz clic en **Sugerir mejora** (dentro del chat o dentro del panel de sugerencias SSH).
2. Escribe tu correccion o sugerencia en el modal y envía.
3. El **badge del gestor de colas** aparece en el sidebar con el job en progreso.
4. La IA del servidor Share analiza tu feedback en tiempo real. Puedes ver el streaming.
5. Al terminar recibes una entrada en el panel **Notificaciones** (badge del sidebar): "Sugerencia procesada".
6. El **informe** del teacher se genera en la carpeta `reports/` de tu Mac.
7. El conocimiento aprendido se almacena en el `soul.dat` de **ambas** instalaciones:
   - **Windows (Share):** donde corrio la inferencia.
   - **Mac (Connect):** sincronizado automaticamente desde el evento de aprendizaje.

### Que ver si algo falla

| Sintoma | Causa probable | Accion |
|---------|---------------|--------|
| El badge no avanza | El nodo Connect no llega al servidor Share | Comprueba la conexion con `laim connect` en la terminal |
| No llega la notificacion | El job termino con error | Abre el Gestor de colas y busca el job en estado *error* |
| El informe no aparece | El servidor Share no tiene un modelo teacher configurado | El admin debe asignar un tier al agente Teacher |
| soul.dat no sincronizado | El master no emitio el evento learn_action (posible error en la inferencia) | Repite la sugerencia cuando el servidor este disponible |

### Nota sobre preguntas de aclaracion

Si el agente Teacher hace una **pregunta** antes de guardar el conocimiento, el sistema queda a la espera de tu respuesta. Responde desde el mismo modal del job. Si el job lleva mas de 2 horas sin respuesta, el aprendizaje se registrara de forma parcial con la informacion recibida hasta ese momento.

---

## 14. Preguntas frecuentes

**La IA accede a Internet?**
No. LAIM usa modelos locales (Ollama o, en Direct, LM Studio si activas el interruptor) que funcionan completamente sin conexion. Tus datos nunca salen del sistema.

**Que es el boton LMStudio en Inferencia directa?**
Solo se ve mientras LM Studio esta arrancado con la API en `http://localhost:1234/v1` (Direct lo comprueba en vivo: aparece al arrancar la app y desaparece al cerrarla). Al pulsarlo, Direct deja de usar Ollama y envia el turno a LM Studio (GGUF / llama.cpp). El botón **MLX** (Apple Silicon) es otro camino: usa mlx-lm nativo y no necesita LM Studio. Detalle en la [seccion 7.4](#74-lm-studio-y-mlx-apple-silicon).

**Mis conversaciones son privadas?**
Si. Todo se procesa y almacena en tu ordenador (o en el servidor de tu empresa si usas modo Connect). El cifrado AES-256-GCM protege todos los datos en reposo.

**Donde estan los ajustes de configuracion?**
Los ajustes avanzados (modelos, conexiones, agentes, etc.) los gestiona el administrador desde el boton **config**. Tu como usuario solo veras las funciones basicas en el sidebar.

**Por que a veces la respuesta tarda mucho?**
Depende del tamano del modelo y del hardware disponible. Los modelos mas grandes son mas precisos pero mas lentos. Tu admin puede configurar distintos tiers de velocidad/calidad para cada fase.

**Que significa "Contexto comprimido" en el chat?**
Que el historial de la sesion habia crecido demasiado y LAIM lo ha resumido automaticamente para poder seguir conversando sin saturar la memoria de la GPU. Los detalles relevantes se conservan. Para empezar de cero, abre una sesion o conversacion nueva. Ver [seccion 5.1](#51-memoria-contexto-y-compresion).

**Donde estan mis notas del Editor?**
En tu instalacion LAIM, cifradas y asociadas a tu usuario. Solo tu (y el administrador a nivel de ficheros del servidor, no desde la UI de otro usuario) tienes acceso al contenido. Abre el Editor desde **help → Editor**.

**El Editor usa la IA del Share en modo Connect?**
Si. En Connect las **notas** se guardan en tu equipo (carpeta `notes/` y tu `laim.dat` local), pero las acciones de IA del Editor (Mejorar, Reescribir, Continuar, Resumir, Traducir y el chat del documento) se ejecutan en el servidor **Share**, con los modelos y la ventana de contexto configurados alli. No hace falta configurar modelos del Editor en el Connect. Si el Share no esta disponible y tu equipo tiene Ollama local, LAIM intenta un fallback local. Ver [seccion 12 — Editor (Modo Connect)](#12-editor-markdown-con-ia).

**Por que no veo Notificaciones del Share?**
Las notificaciones son las de **esta** instalacion. El Share solo aporta la IA del hilo si la ruta IA apunta a ese master. Si el Share no responde, el listado local sigue visible.

**Como uso el microfono en Chat o Inferencia directa?**
El boton **🎤** (en Chat bajo el prompt, y en Direct junto a 📄) graba el microfono del host LAIM, transcribe con el tier **Sonido** y deja el texto en el cuadro para que lo revises antes de Enviar. El modelo recomendado (probado con exito) es **`gemma4:e2b`** en ese tier. Detalle en las [secciones 5.4](#54-entrada-por-voz-en-el-chat-) y [7.2](#72-entrada-por-voz-).

**Por que me pide grabar 20 segundos la primera vez?**
Es el **enrollment vocal**: LAIM guarda tu firma de voz (cifrada) para que nadie pueda dictar con tu sesion abierta. Ver [seccion 7.3 — Proteccion de voz](#73-proteccion-de-voz-anti-suplantacion).

**Que pasa si otra persona habla al microfono con mi sesion abierta?**
LAIM compara la voz con tu firma. Si no coincide, **bloquea** la transcripcion (no escribe texto en el prompt) y deja constancia del incidente para el administrador. Cierra sesion cuando te alejes del equipo.

**La voz no transcribe bien o pide configurar Sonido?**
Pide al administrador que asigne **`gemma4:e2b`** (u otro modelo Ollama con audio, p. ej. `gemma4:e4b`) al tier Sonido, comprueba el microfono por defecto del sistema y que no este silenciado. Modelos solo de texto, vision o TTS no sirven para dictado. Si el mensaje habla de «enrollment» o «voz no coincide», revisa la [seccion 7.3](#73-proteccion-de-voz-anti-suplantacion).

**Como cierro la sesion correctamente?**
- Para cerrar sesion y volver al login **sin** detener LAIM: usa el boton **Cerrar sesion** (web) o `laim logout` (CLI).
- Para cerrar solo la pestana del navegador sin cerrar sesion: usa **Salir**.
- Para cerrar sesion y detener LAIM por completo: usa **Terminar** (web) o `laim terminar` (CLI).

**Que es el "modo Connect" / la ruta IA?**
Connect guarda los perfiles de servidores Share. El **selector de ruta IA** (chat, Direct, Acceso remoto) elige **Localhost** (IA en este PC) o un Share alcanzable (IA en el master). El master suele tener mas GPU. Los equipos SSH siguen siendo los de tu instalacion.

**Puedo usar LAIM Connect desde el wifi del hotel o desde 4G?**
Si, si el administrador ha configurado Headscale + subnet routing. Necesitas tener Tailscale instalado y unirte a la malla una vez (desde casa). Despues, en cualquier red externa, Tailscale crea un tunel cifrado automaticamente y LAIM Connect funciona como si estuvieras en casa. Ver seccion "Usar LAIM Connect desde una red externa" mas arriba.

**Que es Tailscale y tengo que instalarlo yo?**
Tailscale es una aplicacion VPN basada en WireGuard. Es gratuita para uso personal. Tu administrador te indicara si la necesitas y te facilitara la PreAuth Key para unirte a la malla privada de tu organizacion. La instalacion es sencilla: descarga desde https://tailscale.com/download e introduce la clave que te de el admin.

**Puedo hablar con LAIM en espanol?**
Si. LAIM detecta automaticamente el idioma de tu mensaje en la primera pregunta de cada sesion y responde siempre en ese idioma. Tambien puedes cambiar el idioma de la interfaz web con las banderas de idioma, y el idioma de los **manuales e informes** con las banderas del visor de Ayuda / Informes.

**Que es el boton "Sugerir mejora"?**
Es un canal de feedback que permite que la IA aprenda de tus correcciones. El agente Teacher analiza tu sugerencia, puede hacerte preguntas y almacena el nuevo conocimiento de forma cifrada para mejorar futuras respuestas. Al terminar recibes una entrada en el panel **Notificaciones**.

**Para que sirve el boton 📋 junto al microfono del chat?**
Genera un informe Markdown de toda la sesion de chat (turnos, comandos, fases). Queda en Informes → grupo **Inferencias**. Ver [seccion 5.5](#55-informe-de-la-sesion-de-chat-).

**Para que sirve el boton 📋 en Inferencia directa?**
Guarda una copia Markdown de la conversacion activa en Informes → grupo **Direct**. Usalo **antes** de borrar la conversacion con la X roja si quieres conservar el contenido. Ver [seccion 7.5](#75-copiar-conversacion-a-informes-).

**Por que la ficha del modelo en Direct no vuelve a «pensar»?**
Porque ya esta cacheada (motor + modelo + idioma). Nueva conversacion o el mismo selector reutilizan `Direct.ModelPresentations`. Un modelo distinto o MLX frente a Ollama si infiere. Ver [seccion 7](#7-inferencia-directa).

**Como cambio el aspecto de la interfaz (CRT / Soft UI)?**
Ayuda → **Temas**. La eleccion queda en tu usuario. El tema **default** es el CRT verde; puedes volver a el en cualquier momento.

---

## Soporte

Para cualquier problema tecnico, contacta con tu **administrador de LAIM**.

---

*Manual de usuario — LAIM Core · Actualizado 2026-09-09 (ejemplos por seccion, ficha Direct en cache, F8 Ejemplo/Codigo, temas)*
