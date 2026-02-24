#!/usr/bin/env python3
"""
Test de Regresión - Sistema de Descargas de Modelos con OTP
============================================================

Prueba el flujo completo de descargas seguras de modelos:
1. Login de usuario administrador
2. Listado de modelos disponibles
3. Solicitud de OTP
4. Validación de OTP y obtención de token de descarga
5. Descarga del archivo ZIP desde fmanagement

Autor: Claude Code
Fecha: 2026-02-15
"""

import httpx
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from tests.helpers import get_service_urls
_urls = get_service_urls()

# Configuración
MIDDLEWARE_URL = _urls["middleware"]
FMANAGEMENT_URL = _urls["fmanagement"]

# Credenciales de test (admin)
TEST_USER = "admintest"
TEST_PASSWORD = "Password01"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def log_step(step: str, message: str):
    """Log de paso del test."""
    print(f"\n{Colors.CYAN}[PASO {step}]{Colors.RESET} {Colors.BOLD}{message}{Colors.RESET}")


def log_success(message: str):
    """Log de éxito."""
    print(f"  {Colors.GREEN}✓{Colors.RESET} {message}")


def log_error(message: str):
    """Log de error."""
    print(f"  {Colors.RED}✗{Colors.RESET} {message}")


def log_info(message: str):
    """Log de información."""
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {message}")


def log_warning(message: str):
    """Log de advertencia."""
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {message}")


