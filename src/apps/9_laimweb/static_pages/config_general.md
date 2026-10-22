# Configuración general

El menú **Configuración** lo ve el administrador del portal. Tiene dos
páginas: **General** (esta) y **Foro LAIM**.

## General

Desde aquí se administran las cuentas del portal y las instalaciones de
este entorno.

### Usuarios

Abre las cuentas de este portal.

- **Buscar** filtra por usuario o por email.
- La tabla muestra identificador, usuario, email, móvil y estado
  (**activo** o **bloqueado**). Pulsar el estado lo cambia. Si el
  servidor no confirma el cambio, la fila se queda como estaba.
- **Abrir** edita el usuario, el nombre completo, el email y el móvil.
  **Guardar** aplica esos datos.
- **Actualizar contraseña** pide la contraseña y su confirmación. No
  muestra la clave anterior.

### Registro

Abre el inventario de instalaciones de este entorno: identificador,
usuario, alias, número de serie enmascarado, sistema, edición, estado
y fecha de registro.

**Evolución de registros** abre el cuadro de la evolución de altas.
El menú público **Registro** sigue siendo el alta que hace cada usuario.

## Foro LAIM

Abre el panel del servicio de foro. Arriba se ve si está **En línea** o
**Detenido**. El resto son estos botones. Dentro de una acción,
**Volver al panel del servicio** regresa a esta rejilla.

Prefijos, permisos, reglas, URLs y moderadores comparten unas pestañas
(Ajustes, Prefijos, Palabras, URLs, Moderadores y Avatares) para pasar
de una a otra sin volver al panel.

### Configuración general

Muestra, sin poder editarlos, el host, el puerto, el estado, el
intervalo de sondeo y los strikes de URL. **Actualizar estado del
servicio** vuelve a leerlos.

### Categorías

Crea o edita una categoría: identificador, nombre, descripción, orden
y si está activa. **Guardar categoría** la escribe. El árbol de la
derecha lista las categorías, también las inactivas. El clic derecho
sobre una ofrece **Nueva subcategoría**, **Editar categoría** y
**Eliminar categoría**. Eliminar una categoría elimina también sus
subcategorías y sus hilos, y pide confirmación.

### Subcategorías

El mismo árbol, con el formulario de subcategoría: identificador,
nombre, descripción, orden, si está activa, la duración del ban en
segundos y la rotación del log (`weekly`, `daily` o `none`).
**Guardar subcategoría** la escribe. **Nueva subcategoría** abre el
alta dentro de la categoría elegida, con **Crear** y **Cancelar**.

### Prefijos de hilo

Etiquetas que el usuario puede poner a un hilo. Se rellenan el
identificador, el texto, el color y si está activo. **Guardar prefijo**
lo escribe. **Editar** carga uno ya existente, también si está inactivo.

### Moderadores

Tres selectores, en este orden: usuario, categoría y subcategoría.
**Asignar moderador** añade la fila y refresca la tabla (usuario,
categoría y subcategoría). **Desactivar** retira esa asignación.

### Baneos activos

Lista los baneos en vigor: usuario, subcategoría, motivo, moderador y
caducidad. **Recargar baneos** vuelve a pedirlos. **Revocar** levanta
ese baneo.

### Permisos moderación

Ajustes del aviso de moderación: la casilla **Anunciar ban en log**,
la plantilla del ban y la plantilla de eliminación. **Guardar ajustes**
los escribe.

### Reglas automáticas

Una palabra, una acción (**Agradecimientos**, **Amonestaciones**,
**Sugerencias**, **Ban** o **Kick**), el mensaje que verá el usuario y
si la regla está activa. **Añadir regla** crea una nueva y **Guardar
regla** actualiza la que se está editando. En la lista, **Editar**
rellena el formulario y **Activar** o **Desactivar** cambia su estado.

### URLs autorizadas

Un dominio y una descripción. **Añadir dominio** lo incorpora a la
lista. **Eliminar** lo quita.

### Visor de logs

Muestra la actividad de moderación ya guardada (asignaciones, baneos y
reglas). Categoría y subcategoría empiezan en **ALL**, que significa
ese nivel sin acotar, y el resto de valores son las categorías y
subcategorías que existan en ese momento. **Desde** y **Hasta** abren
un calendario para el intervalo de días. La tabla muestra fecha,
categoría, subcategoría, tipo, quién y la actividad. Crear un hilo o
responder no aparece aquí: eso queda en el propio foro.

### Estadísticas

Abre la ventana **Estadísticas del foro**: categorías, subcategorías,
hilos, respuestas, valoraciones, promedio, usuarios activos, baneos
activos, infracciones de hoy y adjuntos. **Cerrar** vuelve al panel.

### Actualizar estado

Vuelve a preguntar al servicio si está en línea y refresca el indicador
del panel.

El menú público **Foro** (Foro, Mi perfil, Mis hilos y Mis respuestas)
no incluye estas acciones.
