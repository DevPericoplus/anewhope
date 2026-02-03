# Solución Rápida: Certificado "No Seguro" en Windows

## ✅ Estado Actual

Los certificados del servidor han sido **regenerados** incluyendo las IPs de red local:
- ✅ `192.168.0.39`
- ✅ `192.168.0.101`
- ✅ Firmados por la CA actual de mkcert
- ✅ Nginx recargado con los nuevos certificados

## 🔧 Pasos en Windows

### 1. Instalar el Certificado CA (Si aún no lo hiciste)

**Opción A: Instalador Automático**
```powershell
# Click derecho en: instalar_certificado.ps1
# → "Ejecutar con PowerShell como Administrador"
```

**Opción B: Instalación Manual**
1. Doble clic en `mkcert-rootCA.crt`
2. "Instalar certificado..." → "Equipo local" (requiere admin)
3. "Colocar todos los certificados en el siguiente almacén"
4. **IMPORTANTE**: Seleccionar **"Entidades de certificación raíz de confianza"**
5. Finalizar → Aceptar advertencia

### 2. Verificar que se Instaló Correctamente

```powershell
# Abrir PowerShell y ejecutar:
Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"}
```

**Resultado esperado:**
```
Subject      : CN=mkcert administrator@...
Thumbprint   : ...
NotAfter     : 26/01/2036
```

Si NO aparece nada:
- ❌ El certificado NO está instalado
- Vuelve al paso 1 y asegúrate de instalar en "Entidades de certificación raíz de confianza"
- NO en "Personal" ni otras opciones

### 3. Reiniciar Navegador COMPLETAMENTE

**Chrome/Edge:**
- Cierra TODAS las ventanas del navegador
- Abre el Administrador de Tareas → Finaliza todos los procesos de Chrome/Edge
- Vuelve a abrir el navegador

**Alternativa rápida en Chrome:**
- Escribe en la barra: `chrome://restart`

### 4. Limpiar Caché SSL del Navegador

**Chrome/Edge:**
1. `chrome://settings/security`
2. Scroll abajo → "Administrar certificados"
3. Pestaña "Entidades de certificación raíz de confianza"
4. Verifica que aparece "mkcert"

### 5. Acceder a la URL

```
https://192.168.0.39
```

**Resultado esperado:**
- ✅ Candado verde/gris (sin advertencia)
- ✅ "Conexión segura"

## 🔍 Diagnóstico: Si Aún Marca "No Seguro"

### Verificar que el certificado está bien instalado

```powershell
# Listar certificados instalados en el almacén Root
certutil -store Root | findstr mkcert
```

### Ver detalles del certificado del servidor desde Windows

```powershell
# Probar conexión y ver certificado
$url = "https://192.168.0.39"
$request = [System.Net.WebRequest]::Create($url)
$request.GetResponse() | Out-Null
```

Si falla con error SSL, el certificado CA no está correctamente instalado.

### Verificar en el navegador

1. Accede a `https://192.168.0.39`
2. Click en el **candado rojo** o advertencia
3. "Certificado" → "Ver certificado"
4. Pestaña "Ruta de certificación"

**Esperado:**
```
mkcert administrator@... (raíz)
  └─ *.tfmmyllm.ai (hoja)
```

**Si dice "No confiable" en la raíz:**
- El certificado CA NO está instalado correctamente
- Reinstalar siguiendo el paso 1 cuidadosamente

## ⚠️ Problemas Comunes

### Problema 1: Instalé el certificado pero sigue sin funcionar

**Causa:** Instalaste en el almacén incorrecto (ej: "Personal")

**Solución:**
1. `Win + R` → `certmgr.msc`
2. "Personal" → "Certificados" → Buscar y **eliminar** el certificado mkcert si está ahí
3. "Entidades de certificación raíz de confianza" → Verificar que el certificado está aquí
4. Si no está, reinstalar desde el paso 1

### Problema 2: Chrome sigue mostrando advertencia

**Causa:** Caché del navegador

**Solución:**
```
1. Ctrl + Shift + Delete (Borrar datos de navegación)
2. Seleccionar "Imágenes y archivos en caché"
3. Seleccionar "Todo el tiempo"
4. Borrar datos
5. chrome://restart
```

### Problema 3: El certificado dice "Emitido para: tfmmyllm.ai"

**Causa:** Estás accediendo por IP pero el certificado ahora SÍ incluye las IPs

**Solución:**
Este YA NO es un problema. Los certificados nuevos incluyen:
- ✅ `192.168.0.39`
- ✅ `192.168.0.101`

Si aún aparece error, verifica que nginx se recargó:
```bash
# En el Mac:
nginx -s reload
```

### Problema 4: Firefox no confía en el certificado

**Causa:** Firefox usa su propio almacén de certificados

**Solución:**
1. Firefox → Menú → Configuración
2. Privacidad y Seguridad → Certificados → "Ver certificados"
3. Pestaña "Autoridades"
4. "Importar..." → Seleccionar `mkcert-rootCA.crt`
5. Marcar "Confiar en esta CA para identificar sitios web"
6. Aceptar

## ✅ Checklist Final

Antes de contactar soporte, verifica:

- [ ] Certificado CA instalado en "Entidades de certificación raíz de confianza"
- [ ] Verificado con `certmgr.msc` que el certificado mkcert está presente
- [ ] Navegador reiniciado completamente (cerrar todas las ventanas)
- [ ] Caché del navegador borrada
- [ ] URL correcta: `https://192.168.0.39` (no http, no localhost)
- [ ] Accediendo desde la misma red local (192.168.0.x)

## 📞 Si Nada Funciona

1. **Desinstalar el certificado:**
   - `certmgr.msc` → Buscar mkcert → Click derecho → Eliminar

2. **Reinstalar desde cero:**
   - Ejecutar `instalar_certificado.ps1` como administrador
   - O seguir pasos manuales cuidadosamente

3. **Verificar con PowerShell:**
   ```powershell
   # Ver si el certificado está instalado
   Get-ChildItem -Path Cert:\LocalMachine\Root | Where-Object {$_.Subject -like "*mkcert*"} | Format-List Subject, Thumbprint, NotAfter
   ```

4. **Probar con otro navegador:**
   - Si funciona en Edge pero no en Chrome → Problema de caché
   - Si no funciona en ninguno → Certificado CA no instalado correctamente

---

**Fecha:** 2026-02-02
**Certificados válidos hasta:** 2 Mayo 2028
**Versión:** 1.0
