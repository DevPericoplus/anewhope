"""
Database connection utilities for backend core.
"""

import mysql.connector
from mysql.connector import Error
import os
import logging

logger = logging.getLogger(__name__)

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', '3306')),
    'user': os.environ.get('DB_USER', 'myllm_writer'),
    'password': os.environ.get('DB_PASSWORD', 'Us3r@wr1t3rP@ss'),
    'database': os.environ.get('DB_NAME', 'myllm_projects_db'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': False,
}


def get_db_connection():
    """
    Create and return a database connection.

    Returns:
        mysql.connector.connection: Active database connection

    Raises:
        Error: If connection fails
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            logger.debug(f"Connected to database: {DB_CONFIG['database']}")
            return connection
        else:
            raise Error("Failed to connect to database")

    except Error as e:
        logger.error(f"Database connection error: {e}")
        raise
