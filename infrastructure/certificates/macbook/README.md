# Certificados SSL para desarrollo local (macbook)

Este directorio contiene los certificados SSL/TLS para el dominio `tfmmyllm.ai` en el entorno de desarrollo local (macbook).

## Archivos

### Certificados del servidor
- `generate_certs.sh` - Script para generar/regenerar certificados con mkcert
- `tfmmyllm.ai.pem` - Certificado público del servidor (no commitear)
- `tfmmyllm.ai-key.pem` - Clave privada del servidor (no commitear)

### Certificado CA para equipos clientes
- `mkcert-rootCA.crt` - Certificado CA en formato CRT (para Windows)
- `mkcert-rootCA.pem` - Certificado CA en formato PEM (para Linux/Mac)
- `prepare_for_windows.sh` - Script para preparar paquete de instalación para Windows
- `WINDOWS_INSTALL.md` - Guía detallada de instalación en Windows
- `windows-install-package/` - Paquete completo con certificado e instalador para Windows

## Generar certificados

### Requisitos previos

**⚠️ IMPORTANTE**: mkcert debe estar instalado antes de continuar.

1. **Verificar si mkcert está instalado:**
   ```bash
   command -v mkcert
   ```

2. **Si no está instalado, instalarlo:**
   ```bash
   # Instalar mkcert y nss con Homebrew
   brew install mkcert nss
   
   # Instalar la Certificate Authority (CA) local
   mkcert -install
   ```
   
   El comando `mkcert -install` es **obligatorio** y debe ejecutarse solo una vez. Instala una CA local en tu sistema para que los navegadores confíen en los certificados generados.

3. **Configurar `/etc/hosts`:**
   ```bash
   echo "127.0.0.1       tfmmyllm.ai" | sudo tee -a /etc/hosts
   ```

### Generación

```bash
./generate_certs.sh
```

## Dominios incluidos

El certificado incluye:
- `tfmmyllm.ai` (dominio principal)
- `*.tfmmyllm.ai` (wildcard para subdominios)
- `localhost`
- `127.0.0.1`
- `::1` (IPv6 localhost)

## Validez

Los certificados generados por mkcert tienen una validez predeterminada que depende de la versión:
- Versiones recientes: ~10 años (3650 días)
- Algunas versiones: 825 días

Para verificar la fecha de expiración:
```bash
openssl x509 -in tfmmyllm.ai.pem -noout -dates
```

## Renovación

Si el certificado expira o necesitas regenerarlo:

```bash
# Regenerar con el script
./generate_certs.sh

# O manualmente
mkcert -key-file tfmmyllm.ai-key.pem \
       -cert-file tfmmyllm.ai.pem \
       tfmmyllm.ai "*.tfmmyllm.ai" localhost 127.0.0.1 ::1
```

Después de regenerar, reiniciar nginx:
```bash
cd ../../..
./deploy_nginx_macbook.sh
```

## Problemas de confianza

Si los navegadores no confían en el certificado:

```bash
# Reinstalar la CA de mkcert
mkcert -uninstall
mkcert -install

# Regenerar certificados
./generate_certs.sh
```

## Uso en nginx

Los certificados se referencian con **rutas absolutas** en la configuración de nginx.

**Ubicación en el sistema:**
```
/Users/administrator/develop/anewhope/infrastructure/certificates/macbook/
├── tfmmyllm.ai.pem       # Certificado público
└── tfmmyllm.ai-key.pem   # Clave privada
```

**Configuración en `infrastructure/servers/macbook/nginx/nginx.conf`:**

```nginx
http {
    # Configuración SSL global
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Servidor HTTPS (puerto 443)
    server {
        listen 443 ssl;
        server_name tfmmyllm.ai *.tfmmyllm.ai;
        
        # Certificados SSL - Rutas absolutas desde la raíz del proyecto
        ssl_certificate /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai.pem;
        ssl_certificate_key /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/tfmmyllm.ai-key.pem;
        
        # Configuración SSL adicional
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        
        # ... configuración de locations
    }
}
```

**¿Por qué rutas absolutas?**

Las rutas absolutas se usan porque:
1. Nginx se instala en `/usr/local/etc/nginx/` (Homebrew)
2. Los certificados están en el directorio del proyecto
3. Evita problemas con rutas relativas al iniciar nginx
4. Facilita la identificación de la ubicación de los certificados

**Verificar certificados en nginx:**

```bash
# Ver información del certificado usado
echo | openssl s_client -connect tfmmyllm.ai:443 2>/dev/null | openssl x509 -noout -dates -subject

# Verificar archivos en el sistema
ls -lh /Users/administrator/develop/anewhope/infrastructure/certificates/macbook/
```

## Compartir certificados con otros equipos (Windows/Linux)

### Problema: Advertencias de certificado en equipos externos

Cuando accedes al servidor desde otros equipos en la red local (por IP), los navegadores mostrarán advertencia de certificado porque no confían en la CA de mkcert que generó los certificados.