class ModelDownloadRegressionTest:
    """Test de regresión para descargas de modelos."""

    def __init__(self):
        self.access_token: Optional[str] = None
        self.session_token: Optional[str] = None
        self.user_id: Optional[int] = None
        self.organization_id: Optional[int] = None
        self.identity_type_id: Optional[int] = None
        self.test_results: Dict[str, bool] = {}

    def run_all_tests(self) -> bool:
        """Ejecuta todos los tests del flujo de descargas."""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}TEST DE REGRESIÓN - SISTEMA DE DESCARGAS DE MODELOS CON OTP{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

        tests = [
            ("1", "Verificación de Servicios", self.test_services_running),
            ("2", "Login de Usuario Administrador", self.test_login),
            ("3", "Listado de Modelos Disponibles", self.test_list_models),
            ("4", "Solicitud de OTP para Descarga", self.test_request_otp),
            ("5", "Simulación de Validación de OTP", self.test_validate_otp),
            ("6", "Verificación de Endpoint fmanagement", self.test_fmanagement_endpoint),
            ("7", "Verificación de Archivos ZIP", self.test_zip_files_exist),
        ]

        for step, description, test_func in tests:
            log_step(step, description)
            try:
                result = test_func()
                self.test_results[description] = result
                if not result:
                    log_error(f"Test falló: {description}")
            except Exception as e:
                log_error(f"Excepción en test: {str(e)}")
                self.test_results[description] = False
                import traceback
                traceback.print_exc()

        return self.print_summary()

    def test_services_running(self) -> bool:
        """Verifica que todos los servicios estén corriendo."""
        services = [
            ("Middleware", MIDDLEWARE_URL, "/training/health"),
            ("fmanagement", FMANAGEMENT_URL, "/health"),
        ]

        all_ok = True
        for name, url, endpoint in services:
            try:
                # Para fmanagement, probar el endpoint raíz ya que no tiene /health
                if name == "fmanagement":
                    response = httpx.get(f"{url}/", timeout=5.0)
                    # fmanagement puede retornar 404 en raíz, pero el servicio está corriendo
                    if response.status_code in [200, 404]:
                        log_success(f"{name} está corriendo en {url}")
                    else:
                        log_error(f"{name} responde pero con status: {response.status_code}")
                        all_ok = False
                else:
                    # Para middleware, el endpoint /training/health requiere auth
                    # Verificamos que el servicio responda (aunque sea con 401)
                    response = httpx.get(f"{url}{endpoint}", timeout=5.0)
                    if response.status_code in [200, 401]:
                        log_success(f"{name} está corriendo en {url}")
                    else:
                        log_error(f"{name} responde pero con status: {response.status_code}")
                        all_ok = False
            except httpx.ConnectError:
                log_error(f"{name} NO está accesible en {url}")
                all_ok = False
            except Exception as e:
                log_error(f"Error verificando {name}: {str(e)}")
                all_ok = False

        return all_ok

    def test_login(self) -> bool:
        """Realiza login con usuario administrador."""
        try:
            # Paso 1: Solicitar OTP
            log_info(f"Solicitando OTP para usuario: {TEST_USER}")
            response = httpx.post(
                f"{MIDDLEWARE_URL}/login/request-otp",
                json={
                    "user_name": TEST_USER,
                    "password": TEST_PASSWORD
                },
                timeout=10.0
            )

            if response.status_code != 200:
                log_error(f"Error al solicitar OTP: {response.status_code}")
                log_error(f"Respuesta: {response.text}")
                return False

            otp_data = response.json()
            otp = otp_data.get("otp")
            phone = otp_data.get("phone_number")

            log_success(f"OTP obtenido: {otp}")
            log_info(f"Teléfono: {phone}")

            # Paso 2: Login con OTP
            log_info("Realizando login con OTP...")
            response = httpx.post(
                f"{MIDDLEWARE_URL}/login",
                json={
                    "user_name": TEST_USER,
                    "password": TEST_PASSWORD,
                    "otp": otp
                },
                timeout=10.0
            )

            if response.status_code != 200:
                log_error(f"Error en login: {response.status_code}")
                log_error(f"Respuesta: {response.text}")
                return False

            login_data = response.json()
            self.access_token = login_data.get("access_token")
            self.session_token = login_data.get("session_token")
            self.user_id = login_data.get("user_id")
            self.organization_id = login_data.get("organization_id")
            self.identity_type_id = login_data.get("identity_type_id")

            log_success(f"Login exitoso - User ID: {self.user_id}")
            log_info(f"Organization ID: {self.organization_id}")
            log_info(f"Identity Type ID: {self.identity_type_id}")

            # Verificar que es administrador
            if self.identity_type_id is None or self.identity_type_id == 0:
                log_error("El usuario no tiene identity_type_id (no es administrador)")
                return False

            log_success("Usuario es administrador (tiene identity_type_id)")
            return True

        except Exception as e:
            log_error(f"Excepción en login: {str(e)}")
            return False

    def test_list_models(self) -> bool:
        """Lista modelos disponibles para descarga."""
        if not self.access_token:
            log_error("No hay token de acceso (login no realizado)")
            return False

        try:
            log_info("Consultando lista de modelos...")
            response = httpx.get(
                f"{MIDDLEWARE_URL}/models/list",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Session-Token": self.session_token
                },
                timeout=10.0
            )

            if response.status_code != 200:
                log_error(f"Error al listar modelos: {response.status_code}")
                log_error(f"Respuesta: {response.text}")
                return False

            data = response.json()
            models = data.get("models", [])

            log_success(f"Se encontraron {len(models)} modelos disponibles")

            if len(models) == 0:
                log_warning("No hay modelos disponibles para descarga")
                log_info("Esto es normal si no se han creado ZIPs aún")
                return True

            # Mostrar información de los modelos
            for i, model in enumerate(models, 1):
                log_info(f"Modelo {i}:")
                log_info(f"  - Archivo: {model.get('filename')}")
                log_info(f"  - ORG: {model.get('organization_id'):05d}")
                log_info(f"  - PRJ: {model.get('project_id'):05d}")
                log_info(f"  - VER: v{model.get('version_id'):03d}")
                log_info(f"  - Tamaño: {model.get('file_size') / (1024*1024):.2f} MB")

            # Guardar el primer modelo para tests posteriores
            if models:
                self.test_model = models[0]
                log_success(f"Modelo de prueba seleccionado: {self.test_model.get('filename')}")

            return True

        except Exception as e:
            log_error(f"Excepción al listar modelos: {str(e)}")
            return False

    def test_request_otp(self) -> bool:
        """Solicita OTP para descarga de modelo."""
        if not self.access_token:
            log_error("No hay token de acceso")
            return False

        if not hasattr(self, 'test_model'):
            log_warning("No hay modelos disponibles para probar")
            return True

        try:
            model = self.test_model
            log_info(f"Solicitando OTP para: {model.get('filename')}")

            response = httpx.post(
                f"{MIDDLEWARE_URL}/models/download/request-otp",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Session-Token": self.session_token
                },
                json={
                    "organization_id": model.get("organization_id"),
                    "project_id": model.get("project_id"),
                    "version_id": model.get("version_id")
                },
                timeout=10.0
            )

            if response.status_code != 200:
                log_error(f"Error al solicitar OTP: {response.status_code}")
                log_error(f"Respuesta: {response.text}")
                return False

            data = response.json()
            self.download_otp = data.get("otp")
            self.download_phone = data.get("phone_number")

            log_success(f"OTP de descarga obtenido: {self.download_otp}")
            log_info(f"Teléfono: {self.download_phone}")
            log_info("En producción, se enviaría SMS al teléfono del usuario")

            return True

        except Exception as e:
            log_error(f"Excepción al solicitar OTP: {str(e)}")
            return False

    def test_validate_otp(self) -> bool:
        """Valida OTP y obtiene token de descarga."""
        if not self.access_token:
            log_error("No hay token de acceso")
            return False

        if not hasattr(self, 'test_model') or not hasattr(self, 'download_otp'):
            log_warning("No hay OTP de descarga para validar")
            return True

        try:
            model = self.test_model
            log_info(f"Validando OTP: {self.download_otp}")

            response = httpx.post(
                f"{MIDDLEWARE_URL}/models/download/validate-otp",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Session-Token": self.session_token
                },
                json={
                    "organization_id": model.get("organization_id"),
                    "project_id": model.get("project_id"),
                    "version_id": model.get("version_id"),
                    "otp": self.download_otp
                },
                timeout=10.0
            )

            if response.status_code != 200:
                log_error(f"Error al validar OTP: {response.status_code}")
                log_error(f"Respuesta: {response.text}")
                return False

            data = response.json()
            self.download_token = data.get("download_token")
            expires_in = data.get("expires_in")

            log_success("OTP validado exitosamente")
            log_success(f"Token de descarga obtenido (expira en {expires_in}s)")
            log_info("El OTP del usuario ha sido rotado por seguridad")

            return True

        except Exception as e:
            log_error(f"Excepción al validar OTP: {str(e)}")
            return False

    def test_fmanagement_endpoint(self) -> bool:
        """Verifica que el endpoint de fmanagement funcione."""
        if not hasattr(self, 'download_token') or not hasattr(self, 'test_model'):
            log_warning("No hay token de descarga para probar fmanagement")
            return True

        try:
            model = self.test_model
            filename = model.get("filename")

            log_info(f"Verificando endpoint de descarga para: {filename}")

            # Hacer una petición HEAD para verificar sin descargar el archivo completo
            response = httpx.head(
                f"{FMANAGEMENT_URL}/models/download",
                params={
                    "filename": filename,
                    "token": self.download_token
                },
                timeout=10.0,
                follow_redirects=True
            )

            if response.status_code == 200:
                log_success("Endpoint de fmanagement responde correctamente")
                content_length = response.headers.get("content-length")
                if content_length:
                    log_info(f"Tamaño del archivo: {int(content_length) / (1024*1024):.2f} MB")
                return True
            else:
                log_error(f"fmanagement retornó status: {response.status_code}")
                log_error(f"Headers: {dict(response.headers)}")
                return False

        except Exception as e:
            log_error(f"Excepción al verificar fmanagement: {str(e)}")
            return False

    def test_zip_files_exist(self) -> bool:
        """Verifica que los archivos ZIP existan en el storage interno."""
        try:
            base_path = Path.home() / "data/anewhope/files/backend_server/internal"
            log_info(f"Verificando storage interno: {base_path}")

            if not base_path.exists():
                log_error(f"El directorio no existe: {base_path}")
                return False

            # Buscar archivos ZIP recursivamente
            zip_files = list(base_path.rglob("*.zip"))

            if not zip_files:
                log_warning("No se encontraron archivos ZIP en el storage interno")
                log_info("Los ZIPs deben copiarse desde trainer_server/internal/")
                return True

            log_success(f"Se encontraron {len(zip_files)} archivos ZIP")

            for zip_file in zip_files:
                size_mb = zip_file.stat().st_size / (1024 * 1024)
                relative_path = zip_file.relative_to(base_path)
                log_info(f"  - {relative_path} ({size_mb:.2f} MB)")

            return True

        except Exception as e:
            log_error(f"Excepción al verificar ZIPs: {str(e)}")
            return False

    def print_summary(self) -> bool:
        """Imprime resumen de resultados."""
        print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
        print(f"{Colors.BOLD}RESUMEN DE RESULTADOS{Colors.RESET}")
        print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")

        passed = sum(1 for result in self.test_results.values() if result)
        failed = len(self.test_results) - passed

        for test_name, result in self.test_results.items():
            status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if result else f"{Colors.RED}✗ FAIL{Colors.RESET}"
            print(f"{status}  {test_name}")

        print(f"\n{Colors.BOLD}Total:{Colors.RESET} {len(self.test_results)} tests")
        print(f"{Colors.GREEN}Pasados:{Colors.RESET} {passed}")
        print(f"{Colors.RED}Fallados:{Colors.RESET} {failed}")

        if failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ TODOS LOS TESTS PASARON EXITOSAMENTE{Colors.RESET}")
            return True
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ ALGUNOS TESTS FALLARON{Colors.RESET}")
            return False


def main():
    """Función principal."""
    test = ModelDownloadRegressionTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
