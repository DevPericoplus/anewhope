# Diseño de Conmutación Frontend ↔ Backoffice

## Resumen ejecutivo

Sistema de conmutación (switching) entre aplicación web pública (`5_web_frontend`) y backoffice administrativo (`6_web_backoffice`) usando sesión compartida mediante cookies seguras y JWT.

## Arquitectura

### Componentes

```
┌────────────────────────────────────────────────────────┐
│              Nginx (Puerto 443 HTTPS)                  │
│              https://tfmmyllm.ai                       │
└───────────────┬──────────────────┬─────────────────────┘
                │                  │
       ┌────────▼────────┐   ┌────▼──────────────┐
       │ Frontend Público│   │ Backoffice Admin  │
       │    (/)          │   │  (/backoffice/)   │
       │ Puerto 8005     │   │  Puerto 8006      │
       │ .venv_frontend  │   │ .venv_backoffice  │
       └────────┬────────┘   └────┬──────────────┘
                │                  │
                └────────┬─────────┘
                         │
              ┌──────────▼────────────┐
              │   Sesión Compartida   │
              │   - Cookie segura     │
              │   - JWT tokens        │
              │   - sessions.json     │
              │   - MariaDB users     │
              └───────────────────────┘
```

### URLs

- **Frontend público**: `https://tfmmyllm.ai/`
- **Backoffice**: `https://tfmmyllm.ai/backoffice/`
- **API Frontend**: `https://tfmmyllm.ai/_event` (WebSocket)
- **API Backoffice**: `https://tfmmyllm.ai/backoffice/_event` (WebSocket)

## Flujo de autenticación y conmutación

### 1. Login inicial (Frontend público)

```
Usuario → https://tfmmyllm.ai/
       ↓
  [Login] email + password + OTP
       ↓
  Middleware valida credenciales
       ↓
  Genera JWT (access + refresh)
       ↓
  Crea sesión en sessions.json
       ↓
  Set-Cookie: session_token=JWT
             domain=tfmmyllm.ai
             path=/
             secure=true
             httponly=true
             samesite=strict
       ↓
  Frontend carga datos de usuario
       ↓
  Si user.training_create == true:
    → Muestra botón "Backoffice"
```

### 2. Conmutación a Backoffice

```
Usuario click "Backoffice"
       ↓
  window.location.href = "/backoffice/"
       ↓
  Navegador envía cookie session_token
       ↓
  Nginx proxy → 127.0.0.1:8006
       ↓
  Backoffice lee cookie
       ↓
  Valida JWT contra middleware
       ↓
  Verifica permiso training_create
       ↓
  Si válido: carga UI backoffice
  Si inválido: redirect a "/"
```

### 3. Conmutación de vuelta a Frontend

```
Usuario click "Desconectar" en Backoffice
       ↓
  Opción A: Logout completo
    → Invalida sesión
    → Redirect a "/"
    
  Opción B: Solo cambio de vista
    → window.location.href = "/"
    → Mantiene sesión activa
```

## Estructura de archivos

```
src/apps/
├── 5_web_frontend/
│   ├── .venv_frontend313/          # Entorno virtual frontend
│   ├── rxconfig.py                 # backend_port=8005
│   ├── run.sh
│   ├── web_frontend/
│   │   ├── web_frontend.py         # UI verde
│   │   ├── components/
│   │   │   └── auth_session.py     # Helper sesión compartida
│   │   └── state/
│   │       └── shared_session.py   # State compartido
│   └── requirements.txt
│
└── 6_web_backoffice/
    ├── .venv_backoffice313/        # Entorno virtual backoffice (clon)
    ├── rxconfig.py                 # backend_port=8006
    ├── run.sh
    ├── web_backoffice/
    │   ├── web_backoffice.py       # UI naranja, sin "Acceso Usuario"
    │   ├── components/
    │   │   └── auth_session.py     # Mismo helper
    │   └── state/
    │       └── shared_session.py   # State compartido
    └── requirements.txt
```

## Implementación de sesión compartida

### Archivo: `src/2_shared_application/session_manager.py`