### Solución: Instalar el certificado CA en equipos clientes

Para que otros equipos confíen en los certificados, debes instalar el **certificado CA raíz** de mkcert en esos equipos.

#### Archivos disponibles

En esta carpeta encontrarás:

- **`mkcert-rootCA.crt`** - Certificado CA en formato CRT (para Windows)
- **`mkcert-rootCA.pem`** - Certificado CA en formato PEM (para Linux/Mac)
- **`windows-install-package/`** - Paquete completo para instalación en Windows

#### Preparar paquete para Windows

Ejecuta el script para crear un paquete de instalación completo:

```bash
./prepare_for_windows.sh
```

Este script crea la carpeta `windows-install-package/` con:
- `mkcert-rootCA.crt` - Certificado CA
- `instalar_certificado.ps1` - Script PowerShell para instalación automática
- `LEEME.txt` - Instrucciones rápidas
- `INSTRUCCIONES.md` - Guía completa con solución de problemas

#### Instalación en Windows

**Método 1: Instalación Automática (Recomendado)**

1. Copia la carpeta `windows-install-package` al equipo Windows
2. Click derecho en `instalar_certificado.ps1`
3. Selecciona "Ejecutar con PowerShell como Administrador"
4. Sigue las instrucciones en pantalla
5. Reinicia el navegador

**Método 2: Instalación Manual**

1. Doble clic en `mkcert-rootCA.crt`
2. Click en "Instalar certificado..."
3. Selecciona "Equipo local" (requiere permisos de administrador)
4. Selecciona "Colocar todos los certificados en el siguiente almacén"
5. Click en "Examinar..." → Selecciona "Entidades de certificación raíz de confianza"
6. Finalizar → Aceptar la advertencia de seguridad
7. Reinicia el navegador

**Verificar instalación:**
- Presiona `Win + R` → Escribe `certmgr.msc`
- Navega a "Entidades de certificación raíz de confianza" → "Certificados"
- Busca el certificado "mkcert"

#### Instalación en Linux

```bash
# Ubuntu/Debian
sudo cp mkcert-rootCA.pem /usr/local/share/ca-certificates/mkcert-rootCA.crt
sudo update-ca-certificates

# Fedora/RHEL/CentOS
sudo cp mkcert-rootCA.pem /etc/pki/ca-trust/source/anchors/mkcert-rootCA.crt
sudo update-ca-trust

# Firefox (usa su propio almacén)
# Configuración → Privacidad y Seguridad → Certificados → Ver certificados
# Pestaña "Autoridades" → Importar → Seleccionar mkcert-rootCA.crt
```

#### Instalación en macOS (otros equipos Mac)

```bash
# Copiar el certificado
cp mkcert-rootCA.pem ~/Desktop/

# Doble clic en el archivo → Se abre "Acceso a llaveros"
# Seleccionar "Sistema" en la lista de llaveros
# Buscar el certificado "mkcert" → Doble clic
# Expandir "Confianza" → Seleccionar "Confiar siempre"
```

#### Resultado esperado

Después de instalar el certificado CA:
- ✅ Sin advertencias de seguridad al acceder por HTTPS
- ✅ Candado verde/gris en el navegador
- ✅ Conexión segura establecida

**URLs que funcionarán:**
- `https://192.168.0.39` (o la IP del servidor)
- `https://192.168.0.39:8443`
- `https://tfmmyllm.ai` (si configuraste `/etc/hosts`)

#### Regenerar certificado CA

Si cambias el certificado CA de mkcert o lo reinstalas:

```bash
# 1. Reinstalar CA de mkcert (genera nueva CA)
mkcert -uninstall
mkcert -install

# 2. Regenerar certificados del servidor
./generate_certs.sh

# 3. Preparar nuevo paquete para Windows
./prepare_for_windows.sh

# 4. Reinstalar en todos los equipos clientes
```

#### Notas de seguridad

⚠️ **IMPORTANTE al compartir certificados CA:**
- Solo instala en equipos de tu red local de confianza
- NO compartas el certificado CA fuera de tu red local
- NO compartas NUNCA el archivo `rootCA-key.pem` (clave privada del CA)
- Estos certificados son solo para desarrollo, no para producción

#### Documentación adicional

Para instrucciones detalladas y solución de problemas, consulta:
- `windows-install-package/INSTRUCCIONES.md` - Guía completa para Windows
- `WINDOWS_INSTALL.md` - Documentación técnica completa

## Seguridad

⚠️ **IMPORTANTE**:
- Los archivos `.pem` y `-key.pem` NO deben commiterse a git
- Están excluidos en `.gitignore`
- Solo para desarrollo local
- Para producción, usar Let's Encrypt o una CA comercial
- **NO compartir NUNCA** el archivo `tfmmyllm.ai-key.pem` (clave privada del servidor)
- **NO compartir** el archivo `rootCA-key.pem` de mkcert (ubicado en `~/Library/Application Support/mkcert/`)
