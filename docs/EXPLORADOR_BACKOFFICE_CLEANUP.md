# Limpieza de Backoffice - Función Duplicada

**Fecha**: 2026-02-03  
**Estado**: Documentado para ejecución  
**Archivo**: `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`

---

## ⚠️ PROBLEMA DETECTADO

Hay **2 definiciones** de `proyecciones_management_panel()` en el archivo Backoffice:

1. **Primera definición** (línea 2390-2541): 152 líneas, **placeholder sin explorador** ❌
2. **Segunda definición** (línea 2865): **versión avanzada CON explorador integrado** ✅

---

## 🎯 ACCIÓN REQUERIDA

**Eliminar la primera definición** (líneas 2390-2541) y mantener solo la segunda.

---

## 📝 COMANDO PARA ELIMINAR (ejecutar desde terminal)

```bash
# Backup del archivo
cp src/apps/6_web_backoffice/web_backoffice/web_backoffice.py src/apps/6_web_backoffice/web_backoffice/web_backoffice.py.backup_2026_02_03

# Eliminar líneas 2390-2541 (primera función duplicada)
sed -i '' '2390,2541d' src/apps/6_web_backoffice/web_backoffice/web_backoffice.py

# Verificar resultado
grep -n "^def proyecciones_management_panel" src/apps/6_web_backoffice/web_backoffice/web_backoffice.py
```

**Resultado esperado**: Solo debe aparecer 1 línea (la segunda definición, que ahora estará en línea ~2714)

---

## 🔍 VERIFICACIÓN MANUAL (alternativa si comando falla)

### Opción A - Con editor de texto:

1. Abrir: `src/apps/6_web_backoffice/web_backoffice/web_backoffice.py`
2. Ir a línea 2390
3. Seleccionar desde línea 2390 hasta línea 2541 (ambas incluidas)
4. Eliminar
5. Guardar

### Opción B - Verificar qué función quedó:

```bash
# Debe mostrar "Versión avanzada backoffice" y explorador_panel
sed -n '2714,2770p' src/apps/6_web_backoffice/web_backoffice/web_backoffice.py | head -n 20
```

**Debe contener**:
- Línea con: `"""Panel de gestión de versiones de proyecto (3 capas) - Versión avanzada backoffice."""`
- Línea con: `explorador_panel(`

---

## 📊 IMPACTO DE LA ELIMINACIÓN

- **Líneas eliminadas**: 152
- **Nueva numeración**: La segunda función (línea 2865) pasará a línea 2713
- **Funciones afectadas**: Ninguna (solo se elimina duplicado)
- **Imports afectados**: Ninguno

---

## ✅ DESPUÉS DE ELIMINAR

Continuar con:
- **PASO 7.13**: Actualizar `create_new_version()` en Backoffice
- **PASO 7.14**: Verificar import de `create_version_full`
- **PASO 7.15**: Documentar en `EXPLORADOR_PROGRESS.md`

---

**Fin del documento - Ejecutar eliminación y continuar**
