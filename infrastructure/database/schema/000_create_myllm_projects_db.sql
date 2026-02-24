-- ============================================================================
-- 000_create_myllm_projects_db.sql
-- Schema canónico de myllm_projects_db exportado desde PRE
-- Fuente: mysqldump --no-data --routines --triggers
-- Fecha de captura: 2026-02-24
-- Contiene: 50 tablas + 11 triggers + 12 vistas
-- NOTA: Las routines están en 000_create_routines.sql
-- ============================================================================

CREATE DATABASE IF NOT EXISTS myllm_projects_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE myllm_projects_db;

 

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `asignaciones_organizaciones_internas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `asignaciones_organizaciones_internas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario_interno` int(11) NOT NULL COMMENT 'Usuario interno (ref: myllm_core_db.users)',
  `id_organizacion` int(11) NOT NULL COMMENT 'Organización cliente (ref: myllm_core_db.organizations)',
  `id_rol` int(11) NOT NULL COMMENT 'Rol del usuario interno para esta organización',
  `fecha_asignacion` timestamp NOT NULL DEFAULT current_timestamp(),
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Si la asignación está activa',
  `asignado_por` int(11) NOT NULL COMMENT 'Super admin que hizo la asignación (ref: myllm_core_db.users)',
  `notas` text DEFAULT NULL COMMENT 'Notas sobre la asignación',
  `fecha_desactivacion` timestamp NULL DEFAULT NULL COMMENT 'Cuándo se desactivó',
  `desactivado_por` int(11) DEFAULT NULL COMMENT 'Quién desactivó (ref: myllm_core_db.users)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_asignacion` (`id_usuario_interno`,`id_organizacion`,`id_rol`),
  KEY `id_rol` (`id_rol`),
  KEY `idx_usuario_interno` (`id_usuario_interno`,`activo`),
  KEY `idx_organizacion` (`id_organizacion`,`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Asignación de usuarios internos a organizaciones cliente';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `cambios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cambios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_version` int(11) NOT NULL,
  `fecha_cambio` date NOT NULL,
  `tipo_cambio` varchar(255) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `creado_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `actualizado_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `id_organizacion` int(11) NOT NULL,
  `id_proyecto` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_cambios_version` (`id_version`),
  KEY `idx_cambios_proyecto` (`id_proyecto`),
  KEY `idx_cambios_organizacion` (`id_organizacion`),
  CONSTRAINT `fk_cambios_proyecto` FOREIGN KEY (`id_proyecto`) REFERENCES `proyectos` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cambios_version` FOREIGN KEY (`id_version`) REFERENCES `versiones` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `conversaciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversaciones` (
  `id_conversacion` int(11) NOT NULL AUTO_INCREMENT,
  `id_organizacion` int(11) NOT NULL COMMENT 'Organización (ref: myllm_core_db.organizations)',
  `id_usuario_cliente` int(11) NOT NULL COMMENT 'Usuario cliente (ref: myllm_core_db.users)',
  `id_ticket_principal` int(11) DEFAULT NULL COMMENT 'Ticket principal relacionado (opcional)',
  `asunto` varchar(255) DEFAULT NULL COMMENT 'Título o tema de la conversación',
  `estado` enum('abierta','en_curso','resuelta','cerrada') DEFAULT 'abierta',
  `prioridad` enum('baja','media','alta','urgente') DEFAULT 'media',
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_ultima_actualizacion` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `ultimo_mensaje_texto` text DEFAULT NULL COMMENT 'Cache del último mensaje',
  `ultimo_mensaje_de` enum('cliente','interno') DEFAULT NULL COMMENT 'Quién envió el último mensaje',
  `ultimo_mensaje_fecha` timestamp NULL DEFAULT NULL COMMENT 'Fecha del último mensaje',
  `mensajes_sin_leer_cliente` int(11) DEFAULT 0 COMMENT 'Contador de mensajes sin leer por cliente',
  `mensajes_sin_leer_interno` int(11) DEFAULT 0 COMMENT 'Contador de mensajes sin leer por internos',
  `total_mensajes` int(11) DEFAULT 0 COMMENT 'Total de mensajes en la conversación',
  `cerrada_por` int(11) DEFAULT NULL COMMENT 'Usuario que cerró (ref: myllm_core_db.users)',
  `fecha_cierre` timestamp NULL DEFAULT NULL COMMENT 'Fecha de cierre',
  PRIMARY KEY (`id_conversacion`),
  KEY `idx_org_estado` (`id_organizacion`,`estado`),
  KEY `idx_fecha_actualizacion` (`fecha_ultima_actualizacion`),
  KEY `idx_usuario_cliente` (`id_usuario_cliente`,`estado`),
  KEY `idx_ticket` (`id_ticket_principal`),
  KEY `idx_conv_org_estado_fecha` (`id_organizacion`,`estado`,`fecha_ultima_actualizacion`),
  CONSTRAINT `conversaciones_ibfk_1` FOREIGN KEY (`id_ticket_principal`) REFERENCES `tickets` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Conversaciones entre clientes e internos';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `conversaciones_tickets_relacionados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversaciones_tickets_relacionados` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_conversacion` int(11) NOT NULL,
  `id_ticket` int(11) NOT NULL,
  `tipo_relacion` enum('principal','secundario','mencionado') DEFAULT 'mencionado',
  `mencionado_por` int(11) DEFAULT NULL COMMENT 'Usuario que hizo referencia (ref: myllm_core_db.users)',
  `fecha_vinculacion` timestamp NOT NULL DEFAULT current_timestamp(),
  `notas` text DEFAULT NULL COMMENT 'Notas sobre la relación',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_conv_ticket` (`id_conversacion`,`id_ticket`),
  KEY `idx_ticket` (`id_ticket`),
  KEY `idx_tipo_relacion` (`tipo_relacion`),
  KEY `idx_mencionado_por` (`mencionado_por`),
  CONSTRAINT `conversaciones_tickets_relacionados_ibfk_1` FOREIGN KEY (`id_conversacion`) REFERENCES `conversaciones` (`id_conversacion`) ON DELETE CASCADE,
  CONSTRAINT `conversaciones_tickets_relacionados_ibfk_2` FOREIGN KEY (`id_ticket`) REFERENCES `tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Relaciones entre conversaciones y tickets';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `entrenamientos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `entrenamientos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_organizacion` int(11) NOT NULL COMMENT 'ID de la organización (ref: myllm_core_db.organizations)',
  `id_proyecto` int(11) NOT NULL COMMENT 'ID del proyecto (ref: proyectos)',
  `id_version` int(11) NOT NULL COMMENT 'ID de la versión entrenada',
  `pat_version` varchar(500) NOT NULL COMMENT 'Ruta completa al contenido de la versión',
  `entrenamiento_inicial` tinyint(1) DEFAULT 1 COMMENT 'TRUE si es el primer entrenamiento de esta versión',
  `reentrenamiento` tinyint(1) DEFAULT 0 COMMENT 'TRUE si es un reentrenamiento para optimizar',
  `numero_secuencia` int(11) DEFAULT 1 COMMENT 'Secuencia autoincremental por versión (1, 2, 3...)',
  `fase_actual` varchar(50) DEFAULT 'recepcion' COMMENT 'Fase actual: recepcion, validacion, preparacion, configuracion, entrenamiento',
  `estado` varchar(50) DEFAULT 'pendiente' COMMENT 'Estado: pendiente, en_progreso, completado, error',
  `collection_name` varchar(300) DEFAULT NULL COMMENT 'Nombre de la colección ChromaDB (ORG_PRJ_v_ENT_SEQ)',
  `modelo_path` varchar(500) DEFAULT NULL COMMENT 'Ruta del modelo generado (un nivel sobre la carpeta de versión)',
  `error_mensaje` text DEFAULT NULL COMMENT 'Mensaje de error si el proceso falló',
  `id_job_entrenamientos` int(11) DEFAULT NULL COMMENT 'ID de los parámetros usados en este entrenamiento',
  `fecha_inicio` datetime DEFAULT NULL COMMENT 'Fecha/hora de inicio del proceso',
  `fecha_fin` datetime DEFAULT NULL COMMENT 'Fecha/hora de finalización del proceso',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_ent_job_params` (`id_job_entrenamientos`),
  KEY `idx_ent_org_prj_ver` (`id_organizacion`,`id_proyecto`,`id_version`),
  KEY `idx_ent_estado` (`estado`),
  KEY `idx_ent_fase` (`fase_actual`),
  KEY `idx_ent_collection` (`collection_name`),
  KEY `idx_ent_secuencia` (`id_version`,`numero_secuencia`),
  CONSTRAINT `fk_ent_job_params` FOREIGN KEY (`id_job_entrenamientos`) REFERENCES `jobs_entrenamientos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Registro de cada proceso de entrenamiento o reentrenamiento de modelos LLM';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `entrenamientos_autonomos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `entrenamientos_autonomos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_entrenamiento` int(11) NOT NULL COMMENT 'FK a entrenamientos.id',
  `training_mode` enum('simulation','test','production') NOT NULL DEFAULT 'simulation' COMMENT 'Modo: simulation (solo RAG), test (LoRA ligero), production (LoRA completo)',
  `dataset_path` varchar(500) DEFAULT NULL COMMENT 'Ruta del dataset JSONL generado',
  `dataset_size` int(11) DEFAULT 0 COMMENT 'Número de ejemplos en el dataset',
  `dataset_generated_at` datetime DEFAULT NULL COMMENT 'Timestamp de generación del dataset',
  `lora_config` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Configuración LoRA (rank, alpha, epochs, etc.)' CHECK (json_valid(`lora_config`)),
  `lora_adapters_path` varchar(500) DEFAULT NULL COMMENT 'Ruta de los adaptadores LoRA entrenados',
  `lora_training_time_seconds` int(11) DEFAULT NULL COMMENT 'Tiempo de entrenamiento LoRA en segundos',
  `lora_final_loss` decimal(10,6) DEFAULT NULL COMMENT 'Loss final del entrenamiento',
  `lora_completed_at` datetime DEFAULT NULL COMMENT 'Timestamp de finalización LoRA',
  `gguf_path` varchar(500) DEFAULT NULL COMMENT 'Ruta del archivo GGUF generado',
  `gguf_size_mb` decimal(10,2) DEFAULT NULL COMMENT 'Tamaño del GGUF en MB',
  `gguf_quantization` varchar(20) DEFAULT 'q8_0' COMMENT 'Tipo de cuantización (q8_0, q4_k_m, etc.)',
  `gguf_generated_at` datetime DEFAULT NULL COMMENT 'Timestamp de generación del GGUF',
  `package_path` varchar(500) DEFAULT NULL COMMENT 'Ruta del ZIP con GGUF + Modelfile + README',
  `package_size_mb` decimal(10,2) DEFAULT NULL COMMENT 'Tamaño del paquete en MB',
  `package_generated_at` datetime DEFAULT NULL COMMENT 'Timestamp de generación del paquete',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_entrenamiento` (`id_entrenamiento`),
  KEY `idx_id_entrenamiento` (`id_entrenamiento`),
  KEY `idx_training_mode` (`training_mode`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_entrenamientos_autonomos_entrenamiento` FOREIGN KEY (`id_entrenamiento`) REFERENCES `entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Datos extendidos para entrenamientos con fine-tuning LoRA y exportación GGUF';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `entrenamientos_metricas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `entrenamientos_metricas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_entrenamiento` int(11) NOT NULL COMMENT 'FK a entrenamientos',
  `loss_inicial` decimal(12,6) DEFAULT NULL COMMENT 'Loss en época 1',
  `loss_final` decimal(12,6) DEFAULT NULL COMMENT 'Loss en última época',
  `loss_promedio` decimal(12,6) DEFAULT NULL COMMENT 'Loss promedio en todas las épocas',
  `loss_minimo` decimal(12,6) DEFAULT NULL COMMENT 'Mejor loss alcanzado',
  `epoca_mejor_loss` int(11) DEFAULT NULL COMMENT 'Época donde se alcanzó el mejor loss',
  `accuracy_validacion` decimal(7,4) DEFAULT NULL COMMENT 'Accuracy en set de validación (0-1)',
  `f1_score` decimal(7,4) DEFAULT NULL COMMENT 'F1-Score',
  `precision_score` decimal(7,4) DEFAULT NULL COMMENT 'Precisión',
  `recall_score` decimal(7,4) DEFAULT NULL COMMENT 'Recall',
  `retrieval_precision` decimal(7,4) DEFAULT NULL COMMENT 'Precisión de recuperación RAG (0-1)',
  `retrieval_recall` decimal(7,4) DEFAULT NULL COMMENT 'Recall de recuperación RAG (0-1)',
  `avg_similarity_score` decimal(7,4) DEFAULT NULL COMMENT 'Score de similitud promedio',
  `perplexity` decimal(12,4) DEFAULT NULL COMMENT 'Perplejidad del modelo',
  `bleu_score` decimal(7,4) DEFAULT NULL COMMENT 'BLEU score (calidad de generación)',
  `rouge_l_score` decimal(7,4) DEFAULT NULL COMMENT 'ROUGE-L score',
  `tiempo_entrenamiento_seg` int(11) DEFAULT NULL COMMENT 'Tiempo total de entrenamiento en segundos',
  `tokens_procesados` bigint(20) DEFAULT NULL COMMENT 'Total de tokens procesados',
  `tokens_por_segundo` decimal(12,2) DEFAULT NULL COMMENT 'Throughput de procesamiento',
  `memoria_pico_mb` int(11) DEFAULT NULL COMMENT 'Uso máximo de memoria en MB',
  `overfitting_detectado` tinyint(1) DEFAULT 0 COMMENT '1=Se detectó overfitting (loss val > loss train)',
  `underfitting_detectado` tinyint(1) DEFAULT 0 COMMENT '1=Se detectó underfitting (loss alto estable)',
  `convergencia_lenta` tinyint(1) DEFAULT 0 COMMENT '1=Convergencia muy lenta',
  `gradientes_explosivos` tinyint(1) DEFAULT 0 COMMENT '1=Se detectaron gradientes explosivos',
  `metricas_adicionales` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Métricas adicionales específicas del modelo' CHECK (json_valid(`metricas_adicionales`)),
  `graficas_paths` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Paths a gráficas de pérdida, accuracy, etc.' CHECK (json_valid(`graficas_paths`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_metricas_entrenamiento` (`id_entrenamiento`),
  KEY `idx_metricas_loss_final` (`loss_final`),
  KEY `idx_metricas_accuracy` (`accuracy_validacion`),
  CONSTRAINT `fk_metricas_entrenamiento` FOREIGN KEY (`id_entrenamiento`) REFERENCES `entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Métricas y resultados observados de entrenamientos';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `estado`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `estado` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_organizacion` int(11) NOT NULL,
  `id_proyecto` int(11) NOT NULL,
  `id_version` int(11) NOT NULL,
  `propuesta_cliente` tinyint(1) NOT NULL DEFAULT 0,
  `revision_interna` tinyint(1) NOT NULL DEFAULT 0,
  `propuesta_mejoras` tinyint(1) NOT NULL DEFAULT 0,
  `aceptacion_cliente` tinyint(1) NOT NULL DEFAULT 0,
  `aceptacion_interna` tinyint(1) NOT NULL DEFAULT 0,
  `entrenamiento_inicial` tinyint(1) NOT NULL DEFAULT 0,
  `evaluacion_entrenamiento` tinyint(1) NOT NULL DEFAULT 0,
  `reentrenamiento` tinyint(1) NOT NULL DEFAULT 0,
  `optimizacion` tinyint(1) NOT NULL DEFAULT 0,
  `aprobacion_calidad` tinyint(1) NOT NULL DEFAULT 0,
  `generacion_llm` tinyint(1) NOT NULL DEFAULT 0,
  `notificacion_descarga` tinyint(1) NOT NULL DEFAULT 0,
  `creado_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `actualizado_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_estado_org_proy_ver` (`id_organizacion`,`id_proyecto`,`id_version`),
  KEY `idx_estado_proyecto` (`id_proyecto`),
  KEY `fk_estado_version` (`id_proyecto`,`id_version`),
  CONSTRAINT `fk_estado_proyecto` FOREIGN KEY (`id_proyecto`) REFERENCES `proyectos` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_estado_version` FOREIGN KEY (`id_proyecto`, `id_version`) REFERENCES `versiones` (`id_proyecto`, `id_version`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Estado por version de proyecto y organizacion';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `estado_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `estado_version` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_organizacion` int(11) NOT NULL,
  `id_proyecto` int(11) NOT NULL,
  `id_version` int(11) NOT NULL,
  `state` enum('Abierta','Bloqueada','Entrenar','Final') NOT NULL DEFAULT 'Abierta',
  `protected` tinyint(1) NOT NULL DEFAULT 0,
  `size` bigint(20) unsigned NOT NULL DEFAULT 0 COMMENT 'Tamaño en bytes',
  `final_c` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Cliente solicita entrenamiento',
  `final_i` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Interno confirma entrenamiento',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `state_internal` varchar(50) DEFAULT 'propuesta_cliente' COMMENT 'Estado interno para backoffice (sincronizado con página Flujos)',
  `revision_interna` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Revisión interna en curso (bucle propuesta-revisión-mejoras)',
  `propuesta_mejoras` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Propuesta de mejoras generada (bucle propuesta-revisión-mejoras)',
  `entrenamiento_inicial_solicitado` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Entrenamiento inicial solicitado (activado automáticamente cuando final_c=1 AND final_i=1)',
  `entrenamiento_inicial_completado` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Entrenamiento inicial completado',
  `entrenamiento_inicial_fecha` datetime DEFAULT NULL COMMENT 'Fecha de completado del entrenamiento inicial',
  `evaluacion_entrenamiento` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Evaluación del entrenamiento en curso (bucle evaluación-reentrenamiento-optimización)',
  `reentrenamiento` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Reentrenamiento en curso (bucle evaluación-reentrenamiento-optimización)',
  `optimizacion` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Optimización del modelo en curso (bucle evaluación-reentrenamiento-optimización)',
  `control_calidad_aprobado` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Control de calidad aprobado (salida del bucle de entrenamiento)',
  `generacion_llm_solicitada` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Generación del fichero LLM solicitada',
  `generacion_llm_completada` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Generación del fichero LLM completada',
  `generacion_llm_fecha` datetime DEFAULT NULL COMMENT 'Fecha de completado de la generación del modelo',
  `ruta_fichero_modelo` varchar(500) DEFAULT NULL COMMENT 'Ruta del fichero del modelo LLM generado',
  `notificacion_descarga_enviada` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Notificación de descarga enviada al cliente',
  `notificacion_descarga_fecha` datetime DEFAULT NULL COMMENT 'Fecha de envío de la notificación de descarga',
  `updated_by` int(11) DEFAULT NULL COMMENT 'ID del usuario que hizo el último cambio (myllm_core_db.users.user_id)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_version` (`id_organizacion`,`id_proyecto`,`id_version`),
  KEY `idx_org_project` (`id_organizacion`,`id_proyecto`),
  KEY `idx_state_internal` (`state_internal`),
  KEY `idx_updated_by` (`updated_by`),
  KEY `idx_fase_entrenamiento` (`entrenamiento_inicial_solicitado`,`entrenamiento_inicial_completado`),
  KEY `idx_control_calidad` (`control_calidad_aprobado`),
  KEY `idx_generacion_llm` (`generacion_llm_solicitada`,`generacion_llm_completada`),
  CONSTRAINT `chk_state_protected` CHECK (`state` = 'Abierta' and `protected` = 0 and `final_c` = 0 and `final_i` = 0 or `state` = 'Bloqueada' and `protected` = 1 and `final_c` = 0 and `final_i` = 0 or `state` = 'Entrenar' and `protected` = 1 and `final_c` = 1 or `state` = 'Final' and `protected` = 1 and `final_c` = 1 and `final_i` = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER trg_estado_version_after_insert
AFTER INSERT ON estado_version
FOR EACH ROW
BEGIN
    
    INSERT INTO estado (
        id_organizacion,
        id_proyecto,
        id_version,
        propuesta_cliente,
        revision_interna,
        propuesta_mejoras,
        aceptacion_cliente,
        aceptacion_interna,
        entrenamiento_inicial,
        evaluacion_entrenamiento,
        reentrenamiento,
        optimizacion,
        aprobacion_calidad,
        generacion_llm,
        notificacion_descarga
    ) VALUES (
        NEW.id_organizacion,
        NEW.id_proyecto,
        NEW.id_version,
        1,
        IFNULL(NEW.revision_interna, 0),
        IFNULL(NEW.propuesta_mejoras, 0),
        IFNULL(NEW.final_c, 0),
        IFNULL(NEW.final_i, 0),
        IFNULL(NEW.entrenamiento_inicial_completado, 0),
        IFNULL(NEW.evaluacion_entrenamiento, 0),
        IFNULL(NEW.reentrenamiento, 0),
        IFNULL(NEW.optimizacion, 0),
        IFNULL(NEW.control_calidad_aprobado, 0),
        IFNULL(NEW.generacion_llm_completada, 0),
        IFNULL(NEW.notificacion_descarga_enviada, 0)
    );
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER trg_estado_version_auto_entrenamiento
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    
    IF NEW.final_c = 1 AND NEW.final_i = 1 THEN
        SET NEW.entrenamiento_inicial_solicitado = 1;
    END IF;

    
    IF NEW.final_c = 0 OR NEW.final_i = 0 THEN
        SET NEW.entrenamiento_inicial_solicitado = 0;
        
        IF OLD.entrenamiento_inicial_solicitado = 1 THEN
            SET NEW.entrenamiento_inicial_completado = 0;
            SET NEW.entrenamiento_inicial_fecha = NULL;
        END IF;
    END IF;

    
    SET NEW.updated_at = NOW();
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER trg_estado_version_auto_state_internal
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    DECLARE new_state_internal VARCHAR(50);

    
    IF NEW.notificacion_descarga_enviada = 1 THEN
        SET new_state_internal = 'notificacion_descarga';

    
    ELSEIF NEW.generacion_llm_completada = 1 THEN
        SET new_state_internal = 'generacion_llm_completada';
    ELSEIF NEW.generacion_llm_solicitada = 1 THEN
        SET new_state_internal = 'generacion_llm';

    
    ELSEIF NEW.control_calidad_aprobado = 1 THEN
        SET new_state_internal = 'aprobacion_calidad';
    ELSEIF NEW.optimizacion = 1 THEN
        SET new_state_internal = 'optimizacion';
    ELSEIF NEW.reentrenamiento = 1 THEN
        SET new_state_internal = 'reentrenamiento';
    ELSEIF NEW.evaluacion_entrenamiento = 1 THEN
        SET new_state_internal = 'evaluacion_entrenamiento';

    
    ELSEIF NEW.entrenamiento_inicial_completado = 1 THEN
        SET new_state_internal = 'entrenamiento_inicial_completado';
    ELSEIF NEW.entrenamiento_inicial_solicitado = 1 THEN
        SET new_state_internal = 'entrenamiento_inicial';

    
    ELSEIF NEW.final_i = 1 THEN
        SET new_state_internal = 'aceptacion_interna';
    ELSEIF NEW.final_c = 1 THEN
        SET new_state_internal = 'aceptacion_cliente';
    ELSEIF NEW.propuesta_mejoras = 1 THEN
        SET new_state_internal = 'propuesta_mejoras';
    ELSEIF NEW.revision_interna = 1 THEN
        SET new_state_internal = 'revision_interna';
    ELSE
        SET new_state_internal = 'propuesta_cliente';
    END IF;

    
    IF NEW.state_internal != new_state_internal THEN
        SET NEW.state_internal = new_state_internal;
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER trg_estado_version_validacion_transiciones
BEFORE UPDATE ON estado_version
FOR EACH ROW
BEGIN
    
    IF NEW.generacion_llm_solicitada = 1 AND NEW.control_calidad_aprobado = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No se puede solicitar generación LLM sin aprobación de calidad';
    END IF;

    
    IF NEW.notificacion_descarga_enviada = 1 AND NEW.generacion_llm_completada = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'No se puede enviar notificación sin generación LLM completada';
    END IF;

    
    IF NEW.entrenamiento_inicial_completado = 1 AND OLD.entrenamiento_inicial_completado = 0 THEN
        SET NEW.entrenamiento_inicial_fecha = NOW();
    END IF;

    
    IF NEW.generacion_llm_completada = 1 AND OLD.generacion_llm_completada = 0 THEN
        SET NEW.generacion_llm_fecha = NOW();
    END IF;

    
    IF NEW.notificacion_descarga_enviada = 1 AND OLD.notificacion_descarga_enviada = 0 THEN
        SET NEW.notificacion_descarga_fecha = NOW();
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER trg_estado_version_after_update
AFTER UPDATE ON estado_version
FOR EACH ROW
BEGIN
    
    UPDATE estado
    SET
        revision_interna = IFNULL(NEW.revision_interna, 0),
        propuesta_mejoras = IFNULL(NEW.propuesta_mejoras, 0),
        aceptacion_cliente = IFNULL(NEW.final_c, 0),
        aceptacion_interna = IFNULL(NEW.final_i, 0),
        entrenamiento_inicial = IFNULL(NEW.entrenamiento_inicial_completado, 0),
        evaluacion_entrenamiento = IFNULL(NEW.evaluacion_entrenamiento, 0),
        reentrenamiento = IFNULL(NEW.reentrenamiento, 0),
        optimizacion = IFNULL(NEW.optimizacion, 0),
        aprobacion_calidad = IFNULL(NEW.control_calidad_aprobado, 0),
        generacion_llm = IFNULL(NEW.generacion_llm_completada, 0),
        notificacion_descarga = IFNULL(NEW.notificacion_descarga_enviada, 0)
    WHERE
        id_organizacion = NEW.id_organizacion
        AND id_proyecto = NEW.id_proyecto
        AND id_version = NEW.id_version;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
DROP TABLE IF EXISTS `evoluciones_autonomas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `evoluciones_autonomas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_entrenamiento` int(11) NOT NULL COMMENT 'FK a entrenamientos.id',
  `phase_key` varchar(10) NOT NULL COMMENT 'Fase (6, 7, 8, 9)',
  `subfase_key` varchar(10) NOT NULL COMMENT 'Subfase (6.1, 6.2, ..., 9.5)',
  `subfase_name` varchar(200) NOT NULL COMMENT 'Nombre de la subfase',
  `status` enum('pending','in_progress','completed','failed') NOT NULL DEFAULT 'pending',
  `started_at` datetime DEFAULT NULL COMMENT 'Timestamp de inicio',
  `completed_at` datetime DEFAULT NULL COMMENT 'Timestamp de finalización',
  `duracion_segundos` int(11) DEFAULT NULL COMMENT 'Duración real en segundos',
  `metrics` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Métricas específicas (loss, accuracy, etc.)' CHECK (json_valid(`metrics`)),
  `error_message` text DEFAULT NULL COMMENT 'Mensaje de error si status = failed',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_unique_subfase_per_entrenamiento` (`id_entrenamiento`,`subfase_key`),
  KEY `idx_id_entrenamiento` (`id_entrenamiento`),
  KEY `idx_phase_key` (`phase_key`),
  KEY `idx_subfase_key` (`subfase_key`),
  KEY `idx_status` (`status`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `fk_evoluciones_autonomas_entrenamiento` FOREIGN KEY (`id_entrenamiento`) REFERENCES `entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Progreso detallado de subfases autónomas (fases 6-9) por entrenamiento';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `evoluciones_entrenamientos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `evoluciones_entrenamientos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_entrenamiento` int(11) NOT NULL COMMENT 'FK al entrenamiento en curso',
  `phase_key` varchar(10) NOT NULL COMMENT 'Clave de fase: "1", "2", "3", "4", "5"',
  `subfase_key` varchar(10) NOT NULL COMMENT 'Clave de subfase: "2.1", "2.2", "3.1", etc',
  `subfase_name` varchar(100) NOT NULL COMMENT 'Nombre descriptivo de la subfase',
  `status` varchar(20) NOT NULL COMMENT 'Estado: pending, in_progress, completed, error',
  `fecha_inicio` timestamp NULL DEFAULT NULL COMMENT 'Inicio de la subfase',
  `fecha_fin` timestamp NULL DEFAULT NULL COMMENT 'Fin de la subfase',
  `duracion_segundos` int(11) DEFAULT NULL COMMENT 'Duración en segundos',
  `error_mensaje` text DEFAULT NULL COMMENT 'Mensaje de error si status=error',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_entrenamiento_subfase` (`id_entrenamiento`,`subfase_key`),
  KEY `idx_evol_entrenamiento` (`id_entrenamiento`),
  KEY `idx_evol_status` (`status`),
  KEY `idx_evol_fase` (`phase_key`,`subfase_key`),
  KEY `idx_evol_created` (`created_at`),
  CONSTRAINT `fk_evol_entrenamiento` FOREIGN KEY (`id_entrenamiento`) REFERENCES `entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Evolución detallada de subfases de entrenamientos para auditoría y métricas';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `flujos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `flujos` (
  `id_flujo` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL COMMENT 'Identificador interno del paso (snake_case)',
  `nombre` varchar(100) NOT NULL COMMENT 'Nombre visible del paso',
  `descripcion` varchar(255) DEFAULT NULL COMMENT 'Descripción del paso',
  `emoji` varchar(10) DEFAULT NULL COMMENT 'Emoji representativo del paso',
  `color` varchar(20) DEFAULT NULL COMMENT 'Color hexadecimal para UI',
  `orden` int(11) NOT NULL COMMENT 'Orden secuencial del paso en el flujo',
  `es_bloque_inicio` tinyint(1) DEFAULT 0 COMMENT 'Indica si pertenece al bloque inicial',
  `es_bloque_iteracion` tinyint(1) DEFAULT 0 COMMENT 'Indica si pertenece al bloque de iteración',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Indica si el paso está activo',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_flujo`),
  UNIQUE KEY `clave` (`clave`),
  KEY `idx_flujos_orden` (`orden`),
  KEY `idx_flujos_clave` (`clave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de pasos del flujo de trabajo para generación de modelos LLM';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `job_entrenamientos_analisis`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_entrenamientos_analisis` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_entrenamiento` int(11) NOT NULL COMMENT 'FK a entrenamientos',
  `id_job_entrenamientos` int(11) NOT NULL COMMENT 'FK a jobs_entrenamientos',
  `numero_secuencia` int(11) NOT NULL COMMENT 'Secuencia del entrenamiento',
  `nombre_modelo` varchar(300) DEFAULT NULL COMMENT 'Nombre del modelo generado',
  `ruta_modelo` varchar(500) DEFAULT NULL COMMENT 'Ruta del modelo en filesystem',
  `rag_precision` decimal(7,4) DEFAULT NULL COMMENT 'Precisión de recuperación 0-1',
  `rag_recall` decimal(7,4) DEFAULT NULL COMMENT 'Recall de recuperación 0-1',
  `rag_f1_score` decimal(7,4) DEFAULT NULL COMMENT 'F1 score de RAG',
  `rag_mrr` decimal(7,4) DEFAULT NULL COMMENT 'Mean Reciprocal Rank',
  `rag_ndcg` decimal(7,4) DEFAULT NULL COMMENT 'Normalized Discounted Cumulative Gain',
  `avg_retrieval_time_ms` int(11) DEFAULT NULL COMMENT 'Tiempo promedio de recuperación en ms',
  `response_relevance` decimal(7,4) DEFAULT NULL COMMENT 'Relevancia de respuestas 0-1',
  `response_coherence` decimal(7,4) DEFAULT NULL COMMENT 'Coherencia de respuestas 0-1',
  `response_fluency` decimal(7,4) DEFAULT NULL COMMENT 'Fluidez de respuestas 0-1',
  `response_groundedness` decimal(7,4) DEFAULT NULL COMMENT 'Fundamentación en documentos 0-1',
  `response_completeness` decimal(7,4) DEFAULT NULL COMMENT 'Completitud de respuestas 0-1',
  `semantic_similarity_score` decimal(7,4) DEFAULT NULL COMMENT 'Score promedio de similitud semántica',
  `embedding_quality_score` decimal(7,4) DEFAULT NULL COMMENT 'Calidad de embeddings generados',
  `bleu_score` decimal(7,4) DEFAULT NULL COMMENT 'BLEU score (n-gram overlap)',
  `rouge_1` decimal(7,4) DEFAULT NULL COMMENT 'ROUGE-1 score',
  `rouge_2` decimal(7,4) DEFAULT NULL COMMENT 'ROUGE-2 score',
  `rouge_l` decimal(7,4) DEFAULT NULL COMMENT 'ROUGE-L score',
  `meteor_score` decimal(7,4) DEFAULT NULL COMMENT 'METEOR score',
  `perplexity` decimal(12,4) DEFAULT NULL COMMENT 'Perplejidad del modelo',
  `factual_accuracy` decimal(7,4) DEFAULT NULL COMMENT 'Precisión factual 0-1',
  `hallucination_rate` decimal(7,4) DEFAULT NULL COMMENT 'Tasa de alucinaciones 0-1 (menor mejor)',
  `citation_accuracy` decimal(7,4) DEFAULT NULL COMMENT 'Precisión de citaciones 0-1',
  `avg_inference_time_ms` int(11) DEFAULT NULL COMMENT 'Tiempo promedio de inferencia en ms',
  `tokens_per_second` decimal(10,2) DEFAULT NULL COMMENT 'Throughput de generación',
  `memory_usage_mb` int(11) DEFAULT NULL COMMENT 'Uso de memoria en MB',
  `model_size_mb` int(11) DEFAULT NULL COMMENT 'Tamaño del modelo en MB',
  `user_satisfaction_score` decimal(4,2) DEFAULT NULL COMMENT 'Score de satisfacción 1-5',
  `task_completion_rate` decimal(7,4) DEFAULT NULL COMMENT 'Tasa de completación de tareas 0-1',
  `overall_quality_score` decimal(7,4) DEFAULT NULL COMMENT 'Score general ponderado 0-1',
  `improvement_vs_previous_pct` decimal(7,2) DEFAULT NULL COMMENT 'Mejora vs entrenamiento anterior %',
  `eval_dataset_size` int(11) DEFAULT NULL COMMENT 'Tamaño del dataset de evaluación',
  `eval_dataset_name` varchar(200) DEFAULT NULL COMMENT 'Nombre del dataset usado',
  `notas` text DEFAULT NULL COMMENT 'Observaciones del análisis',
  `metricas_adicionales` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Métricas adicionales en JSON' CHECK (json_valid(`metricas_adicionales`)),
  `version_analisis` int(11) DEFAULT 1 COMMENT 'Versión del análisis (para reanalizar)',
  `analisis_automatico` tinyint(1) DEFAULT 1 COMMENT '1=automático, 0=manual',
  `fecha_analisis` datetime DEFAULT NULL COMMENT 'Cuándo se realizó el análisis',
  `duracion_analisis_seg` int(11) DEFAULT NULL COMMENT 'Duración del análisis en segundos',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_entrenamiento` (`id_entrenamiento`),
  KEY `fk_analisis_job_params` (`id_job_entrenamientos`),
  KEY `idx_analisis_entrenamiento` (`id_entrenamiento`),
  KEY `idx_analisis_secuencia` (`numero_secuencia`),
  KEY `idx_analisis_quality` (`overall_quality_score`),
  KEY `idx_analisis_fecha` (`fecha_analisis`),
  CONSTRAINT `fk_analisis_entrenamiento` FOREIGN KEY (`id_entrenamiento`) REFERENCES `entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_analisis_job_params` FOREIGN KEY (`id_job_entrenamientos`) REFERENCES `jobs_entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Análisis de calidad de modelos generados por entrenamiento';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_template` int(11) NOT NULL COMMENT 'FK a jobs_templates',
  `id_organizacion` int(11) NOT NULL COMMENT 'Organización propietaria',
  `id_proyecto` int(11) NOT NULL COMMENT 'Proyecto asociado',
  `id_version` int(11) NOT NULL COMMENT 'Versión asociada',
  `nombre` varchar(200) NOT NULL COMMENT 'Heredado de plantilla, modificable',
  `descripcion` text DEFAULT NULL COMMENT 'Descripción del job',
  `id_tipo` int(11) NOT NULL COMMENT 'FK a jobs_tipos',
  `id_estado` int(11) NOT NULL COMMENT 'FK a jobs_estados (actualizado en runtime)',
  `id_modelo` int(11) DEFAULT NULL COMMENT 'FK a jobs_modelos',
  `id_salida` int(11) DEFAULT NULL COMMENT 'FK a jobs_salidas',
  `programado_para` datetime DEFAULT NULL COMMENT 'Fecha/hora de ejecución programada',
  `iniciado_en` datetime DEFAULT NULL COMMENT 'Cuándo empezó a ejecutarse',
  `completado_en` datetime DEFAULT NULL COMMENT 'Cuándo terminó (para calcular duración)',
  `error` text DEFAULT NULL COMMENT 'Descripción del error si aplica',
  `id_cambio` int(11) DEFAULT NULL COMMENT 'FK a cambios (registro en tabla de cambios)',
  `id_job_padre` int(11) DEFAULT NULL COMMENT 'FK a jobs (self-reference para jerarquía)',
  `datos_entrada` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Datos recibidos del padre (flexible)' CHECK (json_valid(`datos_entrada`)),
  `datos_salida` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Datos producidos para hijos (flexible)' CHECK (json_valid(`datos_salida`)),
  `referencia_salida` varchar(500) DEFAULT NULL COMMENT 'path, id_conversacion, id_ticket según tipo',
  `configuracion` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Config del job (heredada de plantilla + modificaciones)' CHECK (json_valid(`configuracion`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_job_modelo` (`id_modelo`),
  KEY `fk_job_salida` (`id_salida`),
  KEY `idx_jobs_org_proj_ver` (`id_organizacion`,`id_proyecto`,`id_version`),
  KEY `idx_jobs_padre` (`id_job_padre`),
  KEY `idx_jobs_estado` (`id_estado`),
  KEY `idx_jobs_tipo` (`id_tipo`),
  KEY `idx_jobs_template` (`id_template`),
  KEY `idx_jobs_programado` (`programado_para`),
  CONSTRAINT `fk_job_estado` FOREIGN KEY (`id_estado`) REFERENCES `jobs_estados` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_job_modelo` FOREIGN KEY (`id_modelo`) REFERENCES `jobs_modelos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_job_padre` FOREIGN KEY (`id_job_padre`) REFERENCES `jobs` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_job_salida` FOREIGN KEY (`id_salida`) REFERENCES `jobs_salidas` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_job_template` FOREIGN KEY (`id_template`) REFERENCES `jobs_templates` (`id`) ON UPDATE CASCADE,
  CONSTRAINT `fk_job_tipo` FOREIGN KEY (`id_tipo`) REFERENCES `jobs_tipos` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Instancias de jobs creados desde plantillas';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_documentacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_documentacion` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) NOT NULL COMMENT 'Nombre descriptivo de la plantilla',
  `descripcion` text DEFAULT NULL COMMENT 'Para qué sirve la plantilla',
  `template_path` varchar(500) NOT NULL COMMENT 'Path completo al fichero .j2',
  `template_filename` varchar(200) NOT NULL COMMENT 'Nombre del fichero .j2',
  `formato_salida` varchar(50) DEFAULT 'markdown' COMMENT 'Formato del output (markdown, html, pdf, etc.)',
  `variables_requeridas` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Lista de variables que necesita el template' CHECK (json_valid(`variables_requeridas`)),
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Plantilla activa/inactiva',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_jobs_doc_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Plantillas Jinja2 para generación de informes';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_entradas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_entradas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_job_padre` int(11) NOT NULL COMMENT 'FK a jobs (job padre)',
  `id_job_hijo` int(11) NOT NULL COMMENT 'FK a jobs (job hijo)',
  `id_tipo_salida` int(11) DEFAULT NULL COMMENT 'FK a jobs_salidas (qué tipo de dato se transfiere)',
  `id_resultado` int(11) DEFAULT NULL COMMENT 'FK a jobs_resultados (si se pasa referencia a resultado)',
  `datos` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Payload flexible con lo que el padre pasa al hijo' CHECK (json_valid(`datos`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_entrada_tipo_salida` (`id_tipo_salida`),
  KEY `idx_entradas_padre` (`id_job_padre`),
  KEY `idx_entradas_hijo` (`id_job_hijo`),
  KEY `idx_entradas_resultado` (`id_resultado`),
  CONSTRAINT `fk_entrada_hijo` FOREIGN KEY (`id_job_hijo`) REFERENCES `jobs` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_entrada_padre` FOREIGN KEY (`id_job_padre`) REFERENCES `jobs` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_entrada_resultado` FOREIGN KEY (`id_resultado`) REFERENCES `jobs_resultados` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_entrada_tipo_salida` FOREIGN KEY (`id_tipo_salida`) REFERENCES `jobs_salidas` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Transferencia de datos entre jobs padre e hijo';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_entrenamientos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_entrenamientos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) NOT NULL COMMENT 'Nombre de la configuración',
  `descripcion` text DEFAULT NULL COMMENT 'Descripción de la configuración',
  `learning_rate` decimal(10,8) DEFAULT 0.00100000 COMMENT 'Tasa de aprendizaje',
  `batch_size` int(11) DEFAULT 32 COMMENT 'Tamaño de lote',
  `epochs` int(11) DEFAULT 10 COMMENT 'Número de épocas',
  `embedding_dimension` int(11) DEFAULT 768 COMMENT 'Dimensión de embeddings',
  `sequence_length` int(11) DEFAULT 512 COMMENT 'Longitud de secuencia',
  `hidden_units` int(11) DEFAULT 256 COMMENT 'Unidades ocultas',
  `dropout_rate` decimal(5,4) DEFAULT 0.1000 COMMENT 'Tasa de dropout',
  `collection_name` varchar(200) DEFAULT NULL COMMENT 'Nombre de la colección ChromaDB',
  `distance_metric` varchar(50) DEFAULT 'cosine' COMMENT 'Métrica de distancia (cosine, euclidean, etc.)',
  `persist_directory` varchar(500) DEFAULT NULL COMMENT 'Directorio de persistencia ChromaDB',
  `top_k` int(11) DEFAULT 5 COMMENT 'Número de resultados a recuperar',
  `chunk_size` int(11) DEFAULT 1000 COMMENT 'Tamaño de fragmento de texto',
  `chunk_overlap` int(11) DEFAULT 200 COMMENT 'Solapamiento entre fragmentos',
  `temperature` decimal(4,3) DEFAULT 0.700 COMMENT 'Temperatura de generación',
  `max_tokens` int(11) DEFAULT 2048 COMMENT 'Máximo de tokens a generar',
  `loss_function` varchar(100) DEFAULT 'cross_entropy' COMMENT 'Función de pérdida',
  `optimizer` varchar(100) DEFAULT 'adam' COMMENT 'Optimizador',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Configuración activa/inactiva',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_jobs_entren_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Configuraciones de parámetros de entrenamiento RAG';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_entrenamientos_sugeridos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_entrenamientos_sugeridos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_job_entrenamiento` int(11) NOT NULL COMMENT 'FK a jobs_entrenamientos (parámetros usados)',
  `id_entrenamiento` int(11) NOT NULL COMMENT 'FK a entrenamientos',
  `nombre_sugerencia` varchar(200) NOT NULL COMMENT 'Nombre descriptivo de la sugerencia',
  `razon_sugerencia` text NOT NULL COMMENT 'Explicación del por qué de los cambios',
  `confianza_score` decimal(5,2) DEFAULT 0.00 COMMENT 'Confianza en la sugerencia 0-100',
  `mejora_esperada_pct` decimal(7,2) DEFAULT NULL COMMENT 'Mejora esperada en % (ej: 15.5 = 15.5%)',
  `learning_rate_sugerido` decimal(10,8) DEFAULT NULL COMMENT 'Tasa de aprendizaje sugerida',
  `learning_rate_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `learning_rate_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `batch_size_sugerido` int(11) DEFAULT NULL COMMENT 'Tamaño de lote sugerido',
  `batch_size_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `batch_size_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `epochs_sugerido` int(11) DEFAULT NULL COMMENT 'Número de épocas sugerido',
  `epochs_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `epochs_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `embedding_dimension_sugerido` int(11) DEFAULT NULL COMMENT 'Dimensión de embeddings sugerida',
  `embedding_dimension_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `embedding_dimension_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `sequence_length_sugerido` int(11) DEFAULT NULL COMMENT 'Longitud de secuencia sugerida',
  `sequence_length_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `sequence_length_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `hidden_units_sugerido` int(11) DEFAULT NULL COMMENT 'Unidades ocultas sugeridas',
  `hidden_units_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `hidden_units_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `dropout_rate_sugerido` decimal(5,4) DEFAULT NULL COMMENT 'Tasa de dropout sugerida',
  `dropout_rate_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `dropout_rate_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `distance_metric_sugerido` varchar(50) DEFAULT NULL COMMENT 'Métrica de distancia sugerida',
  `distance_metric_cambio` varchar(20) DEFAULT NULL COMMENT 'cambiar|mantener',
  `distance_metric_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `top_k_sugerido` int(11) DEFAULT NULL COMMENT 'Top-k sugerido',
  `top_k_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `top_k_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `chunk_size_sugerido` int(11) DEFAULT NULL COMMENT 'Tamaño de chunk sugerido',
  `chunk_size_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `chunk_size_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `chunk_overlap_sugerido` int(11) DEFAULT NULL COMMENT 'Overlap sugerido',
  `chunk_overlap_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `chunk_overlap_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `temperature_sugerido` decimal(4,3) DEFAULT NULL COMMENT 'Temperatura sugerida',
  `temperature_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `temperature_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `max_tokens_sugerido` int(11) DEFAULT NULL COMMENT 'Max tokens sugerido',
  `max_tokens_cambio` varchar(20) DEFAULT NULL COMMENT 'aumentar|disminuir|mantener',
  `max_tokens_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `loss_function_sugerido` varchar(100) DEFAULT NULL COMMENT 'Función de pérdida sugerida',
  `loss_function_cambio` varchar(20) DEFAULT NULL COMMENT 'cambiar|mantener',
  `loss_function_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `optimizer_sugerido` varchar(100) DEFAULT NULL COMMENT 'Optimizador sugerido',
  `optimizer_cambio` varchar(20) DEFAULT NULL COMMENT 'cambiar|mantener',
  `optimizer_razon` text DEFAULT NULL COMMENT 'Razón del cambio',
  `tecnicas_adicionales` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Técnicas adicionales sugeridas (early stopping, lr schedule, etc.)' CHECK (json_valid(`tecnicas_adicionales`)),
  `prioridad_cambios` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Array ordenado de cambios por prioridad' CHECK (json_valid(`prioridad_cambios`)),
  `aplicado` tinyint(1) DEFAULT 0 COMMENT '1=Sugerencias aplicadas en nuevo entrenamiento',
  `id_entrenamiento_aplicado` int(11) DEFAULT NULL COMMENT 'FK a entrenamientos donde se aplicó',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `id_job_entrenamiento` (`id_job_entrenamiento`),
  KEY `fk_sugerencia_aplicado` (`id_entrenamiento_aplicado`),
  KEY `idx_sugerencias_job` (`id_job_entrenamiento`),
  KEY `idx_sugerencias_entrenamiento` (`id_entrenamiento`),
  KEY `idx_sugerencias_aplicado` (`aplicado`),
  KEY `idx_sugerencias_confianza` (`confianza_score`),
  CONSTRAINT `fk_sugerencia_aplicado` FOREIGN KEY (`id_entrenamiento_aplicado`) REFERENCES `entrenamientos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_sugerencia_entrenamiento` FOREIGN KEY (`id_entrenamiento`) REFERENCES `entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_sugerencia_job_params` FOREIGN KEY (`id_job_entrenamiento`) REFERENCES `jobs_entrenamientos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Sugerencias automáticas de parámetros para reentrenamiento';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_estados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_estados` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL COMMENT 'Clave interna (snake_case)',
  `nombre` varchar(100) NOT NULL COMMENT 'Nombre visible en UI',
  `descripcion` varchar(255) DEFAULT NULL COMMENT 'Descripción del estado',
  `color` varchar(20) DEFAULT NULL COMMENT 'Color hexadecimal para badges en UI',
  `es_final` tinyint(1) DEFAULT 0 COMMENT 'Indica si el estado es terminal',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Estado activo/inactivo',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `clave` (`clave`),
  KEY `idx_jobs_estados_clave` (`clave`),
  KEY `idx_jobs_estados_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de estados posibles de un job';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_eventos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_eventos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `referencia_compuesta` varchar(200) NOT NULL COMMENT 'Calculado: ORG{id}-PRJ{id}-VER{id}-JOB{id}',
  `id_job` int(11) NOT NULL COMMENT 'FK a jobs',
  `id_organizacion` int(11) NOT NULL COMMENT 'Organización',
  `id_proyecto` int(11) NOT NULL COMMENT 'Proyecto',
  `id_version` int(11) NOT NULL COMMENT 'Versión',
  `tipo_evento` varchar(100) NOT NULL COMMENT 'inicio, progreso, error, fin, etc.',
  `descripcion` text DEFAULT NULL COMMENT 'Descripción del evento',
  `datos_evento` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Datos adicionales flexibles' CHECK (json_valid(`datos_evento`)),
  `fecha_evento` timestamp NOT NULL DEFAULT current_timestamp() COMMENT 'Fecha y hora del evento',
  PRIMARY KEY (`id`),
  KEY `idx_eventos_job` (`id_job`),
  KEY `idx_eventos_referencia` (`referencia_compuesta`),
  KEY `idx_eventos_fecha` (`fecha_evento`),
  KEY `idx_eventos_tipo` (`tipo_evento`),
  CONSTRAINT `fk_evento_job` FOREIGN KEY (`id_job`) REFERENCES `jobs` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Log cronológico de eventos de ejecución de jobs';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_generacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_generacion` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_modelo_base` int(11) DEFAULT NULL COMMENT 'FK a jobs_modelos (modelo base usado)',
  `nombre` varchar(200) NOT NULL COMMENT 'Nombre del modelo generado',
  `path_modelo` varchar(500) NOT NULL COMMENT 'Path interno completo al fichero del modelo',
  `size_bytes` bigint(20) DEFAULT 0 COMMENT 'Tamaño del modelo en bytes',
  `id_organizacion` int(11) NOT NULL COMMENT 'Organización propietaria',
  `id_proyecto` int(11) NOT NULL COMMENT 'Proyecto asociado',
  `id_version` int(11) NOT NULL COMMENT 'Versión asociada',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Modelo generado activo/inactivo',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_jobs_gen_modelo` (`id_modelo_base`),
  KEY `idx_jobs_gen_org_proj_ver` (`id_organizacion`,`id_proyecto`,`id_version`),
  KEY `idx_jobs_gen_activo` (`activo`),
  CONSTRAINT `fk_generacion_modelo` FOREIGN KEY (`id_modelo_base`) REFERENCES `jobs_modelos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Modelos LLM generados a partir de entrenamiento';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_modelos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_modelos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) NOT NULL COMMENT 'Nombre del modelo (ej: llama3:latest)',
  `tag` varchar(100) DEFAULT NULL COMMENT 'Tag o versión del modelo',
  `size_bytes` bigint(20) DEFAULT 0 COMMENT 'Tamaño en bytes',
  `digest` varchar(200) DEFAULT NULL COMMENT 'Hash/digest del modelo',
  `familia` varchar(100) DEFAULT NULL COMMENT 'Familia del modelo (llama, mistral, etc.)',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Modelo activo/inactivo',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_jobs_modelos_nombre` (`nombre`),
  KEY `idx_jobs_modelos_familia` (`familia`),
  KEY `idx_jobs_modelos_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Modelos LLM disponibles (sincronizado con ollama list)';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_resultados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_resultados` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_job` int(11) DEFAULT NULL COMMENT 'FK a jobs (se vincula cuando exista la tabla)',
  `id_documentacion` int(11) DEFAULT NULL COMMENT 'FK a jobs_documentacion (template Jinja2 usado)',
  `tipo_resultado` varchar(100) NOT NULL COMMENT 'Tipo: metricas_entrenamiento, informe_generado, evaluacion_modelo, etc.',
  `datos_resultado` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL COMMENT 'Datos flexibles en JSON' CHECK (json_valid(`datos_resultado`)),
  `path_fichero` varchar(500) DEFAULT NULL COMMENT 'Path al fichero de salida si aplica',
  `nombre_fichero` varchar(200) DEFAULT NULL COMMENT 'Nombre del fichero generado',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_jobs_result_job` (`id_job`),
  KEY `idx_jobs_result_tipo` (`tipo_resultado`),
  KEY `idx_jobs_result_doc` (`id_documentacion`),
  CONSTRAINT `fk_resultado_documentacion` FOREIGN KEY (`id_documentacion`) REFERENCES `jobs_documentacion` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_resultado_job` FOREIGN KEY (`id_job`) REFERENCES `jobs` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Resultados de ejecución de jobs (métricas, informes, evaluaciones)';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_salidas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_salidas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL COMMENT 'Clave interna (snake_case)',
  `nombre` varchar(100) NOT NULL COMMENT 'Nombre visible en UI',
  `descripcion` varchar(255) DEFAULT NULL COMMENT 'Descripción del tipo de salida',
  `campo_referencia` varchar(50) DEFAULT NULL COMMENT 'Campo clave de referencia (id_job, path_fichero, etc.)',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Tipo de salida activo/inactivo',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `clave` (`clave`),
  KEY `idx_jobs_salidas_clave` (`clave`),
  KEY `idx_jobs_salidas_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de tipos de salida que un job puede producir';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_templates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_templates` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(200) NOT NULL COMMENT 'Nombre de la plantilla',
  `descripcion` text DEFAULT NULL COMMENT 'Descripción detallada',
  `id_tipo` int(11) NOT NULL COMMENT 'FK a jobs_tipos',
  `es_programable` tinyint(1) DEFAULT 0 COMMENT 'Si los jobs de esta plantilla soportan programación',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Plantilla activa/inactiva',
  `id_estado_inicial` int(11) DEFAULT NULL COMMENT 'FK a jobs_estados (estado inicial por defecto)',
  `id_modelo` int(11) DEFAULT NULL COMMENT 'FK a jobs_modelos (modelo LLM por defecto)',
  `id_salida` int(11) DEFAULT NULL COMMENT 'FK a jobs_salidas (tipo de salida por defecto)',
  `acepta_entrada` tinyint(1) DEFAULT 0 COMMENT 'Si puede ser job hijo (recibe datos de padre)',
  `permite_hijos` tinyint(1) DEFAULT 0 COMMENT 'Si puede ser job padre (envía datos a hijos)',
  `configuracion_defecto` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Configuración por defecto flexible' CHECK (json_valid(`configuracion_defecto`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `fk_template_estado` (`id_estado_inicial`),
  KEY `fk_template_modelo` (`id_modelo`),
  KEY `fk_template_salida` (`id_salida`),
  KEY `idx_template_tipo` (`id_tipo`),
  KEY `idx_template_activo` (`activo`),
  CONSTRAINT `fk_template_estado` FOREIGN KEY (`id_estado_inicial`) REFERENCES `jobs_estados` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_template_modelo` FOREIGN KEY (`id_modelo`) REFERENCES `jobs_modelos` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_template_salida` FOREIGN KEY (`id_salida`) REFERENCES `jobs_salidas` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_template_tipo` FOREIGN KEY (`id_tipo`) REFERENCES `jobs_tipos` (`id`) ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Plantillas de jobs con valores por defecto heredables';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `jobs_tipos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs_tipos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL COMMENT 'Clave interna (snake_case)',
  `nombre` varchar(100) NOT NULL COMMENT 'Nombre visible en UI',
  `descripcion` varchar(255) DEFAULT NULL COMMENT 'Descripción del tipo',
  `pagina_backoffice` varchar(100) DEFAULT NULL COMMENT 'Página del backoffice donde se usa',
  `activo` tinyint(1) DEFAULT 1 COMMENT 'Tipo activo/inactivo',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `clave` (`clave`),
  KEY `idx_jobs_tipos_clave` (`clave`),
  KEY `idx_jobs_tipos_activo` (`activo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de tipos de job (uno por página del backoffice)';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `mensajes_conversacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `mensajes_conversacion` (
  `id_mensaje` int(11) NOT NULL AUTO_INCREMENT,
  `id_conversacion` int(11) NOT NULL,
  `id_usuario_emisor` int(11) NOT NULL COMMENT 'Usuario emisor (ref: myllm_core_db.users)',
  `tipo_emisor` enum('cliente','interno') NOT NULL,
  `id_ticket_referenciado` int(11) DEFAULT NULL COMMENT 'Ticket mencionado en este mensaje',
  `texto_mensaje` text NOT NULL,
  `fecha_envio` timestamp NOT NULL DEFAULT current_timestamp(),
  `leido_por_cliente` tinyint(1) DEFAULT 0 COMMENT 'Si el cliente leyó este mensaje',
  `leido_por_interno` tinyint(1) DEFAULT 0 COMMENT 'Si algún interno leyó este mensaje',
  `fecha_lectura_cliente` timestamp NULL DEFAULT NULL,
  `fecha_lectura_interno` timestamp NULL DEFAULT NULL,
  `editado` tinyint(1) DEFAULT 0,
  `fecha_edicion` timestamp NULL DEFAULT NULL,
  `editado_por` int(11) DEFAULT NULL COMMENT 'Usuario que editó (ref: myllm_core_db.users)',
  `mensaje_sistema` tinyint(1) DEFAULT 0 COMMENT 'Si es un mensaje automático del sistema',
  PRIMARY KEY (`id_mensaje`),
  KEY `idx_conversacion_fecha` (`id_conversacion`,`fecha_envio`),
  KEY `idx_no_leidos_cliente` (`id_conversacion`,`leido_por_cliente`,`tipo_emisor`),
  KEY `idx_no_leidos_interno` (`id_conversacion`,`leido_por_interno`,`tipo_emisor`),
  KEY `idx_ticket_ref` (`id_ticket_referenciado`),
  KEY `idx_usuario_emisor` (`id_usuario_emisor`),
  CONSTRAINT `mensajes_conversacion_ibfk_1` FOREIGN KEY (`id_conversacion`) REFERENCES `conversaciones` (`id_conversacion`) ON DELETE CASCADE,
  CONSTRAINT `mensajes_conversacion_ibfk_2` FOREIGN KEY (`id_ticket_referenciado`) REFERENCES `tickets` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Mensajes de las conversaciones';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER after_mensaje_insert
AFTER INSERT ON mensajes_conversacion
FOR EACH ROW
BEGIN
    
    UPDATE conversaciones
    SET
        ultimo_mensaje_texto = NEW.texto_mensaje,
        ultimo_mensaje_de = NEW.tipo_emisor,
        ultimo_mensaje_fecha = NEW.fecha_envio,
        total_mensajes = total_mensajes + 1,
        mensajes_sin_leer_cliente = CASE
            WHEN NEW.tipo_emisor = 'interno' THEN mensajes_sin_leer_cliente + 1
            ELSE mensajes_sin_leer_cliente
        END,
        mensajes_sin_leer_interno = CASE
            WHEN NEW.tipo_emisor = 'cliente' THEN mensajes_sin_leer_interno + 1
            ELSE mensajes_sin_leer_interno
        END
    WHERE id_conversacion = NEW.id_conversacion;

    
    IF NEW.id_ticket_referenciado IS NOT NULL THEN
        INSERT IGNORE INTO conversaciones_tickets_relacionados
            (id_conversacion, id_ticket, tipo_relacion, mencionado_por)
        VALUES
            (NEW.id_conversacion, NEW.id_ticket_referenciado, 'mencionado', NEW.id_usuario_emisor);
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER after_mensaje_leido_cliente
AFTER UPDATE ON mensajes_conversacion
FOR EACH ROW
BEGIN
    IF NEW.leido_por_cliente = TRUE AND OLD.leido_por_cliente = FALSE AND NEW.tipo_emisor = 'interno' THEN
        UPDATE conversaciones
        SET mensajes_sin_leer_cliente = GREATEST(0, mensajes_sin_leer_cliente - 1)
        WHERE id_conversacion = NEW.id_conversacion;
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER after_mensaje_leido_interno
AFTER UPDATE ON mensajes_conversacion
FOR EACH ROW
BEGIN
    IF NEW.leido_por_interno = TRUE AND OLD.leido_por_interno = FALSE AND NEW.tipo_emisor = 'cliente' THEN
        UPDATE conversaciones
        SET mensajes_sin_leer_interno = GREATEST(0, mensajes_sin_leer_interno - 1)
        WHERE id_conversacion = NEW.id_conversacion;
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
DROP TABLE IF EXISTS `participantes_conversacion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `participantes_conversacion` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_conversacion` int(11) NOT NULL,
  `id_usuario` int(11) NOT NULL COMMENT 'Usuario participante (ref: myllm_core_db.users)',
  `tipo_participante` enum('cliente','interno') NOT NULL,
  `fecha_union` timestamp NOT NULL DEFAULT current_timestamp() COMMENT 'Cuándo se unió a la conversación',
  `activo` tinyint(1) DEFAULT 1,
  `ultimo_acceso` timestamp NULL DEFAULT NULL COMMENT 'Última vez que accedió a la conversación',
  `notificaciones_activadas` tinyint(1) DEFAULT 1 COMMENT 'Si recibe notificaciones',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_participante` (`id_conversacion`,`id_usuario`),
  KEY `idx_usuario_tipo` (`id_usuario`,`tipo_participante`,`activo`),
  KEY `idx_conversacion` (`id_conversacion`,`activo`),
  CONSTRAINT `participantes_conversacion_ibfk_1` FOREIGN KEY (`id_conversacion`) REFERENCES `conversaciones` (`id_conversacion`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Participantes de cada conversación';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `prompts_contexto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `prompts_contexto` (
  `id_prompt` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `prompt` mediumtext NOT NULL,
  `active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` int(11) DEFAULT NULL,
  `updated_by` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_prompt`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_active` (`active`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `prompts_identidades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `prompts_identidades` (
  `id_prompt` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `prompt` mediumtext NOT NULL,
  `active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` int(11) DEFAULT NULL,
  `updated_by` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_prompt`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_active` (`active`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `prompts_modalidad`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `prompts_modalidad` (
  `id_prompt` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `prompt` mediumtext NOT NULL,
  `active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` int(11) DEFAULT NULL,
  `updated_by` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_prompt`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_active` (`active`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `prompts_solicitudes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `prompts_solicitudes` (
  `id_prompt` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `prompt` mediumtext NOT NULL,
  `active` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` int(11) DEFAULT NULL,
  `updated_by` int(11) DEFAULT NULL,
  PRIMARY KEY (`id_prompt`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_active` (`active`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `proyecto_flujo_historico`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `proyecto_flujo_historico` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `id_proyecto` int(11) NOT NULL COMMENT 'FK a proyectos.id',
  `id_organizacion` int(11) NOT NULL COMMENT 'FK a organizaciones (desnormalizado para consultas rápidas)',
  `id_flujo_anterior` int(11) DEFAULT NULL COMMENT 'FK a flujos.id_flujo (NULL si es el primer estado)',
  `id_flujo_nuevo` int(11) NOT NULL COMMENT 'FK a flujos.id_flujo',
  `fecha_cambio` timestamp NOT NULL DEFAULT current_timestamp() COMMENT 'Momento del cambio',
  `id_usuario_cambio` int(11) DEFAULT NULL COMMENT 'FK a users.user_id (quien realizó el cambio)',
  `motivo_cambio` varchar(500) DEFAULT NULL COMMENT 'Motivo o comentario del cambio (opcional)',
  `tiempo_en_paso_anterior_segundos` bigint(20) DEFAULT NULL COMMENT 'Segundos que estuvo en el paso anterior',
  `ip_origen` varchar(45) DEFAULT NULL COMMENT 'IP desde donde se realizó el cambio',
  `app_origen` varchar(50) DEFAULT NULL COMMENT 'Aplicación origen (frontend, backoffice, api)',
  PRIMARY KEY (`id`),
  KEY `idx_historico_proyecto` (`id_proyecto`),
  KEY `idx_historico_organizacion` (`id_organizacion`),
  KEY `idx_historico_fecha` (`fecha_cambio`),
  KEY `idx_historico_flujo_nuevo` (`id_flujo_nuevo`),
  KEY `idx_historico_usuario` (`id_usuario_cambio`),
  KEY `fk_historico_flujo_anterior` (`id_flujo_anterior`),
  CONSTRAINT `fk_historico_flujo_anterior` FOREIGN KEY (`id_flujo_anterior`) REFERENCES `flujos` (`id_flujo`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `fk_historico_flujo_nuevo` FOREIGN KEY (`id_flujo_nuevo`) REFERENCES `flujos` (`id_flujo`) ON UPDATE CASCADE,
  CONSTRAINT `fk_historico_proyecto` FOREIGN KEY (`id_proyecto`) REFERENCES `proyectos` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Auditoría de cambios de flujo en proyectos';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `proyectos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `proyectos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `nombre` varchar(255) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `creado_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `actualizado_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `id_organizacion` int(11) NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 1,
  `id_flujo` int(11) DEFAULT 1 COMMENT 'Paso actual del proyecto en el flujo de trabajo',
  `existe` tinyint(1) NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `idx_proyectos_organizacion` (`id_organizacion`),
  KEY `idx_proyectos_flujo` (`id_flujo`),
  CONSTRAINT `fk_proyectos_flujo` FOREIGN KEY (`id_flujo`) REFERENCES `flujos` (`id_flujo`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER tr_proyecto_flujo_inicial
AFTER INSERT ON proyectos
FOR EACH ROW
BEGIN
    DECLARE v_id_usuario INT DEFAULT NULL;
    DECLARE v_ip_origen VARCHAR(45) DEFAULT NULL;
    DECLARE v_app_origen VARCHAR(50) DEFAULT NULL;
    DECLARE v_sesion_id VARCHAR(100);
    
    
    IF NEW.id_flujo IS NOT NULL THEN
        
        
        SET v_sesion_id = CAST(CONNECTION_ID() AS CHAR);
        
        SELECT id_usuario, ip_origen, app_origen
        INTO v_id_usuario, v_ip_origen, v_app_origen
        FROM sesion_contexto
        WHERE id_sesion = v_sesion_id
        LIMIT 1;
        
        
        INSERT INTO proyecto_flujo_historico (
            id_proyecto,
            id_organizacion,
            id_flujo_anterior,
            id_flujo_nuevo,
            fecha_cambio,
            id_usuario_cambio,
            motivo_cambio,
            tiempo_en_paso_anterior_segundos,
            ip_origen,
            app_origen
        ) VALUES (
            NEW.id,
            NEW.id_organizacion,
            NULL,  
            NEW.id_flujo,
            NOW(),
            v_id_usuario,
            'Creación del proyecto',
            NULL,
            v_ip_origen,
            v_app_origen
        );
        
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8mb4 */ ;
/*!50003 SET character_set_results = utf8mb4 */ ;
/*!50003 SET collation_connection  = utf8mb4_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER tr_proyecto_flujo_cambio
AFTER UPDATE ON proyectos
FOR EACH ROW
BEGIN
    DECLARE v_id_usuario INT DEFAULT NULL;
    DECLARE v_ip_origen VARCHAR(45) DEFAULT NULL;
    DECLARE v_app_origen VARCHAR(50) DEFAULT NULL;
    DECLARE v_motivo VARCHAR(500) DEFAULT NULL;
    DECLARE v_tiempo_anterior BIGINT DEFAULT NULL;
    DECLARE v_fecha_ultimo_cambio TIMESTAMP DEFAULT NULL;
    DECLARE v_sesion_id VARCHAR(100);
    
    
    IF (OLD.id_flujo IS NULL AND NEW.id_flujo IS NOT NULL) 
       OR (OLD.id_flujo IS NOT NULL AND NEW.id_flujo IS NULL)
       OR (OLD.id_flujo <> NEW.id_flujo) THEN
        
        
        SET v_sesion_id = CAST(CONNECTION_ID() AS CHAR);
        
        SELECT id_usuario, ip_origen, app_origen, motivo_cambio
        INTO v_id_usuario, v_ip_origen, v_app_origen, v_motivo
        FROM sesion_contexto
        WHERE id_sesion = v_sesion_id
        LIMIT 1;
        
        
        SELECT fecha_cambio INTO v_fecha_ultimo_cambio
        FROM proyecto_flujo_historico
        WHERE id_proyecto = OLD.id
        ORDER BY fecha_cambio DESC
        LIMIT 1;
        
        IF v_fecha_ultimo_cambio IS NOT NULL THEN
            SET v_tiempo_anterior = TIMESTAMPDIFF(SECOND, v_fecha_ultimo_cambio, NOW());
        END IF;
        
        
        INSERT INTO proyecto_flujo_historico (
            id_proyecto,
            id_organizacion,
            id_flujo_anterior,
            id_flujo_nuevo,
            fecha_cambio,
            id_usuario_cambio,
            motivo_cambio,
            tiempo_en_paso_anterior_segundos,
            ip_origen,
            app_origen
        ) VALUES (
            NEW.id,
            NEW.id_organizacion,
            OLD.id_flujo,
            NEW.id_flujo,
            NOW(),
            v_id_usuario,
            v_motivo,
            v_tiempo_anterior,
            v_ip_origen,
            v_app_origen
        );
        
    END IF;
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
DROP TABLE IF EXISTS `proyectos_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `proyectos_roles` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_usuario` int(11) NOT NULL,
  `id_organizacion` int(11) NOT NULL,
  `id_rol` int(11) NOT NULL,
  `active` tinyint(1) DEFAULT 0,
  `id_proyecto` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `proyectos_roles_base`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `proyectos_roles_base` (
  `id` int(11) NOT NULL COMMENT 'ID del rol (0=Sin asignar, 3=Editor, 4=Lector, 5=Auditor)',
  `nombre_rol` varchar(50) NOT NULL COMMENT 'Nombre visible del rol',
  `descripcion` varchar(255) DEFAULT NULL COMMENT 'Descripción del rol y sus permisos',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp() COMMENT 'Fecha de creación',
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Última actualización',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo maestro de roles para asignar a usuarios en proyectos';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `proyectos_tecnologia`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `proyectos_tecnologia` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_proyecto` int(11) NOT NULL,
  `id_tecnologia` int(11) NOT NULL,
  `coste_base` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_proyecto` (`id_proyecto`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `sesion_contexto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `sesion_contexto` (
  `id_sesion` varchar(100) NOT NULL COMMENT 'CONNECTION_ID() o session_token',
  `id_usuario` int(11) DEFAULT NULL COMMENT 'Usuario que está ejecutando la operación',
  `ip_origen` varchar(45) DEFAULT NULL COMMENT 'IP del cliente',
  `app_origen` varchar(50) DEFAULT NULL COMMENT 'frontend, backoffice, api, etc.',
  `motivo_cambio` varchar(500) DEFAULT NULL COMMENT 'Motivo del cambio (si aplica)',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id_sesion`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Contexto de sesión para triggers (temporal por conexión)';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `subfases_autonomas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `subfases_autonomas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `phase_key` varchar(10) NOT NULL COMMENT 'Clave de fase (6, 7, 8, 9)',
  `phase_name` varchar(100) NOT NULL COMMENT 'Nombre de la fase',
  `subfase_key` varchar(10) NOT NULL COMMENT 'Clave subfase (6.1, 6.2, ..., 9.5)',
  `subfase_name` varchar(200) NOT NULL COMMENT 'Nombre descriptivo de la subfase',
  `subfase_order` int(11) NOT NULL COMMENT 'Orden de ejecución (17-36)',
  `estimated_duration_seconds` int(11) DEFAULT NULL COMMENT 'Duración estimada en segundos',
  `description` text DEFAULT NULL COMMENT 'Descripción detallada de lo que hace la subfase',
  PRIMARY KEY (`id`),
  UNIQUE KEY `subfase_key` (`subfase_key`),
  UNIQUE KEY `idx_subfase_key` (`subfase_key`),
  KEY `idx_phase_key` (`phase_key`),
  KEY `idx_subfase_order` (`subfase_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de subfases para entrenamiento autónomo (fases 6-9)';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `tecnologia`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tecnologia` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `descripcion` mediumtext NOT NULL,
  `active` tinyint(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `tecnologia_id_IDX` (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `ticket_interacciones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `ticket_interacciones` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `ticket_id` int(11) NOT NULL,
  `autor_consulta_id` int(11) NOT NULL,
  `autor_respuesta_id` int(11) DEFAULT NULL,
  `consulta` mediumtext NOT NULL,
  `respuesta` mediumtext DEFAULT NULL,
  `fecha_consulta` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_respuesta` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ticket_id` (`ticket_id`),
  CONSTRAINT `fk_ticket_rel` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `tickets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tickets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `titulo` varchar(200) NOT NULL,
  `cliente_id` int(11) NOT NULL,
  `id_proyecto` int(11) DEFAULT NULL,
  `id_organizacion` int(11) NOT NULL,
  `estado` enum('abierto','en_espera','resuelto','cerrado') DEFAULT 'abierto',
  `prioridad` enum('baja','media','alta','urgente') DEFAULT 'media',
  `fecha_creacion` timestamp NOT NULL DEFAULT current_timestamp(),
  `fecha_actualizacion` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `cliente_id` (`cliente_id`),
  KEY `id_organizacion` (`id_organizacion`),
  KEY `estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `tipos_cambio`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tipos_cambio` (
  `id_tipo_cambio` int(11) NOT NULL AUTO_INCREMENT,
  `clave` varchar(50) NOT NULL COMMENT 'Identificador interno',
  `nombre` varchar(100) NOT NULL COMMENT 'Nombre visible',
  `descripcion_plantilla` varchar(255) NOT NULL COMMENT 'Plantilla de descripción',
  `aplica_a` varchar(50) NOT NULL DEFAULT 'proyecto' COMMENT 'Entidad afectada: proyecto, version, usuario',
  `activo` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`id_tipo_cambio`),
  UNIQUE KEY `clave` (`clave`),
  KEY `idx_tipos_cambio_clave` (`clave`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Catálogo de tipos de cambio para auditoría';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `v_conversaciones_activas`;
/*!50001 DROP VIEW IF EXISTS `v_conversaciones_activas`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_conversaciones_activas` AS SELECT
 1 AS `id_conversacion`,
  1 AS `asunto`,
  1 AS `estado`,
  1 AS `prioridad`,
  1 AS `id_organizacion`,
  1 AS `id_usuario_cliente`,
  1 AS `ticket_titulo`,
  1 AS `ticket_estado`,
  1 AS `fecha_creacion`,
  1 AS `fecha_ultima_actualizacion`,
  1 AS `ultimo_mensaje_texto`,
  1 AS `ultimo_mensaje_de`,
  1 AS `mensajes_sin_leer_interno`,
  1 AS `total_mensajes`,
  1 AS `usuarios_internos_ids` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `version_states`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `version_states` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT 'ID autoincremental',
  `id_organizacion` int(11) NOT NULL COMMENT 'FK a tabla organizaciones (no enforced)',
  `id_proyecto` int(11) NOT NULL COMMENT 'FK a tabla proyectos',
  `id_version` int(11) NOT NULL COMMENT 'Número de versión (no string)',
  `state` enum('Abierta','Bloqueada','Entrenar','Final') NOT NULL DEFAULT 'Abierta',
  `protected` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Si TRUE, no se puede editar',
  `size_bytes` bigint(20) DEFAULT 0 COMMENT 'Tamaño total de la versión en bytes',
  `final_c` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Cliente solicitó entrenamiento',
  `final_i` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Interno confirmó preparación',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp() COMMENT 'Cuándo se creó el registro',
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Última actualización',
  `updated_by_user_id` int(11) DEFAULT NULL COMMENT 'Usuario que hizo el último cambio',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_version` (`id_proyecto`,`id_version`) COMMENT 'Una versión única por proyecto',
  KEY `idx_org_prj` (`id_organizacion`,`id_proyecto`),
  KEY `idx_state` (`state`),
  KEY `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Estados y configuraciones de versiones de proyectos';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `versiones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `versiones` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_proyecto` int(11) NOT NULL,
  `id_version` int(11) NOT NULL,
  `fecha_lanzamiento` date NOT NULL,
  `descripcion` text DEFAULT NULL,
  `archivo_bloqueo` blob DEFAULT NULL,
  `creado_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `actualizado_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `id_organizacion` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_versiones_proyecto_version` (`id_proyecto`,`id_version`),
  KEY `idx_versiones_org` (`id_organizacion`),
  CONSTRAINT `fk_versiones_proyecto` FOREIGN KEY (`id_proyecto`) REFERENCES `proyectos` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!50003 SET @saved_cs_client      = @@character_set_client */ ;
/*!50003 SET @saved_cs_results     = @@character_set_results */ ;
/*!50003 SET @saved_col_connection = @@collation_connection */ ;
/*!50003 SET character_set_client  = utf8 */ ;
/*!50003 SET character_set_results = utf8 */ ;
/*!50003 SET collation_connection  = utf8_general_ci */ ;
/*!50003 SET @saved_sql_mode       = @@sql_mode */ ;
/*!50003 SET sql_mode              = 'STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION' */ ;
DELIMITER ;;
/*!50003 CREATE*/ /*!50017 DEFINER=`myllm_admin`@`localhost`*/ /*!50003 TRIGGER trg_versiones_after_insert
AFTER INSERT ON versiones
FOR EACH ROW
BEGIN
    INSERT INTO estado_version (
        id_organizacion,
        id_proyecto,
        id_version,
        state,
        state_internal,
        final_c,
        final_i,
        protected,
        size,
        created_at,
        updated_at
    ) VALUES (
        NEW.id_organizacion,
        NEW.id_proyecto,
        NEW.id_version,
        'Abierta',                   
        'propuesta_cliente',
        0,
        0,
        0,
        0,
        NOW(),
        NOW()
    );
END */;;
DELIMITER ;
/*!50003 SET sql_mode              = @saved_sql_mode */ ;
/*!50003 SET character_set_client  = @saved_cs_client */ ;
/*!50003 SET character_set_results = @saved_cs_results */ ;
/*!50003 SET collation_connection  = @saved_col_connection */ ;
DROP TABLE IF EXISTS `view_comparativa_consecutivos`;
/*!50001 DROP VIEW IF EXISTS `view_comparativa_consecutivos`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_comparativa_consecutivos` AS SELECT
 1 AS `id_organizacion`,
  1 AS `id_proyecto`,
  1 AS `id_version`,
  1 AS `secuencia_actual`,
  1 AS `secuencia_anterior`,
  1 AS `score_actual`,
  1 AS `score_anterior`,
  1 AS `mejora_real_pct`,
  1 AS `mejora_esperada_pct`,
  1 AS `desviacion_pct`,
  1 AS `rag_precision_actual`,
  1 AS `rag_precision_anterior`,
  1 AS `relevance_actual`,
  1 AS `relevance_anterior`,
  1 AS `perplexity_actual`,
  1 AS `perplexity_anterior`,
  1 AS `cambio_lr`,
  1 AS `cambio_batch`,
  1 AS `cambio_epochs`,
  1 AS `fecha_analisis_actual`,
  1 AS `fecha_analisis_anterior` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_entrenamientos_completo`;
/*!50001 DROP VIEW IF EXISTS `view_entrenamientos_completo`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_entrenamientos_completo` AS SELECT
 1 AS `id`,
  1 AS `id_organizacion`,
  1 AS `id_proyecto`,
  1 AS `id_version`,
  1 AS `pat_version`,
  1 AS `entrenamiento_inicial`,
  1 AS `reentrenamiento`,
  1 AS `numero_secuencia`,
  1 AS `fase_actual`,
  1 AS `estado`,
  1 AS `collection_name`,
  1 AS `modelo_path`,
  1 AS `error_mensaje`,
  1 AS `fecha_inicio`,
  1 AS `fecha_fin`,
  1 AS `created_at`,
  1 AS `updated_at`,
  1 AS `params_nombre`,
  1 AS `learning_rate`,
  1 AS `batch_size`,
  1 AS `epochs`,
  1 AS `embedding_dimension`,
  1 AS `sequence_length`,
  1 AS `hidden_units`,
  1 AS `dropout_rate`,
  1 AS `chunk_size`,
  1 AS `chunk_overlap`,
  1 AS `distance_metric`,
  1 AS `top_k`,
  1 AS `temperature`,
  1 AS `max_tokens`,
  1 AS `loss_function`,
  1 AS `optimizer` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_entrenamientos_detalle`;
/*!50001 DROP VIEW IF EXISTS `view_entrenamientos_detalle`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_entrenamientos_detalle` AS SELECT
 1 AS `id`,
  1 AS `id_organizacion`,
  1 AS `organization_name`,
  1 AS `id_proyecto`,
  1 AS `proyecto_nombre`,
  1 AS `id_version`,
  1 AS `pat_version`,
  1 AS `entrenamiento_inicial`,
  1 AS `reentrenamiento`,
  1 AS `numero_secuencia`,
  1 AS `fase_actual`,
  1 AS `estado`,
  1 AS `collection_name`,
  1 AS `modelo_path`,
  1 AS `error_mensaje`,
  1 AS `id_job_entrenamientos`,
  1 AS `params_nombre`,
  1 AS `learning_rate`,
  1 AS `batch_size`,
  1 AS `epochs`,
  1 AS `embedding_dimension`,
  1 AS `chunk_size`,
  1 AS `chunk_overlap`,
  1 AS `fecha_inicio`,
  1 AS `fecha_fin`,
  1 AS `created_at`,
  1 AS `updated_at` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_estado_version_completo`;
/*!50001 DROP VIEW IF EXISTS `view_estado_version_completo`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_estado_version_completo` AS SELECT
 1 AS `id`,
  1 AS `id_organizacion`,
  1 AS `id_proyecto`,
  1 AS `proyecto_nombre`,
  1 AS `id_version`,
  1 AS `state`,
  1 AS `state_internal`,
  1 AS `protected`,
  1 AS `size`,
  1 AS `propuesta_cliente`,
  1 AS `revision_interna`,
  1 AS `propuesta_mejoras`,
  1 AS `aceptacion_cliente`,
  1 AS `aceptacion_interna`,
  1 AS `entrenamiento_inicial_solicitado`,
  1 AS `entrenamiento_inicial_completado`,
  1 AS `entrenamiento_inicial_fecha`,
  1 AS `evaluacion_entrenamiento`,
  1 AS `reentrenamiento`,
  1 AS `optimizacion`,
  1 AS `control_calidad_aprobado`,
  1 AS `generacion_llm_solicitada`,
  1 AS `generacion_llm_completada`,
  1 AS `generacion_llm_fecha`,
  1 AS `ruta_fichero_modelo`,
  1 AS `notificacion_descarga_enviada`,
  1 AS `notificacion_descarga_fecha`,
  1 AS `created_at`,
  1 AS `updated_at`,
  1 AS `updated_by` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_evolucion_modelos`;
/*!50001 DROP VIEW IF EXISTS `view_evolucion_modelos`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_evolucion_modelos` AS SELECT
 1 AS `id_organizacion`,
  1 AS `id_proyecto`,
  1 AS `id_version`,
  1 AS `numero_secuencia`,
  1 AS `entrenamiento_id`,
  1 AS `entrenamiento_estado`,
  1 AS `fecha_entrenamiento`,
  1 AS `learning_rate`,
  1 AS `batch_size`,
  1 AS `epochs`,
  1 AS `dropout_rate`,
  1 AS `chunk_size`,
  1 AS `temperature`,
  1 AS `overall_quality_score`,
  1 AS `improvement_vs_previous_pct`,
  1 AS `rag_precision`,
  1 AS `rag_recall`,
  1 AS `rag_f1_score`,
  1 AS `response_relevance`,
  1 AS `response_coherence`,
  1 AS `bleu_score`,
  1 AS `perplexity`,
  1 AS `factual_accuracy`,
  1 AS `hallucination_rate`,
  1 AS `avg_inference_time_ms`,
  1 AS `tiene_sugerencias`,
  1 AS `sugerencias_confianza`,
  1 AS `sugerencias_mejora_esperada`,
  1 AS `fecha_analisis`,
  1 AS `created_at` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_evoluciones_entrenamientos`;
/*!50001 DROP VIEW IF EXISTS `view_evoluciones_entrenamientos`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_evoluciones_entrenamientos` AS SELECT
 1 AS `id`,
  1 AS `id_entrenamiento`,
  1 AS `id_organizacion`,
  1 AS `organization_name`,
  1 AS `id_proyecto`,
  1 AS `proyecto_nombre`,
  1 AS `id_version`,
  1 AS `numero_secuencia`,
  1 AS `phase_key`,
  1 AS `subfase_key`,
  1 AS `subfase_name`,
  1 AS `status`,
  1 AS `fecha_inicio`,
  1 AS `fecha_fin`,
  1 AS `duracion_segundos`,
  1 AS `error_mensaje`,
  1 AS `created_at`,
  1 AS `updated_at` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_jobs_completo`;
/*!50001 DROP VIEW IF EXISTS `view_jobs_completo`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_jobs_completo` AS SELECT
 1 AS `id`,
  1 AS `nombre`,
  1 AS `descripcion`,
  1 AS `id_organizacion`,
  1 AS `id_proyecto`,
  1 AS `id_version`,
  1 AS `id_template`,
  1 AS `template_nombre`,
  1 AS `id_tipo`,
  1 AS `tipo_clave`,
  1 AS `tipo_nombre`,
  1 AS `id_estado`,
  1 AS `estado_clave`,
  1 AS `estado_nombre`,
  1 AS `estado_color`,
  1 AS `estado_es_final`,
  1 AS `id_modelo`,
  1 AS `modelo_nombre`,
  1 AS `id_salida`,
  1 AS `salida_clave`,
  1 AS `salida_nombre`,
  1 AS `programado_para`,
  1 AS `iniciado_en`,
  1 AS `completado_en`,
  1 AS `error`,
  1 AS `id_job_padre`,
  1 AS `referencia_salida`,
  1 AS `configuracion`,
  1 AS `created_at`,
  1 AS `updated_at` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_jobs_templates`;
/*!50001 DROP VIEW IF EXISTS `view_jobs_templates`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_jobs_templates` AS SELECT
 1 AS `id`,
  1 AS `nombre`,
  1 AS `descripcion`,
  1 AS `id_tipo`,
  1 AS `tipo_clave`,
  1 AS `tipo_nombre`,
  1 AS `pagina_backoffice`,
  1 AS `es_programable`,
  1 AS `activo`,
  1 AS `id_estado_inicial`,
  1 AS `estado_inicial_clave`,
  1 AS `estado_inicial_nombre`,
  1 AS `id_modelo`,
  1 AS `modelo_nombre`,
  1 AS `id_salida`,
  1 AS `salida_clave`,
  1 AS `salida_nombre`,
  1 AS `acepta_entrada`,
  1 AS `permite_hijos`,
  1 AS `configuracion_defecto`,
  1 AS `created_at`,
  1 AS `updated_at` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_parametros_comparativa`;
/*!50001 DROP VIEW IF EXISTS `view_parametros_comparativa`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_parametros_comparativa` AS SELECT
 1 AS `entrenamiento_id`,
  1 AS `numero_secuencia`,
  1 AS `entrenamiento_estado`,
  1 AS `params_originales_id`,
  1 AS `params_originales_nombre`,
  1 AS `sugerencias_id`,
  1 AS `nombre_sugerencia`,
  1 AS `razon_sugerencia`,
  1 AS `confianza_score`,
  1 AS `mejora_esperada_pct`,
  1 AS `aplicado`,
  1 AS `loss_final`,
  1 AS `accuracy_validacion`,
  1 AS `retrieval_precision`,
  1 AS `overfitting_detectado`,
  1 AS `convergencia_lenta`,
  1 AS `lr_original`,
  1 AS `lr_sugerido`,
  1 AS `lr_cambio`,
  1 AS `batch_original`,
  1 AS `batch_sugerido`,
  1 AS `batch_cambio`,
  1 AS `epochs_original`,
  1 AS `epochs_sugerido`,
  1 AS `epochs_cambio`,
  1 AS `dropout_original`,
  1 AS `dropout_sugerido`,
  1 AS `dropout_cambio`,
  1 AS `chunk_size_original`,
  1 AS `chunk_size_sugerido`,
  1 AS `chunk_size_cambio`,
  1 AS `temp_original`,
  1 AS `temp_sugerido`,
  1 AS `temp_cambio`,
  1 AS `created_at`,
  1 AS `sugerencias_fecha` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_proyectos_flujo`;
/*!50001 DROP VIEW IF EXISTS `view_proyectos_flujo`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_proyectos_flujo` AS SELECT
 1 AS `proyecto_id`,
  1 AS `proyecto_nombre`,
  1 AS `id_organizacion`,
  1 AS `id_flujo`,
  1 AS `flujo_clave`,
  1 AS `flujo_nombre`,
  1 AS `flujo_descripcion`,
  1 AS `flujo_emoji`,
  1 AS `flujo_color`,
  1 AS `flujo_orden`,
  1 AS `es_bloque_inicio`,
  1 AS `es_bloque_iteracion` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_proyectos_roles_base`;
/*!50001 DROP VIEW IF EXISTS `view_proyectos_roles_base`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_proyectos_roles_base` AS SELECT
 1 AS `id`,
  1 AS `nombre_rol`,
  1 AS `descripcion` */;
SET character_set_client = @saved_cs_client;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