```python
"""
Gestor de sesión compartida entre frontend y backoffice
"""
from __future__ import annotations

import os
from typing import Optional
from datetime import datetime, timedelta
import jwt

# Importar configuración de JWT desde middleware
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"


class SessionManager:
    """Maneja sesión compartida entre frontend y backoffice"""
    
    @staticmethod
    def validate_session_token(token: str) -> Optional[dict]:
        """
        Valida token JWT y retorna payload si es válido
        
        Returns:
            dict con user_id, organization_id, session_id, etc. o None si inválido
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            
            # Verificar expiración
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                return None
            
            return payload
            
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def check_permission(user_data: dict, permission: str) -> bool:
        """
        Verifica si el usuario tiene un permiso específico
        
        Args:
            user_data: dict con información del usuario (incluye permissions)
            permission: nombre del permiso (ej: "training_create")
        
        Returns:
            True si tiene el permiso, False en caso contrario
        """
        permissions = user_data.get("permissions", {})
        return permissions.get(permission, False)
    
    @staticmethod
    def can_access_backoffice(user_data: dict) -> bool:
        """
        Determina si el usuario puede acceder al backoffice
        
        Criterio: tener training_create = true
        """
        return SessionManager.check_permission(user_data, "training_create")
```

### Archivo: `src/apps/5_web_frontend/web_frontend/state/session_state.py`

```python
"""
State de sesión compartida para frontend
"""
import reflex as rx
from typing import Optional
import os
import sys

# Cargar helper de sesión compartida
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, _repo_root)

from src.2_shared_application.session_manager import SessionManager


class SessionState(rx.State):
    """State compartido para manejar sesión"""
    
    # Datos del usuario
    user_id: int = 0
    organization_id: int = 0
    user_name: str = ""
    user_email: str = ""
    is_logged_in: bool = False
    
    # Permisos
    can_access_backoffice: bool = False
    
    # JWT tokens
    access_token: str = ""
    refresh_token: str = ""
    session_id: str = ""
    
    def load_session_from_cookie(self):
        """
        Lee cookie session_token y carga datos de usuario
        """
        # En Reflex, acceder a cookies desde el navegador requiere JavaScript
        # Ver método alternativo en on_load del componente
        pass
    
    def validate_and_load_session(self, token: str):
        """
        Valida token JWT y carga datos en el state
        """
        user_data = SessionManager.validate_session_token(token)
        
        if user_data:
            self.user_id = user_data.get("user_id", 0)
            self.organization_id = user_data.get("organization_id", 0)
            self.user_name = user_data.get("user_name", "")
            self.user_email = user_data.get("email", "")
            self.is_logged_in = True
            self.session_id = user_data.get("session_id", "")
            self.access_token = token
            
            # Verificar permisos
            self.can_access_backoffice = SessionManager.can_access_backoffice(user_data)
        else:
            self.clear_session()
    
    def clear_session(self):
        """Limpia la sesión"""
        self.user_id = 0
        self.organization_id = 0
        self.user_name = ""
        self.user_email = ""
        self.is_logged_in = False
        self.can_access_backoffice = False
        self.access_token = ""
        self.refresh_token = ""
        self.session_id = ""
    
    def go_to_backoffice(self):
        """Redirige al backoffice"""
        if self.can_access_backoffice:
            return rx.redirect("/backoffice/")
        else:
            return rx.window_alert("No tienes permisos para acceder al backoffice")
```

### Componente: Botón de conmutación en Frontend

```python
"""
Componente de navegación con botón backoffice
"""
import reflex as rx
from .state.session_state import SessionState


def navigation_bar():
    """Barra de navegación con botón Backoffice"""
    return rx.hstack(
        # ... otros elementos ...
        
        # Botón Backoffice (solo visible si tiene permiso)
        rx.cond(
            SessionState.can_access_backoffice,
            rx.button(
                "🔧 Backoffice",
                on_click=SessionState.go_to_backoffice,
                color_scheme="orange",
                variant="solid",
            ),
        ),
        
        # Botón Desconectar
        rx.button(
            "Desconectar",
            on_click=SessionState.logout,
            color_scheme="red",
            variant="outline",
        ),
        
        spacing="4",
        align="center",
    )
```

### Archivo: `src/apps/6_web_backoffice/web_backoffice/state/session_state.py`

