"""Business rules that don't need the database (easy to unit test)."""
from datetime import date

from .schemas import ApplicationStatus

# A follow-up only matters while the application is still in progress.
ACTIVE_STATUSES = {ApplicationStatus.applied.value, ApplicationStatus.interview.value}


def is_follow_up_due(status: str, follow_up_date: date | None, today: date) -> bool:
    return follow_up_date is not None and follow_up_date <= today and status in ACTIVE_STATUSES
