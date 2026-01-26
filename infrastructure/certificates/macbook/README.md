# Certificados SSL para desarrollo local (macbook)

Este directorio contiene los certificados SSL/TLS para el dominio `tfmmyllm.ai` en el entorno de desarrollo local (macbook).

## Archivos

- `generate_certs.sh` - Script para generar/regenerar certificados con mkcert
- `tfmmyllm.ai.pem` - Certificado público (no commitear)
- `tfmmyllm.ai-key.pem` - Clave privada (no commitear)

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

## Seguridad

⚠️ **IMPORTANTE**: 
- Los archivos `.pem` y `-key.pem` NO deben commiterse a git
- Están excluidos en `.gitignore`
- Solo para desarrollo local
- Para producción, usar Let's Encrypt o una CA comercial