```python
"""
State de sesión para backoffice (mismo que frontend)
"""
# Importar el mismo SessionState desde 2_shared_application
# O duplicar el código con pequeñas variaciones si es necesario
```

### Componente: Botón de retorno en Backoffice

```python
"""
Componente de navegación en backoffice
"""
import reflex as rx
from .state.session_state import SessionState


def backoffice_navigation():
    """Barra de navegación en backoffice"""
    return rx.hstack(
        rx.heading("Backoffice", size="6", color="orange"),
        
        rx.spacer(),
        
        # Botón para volver al frontend
        rx.button(
            "← Volver al Frontend",
            on_click=lambda: rx.redirect("/"),
            color_scheme="orange",
            variant="outline",
        ),
        
        # Botón Desconectar
        rx.button(
            "Desconectar",
            on_click=SessionState.logout,
            color_scheme="red",
            variant="solid",
        ),
        
        width="100%",
        padding="1em",
        background_color="#FF8C00",  # Naranja
    )
```

## Configuración Reflex

### Frontend: `src/apps/5_web_frontend/rxconfig.py`

```python
import reflex as rx

config = rx.Config(
    app_name="web_frontend",
    db_url="sqlite:///reflex.db",
    env=rx.Env.PROD,
    backend_port=8005,
    api_url="https://tfmmyllm.ai",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
```

### Backoffice: `src/apps/6_web_backoffice/rxconfig.py`

```python
import reflex as rx

config = rx.Config(
    app_name="web_backoffice",
    db_url="sqlite:///reflex_backoffice.db",  # BD separada
    env=rx.Env.PROD,
    backend_port=8006,
    api_url="https://tfmmyllm.ai/backoffice",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
```

## Script de clonación

### `scripts/clone_frontend_to_backoffice.sh`

```bash
#!/bin/bash
# Clona frontend a backoffice con cambios específicos

set -e

echo "=================================="
echo "CLONANDO FRONTEND → BACKOFFICE"
echo "=================================="

# Paso 1: Copiar directorio completo
echo "📁 Copiando estructura..."
cp -R src/apps/5_web_frontend src/apps/6_web_backoffice

# Paso 2: Cambiar nombres de archivos y carpetas
cd src/apps/6_web_backoffice
mv web_frontend web_backoffice

# Paso 3: Actualizar rxconfig.py
cat > rxconfig.py << 'EOF'
import reflex as rx

config = rx.Config(
    app_name="web_backoffice",
    db_url="sqlite:///reflex_backoffice.db",
    env=rx.Env.PROD,
    backend_port=8006,
    api_url="https://tfmmyllm.ai/backoffice",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
EOF

# Paso 4: Renombrar entorno virtual
mv .venv_frontend313 .venv_backoffice313 2>/dev/null || echo "Entorno virtual no encontrado"

# Paso 5: Cambiar colores verde → naranja en archivos Python
echo "🎨 Cambiando colores verde → naranja..."
find web_backoffice -name "*.py" -type f -exec sed -i '' \
    -e 's/#00FF00/#FF8C00/g' \
    -e 's/#0f0/#FF8C00/g' \
    -e 's/green/orange/g' \
    -e 's/color_scheme="green"/color_scheme="orange"/g' \
    {} +

# Paso 6: Eliminar panel "Acceso de Usuario"
echo "🗑️  Eliminando panel 'Acceso de Usuario'..."
# (Esto requiere edición manual según la estructura específica)

# Paso 7: Actualizar imports
find web_backoffice -name "*.py" -type f -exec sed -i '' \
    -e 's/from web_frontend/from web_backoffice/g' \
    -e 's/web_frontend\./web_backoffice\./g' \
    {} +

echo "✅ Clonación completada"
echo ""
echo "Próximos pasos:"
echo "1. Crear entorno virtual: python3.13 -m venv .venv_backoffice313"
echo "2. Activar: source .venv_backoffice313/bin/activate"
echo "3. Instalar: pip install -r requirements.txt"
echo "4. Eliminar panel 'Acceso de Usuario' manualmente"
echo "5. Ejecutar: reflex run --env prod"
```

## Seguridad

### Cookie segura

