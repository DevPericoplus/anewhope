"""Gestor de rutas para entrenamiento autónomo.

Maneja la jerarquía Organización → Proyecto → Versión en todos los paths
generados durante el proceso de entrenamiento autónomo.

Estructura de salida (todo bajo backend_ia_internal_storage/models/):
    {backend_ia_internal_storage}/models/
    └── ORG{id}/
        └── PRJ{id}/
            └── v{id}/
                ├── datasets/
                │   └── ENT{id}_dataset.jsonl
                ├── lora_adapters/
                │   └── ENT{id}/
                │       └── lora_adapters/
                └── exports/
                    └── ENT{id}/
                        ├── gguf/
                        ├── package/
                        └── ENT{id}_modelo_autonomo.zip

Autor: Sistema anewhope
Fecha: 2026-02-13
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class PathManager:
    """Gestor de rutas para entrenamiento autónomo.

    Mantiene la jerarquía ORG/PRJ/v en todos los paths generados,
    usando backend_ia_internal_storage del env como base.
    """

    def __init__(
        self,
        id_organizacion: int,
        id_proyecto: int,
        id_version: int,
        id_entrenamiento: int,
        pat_version: str | None = None,
    ):
        """Inicializa el gestor de rutas.

        Args:
            id_organizacion: ID de la organización
            id_proyecto: ID del proyecto
            id_version: ID de la versión
            id_entrenamiento: ID del entrenamiento
            pat_version: Path completo con estructura (opcional, se usa para extraer nombres)
        """
        self.id_organizacion = id_organizacion
        self.id_proyecto = id_proyecto
        self.id_version = id_version
        self.id_entrenamiento = id_entrenamiento

        # Extraer nombres de carpeta del pat_version si está disponible
        if pat_version:
            self.org_folder, self.prj_folder, self.ver_folder = self._parse_pat_version(
                pat_version
            )
        else:
            # Generar nombres por defecto
            self.org_folder = f"ORG{id_organizacion:05d}"
            self.prj_folder = f"PRJ{id_proyecto:05d}"
            self.ver_folder = f"v{id_version:03d}"

        # Obtener base path desde env
        self.base_storage_path = self._get_internal_storage_path()

        logger.info(
            f"[PathManager] Inicializado: {self.org_folder}/{self.prj_folder}/"
            f"{self.ver_folder}/ENT{self.id_entrenamiento}"
        )
        logger.info(f"[PathManager] Base storage: {self.base_storage_path}")

    def _get_internal_storage_path(self) -> Path:
        """Obtiene backend_ia_internal_storage del env.

        Returns:
            Path expandido de backend_ia_internal_storage/models/
        """
        # Importar get_env_value desde shared_application
        try:
            import importlib.util
            import sys

            # Cargar env_settings desde shared_application
            base = Path(__file__).resolve().parents[3]  # src/
            env_settings_path = base / "2_shared_application" / "config" / "env_settings.py"

            spec = importlib.util.spec_from_file_location("env_settings", env_settings_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"No se pudo cargar env_settings desde {env_settings_path}")

            env_settings = importlib.util.module_from_spec(spec)
            sys.modules["env_settings_pathmanager"] = env_settings
            spec.loader.exec_module(env_settings)

            get_env_value = env_settings.get_env_value

        except Exception as e:
            logger.error(f"[PathManager] Error cargando env_settings: {e}")
            # Fallback a valor por defecto
            return Path.home() / "data" / "anewhope" / "files" / "trainer_server" / "internal" / "models"

        # Obtener backend_ia_internal_storage del env
        internal_storage = get_env_value("backend_ia_internal_storage")

        if not internal_storage:
            logger.warning(
                "[PathManager] backend_ia_internal_storage no encontrado en env, "
                "usando fallback"
            )
            internal_storage = "~/data/anewhope/files/trainer_server/internal"

        # Expandir ~ y agregar /models/
        base_path = Path(os.path.expanduser(internal_storage)) / "models"

        logger.debug(f"[PathManager] backend_ia_internal_storage: {internal_storage}")
        logger.debug(f"[PathManager] Base path completo: {base_path}")

        return base_path

    def _parse_pat_version(self, pat_version: str) -> tuple[str, str, str]:
        """Extrae nombres de carpeta del pat_version.

        Args:
            pat_version: Path como ~/data/.../ORG00001/PRJ00001/v002

        Returns:
            Tupla (org_folder, prj_folder, ver_folder)
        """
        # Buscar patrón ORG#####/PRJ#####/v###
        pattern = r"(ORG\d{5})/(PRJ\d{5})/(v\d{3})"
        match = re.search(pattern, pat_version)

        if match:
            org_folder, prj_folder, ver_folder = match.groups()
            logger.debug(
                f"[PathManager] Extraído del pat_version: {org_folder}/{prj_folder}/{ver_folder}"
            )
            return org_folder, prj_folder, ver_folder
        else:
            # Fallback: generar nombres
            logger.warning(
                f"[PathManager] No se pudo parsear pat_version: {pat_version}. "
                "Usando formato por defecto."
            )
            return (
                f"ORG{self.id_organizacion:05d}",
                f"PRJ{self.id_proyecto:05d}",
                f"v{self.id_version:03d}",
            )

    def get_hierarchy_path(self) -> str:
        """Obtiene la ruta jerárquica completa.

        Returns:
            String con formato "ORG00001/PRJ00001/v002/ENT123"
        """
        return (
            f"{self.org_folder}/{self.prj_folder}/{self.ver_folder}/"
            f"ENT{self.id_entrenamiento}"
        )

    def get_version_base_dir(self) -> Path:
        """Obtiene directorio base de la versión.

        Returns:
            Path: {internal_storage}/models/ORG00001/PRJ00001/v002/
        """
        dir_path = (
            self.base_storage_path
            / self.org_folder
            / self.prj_folder
            / self.ver_folder
        )
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_dataset_dir(self) -> Path:
        """Obtiene directorio para datasets.

        Returns:
            Path: .../models/ORG00001/PRJ00001/v002/datasets/
        """
        dir_path = self.get_version_base_dir() / "datasets"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_dataset_path(self) -> Path:
        """Obtiene path completo del dataset JSONL.

        Returns:
            Path: .../datasets/ENT123_dataset.jsonl
        """
        return self.get_dataset_dir() / f"ENT{self.id_entrenamiento}_dataset.jsonl"

    def get_lora_base_dir(self) -> Path:
        """Obtiene directorio base para LoRA de esta versión.

        Returns:
            Path: .../models/ORG00001/PRJ00001/v002/lora_adapters/
        """
        dir_path = self.get_version_base_dir() / "lora_adapters"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_lora_dir(self) -> Path:
        """Obtiene directorio para este entrenamiento específico.

        Returns:
            Path: .../lora_adapters/ENT123/
        """
        dir_path = self.get_lora_base_dir() / f"ENT{self.id_entrenamiento}"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_lora_adapters_path(self) -> Path:
        """Obtiene path de los adaptadores LoRA finales.

        Returns:
            Path: .../lora_adapters/ENT123/lora_adapters/
        """
        return self.get_lora_dir() / "lora_adapters"

    def get_export_base_dir(self) -> Path:
        """Obtiene directorio base para exports de esta versión.

        Returns:
            Path: .../models/ORG00001/PRJ00001/v002/exports/
        """
        dir_path = self.get_version_base_dir() / "exports"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_export_dir(self) -> Path:
        """Obtiene directorio para exportación GGUF de este entrenamiento.

        Returns:
            Path: .../exports/ENT123/
        """
        dir_path = self.get_export_base_dir() / f"ENT{self.id_entrenamiento}"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_gguf_dir(self) -> Path:
        """Obtiene directorio para archivos GGUF.

        Returns:
            Path: .../exports/ENT123/gguf/
        """
        dir_path = self.get_export_dir() / "gguf"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_package_dir(self) -> Path:
        """Obtiene directorio para el paquete entregable.

        Returns:
            Path: .../exports/ENT123/package/
        """
        dir_path = self.get_export_dir() / "package"
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def get_package_path(self) -> Path:
        """Obtiene path del ZIP final.

        Returns:
            Path: .../exports/ENT123_modelo_autonomo.zip
        """
        return self.get_export_dir() / f"ENT{self.id_entrenamiento}_modelo_autonomo.zip"

    def to_dict(self) -> dict[str, Any]:
        """Convierte a diccionario con todos los paths.

        Returns:
            Diccionario con paths organizados
        """
        return {
            "hierarchy": {
                "org_folder": self.org_folder,
                "prj_folder": self.prj_folder,
                "ver_folder": self.ver_folder,
                "entrenamiento": f"ENT{self.id_entrenamiento}",
                "full_path": self.get_hierarchy_path(),
            },
            "ids": {
                "id_organizacion": self.id_organizacion,
                "id_proyecto": self.id_proyecto,
                "id_version": self.id_version,
                "id_entrenamiento": self.id_entrenamiento,
            },
            "paths": {
                "base_storage": str(self.base_storage_path),
                "version_base": str(self.get_version_base_dir()),
                "dataset_dir": str(self.get_dataset_dir()),
                "dataset": str(self.get_dataset_path()),
                "lora_base_dir": str(self.get_lora_base_dir()),
                "lora_dir": str(self.get_lora_dir()),
                "lora_adapters": str(self.get_lora_adapters_path()),
                "export_base_dir": str(self.get_export_base_dir()),
                "export_dir": str(self.get_export_dir()),
                "gguf_dir": str(self.get_gguf_dir()),
                "package_dir": str(self.get_package_dir()),
                "package_zip": str(self.get_package_path()),
            },
        }

    def __str__(self) -> str:
        """Representación en string."""
        return f"PathManager({self.get_hierarchy_path()})"

    def __repr__(self) -> str:
        """Representación para debugging."""
        return (
            f"PathManager(org={self.id_organizacion}, prj={self.id_proyecto}, "
            f"ver={self.id_version}, ent={self.id_entrenamiento})"
        )
