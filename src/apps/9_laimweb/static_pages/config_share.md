# LAIM Share / Connect

## Nodos maestro y cliente

Configuración de topologías **Share** (maestro) y **Connect** (cliente esclavo) para compartir inferencia y recursos entre equipos.

### Share (maestro)

- Estado del listener `share_api` (puerto por defecto `4322`)
- Credenciales de conexión para clientes Connect
- Política de acceso a modelos remotos

### Connect (cliente)

- URL del nodo maestro
- Prueba de conectividad y latencia
- Modo chat remoto sin Ollama local

> Solo administradores pueden modificar estos parámetros, igual que en CLI (`laim share` / `laim connect`).
