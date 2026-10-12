# Configurar Windows para laim remote

Windows 10 (version 1809 o posterior) y Windows Server 2019 o posterior incluyen OpenSSH Server como componente opcional. Cuando esta activo, **laim remote** se conecta sin WSL ni herramientas de terceros.

> **Activar automaticamente:** si esta viendo esta pagina en el **Windows que debe recibir** las conexiones, use el boton **Activar automaticamente usando LAIM** (junto al titulo). Windows pedira **UAC** (pulse Si). El proceso elevado instala el Servidor OpenSSH, arranca `sshd` y el Agente de autenticacion SSH, abre el firewall TCP 22 en **todos** los perfiles y al terminar muestra los datos (Host, IP, puerto, usuario) para registrar este equipo en otro LAIM remote (por ejemplo un Mac Silicon). Requiere sesion **admin** LAIM.

Tambien puede hacerlo a mano: **Configuracion → Aplicaciones → Caracteristicas opcionales → Agregar una caracteristica → Servidor OpenSSH** (y, si lo necesita, Cliente OpenSSH). Luego `services.msc`: **Servidor OpenSSH** y **Agente de autenticacion SSH** → Inicio **Automatico** → Iniciar.

## 1 — Instalar OpenSSH Server (PowerShell como administrador)

Requiere Windows 10 v1809+ o Windows Server 2019+.

```powershell
# Verificar disponibilidad
Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'

# Instalar
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```

## 2 — Iniciar el servicio y habilitarlo en el arranque

```powershell
Start-Service sshd
Set-Service -Name sshd -StartupType 'Automatic'
```

## 3 — Abrir el firewall de Windows

La regla se crea automaticamente al instalar. Verifique o creela a mano:

```powershell
# Verificar que la regla existe
Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP'

# Si no existe, crearla
New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' `
    -DisplayName 'OpenSSH SSH Server (sshd)' `
    -Enabled True -Direction Inbound -Protocol TCP `
    -Action Allow -LocalPort 22 -Profile Any
```

## 4 — Establecer PowerShell como shell por defecto (recomendado)

Sin este paso, el terminal abre `cmd.exe` en lugar de PowerShell.

```powershell
# PowerShell 7 (recomendado — instalar desde https://aka.ms/powershell)
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' `
    -Name DefaultShell `
    -Value 'C:\Program Files\PowerShell\7\pwsh.exe' `
    -PropertyType String -Force

# Alternativa: Windows PowerShell 5 (incluido en Windows)
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' `
    -Name DefaultShell `
    -Value 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' `
    -PropertyType String -Force
