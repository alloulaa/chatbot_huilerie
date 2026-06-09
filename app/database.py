import logging
import os

import mysql.connector
from mysql.connector.connection import MySQLConnection


logger = logging.getLogger(__name__)


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "gestionhuilerie"),
}


def get_db_connection() -> MySQLConnection:
    logger.debug("Opening MySQL connection to %s", DB_CONFIG["database"])
    return mysql.connector.connect(**DB_CONFIG)
