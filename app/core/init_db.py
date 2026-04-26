import logging


logger = logging.getLogger(__name__)


def init_db() -> None:
    logger.info("SQLite initialization is disabled. Using MySQL schema from database gestionhuilerie.")