```

## 5 — Autenticacion con clave RSA/Ed25519 (opcional, recomendada)

Cuentas normales: `%USERPROFILE%\.ssh\authorized_keys`

```powershell
$pubKey = "<contenido de id_ed25519.pub>"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.ssh"
Add-Content -Path "$env:USERPROFILE\.ssh\authorized_keys" -Value $pubKey
```

Cuentas administradoras: ruta distinta (obligatorio en Windows):

```powershell
$adminAuth = "C:\ProgramData\ssh\administrators_authorized_keys"
Add-Content -Path $adminAuth -Value $pubKey
# Corregir permisos (obligatorio)
icacls $adminAuth /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
```

> **Importante:** para cuentas del grupo Administrators, OpenSSH lee **solo** de `C:\ProgramData\ssh\administrators_authorized_keys`, no de `%USERPROFILE%`.

## 6 — Verificar la conexion antes de registrar en LAIM

```powershell
ssh <usuario-windows>@<host-o-ip>
# Resultado esperado:  PS C:\Users\<usuario>>
```

## 7 — Registrar en LAIM

En `laim config` → Gestion de equipos remotos (o Configuracion web → Equipos):

| Campo | Valor |
|-------|-------|
| **Host** | hostname / FQDN (ej. `winserver.local`) |
| **IP Directa** | IP del equipo (reserva si falla el DNS) |
| **Puerto** | `22` |
| **Usuario remoto** | nombre de usuario Windows |
| **Password / clave RSA** | se guarda cifrado en `laim.dat` |
| **Protocolo** | `ssh` |

## Diagnostico

| Sintoma | Causa probable | Solucion |
|---------|----------------|----------|
| Connection refused (puerto 22) | sshd no esta en marcha | `Start-Service sshd` |
| Permission denied (publickey) — admin | Ruta de authorized_keys incorrecta | Usar `C:\ProgramData\ssh\administrators_authorized_keys` |
| El shell abre cmd.exe en vez de PowerShell | Falta la clave de registro DefaultShell | Ver el paso 4 — `New-ItemProperty` en `HKLM:\SOFTWARE\OpenSSH` |
| Bad permissions en authorized_keys | ACL de Windows demasiado permisiva | Ejecutar `icacls` del paso 5 |
| Timeout desde la LAN | La regla solo aplica al perfil Dominio (un error habitual) | Usar `-Profile Any` o el boton automatico de LAIM |
| Caracteres UTF-8 ilegibles en el terminal web | La pagina de codigos de PowerShell no es UTF-8 | Anadir `chcp 65001` al perfil de PowerShell |

Una vez registrado, use `laim remote` o la pestana Acceso remoto en `laim web`.

## 8 — Malla Headscale / Tailscale (equipos en otra red)

OpenSSH resuelve **quien** puede entrar por el puerto 22. La **malla** resuelve **como llegar** cuando Windows no esta en la misma LAN que el LAIM que pregunta.

1. En el LAIM **coordinador** (Linux o Mac): Headscale en marcha (`:8080`) y **Este LAIM es el coordinador** (`mesh_api` **:4324**).
2. En este Windows:
   - **Con LAIM:** Config › malla › Cliente Tailscale › Instalar (MSI silencioso) › Solicitar unirse › en el coordinador **Aprobar** › **Aplicar union**. Debe aparecer IP `100.x` y el nodo en **Nodos conectados** (no basta el ACK `validated`).
   - **Sin LAIM:** instale el cliente Tailscale y `tailscale up --login-server http://<coordinador>:8080 --authkey <preauth>`.
3. En el LAIM que administra (p. ej. Mac Silicon): Equipos → este Windows → `connection_mode=tailscale` y `tailscale_ip`. **Sincronizar IPs**.
4. SSH, chat (selector de equipo) y **Suggestions** en `laim remote` usan `100.x`. El puerto 22 sigue haciendo falta en Windows (pasos 1–3 y firewall **Any**).

No mezcle el daemon Tailscale con `login.tailscale.com` y Headscale a la vez. **Aplicar union** reintenta `--force-reauth` si el cliente ya tenia otro login-server.

## 9 — IA: chat y Suggestions sobre SSH

Con el equipo registrado y SSH vivo:

- **Chat:** elija el Windows como destino. Las preguntas de sistema (`remotesystem`) se ejecutan **en ese host** por SSH (disco, procesos, red, `ollama list` si existe).
- **`laim remote`:** terminal interactiva; **Suggestions** usa los mismos orquestadores Go que el chat (no reinterpreta tablas en Python).
- No invente IPs ni RAM en la UI. Si la malla no tiene `100.x`, use LAN solo si ambos estan en la misma red.

Manual de malla: Ayuda › **Red Mesh WireGuard con Headscale**.

## Administrador — Firewall y puertos LAIM (Internal › Local)

Configuracion → Internal → Local → **Firewall y puertos LAIM** lista **OpenSSH Server (este host)** como TCP **22** entrante (`OpenSSH-Server-In-TCP`) cuando `sshd` esta en marcha. **Reparar** no abre el puerto 22 en `laim init` si sshd no esta activo. Tras la activacion automatica, actualice el panel: la fila debe quedar OK (o Reparar si falta la regla). Use perfil **Any**, no solo Dominio (causa habitual de timeout en LAN; la guia de [Xataka sobre SSH en Windows 11](https://www.xataka.com/basics/ssh-windows-11-que-como-configurarlo-paso-a-paso) cubre `services.msc` — LAIM ademas instala la caracteristica opcional y abre todos los perfiles).
