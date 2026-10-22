# Configuración general

## Operación

Los administradores abren desde aquí **Usuarios** y **Registro**. Cada botón
abre una ventana modal con las mismas operaciones que laim_maintenance:
cuentas del portal e inventario de instalaciones de este entorno.

El navegador no llama a `/api/support/*`. laimweb acuña la credencial en el
servidor y reutiliza `/laim/support/users` y `/laim/support/installations`.

## Parámetros del portal LAIM

Desde esta sección los **administradores** pueden revisar la configuración
global del portal: identidad visual, enlaces de servicio y preferencias de
la organización. Esas fichas siguen siendo de consulta.

### Áreas de consulta

| Área | Descripción |
|------|-------------|
| **Organización** | Datos de la organización LAIM asociada al portal |
| **Servicios** | URLs de middleware, broker y backend (solo lectura en producción) |
| **Preferencias** | Idioma, zona horaria y opciones de notificación |
| **Mantenimiento** | Modo mantenimiento y mensajes informativos para usuarios |
