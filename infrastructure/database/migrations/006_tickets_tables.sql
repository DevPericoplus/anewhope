-- =====================================================
-- Migración: 006_tickets_tables.sql
-- Descripción: Crea las tablas para el sistema de tickets de soporte
-- Base de datos: myllm_projects_db
-- =====================================================

USE myllm_projects_db;

-- Tabla principal de tickets
CREATE TABLE IF NOT EXISTS tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL,
    cliente_id INT NOT NULL,
    id_proyecto INT DEFAULT NULL,
    id_organizacion INT NOT NULL,
    estado ENUM('abierto', 'en_espera', 'resuelto', 'cerrado') DEFAULT 'abierto',
    prioridad ENUM('baja', 'media', 'alta', 'urgente') DEFAULT 'media',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX (cliente_id),
    INDEX (id_organizacion),
    INDEX (estado)
) ENGINE=InnoDB;

-- Tabla de interacciones (consultas y respuestas)
CREATE TABLE IF NOT EXISTS ticket_interacciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    autor_consulta_id INT NOT NULL,
    autor_respuesta_id INT DEFAULT NULL,
    consulta MEDIUMTEXT NOT NULL,
    respuesta MEDIUMTEXT DEFAULT NULL,
    fecha_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_respuesta TIMESTAMP NULL DEFAULT NULL,
    CONSTRAINT fk_ticket_rel FOREIGN KEY (ticket_id) 
        REFERENCES tickets(id) ON DELETE CASCADE,
    INDEX (ticket_id)
) ENGINE=InnoDB;

-- Permisos para myllm_writer (lectura y escritura)
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.tickets TO 'myllm_writer'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON myllm_projects_db.ticket_interacciones TO 'myllm_writer'@'localhost';

-- Permisos para myllm_reader (solo lectura)
GRANT SELECT ON myllm_projects_db.tickets TO 'myllm_reader'@'localhost';
GRANT SELECT ON myllm_projects_db.ticket_interacciones TO 'myllm_reader'@'localhost';

FLUSH PRIVILEGES;
