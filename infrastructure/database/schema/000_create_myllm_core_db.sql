-- ============================================================================
-- 000_create_myllm_core_db.sql
-- Schema canónico de myllm_core_db exportado desde PRE
-- Fuente: mysqldump --no-data --routines --triggers
-- Fecha de captura: 2026-02-24
-- Contiene: 14 tablas + 7 vistas
-- ============================================================================

CREATE DATABASE IF NOT EXISTS myllm_core_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE myllm_core_db;

 

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
DROP TABLE IF EXISTS `auth_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_logs` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `timestamp` timestamp NOT NULL DEFAULT current_timestamp(),
  `user_name` varchar(255) DEFAULT NULL,
  `event` enum('login_success','login_failed','logout','password_change','otp_verification','token_refresh','permission_denied','login_attempt','login_blocked','otp_request') NOT NULL,
  `status` enum('success','failure','failed','blocked') NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `session_id` varchar(36) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`details`)),
  PRIMARY KEY (`id`),
  KEY `idx_timestamp` (`timestamp`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_event` (`event`),
  KEY `idx_status` (`status`),
  KEY `idx_ip_address` (`ip_address`),
  KEY `idx_session_id` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Authentication and security event logs';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `basic_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `basic_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `permission_name` varchar(255) NOT NULL,
  `permission_description` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `permission_name` (`permission_name`),
  KEY `idx_basic_permission_name` (`permission_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Basic permissions source (JSON mirror)';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `estado_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `estado_version` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_organizacion` int(11) NOT NULL,
  `id_proyecto` int(11) NOT NULL,
  `id_version` int(11) NOT NULL,
  `state` enum('Abierta','Bloqueada','Protegida','Final') NOT NULL DEFAULT 'Abierta',
  `protected` tinyint(1) NOT NULL DEFAULT 0,
  `size` bigint(20) unsigned NOT NULL DEFAULT 0 COMMENT 'Tamaño en bytes',
  `final_c` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Cliente solicita entrenamiento',
  `final_i` tinyint(1) NOT NULL DEFAULT 0 COMMENT 'Interno confirma entrenamiento',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_version` (`id_organizacion`,`id_proyecto`,`id_version`),
  KEY `idx_org_project` (`id_organizacion`,`id_proyecto`),
  CONSTRAINT `chk_state_protected` CHECK (`state` = 'Abierta' and `protected` = 0 and `final_c` = 0 and `final_i` = 0 or `state` = 'Bloqueada' and `protected` = 1 and `final_c` = 0 and `final_i` = 0 or `state` = 'Protegida' and `protected` = 1 and `final_c` = 1 and `final_i` = 0 or `state` = 'Final' and `protected` = 1 and `final_c` = 1 and `final_i` = 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `identity_type_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `identity_type_permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `identity_type_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_identity_permission` (`identity_type_id`,`permission_id`),
  UNIQUE KEY `uk_identity_type_id` (`identity_type_id`),
  UNIQUE KEY `uk_permission_id` (`permission_id`),
  KEY `idx_identity_type_id` (`identity_type_id`),
  KEY `idx_permission_id` (`permission_id`),
  CONSTRAINT `identity_type_permissions_ibfk_1` FOREIGN KEY (`identity_type_id`) REFERENCES `identity_types` (`identity_type_id`) ON DELETE CASCADE,
  CONSTRAINT `identity_type_permissions_ibfk_2` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Mapping between identity types and permissions';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `identity_types`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `identity_types` (
  `identity_type_id` int(11) NOT NULL AUTO_INCREMENT,
  `identity_type_name` varchar(255) NOT NULL,
  `identity_type_rol` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`identity_type_id`),
  KEY `idx_identity_type_name` (`identity_type_name`),
  KEY `idx_identity_type_rol` (`identity_type_rol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Different types of identities or roles in the system';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `low_level_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `low_level_permissions` (
  `id_permissions` int(11) NOT NULL,
  `folder_create` tinyint(1) DEFAULT 0,
  `folder_delete` tinyint(1) DEFAULT 0,
  `folder_rename` tinyint(1) DEFAULT 0,
  `folder_read` tinyint(1) DEFAULT 0,
  `file_create` tinyint(1) DEFAULT 0,
  `file_read` tinyint(1) DEFAULT 0,
  `file_update` tinyint(1) DEFAULT 0,
  `file_delete` tinyint(1) DEFAULT 0,
  `project_create` tinyint(1) DEFAULT 0,
  `project_read` tinyint(1) DEFAULT 0,
  `project_update` tinyint(1) DEFAULT 0,
  `project_delete` tinyint(1) DEFAULT 0,
  `version_create` tinyint(1) DEFAULT 0,
  `version_read` tinyint(1) DEFAULT 0,
  `version_update` tinyint(1) DEFAULT 0,
  `version_delete` tinyint(1) DEFAULT 0,
  `training_create` tinyint(1) DEFAULT 0,
  `training_read` tinyint(1) DEFAULT 0,
  `training_update` tinyint(1) DEFAULT 0,
  `training_delete` tinyint(1) DEFAULT 0,
  `training_start` tinyint(1) DEFAULT 0,
  `training_stop` tinyint(1) DEFAULT 0,
  `parameters_create` tinyint(1) DEFAULT 0,
  `parameters_read` tinyint(1) DEFAULT 0,
  `parameters_update` tinyint(1) DEFAULT 0,
  `parameters_delete` tinyint(1) DEFAULT 0,
  `notifications_create` tinyint(1) DEFAULT 0,
  `notifications_read` tinyint(1) DEFAULT 0,
  `notifications_update` tinyint(1) DEFAULT 0,
  `notifications_delete` tinyint(1) DEFAULT 0,
  `user_create` tinyint(1) DEFAULT 0,
  `user_read` tinyint(1) DEFAULT 0,
  `user_update` tinyint(1) DEFAULT 0,
  `user_delete` tinyint(1) DEFAULT 0,
  `user_enable` tinyint(1) DEFAULT 0,
  `user_disable` tinyint(1) DEFAULT 0,
  `folder_list` tinyint(1) DEFAULT 0,
  `file_list` tinyint(1) DEFAULT 0,
  `project_list` tinyint(1) DEFAULT 0,
  `version_list` tinyint(1) DEFAULT 0,
  PRIMARY KEY (`id_permissions`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `organizations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `organizations` (
  `organization_id` int(11) NOT NULL AUTO_INCREMENT,
  `organization_name` varchar(255) NOT NULL,
  `organization_email` varchar(255) NOT NULL,
  `organization_tlf` varchar(20) DEFAULT NULL,
  `organization_address` text DEFAULT NULL,
  `organization_country` varchar(100) DEFAULT NULL,
  `organization_state` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `active` tinyint(1) DEFAULT 1,
  PRIMARY KEY (`organization_id`),
  KEY `idx_organization_name` (`organization_name`),
  KEY `idx_organization_email` (`organization_email`),
  KEY `idx_active` (`active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Organizations in the system';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `permissions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `permission_name` varchar(255) NOT NULL,
  `permission_description` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `permission_name` (`permission_name`),
  KEY `idx_permission_name` (`permission_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Basic permissions for the application';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `permissions_explorer`;
/*!50001 DROP VIEW IF EXISTS `permissions_explorer`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `permissions_explorer` AS SELECT
 1 AS `id_permissions`,
  1 AS `folder_create`,
  1 AS `folder_delete`,
  1 AS `folder_rename`,
  1 AS `folder_read`,
  1 AS `folder_list`,
  1 AS `file_create`,
  1 AS `file_read`,
  1 AS `file_update`,
  1 AS `file_delete`,
  1 AS `file_list`,
  1 AS `version_create`,
  1 AS `training_create` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `identity_type_id` int(11) NOT NULL,
  `identity_type_name` varchar(255) NOT NULL,
  `identity_type_rol` varchar(255) NOT NULL,
  `identity_type_group_permission` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`identity_type_id`),
  KEY `idx_roles_permission` (`identity_type_group_permission`),
  CONSTRAINT `roles_ibfk_1` FOREIGN KEY (`identity_type_group_permission`) REFERENCES `permissions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Roles source (JSON mirror)';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `sessions` (
  `session_id` varchar(36) NOT NULL,
  `user_id` int(11) NOT NULL,
  `organization_id` int(11) NOT NULL,
  `identity_type_id` int(11) NOT NULL,
  `access_token_jti` varchar(36) DEFAULT NULL,
  `session_token_jti` varchar(36) DEFAULT NULL,
  `status` enum('active','inactive','expired','revoked') DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `last_activity` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `expires_at` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  PRIMARY KEY (`session_id`),
  KEY `organization_id` (`organization_id`),
  KEY `identity_type_id` (`identity_type_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_status` (`status`),
  KEY `idx_expires_at` (`expires_at`),
  KEY `idx_created_at` (`created_at`),
  CONSTRAINT `sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `sessions_ibfk_2` FOREIGN KEY (`organization_id`) REFERENCES `organizations` (`organization_id`) ON DELETE CASCADE,
  CONSTRAINT `sessions_ibfk_3` FOREIGN KEY (`identity_type_id`) REFERENCES `identity_types` (`identity_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User session tracking';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_billing_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_billing_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `first_name` varchar(100) DEFAULT NULL,
  `sur_name` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `zip_code` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_names` (`first_name`,`sur_name`),
  CONSTRAINT `user_billing_info_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User billing information';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_contact_info`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_contact_info` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `first_name` varchar(100) DEFAULT NULL,
  `sur_name` varchar(100) DEFAULT NULL,
  `country` varchar(100) DEFAULT NULL,
  `state` varchar(100) DEFAULT NULL,
  `zip_code` varchar(20) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_names` (`first_name`,`sur_name`),
  CONSTRAINT `user_contact_info_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User contact information';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user_organization_management`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_organization_management` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `organization_id` int(11) NOT NULL,
  `identity_type_id` int(11) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by_user_id` int(11) DEFAULT NULL,
  `active` tinyint(1) DEFAULT 1,
  `project_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_org_role` (`user_id`,`organization_id`,`identity_type_id`),
  KEY `created_by_user_id` (`created_by_user_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_organization_id` (`organization_id`),
  KEY `idx_identity_type_id` (`identity_type_id`),
  KEY `idx_active` (`active`),
  CONSTRAINT `user_organization_management_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `user_organization_management_ibfk_2` FOREIGN KEY (`organization_id`) REFERENCES `organizations` (`organization_id`) ON DELETE CASCADE,
  CONSTRAINT `user_organization_management_ibfk_3` FOREIGN KEY (`identity_type_id`) REFERENCES `identity_types` (`identity_type_id`),
  CONSTRAINT `user_organization_management_ibfk_4` FOREIGN KEY (`created_by_user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User organization and role management';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `organization_id` int(11) NOT NULL,
  `identity_type_id` int(11) NOT NULL,
  `user_name` varchar(255) NOT NULL,
  `user_password` varchar(500) NOT NULL,
  `user_email` varchar(255) NOT NULL,
  `user_mobile` varchar(20) DEFAULT NULL,
  `user_otp` varchar(10) DEFAULT NULL,
  `active` tinyint(1) DEFAULT 1,
  `blocked` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `modified_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `[` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_name` (`user_name`),
  KEY `idx_user_name` (`user_name`),
  KEY `idx_user_email` (`user_email`),
  KEY `idx_organization_id` (`organization_id`),
  KEY `idx_identity_type_id` (`identity_type_id`),
  KEY `idx_active_blocked` (`active`,`blocked`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`organization_id`) REFERENCES `organizations` (`organization_id`),
  CONSTRAINT `users_ibfk_2` FOREIGN KEY (`identity_type_id`) REFERENCES `identity_types` (`identity_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='User accounts in the system';
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `v_active_sessions`;
/*!50001 DROP VIEW IF EXISTS `v_active_sessions`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_active_sessions` AS SELECT
 1 AS `session_id`,
  1 AS `user_id`,
  1 AS `user_name`,
  1 AS `user_email`,
  1 AS `organization_id`,
  1 AS `organization_name`,
  1 AS `status`,
  1 AS `created_at`,
  1 AS `last_activity`,
  1 AS `expires_at`,
  1 AS `ip_address`,
  1 AS `inactive_minutes` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `v_auth_events_summary`;
/*!50001 DROP VIEW IF EXISTS `v_auth_events_summary`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_auth_events_summary` AS SELECT
 1 AS `event_date`,
  1 AS `event`,
  1 AS `status`,
  1 AS `event_count` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `v_organization_user_stats`;
/*!50001 DROP VIEW IF EXISTS `v_organization_user_stats`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_organization_user_stats` AS SELECT
 1 AS `organization_id`,
  1 AS `organization_name`,
  1 AS `total_users`,
  1 AS `active_users`,
  1 AS `blocked_users`,
  1 AS `active_sessions` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `v_user_full_info`;
/*!50001 DROP VIEW IF EXISTS `v_user_full_info`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_user_full_info` AS SELECT
 1 AS `user_id`,
  1 AS `user_name`,
  1 AS `user_email`,
  1 AS `user_mobile`,
  1 AS `active`,
  1 AS `blocked`,
  1 AS `organization_id`,
  1 AS `organization_name`,
  1 AS `identity_type_id`,
  1 AS `identity_type_name`,
  1 AS `identity_type_rol`,
  1 AS `first_name`,
  1 AS `sur_name`,
  1 AS `country`,
  1 AS `state`,
  1 AS `created_at`,
  1 AS `modified_at` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `v_user_permissions`;
/*!50001 DROP VIEW IF EXISTS `v_user_permissions`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `v_user_permissions` AS SELECT
 1 AS `user_id`,
  1 AS `user_name`,
  1 AS `organization_id`,
  1 AS `identity_type_id`,
  1 AS `identity_type_name`,
  1 AS `permission_id`,
  1 AS `permission_name`,
  1 AS `permission_description` */;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `view_users_otp`;
/*!50001 DROP VIEW IF EXISTS `view_users_otp`*/;
SET @saved_cs_client     = @@character_set_client;
SET character_set_client = utf8mb4;
/*!50001 CREATE VIEW `view_users_otp` AS SELECT
 1 AS `user_id`,
  1 AS `user_name`,
  1 AS `user_otp` */;
SET character_set_client = @saved_cs_client;
/*!50001 DROP VIEW IF EXISTS `permissions_explorer`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = latin1 */;
/*!50001 SET character_set_results     = latin1 */;
/*!50001 SET collation_connection      = latin1_swedish_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `permissions_explorer` AS select `low_level_permissions`.`id_permissions` AS `id_permissions`,`low_level_permissions`.`folder_create` AS `folder_create`,`low_level_permissions`.`folder_delete` AS `folder_delete`,`low_level_permissions`.`folder_rename` AS `folder_rename`,`low_level_permissions`.`folder_read` AS `folder_read`,`low_level_permissions`.`folder_list` AS `folder_list`,`low_level_permissions`.`file_create` AS `file_create`,`low_level_permissions`.`file_read` AS `file_read`,`low_level_permissions`.`file_update` AS `file_update`,`low_level_permissions`.`file_delete` AS `file_delete`,`low_level_permissions`.`file_list` AS `file_list`,`low_level_permissions`.`version_create` AS `version_create`,`low_level_permissions`.`training_create` AS `training_create` from `low_level_permissions` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `v_active_sessions`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_active_sessions` AS select `s`.`session_id` AS `session_id`,`s`.`user_id` AS `user_id`,`u`.`user_name` AS `user_name`,`u`.`user_email` AS `user_email`,`s`.`organization_id` AS `organization_id`,`o`.`organization_name` AS `organization_name`,`s`.`status` AS `status`,`s`.`created_at` AS `created_at`,`s`.`last_activity` AS `last_activity`,`s`.`expires_at` AS `expires_at`,`s`.`ip_address` AS `ip_address`,timestampdiff(MINUTE,`s`.`last_activity`,current_timestamp()) AS `inactive_minutes` from ((`sessions` `s` left join `users` `u` on(`s`.`user_id` = `u`.`user_id`)) left join `organizations` `o` on(`s`.`organization_id` = `o`.`organization_id`)) where `s`.`status` = 'active' and `s`.`expires_at` > current_timestamp() */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `v_auth_events_summary`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_auth_events_summary` AS select cast(`auth_logs`.`timestamp` as date) AS `event_date`,`auth_logs`.`event` AS `event`,`auth_logs`.`status` AS `status`,count(0) AS `event_count` from `auth_logs` group by cast(`auth_logs`.`timestamp` as date),`auth_logs`.`event`,`auth_logs`.`status` order by cast(`auth_logs`.`timestamp` as date) desc,`auth_logs`.`event` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `v_organization_user_stats`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_organization_user_stats` AS select `o`.`organization_id` AS `organization_id`,`o`.`organization_name` AS `organization_name`,count(distinct `u`.`user_id`) AS `total_users`,sum(case when `u`.`active` = 1 then 1 else 0 end) AS `active_users`,sum(case when `u`.`blocked` = 1 then 1 else 0 end) AS `blocked_users`,count(distinct `s`.`session_id`) AS `active_sessions` from ((`organizations` `o` left join `users` `u` on(`o`.`organization_id` = `u`.`organization_id`)) left join `sessions` `s` on(`u`.`user_id` = `s`.`user_id` and `s`.`status` = 'active' and `s`.`expires_at` > current_timestamp())) group by `o`.`organization_id`,`o`.`organization_name` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `v_user_full_info`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_user_full_info` AS select `u`.`user_id` AS `user_id`,`u`.`user_name` AS `user_name`,`u`.`user_email` AS `user_email`,`u`.`user_mobile` AS `user_mobile`,`u`.`active` AS `active`,`u`.`blocked` AS `blocked`,`o`.`organization_id` AS `organization_id`,`o`.`organization_name` AS `organization_name`,`it`.`identity_type_id` AS `identity_type_id`,`it`.`identity_type_name` AS `identity_type_name`,`it`.`identity_type_rol` AS `identity_type_rol`,`uci`.`first_name` AS `first_name`,`uci`.`sur_name` AS `sur_name`,`uci`.`country` AS `country`,`uci`.`state` AS `state`,`u`.`created_at` AS `created_at`,`u`.`modified_at` AS `modified_at` from (((`users` `u` left join `organizations` `o` on(`u`.`organization_id` = `o`.`organization_id`)) left join `identity_types` `it` on(`u`.`identity_type_id` = `it`.`identity_type_id`)) left join `user_contact_info` `uci` on(`u`.`user_id` = `uci`.`user_id`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `v_user_permissions`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb4 */;
/*!50001 SET character_set_results     = utf8mb4 */;
/*!50001 SET collation_connection      = utf8mb4_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `v_user_permissions` AS select `u`.`user_id` AS `user_id`,`u`.`user_name` AS `user_name`,`u`.`organization_id` AS `organization_id`,`it`.`identity_type_id` AS `identity_type_id`,`it`.`identity_type_name` AS `identity_type_name`,`p`.`id` AS `permission_id`,`p`.`permission_name` AS `permission_name`,`p`.`permission_description` AS `permission_description` from (((`users` `u` left join `identity_types` `it` on(`u`.`identity_type_id` = `it`.`identity_type_id`)) left join `identity_type_permissions` `itp` on(`it`.`identity_type_id` = `itp`.`identity_type_id`)) left join `permissions` `p` on(`itp`.`permission_id` = `p`.`id`)) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `view_users_otp`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = latin1 */;
/*!50001 SET character_set_results     = latin1 */;
/*!50001 SET collation_connection      = latin1_swedish_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 DEFINER=`myllm_admin`@`localhost` SQL SECURITY DEFINER */
/*!50001 VIEW `view_users_otp` AS select `users`.`user_id` AS `user_id`,`users`.`user_name` AS `user_name`,`users`.`user_otp` AS `user_otp` from `users` order by `users`.`user_id` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

