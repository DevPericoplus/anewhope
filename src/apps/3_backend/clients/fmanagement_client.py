"""Cliente HTTP para interactuar con la API de fmanagement.

Este cliente gestiona todas las operaciones de archivos y carpetas
a través del servicio fmanagement (escrito en Go).
"""

from __future__ import annotations

import httpx
import logging
from typing import Any, Optional


class FmanagementClient:
    """Cliente HTTP para fmanagement API."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:1666",
        timeout: int = 30,
        logger: Optional[logging.Logger] = None,
    ):
        """Inicializa el cliente de fmanagement.
        
        Args:
            base_url: URL base de fmanagement
            timeout: Timeout en segundos
            logger: Logger para registrar operaciones
        """
        self.base_url = base_url
        self.timeout = timeout
        self._logger = logger or logging.getLogger(__name__)
    
    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Procesa la respuesta de fmanagement."""
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self._logger.error(
                f"Error HTTP {e.response.status_code} desde fmanagement: {e.response.text}"
            )
            return {
                "error": str(e),
                "status_code": e.response.status_code,
                "details": e.response.text,
            }
        except Exception as e:
            self._logger.error(f"Error de conexión con fmanagement: {e}")
            return {"error": str(e)}
    
    # === LISTADO Y LECTURA ===
    
    def list_structure(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str = "v001",
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Lista la estructura completa de una versión.
        
        Endpoint: GET /fmo/list
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.get("/fmo/list", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en list_structure: {e}")
            return {"error": f"Failed to connect to fmanagement: {e}"}
    
    def read_folder(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str = "",
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Lee información de una carpeta específica.
        
        Endpoint: GET /fmo/readfolder
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.get("/fmo/readfolder", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en read_folder: {e}")
            return {"error": str(e)}
    
    # === OPERACIONES DE CARPETAS ===
    
    def create_folder(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str,
        identity_type_id: int,
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Crea una nueva carpeta.
        
        Endpoint: POST /fmo/createfolder
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "identity_type_id": identity_type_id,
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.post("/fmo/createfolder", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en create_folder: {e}")
            return {"error": str(e)}
    
    def rename_folder(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str,
        new_filename: str,
        identity_type_id: int,
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Renombra una carpeta.
        
        Endpoint: PATCH /fmo/renamefolder
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "new_filename": new_filename,
            "identity_type_id": identity_type_id,
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.patch("/fmo/renamefolder", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en rename_folder: {e}")
            return {"error": str(e)}
    
    def delete_folder(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str,
        identity_type_id: int,
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Elimina una carpeta.
        
        Endpoint: DELETE /fmo/deletefolder
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "identity_type_id": identity_type_id,
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.delete("/fmo/deletefolder", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en delete_folder: {e}")
            return {"error": str(e)}
    
    # === OPERACIONES DE ARCHIVOS ===
    
    def create_file(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str,
        filename: str,
        extfile: str,
        identity_type_id: int,
        file_content: bytes = b"",
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Crea/sube un archivo.
        
        Endpoint: POST /fmo/createfile
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "filename": filename,
            "extfile": extfile,
            "identity_type_id": identity_type_id,
        }
        
        files = {"file": (f"{filename}.{extfile}", file_content)}
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.post("/fmo/createfile", params=params, files=files)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en create_file: {e}")
            return {"error": str(e)}
    
    def rename_file(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str,
        filename: str,
        extfile: str,
        new_filename: str,
        identity_type_id: int,
        new_extfile: str = "",
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Renombra un archivo.

        Permite cambiar tanto el nombre como la extensión del archivo.

        Endpoint: PATCH /fmo (operation=rename)
        """
        # Si no se especifica new_extfile, usar la extensión original
        actual_new_extfile = new_extfile if new_extfile else extfile

        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "filename": filename,
            "extfile": extfile,
            "new_filename": new_filename,
            "new_extfile": actual_new_extfile,
            "identity_type_id": identity_type_id,
            "operation": "rename",
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.patch("/fmo", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en rename_file: {e}")
            return {"error": str(e)}
    
    def delete_file(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str,
        filename: str,
        extfile: str,
        identity_type_id: int,
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Elimina un archivo.
        
        Endpoint: DELETE /fmo/deletefile
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "filename": filename,
            "extfile": extfile,
            "identity_type_id": identity_type_id,
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.delete("/fmo/deletefile", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error en delete_file: {e}")
            return {"error": str(e)}
    
    def download_file(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str,
        filename: str,
        extfile: str,
        iduser: int = 0,
        basepath: str = "default",
    ) -> bytes | dict[str, Any]:
        """Descarga un archivo.
        
        Endpoint: GET /fmo/download
        
        Returns:
            bytes si éxito, dict con error si falla
        """
        params = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "filename": filename,
            "extfile": extfile,
        }
        
        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.get("/fmo/download", params=params)
            response.raise_for_status()
            return response.content
        except Exception as e:
            self._logger.error(f"Error en download_file: {e}")
            return {"error": str(e)}
    
    # === GESTIÓN DE VERSIONES ===

    def create_version(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        identity_type_id: int,
        clone_from: Optional[str] = None,
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Crea una nueva versión (carpeta de versión en disco).

        Si clone_from es None, crea versión vacía con estructura base.
        Si clone_from está especificado, clona desde esa versión.

        Args:
            orgpath: Carpeta organización (ej: ORG0001)
            prjpath: Carpeta proyecto (ej: PRJ00001)
            versionpath: Nueva versión a crear (ej: v001, v002)
            identity_type_id: Tipo de identidad del usuario
            clone_from: Versión origen a clonar (ej: v001). Si None, crea vacía.
            iduser: ID del usuario
            basepath: Ruta base (default usa configuración de fmanagement)

        Returns:
            Dict con resultado de la operación
        """
        if clone_from is None:
            # Crear versión vacía con estructura base
            return self._create_empty_version(
                orgpath=orgpath,
                prjpath=prjpath,
                versionpath=versionpath,
                identity_type_id=identity_type_id,
                iduser=iduser,
                basepath=basepath,
            )
        else:
            # Clonar desde versión existente usando /fmo/newversion
            return self._clone_version(
                orgpath=orgpath,
                prjpath=prjpath,
                source_version=clone_from,
                identity_type_id=identity_type_id,
                iduser=iduser,
                basepath=basepath,
            )

    def _create_empty_version(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        identity_type_id: int,
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Crea una versión vacía con estructura base.

        Usa /fmo/createfolder para crear:
        - ORG.../PRJ.../vXXX/
        - ORG.../PRJ.../vXXX/datos/
        - ORG.../PRJ.../vXXX/modelos/
        - ORG.../PRJ.../vXXX/evaluaciones/
        - ORG.../PRJ.../vXXX/resultados/
        """
        self._logger.info(
            f"Creando versión vacía: {orgpath}/{prjpath}/{versionpath}"
        )

        # Crear carpeta raíz de la versión
        result = self.create_folder(
            orgpath=orgpath,
            prjpath=prjpath,
            versionpath=versionpath,
            subfolders="",  # Raíz de la versión
            identity_type_id=identity_type_id,
            iduser=iduser,
            basepath=basepath,
        )

        if "error" in result:
            return result

        # Crear subcarpetas base
        base_folders = ["datos", "modelos", "evaluaciones", "resultados"]
        for folder in base_folders:
            folder_result = self.create_folder(
                orgpath=orgpath,
                prjpath=prjpath,
                versionpath=versionpath,
                subfolders=folder,
                identity_type_id=identity_type_id,
                iduser=iduser,
                basepath=basepath,
            )
            if "error" in folder_result:
                self._logger.warning(
                    f"No se pudo crear subcarpeta {folder}: {folder_result.get('error')}"
                )

        return {
            "status": "success",
            "message": f"Versión vacía {versionpath} creada exitosamente",
            "new_version": versionpath,
            "old_version": None,
        }

    def _clone_version(
        self,
        orgpath: str,
        prjpath: str,
        source_version: str,
        identity_type_id: int,
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Clona una versión existente a la siguiente.

        Endpoint: POST /fmo/newversion

        IMPORTANTE: fmanagement calcula automáticamente la siguiente versión.
        Si source_version=v001, crea v002.
        Si source_version=v002, crea v003.

        Args:
            orgpath: Carpeta organización
            prjpath: Carpeta proyecto
            source_version: Versión origen a clonar
            identity_type_id: Tipo de identidad
            iduser: ID del usuario
            basepath: Ruta base
        """
        self._logger.info(
            f"Clonando versión: {orgpath}/{prjpath}/{source_version} -> siguiente"
        )

        # NOTA: versionpath en /fmo/newversion es la versión ORIGEN
        # fmanagement calcula automáticamente la siguiente
        payload = {
            "iduser": iduser,
            "basepath": basepath,
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": source_version,  # Versión a clonar (origen)
            "identity_type_id": identity_type_id,
        }

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.post("/fmo/newversion", json=payload)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error clonando versión: {e}")
            return {"error": str(e)}

    def get_properties(
        self,
        orgpath: str,
        prjpath: str,
        versionpath: str,
        subfolders: str = "",
        filename: str = "",
        iduser: int = 0,
        basepath: str = "default",
    ) -> dict[str, Any]:
        """Obtiene las propiedades de un archivo o carpeta usando el comando 'file'.

        Endpoint: GET /properties

        Args:
            orgpath: Carpeta organización (ej: ORG00001)
            prjpath: Carpeta proyecto (ej: PRJ00001)
            versionpath: Carpeta versión (ej: v001)
            subfolders: Subcarpetas relativas (ej: datos/modelos)
            filename: Nombre del archivo con extensión. Si vacío, es una carpeta
            iduser: ID del usuario
            basepath: Ruta base (default usa configuración de fmanagement)

        Returns:
            Dict con:
            - status: "success"
            - path: Ruta completa del elemento
            - name: Nombre del elemento
            - is_dir: True si es carpeta
            - size_bytes: Tamaño en bytes
            - mode: Permisos (ej: -rw-r--r--)
            - mod_time: Fecha de modificación (RFC3339)
            - file_output: Output del comando 'file'
        """
        params = {
            "orgpath": orgpath,
            "prjpath": prjpath,
            "versionpath": versionpath,
            "subfolders": subfolders,
            "filename": filename,
        }

        try:
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                response = client.get("/properties", params=params)
            return self._handle_response(response)
        except Exception as e:
            self._logger.error(f"Error obteniendo propiedades: {e}")
            return {"error": str(e)}
