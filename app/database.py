import logging

import mysql.connector
from mysql.connector.connection import MySQLConnection


logger = logging.getLogger(__name__)


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "gestionhuilerie",
}


def get_db_connection() -> MySQLConnection:
    logger.debug("Opening MySQL connection to %s", DB_CONFIG["database"])
    return mysql.connector.connect(**DB_CONFIG)
