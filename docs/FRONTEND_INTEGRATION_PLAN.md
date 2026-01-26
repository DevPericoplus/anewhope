# Plan de Integración de SharedSessionState en Frontend

## Cambios a realizar en `src/apps/5_web_frontend/web_frontend/web_frontend.py`

### 1. Añadir import de SharedSessionState (línea ~7)
```python
from web_frontend.shared_state import SharedSessionState
```

### 2. Cambiar herencia de State (línea ~31)
```python
# ANTES:
class State(rx.State):

# DESPUÉS:
class State(SharedSessionState):
```

### 3. Actualizar método user_login para usar load_user_data (línea ~96)
```python
def user_login(self):
    """Handle user portal login."""
    if not self.user_username or not self.user_password or not self.user_otp:
        self.login_error = "Debe ingresar usuario, contraseña y OTP"
        return

    response = login_user(self.user_username, self.user_password, self.user_otp)
    access_token = response.get("access_token")
    session_token = response.get("session_token")
    if not access_token or not session_token:
        self.login_error = "No se pudo autenticar con el middleware"
        return

    # Obtener permisos
    permissions_response = get_user_permissions(access_token, session_token)
    permissions_list = permissions_response.get("permissions", [])
    
    # Convertir lista de permisos a diccionario
    permissions_dict = {}
    for perm in permissions_list:
        perm_name = perm.get("permission_name", "")
        perm_value = perm.get("permission_value", False)
        if perm_name:
            permissions_dict[perm_name] = perm_value
    
    # Cargar datos en SharedSessionState
    self.load_user_data(
        user_id=int(response.get("user_id", 0)),
        organization_id=int(response.get("organization_id", 0)),
        identity_type_id=int(response.get("identity_type_id", 0)),
        user_name=self.user_username,
        user_email=response.get("email", ""),
        user_mobile=response.get("mobile", ""),
        access_token=access_token,
        session_token=session_token,
        permissions=permissions_dict,
    )
    
    # Mantener estado local del frontend
    self.user_logged_in = True
    self.login_error = ""
    self.otp_request_message = ""
    self.user_active_menu = "organizacion"
    self.user_permissions = permissions_list
```

### 4. Actualizar user_logout para usar clear_session (línea ~121)
```python
def user_logout(self):
    """Handle user portal logout."""
    if self.access_token and self.session_token:
        logout_user(self.access_token, self.session_token)
    
    # Limpiar SharedSessionState
    self.clear_session()
    
    # Limpiar estado local del frontend
    self.user_logged_in = False
    self.user_username = ""
    self.user_password = ""
    self.user_otp = ""
    self.user_permissions = []
    self.login_error = ""
    self.otp_request_message = ""
    self.user_active_menu = "inicio"
    
    return rx.redirect("/")
```

### 5. Añadir botón "Backoffice" en user_portal (buscar función user_portal)

Buscar la función `user_portal()` y añadir el botón "Backoffice" en la barra superior,
justo antes del botón "Desconectar".

```python
# Añadir después del avatar/nombre de usuario:
rx.cond(
    State.can_access_backoffice,
    rx.button(
        "Backoffice",
        on_click=State.go_to_backoffice,
        bg=COLORS["accent"],
        color="white",
        _hover={"bg": "#1ea34d"},
        size="2",
        variant="solid",
    ),
),
```

## Notas importantes:

1. **No eliminar campos existentes**: El State actual tiene campos como `user_username`,
   `user_password`, `user_otp`, `user_permissions` que son necesarios para la UI.
   Estos campos no están en SharedSessionState y deben mantenerse.

2. **Herencia múltiple de campos**: SharedSessionState aporta:
   - 13 campos de usuario (user_id, organization_id, user_name, etc.)
   - 45 permisos de bajo nivel (can_training_create, etc.)
   - 2 tokens JWT
   - 4 campos de metadata
   
   El State local mantiene sus campos adicionales para UI.

3. **Sincronización automática**: Al heredar de SharedSessionState, todos los cambios
   se sincronizan automáticamente con Redis, permitiendo que el backoffice lea los
   mismos datos.

4. **Compatibilidad**: Los campos duplicados entre State y SharedSessionState
   (como user_id, organization_id, access_token) se usarán de SharedSessionState
   automáticamente debido a la herencia.
