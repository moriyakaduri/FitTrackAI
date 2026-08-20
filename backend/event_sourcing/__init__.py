"""Event Sourcing locator for the append-only user activity log.

Implementation is unchanged:
- UserEvent entity: backend.mvc.models.entities
- append_user_event: backend.cqrs.commands
- dashboard projection: backend.cqrs.queries.get_nutrition_summary
"""

from backend.cqrs.commands import append_user_event
from backend.cqrs.queries import get_nutrition_summary
from backend.mvc.models.entities import UserEvent

__all__ = ["UserEvent", "append_user_event", "get_nutrition_summary"]
