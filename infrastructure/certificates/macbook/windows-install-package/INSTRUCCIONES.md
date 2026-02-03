# Instalación de Certificado CA en Windows

Este documento explica cómo instalar el certificado CA (Certificate Authority) de mkcert en Windows para que confíe en los certificados SSL del servidor.

## 📁 Archivos Disponibles

En esta carpeta encontrarás:

- **`mkcert-rootCA.crt`** - Certificado CA en formato CRT (recomendado para Windows)
- **`mkcert-rootCA.pem`** - Certificado CA en formato PEM (alternativo)
- **`tfmmyllm.ai.pem`** - Certificado del servidor (NO instalar en cliente)
- **`tfmmyllm.ai-key.pem`** - Clave privada del servidor (NO compartir)

## 🔐 ¿Qué certificado necesito instalar?

**Solo necesitas instalar: `mkcert-rootCA.crt`**

Este es el certificado de la autoridad certificadora (CA) que generó los certificados del servidor. Una vez instalado, Windows confiará automáticamente en todos los certificados firmados por esta CA.

## 📥 Método 1: Instalación Gráfica (Recomendado)

### Paso 1: Copiar el certificado al equipo Windows

Copia el archivo `mkcert-rootCA.crt` al equipo Windows mediante:
- USB
- Compartir carpeta de red
- Email (seguro en red local)

### Paso 2: Instalar el certificado

1. **Doble clic** en el archivo `mkcert-rootCA.crt`

2. En la ventana "Certificado", haz clic en **"Instalar certificado..."**

3. Selecciona **"Equipo local"** (no "Usuario actual")
   - ⚠️ Necesitarás permisos de administrador
   - Acepta el UAC (Control de Cuentas de Usuario)

4. Selecciona **"Colocar todos los certificados en el siguiente almacén"**

5. Haz clic en **"Examinar..."**

6. **IMPORTANTE**: Selecciona **"Entidades de certificación raíz de confianza"**
   - ⚠️ NO selecciones "Personal" ni otras opciones
   - En inglés: "Trusted Root Certification Authorities"

7. Haz clic en **"Aceptar"** → **"Siguiente"** → **"Finalizar"**

8. Aparecerá advertencia de seguridad:
   ```
   ¿Desea instalar este certificado?
   ```
   - Haz clic en **"Sí"**

9. Deberías ver el mensaje:
   ```
   La importación se realizó correctamente
   ```

### Paso 3: Verificar instalación

1. Presiona `Win + R`
2. Escribe: `certmgr.msc`
3. Presiona Enter
4. Navega a: **Entidades de certificación raíz de confianza** → **Certificados**
5. Busca un certificado llamado **"mkcert [nombre]"** o similar
6. Si está ahí, ¡instalación exitosa! ✅

### Paso 4: Reiniciar navegador

Cierra y vuelve a abrir tu navegador (Chrome, Edge, Firefox) para que reconozca el nuevo certificado.

## 💻 Método 2: Instalación por Línea de Comandos (PowerShell)

Abre **PowerShell como Administrador** y ejecuta:

```powershell
# Cambiar a la carpeta donde está el certificado
cd C:\Ruta\Donde\Copiaste\

# Instalar el certificado en el almacén de CA raíz
Import-Certificate -FilePath "mkcert-rootCA.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

## 🧪 Probar el Certificado

Una vez instalado, abre tu navegador y accede a:

```
https://192.168.0.39
```

**Resultado esperado:**
- ✅ **SIN advertencia de seguridad** (candado verde/gris)
- ✅ El navegador confía en el certificado
- ✅ Conexión segura establecida

**Si aún aparece advertencia:**
- Reinicia el navegador completamente
- Verifica que instalaste en "Entidades de certificación raíz de confianza"
- Verifica que instalaste para "Equipo local", no solo "Usuario actual"

## 🔍 Ver Información del Certificado

Para ver detalles del certificado CA:

```powershell
# Ver certificado
certutil -dump mkcert-rootCA.crt

# Verificar que está instalado
Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"}
```

## ❌ Desinstalar el Certificado (si es necesario)

Si necesitas eliminar el certificado:

1. Presiona `Win + R` → `certmgr.msc`
2. Navega a: **Entidades de certificación raíz de confianza** → **Certificados**
3. Busca el certificado "mkcert"
4. Click derecho → **Eliminar**
5. Confirma la eliminación

O por PowerShell:

```powershell
# Listar certificados mkcert instalados
Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"}

# Eliminar (cambiar el Thumbprint por el real)
Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"} | Remove-Item
```

## 🌐 URLs que Funcionarán Después de Instalar

Una vez instalado el certificado, estas URLs funcionarán sin advertencias:

- `https://192.168.0.39` (Frontend)
- `https://192.168.0.39:8443` (Backoffice)
- `https://tfmmyllm.ai` (si configuraste el archivo hosts)

## ⚠️ Notas de Seguridad

1. **Solo instala este certificado en equipos de tu red local de confianza**
2. **NO compartas el certificado CA fuera de tu red**
3. **NO compartas el archivo `tfmmyllm.ai-key.pem`** (clave privada)
4. Este certificado es solo para desarrollo/testing, no para producción
5. Los certificados de mkcert caducan después de varios años

## 🔄 Renovar Certificados

Si los certificados caducan:

1. En el Mac, regenera los certificados:
   ```bash
   cd infrastructure/certificates/macbook
   ./generate_certs.sh
   ```

2. Copia el nuevo `mkcert-rootCA.crt` a Windows

3. Si el CA cambió, desinstala el antiguo e instala el nuevo

## 📞 Solución de Problemas

### Problema: Aún aparece advertencia después de instalar

**Solución:**
- Verifica que instalaste en "Entidades de certificación raíz de confianza" (no en "Personal")
- Verifica que instalaste para "Equipo local" (no solo "Usuario actual")
- Reinicia el navegador completamente
- En Chrome: ve a `chrome://restart`
- En Edge: cierra todas las ventanas y vuelve a abrir

### Problema: No puedo instalar (Error de permisos)

**Solución:**
- Ejecuta el instalador como Administrador
- Click derecho en `mkcert-rootCA.crt` → "Ejecutar como administrador"

### Problema: Firefox no confía en el certificado

Firefox usa su propio almacén de certificados:

1. Abre Firefox
2. Menú → **Configuración** → **Privacidad y Seguridad**
3. Desplázate a **Certificados** → **Ver certificados**
4. Pestaña **Autoridades**
5. **Importar...** → Selecciona `mkcert-rootCA.crt`
6. Marca: **"Confiar en esta CA para identificar sitios web"**
7. Aceptar

## 📚 Información Técnica

**Tipo de certificado:** X.509 v3
**Formato:** PEM (base64 encoded)
**Extensiones compatibles:** .crt, .pem, .cer
**Válido para:** Desarrollo local y testing
**Algoritmo:** RSA 2048 bits
**Emisor:** mkcert development CA

---

**Última actualización:** 2026-02-02
**Generado automáticamente por:** Sistema anewhope
