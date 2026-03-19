import logging

from google.adk.sessions import InMemorySessionService

from app.config import settings

logger = logging.getLogger(__name__)

_session_service = None


async def init_session_service():
    """Initialize the ADK session service singleton.

    Uses DatabaseSessionService with asyncpg for PostgreSQL,
    falls back to InMemorySessionService for SQLite.
    """
    global _session_service

    adk_url = settings.adk_database_url
    if adk_url:
        from google.adk.sessions import DatabaseSessionService

        _session_service = DatabaseSessionService(db_url=adk_url)
        logger.info("ADK session service: DatabaseSessionService (PostgreSQL)")
    else:
        _session_service = InMemorySessionService()
        logger.info("ADK session service: InMemorySessionService (SQLite fallback)")

    return _session_service


def get_session_service():
    """Return the initialized session service singleton."""
    if _session_service is None:
        raise RuntimeError("Session service not initialized — call init_session_service() first")
    return _session_service


async def close_session_service():
    """Clean up the session service on shutdown."""
    global _session_service
    if _session_service is not None and hasattr(_session_service, "close"):
        await _session_service.close()
        logger.info("ADK session service closed")
    _session_service = None