```javascript
// Configuración de cookie desde middleware (Python)
response.set_cookie(
    key="session_token",
    value=jwt_token,
    domain="tfmmyllm.ai",    # Compartida en todo el dominio
    path="/",                # Accesible desde cualquier ruta
    secure=True,             # Solo HTTPS
    httponly=True,           # No accesible desde JavaScript
    samesite="strict",       # Protección CSRF
    max_age=3600             # 1 hora
)
```

### Validación de permisos

```python
# En backoffice, verificar en cada carga de página
def on_load_backoffice():
    """Verificar acceso al cargar backoffice"""
    if not SessionState.is_logged_in:
        return rx.redirect("/")
    
    if not SessionState.can_access_backoffice:
        return rx.redirect("/")
    
    # Usuario autorizado, continuar
```

## Testing

### Test de conmutación

```python
# src/apps/6_web_backoffice/tests/test_switching.py

def test_frontend_to_backoffice_switch():
    """Test conmutación frontend → backoffice"""
    # 1. Login en frontend
    # 2. Verificar cookie session_token
    # 3. Click botón "Backoffice"
    # 4. Verificar redirect a /backoffice/
    # 5. Verificar cookie presente
    # 6. Verificar UI backoffice cargada

def test_backoffice_without_permission():
    """Test acceso denegado sin permisos"""
    # 1. Login usuario sin training_create
    # 2. Intentar acceder a /backoffice/
    # 3. Verificar redirect a /
    # 4. Verificar mensaje de error

def test_backoffice_to_frontend_return():
    """Test retorno backoffice → frontend"""
    # 1. Usuario en backoffice
    # 2. Click "Volver al Frontend"
    # 3. Verificar redirect a /
    # 4. Verificar sesión mantenida
```

## Monitoreo

### Logs

```python
# Log de conmutaciones en middleware_activity.log
[2026-01-26 10:30:15] USER_SWITCH: user_id=1, from=frontend, to=backoffice
[2026-01-26 10:45:22] USER_SWITCH: user_id=1, from=backoffice, to=frontend
[2026-01-26 10:46:10] LOGOUT: user_id=1, from=frontend
```

## Diagrama de secuencia completo

```
Usuario  Frontend(8005)  Nginx(443)  Backoffice(8006)  Middleware(8007)

  │         │             │             │                │
  ├─Login──>│             │             │                │
  │         ├─Validate───>│────────────>│───────────────>│
  │         │<────────────│<────────────│<───────────────┤
  │         │             │             │          [JWT+Cookie]
  │<─UI─────┤             │             │                │
  │         │             │             │                │
  │ [Si training_create=true, muestra botón "Backoffice"]
  │         │             │             │                │
  ├─Click──>│             │             │                │
  │  Backoffice           │             │                │
  │         ├─Redirect────>│             │                │
  │         │          /backoffice/      │                │
  │         │             ├─Proxy──────>│                │
  │         │             │         [Cookie presente]    │
  │         │             │<────────────┤                │
  │         │             │      [HTML backoffice]       │
  │<────────┼─────────────┤             │                │
  │         │             │             │                │
  │ [UI naranja, sin "Acceso Usuario"]  │                │
  │         │             │             │                │
  ├─Click──>│             │             │                │
  │  Volver │             │             │                │
  │         │             │             ├─Redirect──────>│
  │         │             │             │            [/] │
  │         │             │<────────────┤                │
  │<─UI─────┼─────────────┤             │                │
  │         │             │             │                │
```

## Ventajas de esta arquitectura

1. ✅ **Separación clara**: Dos aplicaciones independientes
2. ✅ **Sesión única**: Login solo en frontend
3. ✅ **Seguridad**: Cookie HttpOnly, validación JWT
4. ✅ **Escalabilidad**: Fácil migrar a Redis en futuro
5. ✅ **Desarrollo**: Cada app con su entorno virtual
6. ✅ **Testing**: Testeable de forma independiente
7. ✅ **UX fluida**: Conmutación transparente para el usuario

## Próximos pasos

1. Ejecutar script de clonación
2. Crear entorno virtual backoffice
3. Implementar `SessionManager` compartido
4. Actualizar `SessionState` en ambas apps
5. Añadir botón "Backoffice" en frontend
6. Añadir botón "Volver" en backoffice
7. Configurar Nginx (ya hecho)
8. Testing de conmutación
9. Documentar en README.md
