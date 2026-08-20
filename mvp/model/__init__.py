"""Desktop model: API-facing constants and local UI state.

The desktop does not open SQL Server. Persistence models live under
backend.mvc.models. Presenter.active_user is the logged-in session state.
"""

from mvp.model.api import API_BASE_URL, TIMEOUT_SECONDS

__all__ = ["API_BASE_URL", "TIMEOUT_SECONDS"]
