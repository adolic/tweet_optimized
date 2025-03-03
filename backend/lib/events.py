from datetime import datetime
from typing import Optional
from pydantic import BaseModel, IPvAnyAddress
from backend.lib.database import db_execute
import logging

logger = logging.getLogger(__name__)

class EventCreate(BaseModel):
    event_type: str
    library_version_id: int
    size_description: str
    ip: Optional[IPvAnyAddress] = None

def create_event(event: EventCreate) -> int:
    """Create a new event in the database."""
    try:
        query = """
            INSERT INTO events (event_type, library_version_id, size_description, ip)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """
        logger.info(f"Executing query with params: {event.event_type}, {event.library_version_id}, {event.size_description}, {event.ip}")
        res = db_execute(
            query,
            (event.event_type, event.library_version_id, event.size_description, str(event.ip) if event.ip else None)
        )
        if not res:
            raise ValueError("No ID returned from insert")
        # Just return the result since db_execute is already returning the ID
        return res
    except Exception as e:
        logger.error(f"Error creating event: {str(e)}", exc_info=True)
        raise